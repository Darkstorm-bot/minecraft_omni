"""
Minecraft Omni-Builder v3.1 - Sync Engine Module
Bidirectional event stream for world-memory synchronization
Hash-based validation and tombstone reconciliation
"""
import asyncio
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import hashlib

from memory.palace_adapter import MinecraftMemPalace, Tombstone


@dataclass
class WorldEvent:
    """Represents a world change event from Minecraft"""
    event_type: str  # "BLOCK_BREAK", "BLOCK_PLACE", "WORLD_EDIT"
    x: int
    y: int
    z: int
    old_block: Optional[str]
    new_block: Optional[str]
    player_uuid: Optional[str]
    timestamp: float
    dimension: str = "overworld"


@dataclass
class RegionBounds:
    """Defines a 3D region for sync operations"""
    x_min: int
    y_min: int
    z_min: int
    x_max: int
    y_max: int
    z_max: int

    def contains(self, x: int, y: int, z: int) -> bool:
        """Check if coordinate is within bounds"""
        return (self.x_min <= x <= self.x_max and
                self.y_min <= y <= self.y_max and
                self.z_min <= z <= self.z_max)


class SyncEngine:
    """
    Maintains consistency between MemPalace and Minecraft world.

    Features:
    - Bidirectional event streaming
    - Hash-based chunk validation
    - Tombstone reconciliation
    - Partial resync on drift detection
    """

    def __init__(
        self,
        palace: MinecraftMemPalace,
        mc_client: Any,
        check_interval_minutes: int = 5
    ):
        self.palace = palace
        self.mc_client = mc_client
        self.check_interval = check_interval_minutes * 60

        # Event stream state
        self.event_queue: asyncio.Queue[WorldEvent] = asyncio.Queue()
        self.listening = False
        self.sync_task: Optional[asyncio.Task] = None

        # Hash cache for regions
        self.region_hashes: Dict[str, str] = {}

    async def start_listening(self):
        """Start bidirectional event listener"""
        self.listening = True
        self.sync_task = asyncio.create_task(self._event_listener_loop())

    async def stop_listening(self):
        """Stop event listener"""
        self.listening = False
        if self.sync_task:
            self.sync_task.cancel()
            try:
                await self.sync_task
            except asyncio.CancelledError:
                pass

    async def _event_listener_loop(self):
        """Continuously process world events"""
        while self.listening:
            try:
                event = await asyncio.wait_for(
                    self.event_queue.get(),
                    timeout=1.0
                )
                await self._handle_world_event(event)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Event listener error: {e}")
                await asyncio.sleep(1.0)

    async def _handle_world_event(self, event: WorldEvent):
        """Process a single world change event"""
        if event.event_type == "BLOCK_BREAK":
            # Log tombstone for manual break
            self.palace.log_tombstone(
                x=event.x,
                y=event.y,
                z=event.z,
                timestamp=event.timestamp,
                reason="manual_break"
            )

            # Mark spatial registry as invalid
            self.palace._mark_spatial_invalid(event.x, event.y, event.z)

        elif event.event_type == "BLOCK_PLACE":
            # If placed by external source (not our executor), log it
            if event.player_uuid and event.new_block:
                # Could optionally sync external placements to palace
                pass

        elif event.event_type == "WORLD_EDIT":
            # Large region edit - invalidate entire area
            print(f"WorldEdit detected at {event.x},{event.y},{event.z}")
            # Trigger full resync for affected region

    async def inject_event(self, event: WorldEvent):
        """Inject a world event into the stream (called by bridge)"""
        await self.event_queue.put(event)

    async def consistency_check(
        self,
        region: RegionBounds,
        build_id: Optional[str] = None
    ) -> bool:
        """
        Perform hash-based consistency check for a region

        Args:
            region: Bounds to check
            build_id: Optional build session ID

        Returns:
            True if consistent, False if drift detected
        """
        # Generate region key
        region_key = f"{region.x_min}:{region.z_min}:{region.x_max}:{region.z_max}"

        # Get current world hash
        current_hash = await self._compute_region_hash(region)

        # Check against stored hash
        stored_hash = self.region_hashes.get(region_key)

        if stored_hash is None:
            # First check - store hash
            self.region_hashes[region_key] = current_hash
            return True

        if current_hash != stored_hash:
            # Drift detected - trigger resync
            print(f"Sync drift detected in region {region_key}")
            await self._rebuild_spatial_index(region, build_id)
            return False

        return True

    async def _compute_region_hash(self, region: RegionBounds) -> str:
        """
        Compute SHA256 hash of block states in region

        Uses sampled hashing for performance on large regions
        """
        hasher = hashlib.sha256()

        # Sample every 4th block for performance
        sample_rate = 4

        for x in range(region.x_min, region.x_max + 1, sample_rate):
            for z in range(region.z_min, region.z_max + 1, sample_rate):
                for y in range(region.y_min, region.y_max + 1, sample_rate):
                    block = await self.mc_client.get_block_at(x, y, z)
                    hasher.update(f"{x}:{y}:{z}:{block}".encode())

        return hasher.hexdigest()

    async def _rebuild_spatial_index(
        self,
        region: RegionBounds,
        build_id: Optional[str] = None
    ):
        """
        Rebuild spatial registry from world snapshot

        Args:
            region: Region to rebuild
            build_id: Build session to update
        """
        print(f"Rebuilding spatial index for region...")

        updated_count = 0

        for x in range(region.x_min, region.x_max + 1):
            for z in range(region.z_min, region.z_max + 1):
                for y in range(region.y_min, region.y_max + 1):
                    block = await self.mc_client.get_block_at(x, y, z)

                    if block and block != "air":
                        # Update or insert in palace
                        if build_id:
                            self.palace.log_block_placement(
                                build_id=build_id,
                                x=x, y=y, z=z,
                                block_type=block,
                                room_name="Sync_Rebuild",
                                context="auto_sync"
                            )
                            updated_count += 1

        # Update hash
        region_key = f"{region.x_min}:{region.z_min}:{region.x_max}:{region.z_max}"
        self.region_hashes[region_key] = await self._compute_region_hash(region)

        print(f"Rebuilt {updated_count} blocks in spatial index")

    def invalidate_cache(self, region: RegionBounds):
        """Invalidate cached hash for a region"""
        region_key = f"{region.x_min}:{region.z_min}:{region.x_max}:{region.z_max}"
        if region_key in self.region_hashes:
            del self.region_hashes[region_key]

    async def periodic_consistency_loop(self):
        """Run periodic consistency checks (background task)"""
        while True:
            await asyncio.sleep(self.check_interval)

            # Check all tracked regions
            for region_key in list(self.region_hashes.keys()):
                # Parse region key back to bounds
                parts = region_key.split(":")
                if len(parts) == 4:
                    region = RegionBounds(
                        x_min=int(parts[0]),
                        z_min=int(parts[1]),
                        x_max=int(parts[2]),
                        z_max=int(parts[3]),
                        y_min=-64,
                        y_max=320
                    )
                    await self.consistency_check(region)
