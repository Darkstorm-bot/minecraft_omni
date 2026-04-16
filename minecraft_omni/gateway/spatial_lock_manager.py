"""
Minecraft Omni-Builder v3.1 - Spatial Lock Manager Module
Prevents concurrent build overlaps in multiplayer environments
"""
import sqlite3
import time
from typing import Optional, Tuple, List
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RegionLock:
    """Represents an active region lock"""
    x1: int
    z1: int
    x2: int
    z2: int
    player_uuid: str
    expires_at: float
    build_id: Optional[str] = None


class SpatialLockManager:
    """
    Manages spatial locks to prevent overlapping builds in multiplayer.

    Features:
    - Overlap detection for rectangular regions
    - Time-based expiration (TTL)
    - SQLite persistence for crash recovery
    - Auto-release on disconnect
    """

    def __init__(self, db_path: str = "locks.sqlite"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._init_table()

    def _init_table(self):
        """Initialize SQLite table for region locks"""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS region_locks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                x1 INTEGER NOT NULL,
                z1 INTEGER NOT NULL,
                x2 INTEGER NOT NULL,
                z2 INTEGER NOT NULL,
                player_uuid TEXT NOT NULL,
                build_id TEXT,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                released INTEGER DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_region_coords 
            ON region_locks(x1, z1, x2, z2)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_expires 
            ON region_locks(expires_at)
        """)
        self.conn.commit()

    def claim_region(
        self,
        x1: int,
        z1: int,
        x2: int,
        z2: int,
        player_uuid: str,
        ttl_sec: int = 300,
        build_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Attempt to claim a region for building

        Args:
            x1, z1: Minimum X,Z coordinates
            x2, z2: Maximum X,Z coordinates
            player_uuid: Player's unique identifier
            ttl_sec: Lock time-to-live in seconds
            build_id: Optional build session ID

        Returns:
            Tuple of (success, message)
        """
        # Normalize coordinates (ensure x1 <= x2, z1 <= z2)
        x_min, x_max = min(x1, x2), max(x1, x2)
        z_min, z_max = min(z1, z2), max(z1, z2)

        # Clean up expired locks first
        self._cleanup_expired()

        # Check for overlap with existing locks
        overlap = self._check_overlap(x_min, z_min, x_max, z_max)
        if overlap:
            return False, f"Region occupied by {overlap.player_uuid[:8]}..."

        # Insert new lock
        now = time.time()
        expires_at = now + ttl_sec

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO region_locks (x1, z1, x2, z2, player_uuid, build_id, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (x_min, z_min, x_max, z_max, player_uuid, build_id, now, expires_at))
        self.conn.commit()

        return True, "Region claimed successfully"

    def release_region(self, build_id: str) -> bool:
        """
        Release a lock associated with a build ID

        Args:
            build_id: Build session ID to release

        Returns:
            True if released, False if not found
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE region_locks SET released = 1 WHERE build_id = ? AND released = 0
        """, (build_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def release_by_uuid(self, player_uuid: str) -> int:
        """
        Release all locks held by a player

        Args:
            player_uuid: Player's UUID

        Returns:
            Number of locks released
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE region_locks SET released = 1 WHERE player_uuid = ? AND released = 0
        """, (player_uuid,))
        self.conn.commit()
        return cursor.rowcount

    def is_locked(self, x: int, z: int) -> Optional[RegionLock]:
        """
        Check if a specific coordinate is locked

        Args:
            x, z: Coordinates to check

        Returns:
            RegionLock if locked, None otherwise
        """
        self._cleanup_expired()

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT x1, z1, x2, z2, player_uuid, expires_at, build_id
            FROM region_locks
            WHERE released = 0
              AND x1 <= ? AND x2 >= ?
              AND z1 <= ? AND z2 >= ?
            LIMIT 1
        """, (x, x, z, z))

        row = cursor.fetchone()
        if row:
            return RegionLock(
                x1=row[0], z1=row[1], x2=row[2], z2=row[3],
                player_uuid=row[4], expires_at=row[5], build_id=row[6]
            )
        return None

    def get_active_locks(self, player_uuid: Optional[str] = None) -> List[RegionLock]:
        """
        Get all active locks, optionally filtered by player

        Args:
            player_uuid: Optional filter by player

        Returns:
            List of active RegionLock objects
        """
        self._cleanup_expired()

        cursor = self.conn.cursor()
        if player_uuid:
            cursor.execute("""
                SELECT x1, z1, x2, z2, player_uuid, expires_at, build_id
                FROM region_locks
                WHERE released = 0 AND player_uuid = ?
            """, (player_uuid,))
        else:
            cursor.execute("""
                SELECT x1, z1, x2, z2, player_uuid, expires_at, build_id
                FROM region_locks
                WHERE released = 0
            """)

        locks = []
        for row in cursor.fetchall():
            locks.append(RegionLock(
                x1=row[0], z1=row[1], x2=row[2], z2=row[3],
                player_uuid=row[4], expires_at=row[5], build_id=row[6]
            ))
        return locks

    def extend_lock(self, build_id: str, additional_sec: int = 300) -> bool:
        """
        Extend the TTL of an existing lock

        Args:
            build_id: Build session ID
            additional_sec: Seconds to add to expiration

        Returns:
            True if extended, False if not found
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE region_locks 
            SET expires_at = expires_at + ?
            WHERE build_id = ? AND released = 0
        """, (additional_sec, build_id))
        self.conn.commit()
        return cursor.rowcount > 0

    def _check_overlap(
        self,
        x1: int,
        z1: int,
        x2: int,
        z2: int
    ) -> Optional[RegionLock]:
        """
        Check if region overlaps with any active lock

        Uses rectangle intersection logic:
        Two rectangles overlap if NOT (one is completely to left/right/above/below other)
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT x1, z1, x2, z2, player_uuid, expires_at, build_id
            FROM region_locks
            WHERE released = 0
              AND NOT (x2 < ? OR x1 > ? OR z2 < ? OR z1 > ?)
            LIMIT 1
        """, (x1, x2, z1, z2))

        row = cursor.fetchone()
        if row:
            return RegionLock(
                x1=row[0], z1=row[1], x2=row[2], z2=row[3],
                player_uuid=row[4], expires_at=row[5], build_id=row[6]
            )
        return None

    def _cleanup_expired(self):
        """Remove expired locks from database"""
        now = time.time()
        cursor = self.conn.cursor()
        cursor.execute("""
            DELETE FROM region_locks WHERE expires_at < ?
        """, (now,))
        self.conn.commit()

    def get_suggested_offset(
        self,
        x1: int,
        z1: int,
        x2: int,
        z2: int,
        preferred_direction: str = "east"
    ) -> Tuple[int, int]:
        """
        Suggest an offset to avoid overlapping with existing locks

        Args:
            x1, z1, x2, z2: Original desired region
            preferred_direction: Preferred direction to search (north/south/east/west)

        Returns:
            Suggested (offset_x, offset_z) tuple
        """
        width = abs(x2 - x1) + 1
        depth = abs(z2 - z1) + 1

        # Try offsets in expanding radius
        for radius in range(1, 20):
            for dx in range(-radius, radius + 1):
                for dz in range(-radius, radius + 1):
                    if abs(dx) != radius and abs(dz) != radius:
                        continue  # Only check perimeter

                    test_x1 = x1 + dx
                    test_z1 = z1 + dz
                    test_x2 = x2 + dx
                    test_z2 = z2 + dz

                    if not self._check_overlap(test_x1, test_z1, test_x2, test_z2):
                        return (dx, dz)

        # Fallback: just go far east
        return (width + 10, 0)

    def statistics(self) -> dict:
        """Get lock manager statistics"""
        cursor = self.conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM region_locks WHERE released = 0")
        active_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT player_uuid) FROM region_locks WHERE released = 0")
        unique_players = cursor.fetchone()[0]

        cursor.execute("SELECT AVG(expires_at - created_at) FROM region_locks WHERE released = 0")
        avg_ttl = cursor.fetchone()[0] or 0

        return {
            "active_locks": active_count,
            "unique_players": unique_players,
            "average_ttl_seconds": avg_ttl,
        }

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
