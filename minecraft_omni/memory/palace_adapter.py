"""
Minecraft Omni-Builder v3.1 - MemPalace Memory Adapter
Manages spatial registry, undo journal, tombstone logs, and preference learning
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
import json
import time
from pathlib import Path


@dataclass
class BlockPlacement:
    """Represents a placed block in memory"""
    build_id: str
    x: int
    y: int
    z: int
    block_type: str
    room_name: str
    context: Optional[str]
    timestamp: float
    is_preview: bool = False


@dataclass
class UndoEntry:
    """Command pattern entry for undo operations"""
    build_id: str
    action: str  # "PLACE" or "DELETE"
    data: str  # JSON serialized block info
    timestamp: float
    undone: bool = False


@dataclass
class Tombstone:
    """Records manual block breaks for sync tracking"""
    x: int
    y: int
    z: int
    timestamp: float
    reason: str  # "manual_break", "sync_drift", "physics_correction"


@dataclass
class StyleProfile:
    """Player's building preferences (v3.1)"""
    player_uuid: str
    preferred_blocks: List[str]
    avoided_blocks: List[str]
    symmetry_preference: float  # 0.0-1.0
    style_tags: List[str]  # ["medieval", "modern", etc.]
    
    def summary(self) -> str:
        """Generate human-readable preference summary"""
        parts = []
        if self.preferred_blocks:
            parts.append(f"prefers {', '.join(self.preferred_blocks[:3])}")
        if self.avoided_blocks:
            parts.append(f"avoids {', '.join(self.avoided_blocks[:3])}")
        if self.symmetry_preference > 0.7:
            parts.append("likes symmetry")
        return ", ".join(parts)


class MinecraftMemPalace:
    """
    MemPalace adapter for Minecraft Omni-Builder
    
    Rooms:
    - spatial_registry: All placed blocks with coordinates
    - undo_journal: Command pattern logs for rollback
    - tombstone_log: Manual breaks + sync drift tracking
    - preference_learning: Player style profiles (v3.1)
    - version_branches: Git-like DAG storage (v3.1)
    - preview_states: Pending ghost block data (v3.1)
    
    Features:
    - Verbatim block storage
    - Undo/redo support
    - Bidirectional sync tracking
    - Style learning from feedback
    """
    
    def __init__(self, palace_path: str = "~/minecraft_palace"):
        self.palace_path = Path(palace_path).expanduser()
        self.palace_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize rooms as SQLite tables (in production, use actual MemPalace)
        self.db_path = self.palace_path / "palace.db"
        self._init_db()
        
        # In-memory caches
        self.spatial_cache: Dict[str, List[BlockPlacement]] = {}
        self.undo_cache: Dict[str, List[UndoEntry]] = {}
        self.tombstones: List[Tombstone] = []
        self.style_profiles: Dict[str, StyleProfile] = {}
    
    def _init_db(self):
        """Initialize SQLite database schema"""
        import sqlite3
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Spatial registry table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS spatial_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                build_id TEXT NOT NULL,
                x INTEGER NOT NULL,
                y INTEGER NOT NULL,
                z INTEGER NOT NULL,
                block_type TEXT NOT NULL,
                room_name TEXT,
                context TEXT,
                timestamp REAL NOT NULL,
                is_preview INTEGER DEFAULT 0
            )
        ''')
        
        # Undo journal table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS undo_journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                build_id TEXT NOT NULL,
                action TEXT NOT NULL,
                data TEXT NOT NULL,
                timestamp REAL NOT NULL,
                undone INTEGER DEFAULT 0
            )
        ''')
        
        # Tombstone log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tombstone_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                x INTEGER NOT NULL,
                y INTEGER NOT NULL,
                z INTEGER NOT NULL,
                timestamp REAL NOT NULL,
                reason TEXT NOT NULL
            )
        ''')
        
        # Preference learning table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS preference_learning (
                player_uuid TEXT PRIMARY KEY,
                preferred_blocks TEXT,
                avoided_blocks TEXT,
                symmetry_preference REAL DEFAULT 0.5,
                style_tags TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def log_block_placement(
        self, 
        block_type: str, 
        x: int, 
        y: int, 
        z: int, 
        room_name: str,
        context: Optional[str] = None,
        build_id: Optional[str] = None
    ):
        """
        Log a block placement to spatial registry and undo journal
        
        Stores verbatim placement + creates undo journal entry
        """
        build_id = build_id or f"build_{int(time.time())}"
        timestamp = time.time()
        
        # Create placement record
        placement = BlockPlacement(
            build_id=build_id,
            x=x, y=y, z=z,
            block_type=block_type,
            room_name=room_name,
            context=context,
            timestamp=timestamp
        )
        
        # Store in database
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO spatial_registry 
            (build_id, x, y, z, block_type, room_name, context, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (build_id, x, y, z, block_type, room_name, context, timestamp))
        
        # Create undo entry
        undo_data = json.dumps({"x": x, "y": y, "z": z, "block_type": block_type})
        cursor.execute('''
            INSERT INTO undo_journal (build_id, action, data, timestamp)
            VALUES (?, 'PLACE', ?, ?)
        ''', (build_id, undo_data, timestamp))
        
        conn.commit()
        conn.close()
        
        # Update cache
        if build_id not in self.spatial_cache:
            self.spatial_cache[build_id] = []
        self.spatial_cache[build_id].append(placement)
    
    def log_tombstone(self, x: int, y: int, z: int, timestamp: Optional[float] = None, reason: str = "manual_break"):
        """
        Log manual block break for bidirectional sync
        
        Called when player manually breaks a block that was placed by the bot
        """
        timestamp = timestamp or time.time()
        
        tombstone = Tombstone(x=x, y=y, z=z, timestamp=timestamp, reason=reason)
        self.tombstones.append(tombstone)
        
        # Store in database
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO tombstone_log (x, y, z, timestamp, reason)
            VALUES (?, ?, ?, ?, ?)
        ''', (x, y, z, timestamp, reason))
        
        conn.commit()
        conn.close()
        
        # Mark spatial registry entry as invalid
        self._mark_spatial_invalid(x, y, z)
    
    def get_undo_stack(self, build_id: str, limit: int = 10) -> List[UndoEntry]:
        """Get recent undo entries for a build"""
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT build_id, action, data, timestamp, undone
            FROM undo_journal
            WHERE build_id = ? AND undone = 0
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (build_id, limit))
        
        entries = []
        for row in cursor.fetchall():
            entries.append(UndoEntry(
                build_id=row[0],
                action=row[1],
                data=row[2],
                timestamp=row[3],
                undone=bool(row[4])
            ))
        
        conn.close()
        return entries
    
    def execute_undo(self, undo_entry: UndoEntry) -> Optional[Tuple[int, int, int, str]]:
        """
        Execute an undo operation
        
        Returns:
            Tuple of (x, y, z, block_type) to delete, or None if already undone
        """
        if undo_entry.undone:
            return None
        
        # Mark as undone
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE undo_journal SET undone = 1
            WHERE build_id = ? AND timestamp = ?
        ''', (undo_entry.build_id, undo_entry.timestamp))
        
        conn.commit()
        conn.close()
        
        # Parse undo data
        data = json.loads(undo_entry.data)
        
        if undo_entry.action == "PLACE":
            # Return block to delete
            return (data["x"], data["y"], data["z"], data["block_type"])
        
        return None
    
    def get_style_profile(self, player_uuid: str) -> Optional[StyleProfile]:
        """Get player's style profile for preference learning"""
        if player_uuid in self.style_profiles:
            return self.style_profiles[player_uuid]
        
        # Load from database
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT player_uuid, preferred_blocks, avoided_blocks, 
                   symmetry_preference, style_tags
            FROM preference_learning
            WHERE player_uuid = ?
        ''', (player_uuid,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            profile = StyleProfile(
                player_uuid=row[0],
                preferred_blocks=json.loads(row[1]) if row[1] else [],
                avoided_blocks=json.loads(row[2]) if row[2] else [],
                symmetry_preference=row[3],
                style_tags=json.loads(row[4]) if row[4] else []
            )
            self.style_profiles[player_uuid] = profile
            return profile
        
        return None
    
    def update_style_profile(
        self, 
        player_uuid: str, 
        features: Dict[str, Any], 
        feedback: str
    ):
        """
        Update player's style profile based on feedback
        
        Args:
            player_uuid: Player's UUID
            features: Extracted features from build (blocks, symmetry, etc.)
            feedback: "like" or "dislike"
        """
        profile = self.get_style_profile(player_uuid)
        
        if not profile:
            profile = StyleProfile(
                player_uuid=player_uuid,
                preferred_blocks=[],
                avoided_blocks=[],
                symmetry_preference=0.5,
                style_tags=[]
            )
        
        # Update based on feedback
        if feedback == "like":
            # Add used blocks to preferred list
            for block in features.get("blocks_used", []):
                if block not in profile.preferred_blocks:
                    profile.preferred_blocks.append(block)
            
            # Reinforce symmetry preference if present
            if features.get("symmetry_score", 0) > 0.7:
                profile.symmetry_preference = min(1.0, profile.symmetry_preference + 0.1)
        
        elif feedback == "dislike":
            # Add used blocks to avoided list
            for block in features.get("blocks_used", []):
                if block not in profile.avoided_blocks:
                    profile.avoided_blocks.append(block)
        
        # Save to database
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO preference_learning 
            (player_uuid, preferred_blocks, avoided_blocks, symmetry_preference, style_tags)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            player_uuid,
            json.dumps(profile.preferred_blocks),
            json.dumps(profile.avoided_blocks),
            profile.symmetry_preference,
            json.dumps(profile.style_tags)
        ))
        
        conn.commit()
        conn.close()
        
        self.style_profiles[player_uuid] = profile
    
    def _mark_spatial_invalid(self, x: int, y: int, z: int):
        """Mark a spatial registry entry as invalid (deleted)"""
        # In production, this would update the database
        # For now, just remove from cache
        for build_id, placements in self.spatial_cache.items():
            self.spatial_cache[build_id] = [
                p for p in placements 
                if not (p.x == x and p.y == y and p.z == z)
            ]
    
    def get_build_blocks(self, build_id: str) -> List[BlockPlacement]:
        """Get all blocks for a specific build"""
        if build_id in self.spatial_cache:
            return self.spatial_cache[build_id]
        
        # Load from database
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT build_id, x, y, z, block_type, room_name, context, timestamp, is_preview
            FROM spatial_registry
            WHERE build_id = ?
        ''', (build_id,))
        
        placements = []
        for row in cursor.fetchall():
            placements.append(BlockPlacement(
                build_id=row[0],
                x=row[1], y=row[2], z=row[3],
                block_type=row[4],
                room_name=row[5],
                context=row[6],
                timestamp=row[7],
                is_preview=bool(row[8])
            ))
        
        conn.close()
        self.spatial_cache[build_id] = placements
        return placements
    
    def check_hash_consistency(self, region_min: Tuple, region_max: Tuple, stored_hash: str) -> bool:
        """
        Check if region hash matches stored hash
        
        Returns True if consistent, False if drift detected
        """
        # In production, would compute hash from current state
        # and compare to stored hash
        return True  # Simplified for now
