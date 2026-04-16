"""
Minecraft Omni-Builder v3.1 - PostgreSQL Backend & CRDT Sync Engine
Provides distributed state synchronization across multiple servers.
"""
import asyncio
import json
import hashlib
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
import logging

try:
    import asyncpg
except ImportError:
    asyncpg = None  # Fallback for testing without driver

logger = logging.getLogger(__name__)

@dataclass
class CRDTVector:
    """Lamport Timestamp + Server ID for conflict resolution"""
    server_id: str
    timestamp: int
    counter: int = 0

    def increment(self):
        self.counter += 1
        return self

    def __gt__(self, other: 'CRDTVector') -> bool:
        if self.timestamp != other.timestamp:
            return self.timestamp > other.timestamp
        if self.server_id != other.server_id:
            return self.server_id > other.server_id
        return self.counter > other.counter

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'CRDTVector':
        return cls(**data)

@dataclass
class BlockOperation:
    """Atomic block operation with CRDT metadata"""
    op_id: str
    block_type: str
    x: int
    y: int
    z: int
    properties: Dict[str, Any]
    operation: str  # 'PLACE', 'REMOVE', 'UPDATE'
    vector: CRDTVector
    checksum: str = ""

    def __post_init__(self):
        if not self.checksum:
            self.checksum = self._generate_checksum()

    def _generate_checksum(self) -> str:
        data = f"{self.op_id}:{self.block_type}:{self.x}:{self.y}:{self.z}:{self.operation}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def to_json(self) -> str:
        d = asdict(self)
        d['vector'] = self.vector.to_dict()
        return json.dumps(d)

    @classmethod
    def from_json(cls, json_str: str) -> 'BlockOperation':
        data = json.loads(json_str)
        data['vector'] = CRDTVector.from_dict(data['vector'])
        return cls(**data)

class PostgreSQLBackend:
    """Async PostgreSQL connection manager for Omni-Builder"""
    
    def __init__(self, connection_string: str):
        if asyncpg is None:
            raise ImportError("asyncpg library required. Install: pip install asyncpg")
        self.conn_string = connection_string
        self.pool = None
        self.server_id = hashlib.md5(connection_string.encode()).hexdigest()[:8]
        self.local_clock = 0

    async def connect(self):
        """Initialize connection pool"""
        self.pool = await asyncpg.create_pool(
            self.conn_string,
            min_size=5,
            max_size=20,
            command_timeout=60
        )
        await self._init_schema()
        logger.info(f"PostgreSQL backend connected (Server ID: {self.server_id})")

    async def close(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()

    async def _init_schema(self):
        """Create necessary tables if they don't exist"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS global_block_state (
                    x INTEGER NOT NULL,
                    y INTEGER NOT NULL,
                    z INTEGER NOT NULL,
                    dimension VARCHAR(50) DEFAULT 'overworld',
                    block_type VARCHAR(100) NOT NULL,
                    properties JSONB DEFAULT '{}',
                    last_vector JSONB NOT NULL,
                    last_updated TIMESTAMPTZ DEFAULT NOW(),
                    PRIMARY KEY (x, y, z, dimension)
                );
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS operation_log (
                    op_id VARCHAR(64) PRIMARY KEY,
                    server_id VARCHAR(50) NOT NULL,
                    block_type VARCHAR(100),
                    x INTEGER, y INTEGER, z INTEGER,
                    dimension VARCHAR(50),
                    operation VARCHAR(20),
                    properties JSONB,
                    vector JSONB,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ops_time 
                ON operation_log(created_at DESC);
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS build_sessions (
                    session_id VARCHAR(64) PRIMARY KEY,
                    owner VARCHAR(100),
                    status VARCHAR(20) DEFAULT 'active',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    last_heartbeat TIMESTAMPTZ DEFAULT NOW()
                );
            """)

    def _generate_vector(self) -> CRDTVector:
        """Generate a new CRDT vector with incremented clock"""
        self.local_clock += 1
        return CRDTVector(
            server_id=self.server_id,
            timestamp=int(time.time() * 1000),
            counter=self.local_clock
        )

    async def apply_operation(self, op: BlockOperation, dimension: str = 'overworld') -> bool:
        """Apply a block operation using CRDT logic"""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Fetch current state
                row = await conn.fetchrow(
                    "SELECT last_vector FROM global_block_state WHERE x=$1 AND y=$2 AND z=$3 AND dimension=$4",
                    op.x, op.y, op.z, dimension
                )
                
                should_apply = True
                if row:
                    existing_vector = CRDTVector.from_dict(row['last_vector'])
                    # CRDT Conflict Resolution: Last-Writer-Wins with Server ID tiebreaker
                    if not (op.vector > existing_vector):
                        logger.debug(f"Skipping stale operation {op.op_id}")
                        should_apply = False

                if should_apply:
                    if op.operation == 'REMOVE':
                        await conn.execute(
                            "DELETE FROM global_block_state WHERE x=$1 AND y=$2 AND z=$3 AND dimension=$4",
                            op.x, op.y, op.z, dimension
                        )
                    else:
                        await conn.execute("""
                            INSERT INTO global_block_state (x, y, z, dimension, block_type, properties, last_vector)
                            VALUES ($1, $2, $3, $4, $5, $6, $7)
                            ON CONFLICT (x, y, z, dimension) DO UPDATE SET
                                block_type = EXCLUDED.block_type,
                                properties = EXCLUDED.properties,
                                last_vector = EXCLUDED.last_vector,
                                last_updated = NOW()
                        """, op.x, op.y, op.z, dimension, op.block_type, 
                            json.dumps(op.properties), json.dumps(op.vector.to_dict()))
                    
                    # Log operation
                    await conn.execute("""
                        INSERT INTO operation_log (op_id, server_id, block_type, x, y, z, dimension, operation, properties, vector)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                        ON CONFLICT (op_id) DO NOTHING
                    """, op.op_id, op.vector.server_id, op.block_type, op.x, op.y, op.z, 
                        dimension, op.operation, json.dumps(op.properties), json.dumps(op.vector.to_dict()))
                    
                    return True
                return False

    async def get_region_state(self, x1: int, z1: int, x2: int, z2: int, 
                               y_min: int, y_max: int, dimension: str = 'overworld') -> List[Dict]:
        """Fetch state for a specific region"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT x, y, z, block_type, properties FROM global_block_state
                WHERE x BETWEEN $1 AND $2 AND z BETWEEN $3 AND $4 
                AND y BETWEEN $5 AND $6 AND dimension = $7
            """, min(x1, x2), max(x1, x2), min(z1, z2), max(z1, z2), y_min, y_max, dimension)
            
            return [dict(r) for r in rows]

    async def sync_operations_since(self, timestamp_ms: int, server_id_exclude: str = None) -> List[BlockOperation]:
        """Fetch operations newer than a given timestamp for sync"""
        async with self.pool.acquire() as conn:
            query = "SELECT * FROM operation_log WHERE created_at > $1"
            params = [datetime.fromtimestamp(timestamp_ms / 1000)]
            
            if server_id_exclude:
                query += " AND server_id != $2"
                params.append(server_id_exclude)
                
            rows = await conn.fetch(query, *params)
            return [BlockOperation.from_json(json.dumps({
                'op_id': r['op_id'],
                'block_type': r['block_type'],
                'x': r['x'], 'y': r['y'], 'z': r['z'],
                'properties': r['properties'],
                'operation': r['operation'],
                'vector': r['vector']
            })) for r in rows]

class CrossServerSyncEngine:
    """High-level sync engine managing PostgreSQL backend and local cache"""
    
    def __init__(self, db_connection_string: str, local_server_id: str):
        self.backend = PostgreSQLBackend(db_connection_string)
        self.local_server_id = local_server_id
        self.pending_ops: List[BlockOperation] = []
        self.sync_task = None
        self.running = False

    async def start(self):
        """Start the sync engine"""
        await self.backend.connect()
        self.running = True
        self.sync_task = asyncio.create_task(self._sync_loop())
        logger.info("Cross-Server Sync Engine started")

    async def stop(self):
        """Stop the sync engine"""
        self.running = False
        if self.sync_task:
            self.sync_task.cancel()
            try:
                await self.sync_task
            except asyncio.CancelledError:
                pass
        await self.backend.close()

    async def _sync_loop(self):
        """Background loop to push/pull changes"""
        last_sync_time = int(time.time() * 1000)
        while self.running:
            try:
                # Push pending local operations
                if self.pending_ops:
                    ops = self.pending_ops[:]
                    self.pending_ops.clear()
                    for op in ops:
                        await self.backend.apply_operation(op)
                
                # Pull remote operations (simplified polling)
                # In production, use LISTEN/NOTIFY or logical replication
                remote_ops = await self.backend.sync_operations_since(last_sync_time, self.local_server_id)
                if remote_ops:
                    logger.info(f"Synced {len(remote_ops)} remote operations")
                    # Here we would apply to local Minecraft world via WebSocket
                    # self.local_executor.apply_remote_ops(remote_ops)
                
                last_sync_time = int(time.time() * 1000)
                await asyncio.sleep(1.0) # Sync interval
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Sync loop error: {e}")
                await asyncio.sleep(5.0)

    def queue_operation(self, op: BlockOperation):
        """Queue an operation for async sync"""
        if op.vector.server_id != self.local_server_id:
            op.vector.server_id = self.local_server_id
        self.pending_ops.append(op)

    async def force_sync(self):
        """Force immediate synchronization"""
        if self.pending_ops:
            ops = self.pending_ops[:]
            self.pending_ops.clear()
            for op in ops:
                await self.backend.apply_operation(op)

# Example Usage
if __name__ == "__main__":
    async def main():
        # Requires running PostgreSQL: 
        # docker run --name omni-db -e POSTGRES_PASSWORD=secret -p 5432:5432 -d postgres
        db_url = "postgresql://postgres:secret@localhost:5432/minecraft_omni"
        
        sync_engine = CrossServerSyncEngine(db_url, "server_01")
        await sync_engine.start()
        
        # Create an operation
        op = BlockOperation(
            op_id="test_001",
            block_type="stone",
            x=100, y=64, z=200,
            properties={},
            operation="PLACE",
            vector=sync_engine.backend._generate_vector()
        )
        
        sync_engine.queue_operation(op)
        await sync_engine.force_sync()
        
        print("Operation synced to PostgreSQL!")
        await sync_engine.stop()

    # asyncio.run(main())
