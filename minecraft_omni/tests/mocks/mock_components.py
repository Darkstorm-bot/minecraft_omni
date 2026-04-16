"""
Minecraft Omni-Builder v3.1 - Mock Testing Components
Provides mock implementations for offline testing and CI
"""
from typing import Dict, List, Optional, Any
from collections import defaultdict
import asyncio


class MockMinecraftClient:
    """
    Mock Minecraft client for testing without server connection
    
    Simulates:
    - Block placement/deletion
    - World state tracking
    - TPS monitoring
    - Area scanning
    """

    def __init__(self):
        self.world: Dict[tuple, str] = defaultdict(lambda: "air")
        self.tps = 20.0
        self.dimension = "overworld"
        self.placement_history: List[Dict] = []

    async def place_blocks(self, blocks: List[Dict]) -> int:
        """Place multiple blocks in the mock world"""
        placed = 0
        for block in blocks:
            x = block.get("x", 0)
            y = block.get("y", 64)
            z = block.get("z", 0)
            block_type = block.get("type", "stone")
            
            self.world[(x, y, z)] = block_type
            placed += 1
            
            self.placement_history.append({
                "action": "place",
                "x": x, "y": y, "z": z,
                "type": block_type
            })
        
        return placed

    async def delete_blocks(self, positions: List[tuple]) -> int:
        """Delete blocks at specified positions"""
        deleted = 0
        for pos in positions:
            if isinstance(pos, tuple) and len(pos) >= 3:
                x, y, z = pos[:3]
                if self.world[(x, y, z)] != "air":
                    self.world[(x, y, z)] = "air"
                    deleted += 1
                    
                    self.placement_history.append({
                        "action": "delete",
                        "x": x, "y": y, "z": z
                    })
        
        return deleted

    async def get_block_at(self, x: int, y: int, z: int) -> str:
        """Get block type at position"""
        return self.world[(x, y, z)]

    async def scan_area(
        self,
        x_min: int, y_min: int, z_min: int,
        x_max: int, y_max: int, z_max: int
    ) -> Dict[tuple, str]:
        """Scan a region and return all non-air blocks"""
        result = {}
        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                for z in range(z_min, z_max + 1):
                    block = self.world[(x, y, z)]
                    if block != "air":
                        result[(x, y, z)] = block
        return result

    async def get_chunk_hash(self, x_min: int, z_min: int, x_max: int, z_max: int) -> str:
        """Compute a simple hash of chunk contents"""
        import hashlib
        hasher = hashlib.sha256()
        
        for x in range(x_min, x_max + 1, 4):
            for z in range(z_min, z_max + 1, 4):
                for y in range(-64, 320, 4):
                    block = self.world[(x, y, z)]
                    hasher.update(f"{x}:{y}:{z}:{block}".encode())
        
        return hasher.hexdigest()

    def set_tps(self, tps: float):
        """Simulate TPS changes"""
        self.tps = max(0.0, min(20.0, tps))

    def get_tps(self) -> float:
        """Get current simulated TPS"""
        return self.tps

    def clear_world(self):
        """Reset the mock world"""
        self.world.clear()
        self.placement_history.clear()

    def get_statistics(self) -> Dict[str, Any]:
        """Get world statistics"""
        non_air = sum(1 for b in self.world.values() if b != "air")
        return {
            "total_blocks": non_air,
            "tps": self.tps,
            "dimension": self.dimension,
            "placements_tracked": len(self.placement_history),
        }


class DeterministicLLM:
    """
    Deterministic LLM mock for reproducible testing
    
    Returns canned responses based on seed or prompt patterns
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.call_count = 0
        self.response_templates = {
            "rocket": self._rocket_response(),
            "house": self._house_response(),
            "bridge": self._bridge_response(),
            "default": self._default_response(),
        }

    def generate(self, prompt: str, seed: Optional[int] = None) -> Dict:
        """Generate a deterministic response based on prompt content"""
        self.call_count += 1
        use_seed = seed if seed is not None else self.seed

        # Match prompt to template
        prompt_lower = prompt.lower()
        if "rocket" in prompt_lower:
            return self.response_templates["rocket"]
        elif "house" in prompt_lower or "build" in prompt_lower:
            return self.response_templates["house"]
        elif "bridge" in prompt_lower:
            return self.response_templates["bridge"]
        else:
            return self.response_templates["default"]

    def _rocket_response(self) -> Dict:
        """Canned response for rocket builds"""
        return {
            "zones": [
                {
                    "name": "Base",
                    "purpose": "Rocket foundation and launch pad",
                    "bounds": {"x_min": 0, "y_min": 0, "z_min": 0, "x_max": 10, "y_max": 5, "z_max": 10},
                    "materials": ["stone_bricks", "iron_block"],
                    "components": [
                        {
                            "name": "Launch Pad",
                            "description": "Flat stone platform",
                            "block_count": 100,
                            "tool_calls": []
                        }
                    ]
                },
                {
                    "name": "Body",
                    "purpose": "Main rocket structure",
                    "bounds": {"x_min": 2, "y_min": 6, "z_min": 2, "x_max": 8, "y_max": 30, "z_max": 8},
                    "materials": ["white_concrete", "quartz_block"],
                    "components": [
                        {
                            "name": "Cylindrical Shell",
                            "description": "White concrete cylinder",
                            "block_count": 400,
                            "tool_calls": []
                        }
                    ]
                },
                {
                    "name": "Nose Cone",
                    "purpose": "Aerodynamic tip",
                    "bounds": {"x_min": 3, "y_min": 31, "z_min": 3, "x_max": 7, "y_max": 40, "z_max": 7},
                    "materials": ["red_concrete"],
                    "components": [
                        {
                            "name": "Pointed Top",
                            "description": "Tapered red cone",
                            "block_count": 80,
                            "tool_calls": []
                        }
                    ]
                }
            ],
            "templates": [],
            "estimated_blocks": 580,
            "complexity": "medium"
        }

    def _house_response(self) -> Dict:
        """Canned response for house builds"""
        return {
            "zones": [
                {
                    "name": "Foundation",
                    "purpose": "House base and floor",
                    "bounds": {"x_min": 0, "y_min": 0, "z_min": 0, "x_max": 15, "y_max": 1, "z_max": 12},
                    "materials": ["cobblestone", "oak_planks"],
                    "components": []
                },
                {
                    "name": "Walls",
                    "purpose": "Exterior walls",
                    "bounds": {"x_min": 0, "y_min": 2, "z_min": 0, "x_max": 15, "y_max": 8, "z_max": 12},
                    "materials": ["oak_log", "bricks"],
                    "components": []
                },
                {
                    "name": "Roof",
                    "purpose": "Sloped roof covering",
                    "bounds": {"x_min": -1, "y_min": 9, "z_min": -1, "x_max": 16, "y_max": 15, "z_max": 13},
                    "materials": ["spruce_stairs", "spruce_slab"],
                    "components": []
                }
            ],
            "templates": [],
            "estimated_blocks": 850,
            "complexity": "medium"
        }

    def _bridge_response(self) -> Dict:
        """Canned response for bridge builds"""
        return {
            "zones": [
                {
                    "name": "Deck",
                    "purpose": "Walking surface",
                    "bounds": {"x_min": 0, "y_min": 10, "z_min": 0, "x_max": 50, "y_max": 11, "z_max": 5},
                    "materials": ["stone_slab", "cobblestone_wall"],
                    "components": []
                },
                {
                    "name": "Supports",
                    "purpose": "Bridge pillars",
                    "bounds": {"x_min": 0, "y_min": 0, "z_min": 0, "x_max": 50, "y_max": 9, "z_max": 5},
                    "materials": ["stone_bricks", "andesite"],
                    "components": []
                }
            ],
            "templates": [],
            "estimated_blocks": 600,
            "complexity": "medium"
        }

    def _default_response(self) -> Dict:
        """Default generic response"""
        return {
            "zones": [
                {
                    "name": "Main Structure",
                    "purpose": "Primary build area",
                    "bounds": {"x_min": 0, "y_min": 0, "z_min": 0, "x_max": 10, "y_max": 10, "z_max": 10},
                    "materials": ["stone"],
                    "components": []
                }
            ],
            "templates": [],
            "estimated_blocks": 100,
            "complexity": "low"
        }

    def reset(self):
        """Reset call counter"""
        self.call_count = 0


class BuildValidator:
    """
    Validates build integrity for testing
    
    Checks:
    - Structural stability (floating blocks)
    - Lighting coverage
    - Material validity
    - Boundary compliance
    """

    def __init__(self):
        self.support_required_blocks = {
            "stone", "cobblestone", "bricks", "wood", "log",
            "concrete", "wool", "glass", "quartz"
        }

    def check_integrity(self, blocks: List[Dict]) -> List[str]:
        """
        Check build for common issues
        
        Returns list of error codes
        """
        errors = []
        
        if self._has_floating_blocks(blocks):
            errors.append("UNSTABLE_SUPPORT")
        
        if self._has_dark_zones(blocks):
            errors.append("DARK_ZONE")
        
        if self._has_invalid_materials(blocks):
            errors.append("INVALID_MATERIAL")
        
        return errors

    def _has_floating_blocks(self, blocks: List[Dict]) -> bool:
        """Check for blocks without support below"""
        block_positions = {(b["x"], b["y"], b["z"]) for b in blocks}
        
        for block in blocks:
            x, y, z = block["x"], block["y"], block["z"]
            block_type = block.get("type", "")
            
            # Skip bedrock and blocks at y=0
            if y <= 0 or block_type == "bedrock":
                continue
            
            # Check if there's a block below
            if (x, y - 1, z) not in block_positions:
                # This block is floating
                return True
        
        return False

    def _has_dark_zones(self, blocks: List[Dict]) -> bool:
        """Check for areas without light sources"""
        light_sources = {"torch", "lantern", "glowstone", "sea_lantern", "shroomlight"}
        
        has_light = any(
            block.get("type", "") in light_sources
            for block in blocks
        )
        
        # Simple heuristic: large builds need lighting
        if len(blocks) > 100 and not has_light:
            return True
        
        return False

    def _has_invalid_materials(self, blocks: List[Dict]) -> bool:
        """Check for blacklisted materials"""
        blacklist = {"bedrock", "command_block", "barrier", "structure_void"}
        
        return any(
            block.get("type", "") in blacklist
            for block in blocks
        )

    def validate_tool_calls(self, tool_calls: List[Dict]) -> List[str]:
        """Validate a list of tool calls"""
        errors = []
        
        for i, call in enumerate(tool_calls):
            if "tool" not in call:
                errors.append(f"Tool call {i}: missing 'tool' field")
            if "params" not in call:
                errors.append(f"Tool call {i}: missing 'params' field")
            elif "x" not in call["params"]:
                errors.append(f"Tool call {i}: missing 'x' coordinate")
        
        return errors
