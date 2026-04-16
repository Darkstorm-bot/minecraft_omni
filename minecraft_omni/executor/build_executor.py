"""
Minecraft Omni-Builder v3.1 - Build Executor Module
Executes validated tool calls via WebSocket to PaperMC plugin
Supports holographic previews and adaptive throttling
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
import asyncio
import time

from parser.command_parser import Vector3, Bounds
from llm.tool_router import ToolCall
from executor.block_state_registry import BlockData, BlockStateRegistry


@dataclass
class ExecutionResult:
    """Result of block placement execution"""
    success: bool
    blocks_placed: int
    blocks_failed: int
    errors: List[str]
    duration_ms: float


class AdaptiveThrottler:
    """
    Adapts block placement rate based on server TPS
    Prevents lag spikes during large builds
    """
    
    # TPS thresholds and corresponding rates
    TPS_THRESHOLDS = [
        (19.0, 100),  # TPS >= 19: 100 blocks/tick
        (17.0, 50),   # TPS >= 17: 50 blocks/tick
        (15.0, 20),   # TPS >= 15: 20 blocks/tick
        (0.0, 10),    # TPS < 15: 10 blocks/tick
    ]
    
    def __init__(self, initial_tps: float = 20.0):
        self.current_tps = initial_tps
        self.current_rate = 100
        self.last_update = time.time()
    
    def update_tps(self, tps: float):
        """Update current TPS and recalculate rate"""
        self.current_tps = tps
        self._calculate_rate()
        self.last_update = time.time()
    
    def _calculate_rate(self):
        """Calculate placement rate from TPS"""
        for threshold, rate in self.TPS_THRESHOLDS:
            if self.current_tps >= threshold:
                self.current_rate = rate
                return
    
    def get_rate(self) -> int:
        """Get current blocks per tick rate"""
        return self.current_rate
    
    def get_delay_seconds(self) -> float:
        """Get delay between batches (20 ticks/second)"""
        return 1.0 / 20.0  # One batch per tick


class MinecraftWebSocketClient:
    """
    WebSocket client for communicating with PaperMC plugin
    Handles connection, reconnection, and message queuing
    """
    
    def __init__(self, host: str = "localhost", port: int = 8080):
        self.host = host
        self.port = port
        self.ws = None
        self.connected = False
        self.message_queue = []
    
    async def connect(self) -> bool:
        """Establish WebSocket connection"""
        try:
            import websockets
            uri = f"ws://{self.host}:{self.port}/minecraft"
            self.ws = await websockets.connect(uri)
            self.connected = True
            return True
        except Exception as e:
            print(f"WebSocket connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Close WebSocket connection"""
        if self.ws:
            await self.ws.close()
            self.connected = False
    
    async def send(self, message: dict) -> bool:
        """Send message to server"""
        if not self.connected or not self.ws:
            self.message_queue.append(message)
            return False
        
        try:
            import json
            await self.ws.send(json.dumps(message))
            return True
        except Exception as e:
            print(f"Send failed: {e}")
            self.connected = False
            self.message_queue.append(message)
            return False
    
    async def receive(self) -> Optional[dict]:
        """Receive message from server"""
        if not self.connected or not self.ws:
            return None
        
        try:
            import json
            response = await self.ws.recv()
            return json.loads(response)
        except Exception as e:
            print(f"Receive failed: {e}")
            return None
    
    async def flush_queue(self) -> int:
        """Send queued messages after reconnection"""
        sent = 0
        while self.message_queue and self.connected:
            msg = self.message_queue.pop(0)
            if await self.send(msg):
                sent += 1
        return sent


class BuildExecutor:
    """
    Executes build actions via WebSocket to Minecraft server
    
    Features:
    - Adaptive throttling based on TPS
    - Holographic preview support
    - Batch processing for efficiency
    - Error handling and retry logic
    """
    
    def __init__(
        self, 
        ws_client: Optional[MinecraftWebSocketClient] = None,
        block_registry: Optional[BlockStateRegistry] = None
    ):
        self.ws_client = ws_client or MinecraftWebSocketClient()
        self.block_registry = block_registry or BlockStateRegistry()
        self.throttler = AdaptiveThrottler()
        self.pending_previews: Dict[str, List[dict]] = {}  # preview_id -> blocks
    
    async def execute_tool_calls(
        self, 
        tool_calls: List[ToolCall],
        is_preview: bool = False,
        preview_id: Optional[str] = None
    ) -> ExecutionResult:
        """
        Execute a list of validated tool calls
        
        Args:
            tool_calls: List of validated ToolCall objects
            is_preview: If True, spawn ghost blocks instead of real blocks
            preview_id: ID for tracking preview state
            
        Returns:
            ExecutionResult with success/failure info
        """
        start_time = time.time()
        placed = 0
        failed = 0
        errors = []
        
        # Filter to only valid tool calls
        valid_calls = [tc for tc in tool_calls if tc.is_valid]
        
        if is_preview:
            # Handle holographic preview
            return await self._execute_preview(valid_calls, preview_id)
        
        # Group by tool type for batch processing
        place_calls = [tc for tc in valid_calls if tc.tool_name == "place_block"]
        fill_calls = [tc for tc in valid_calls if tc.tool_name == "fill_region"]
        carve_calls = [tc for tc in valid_calls if tc.tool_name == "carve_terrain"]
        lighting_calls = [tc for tc in valid_calls if tc.tool_name == "set_lighting"]
        
        # Execute each type
        for call in place_calls:
            success = await self._place_block(call.params)
            if success:
                placed += 1
            else:
                failed += 1
                errors.append(f"Failed to place block at {call.params['x']},{call.params['y']},{call.params['z']}")
            
            # Apply throttling
            if placed % self.throttler.get_rate() == 0:
                await asyncio.sleep(self.throttler.get_delay_seconds())
        
        for call in fill_calls:
            success = await self._fill_region(call.params)
            if success:
                # Estimate blocks filled (simplified)
                min_c = call.params['min']
                max_c = call.params['max']
                volume = abs(max_c[0] - min_c[0]) * abs(max_c[1] - min_c[1]) * abs(max_c[2] - min_c[2])
                placed += volume
            else:
                failed += 1
                errors.append(f"Failed to fill region")
        
        for call in carve_calls:
            success = await self._carve_terrain(call.params)
            if success:
                placed += 1  # Count as one operation
            else:
                failed += 1
                errors.append(f"Failed to carve terrain")
        
        for call in lighting_calls:
            success = await self._set_lighting(call.params)
            if success:
                placed += len(call.params['positions'])
            else:
                failed += 1
                errors.append(f"Failed to set lighting")
        
        duration_ms = (time.time() - start_time) * 1000
        
        return ExecutionResult(
            success=failed == 0,
            blocks_placed=placed,
            blocks_failed=failed,
            errors=errors,
            duration_ms=duration_ms
        )
    
    async def _place_block(self, params: dict) -> bool:
        """Place a single block via WebSocket"""
        # Resolve block state
        block_data = self.block_registry.resolve(params)
        if not block_data:
            return False
        
        message = {
            "action": "place_block",
            "x": params["x"],
            "y": params["y"],
            "z": params["z"],
            "block": block_data.to_minecraft_string(),
            "state": block_data.state
        }
        
        return await self.ws_client.send(message)
    
    async def _fill_region(self, params: dict) -> bool:
        """Fill a 3D region with blocks"""
        block_data = self.block_registry.resolve({"block": params["block"]})
        if not block_data:
            return False
        
        message = {
            "action": "fill_region",
            "min": list(params["min"]),
            "max": list(params["max"]),
            "block": block_data.to_minecraft_string(),
            "replace": params.get("replace")
        }
        
        return await self.ws_client.send(message)
    
    async def _carve_terrain(self, params: dict) -> bool:
        """Remove blocks in a region (carve terrain)"""
        message = {
            "action": "carve_terrain",
            "min": list(params["min"]),
            "max": list(params["max"]),
            "replace_with": params.get("replace_with", "air")
        }
        
        return await self.ws_client.send(message)
    
    async def _set_lighting(self, params: dict) -> bool:
        """Place light sources at multiple positions"""
        positions = params["positions"]
        level = params.get("level", 15)
        
        # Send as batch
        message = {
            "action": "set_lighting",
            "positions": [list(p) if isinstance(p, tuple) else p for p in positions],
            "level": level
        }
        
        return await self.ws_client.send(message)
    
    async def _execute_preview(
        self, 
        tool_calls: List[ToolCall], 
        preview_id: Optional[str]
    ) -> ExecutionResult:
        """Execute holographic preview (ghost blocks)"""
        import uuid
        preview_id = preview_id or str(uuid.uuid4())
        
        # Collect all block positions for preview
        preview_blocks = []
        for call in tool_calls:
            if call.tool_name == "place_block":
                preview_blocks.append({
                    "x": call.params["x"],
                    "y": call.params["y"],
                    "z": call.params["z"],
                    "block_type": call.params["block"],
                    "alpha": 0.3
                })
        
        # Store for later approval/discarding
        self.pending_previews[preview_id] = preview_blocks
        
        # Send ghost block spawn command
        message = {
            "action": "spawn_ghost_blocks",
            "preview_id": preview_id,
            "blocks": preview_blocks,
            "client_only": True,
            "alpha": 0.3
        }
        
        success = await self.ws_client.send(message)
        
        return ExecutionResult(
            success=success,
            blocks_placed=len(preview_blocks),
            blocks_failed=0 if success else len(preview_blocks),
            errors=[] if success else ["Failed to spawn preview"],
            duration_ms=0
        )
    
    async def approve_preview(self, preview_id: str) -> ExecutionResult:
        """Convert preview blocks to real blocks"""
        if preview_id not in self.pending_previews:
            return ExecutionResult(
                success=False,
                blocks_placed=0,
                blocks_failed=0,
                errors=[f"Preview {preview_id} not found"],
                duration_ms=0
            )
        
        preview_blocks = self.pending_previews[preview_id]
        
        # Convert to real block placements
        message = {
            "action": "convert_preview",
            "preview_id": preview_id,
            "blocks": preview_blocks
        }
        
        success = await self.ws_client.send(message)
        
        # Clean up
        del self.pending_previews[preview_id]
        
        return ExecutionResult(
            success=success,
            blocks_placed=len(preview_blocks) if success else 0,
            blocks_failed=0 if success else len(preview_blocks),
            errors=[] if success else ["Failed to convert preview"],
            duration_ms=0
        )
    
    async def discard_preview(self, preview_id: str) -> ExecutionResult:
        """Remove preview blocks without placing"""
        if preview_id not in self.pending_previews:
            return ExecutionResult(
                success=False,
                blocks_placed=0,
                blocks_failed=0,
                errors=[f"Preview {preview_id} not found"],
                duration_ms=0
            )
        
        message = {
            "action": "remove_ghost_blocks",
            "preview_id": preview_id
        }
        
        success = await self.ws_client.send(message)
        
        # Clean up
        del self.pending_previews[preview_id]
        
        return ExecutionResult(
            success=success,
            blocks_placed=0,
            blocks_failed=0,
            errors=[] if success else ["Failed to discard preview"],
            duration_ms=0
        )
    
    async def scan_area(
        self, 
        origin: Vector3, 
        radius: int = 10
    ) -> Dict[Tuple[int, int, int], str]:
        """Scan an area and return block types"""
        message = {
            "action": "scan_area",
            "origin": {"x": origin.x, "y": origin.y, "z": origin.z},
            "radius": radius
        }
        
        await self.ws_client.send(message)
        response = await self.ws_client.receive()
        
        if response and response.get("action") == "scan_result":
            return {(b["x"], b["y"], b["z"]): b["block"] for b in response.get("blocks", [])}
        
        return {}
