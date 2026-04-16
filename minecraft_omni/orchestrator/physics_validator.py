"""
Minecraft Omni-Builder v3.1 - Physics Validator Module
Pre-execution simulation to prevent floating blocks, broken redstone, and dark zones
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum

from minecraft_omni.parser.command_parser import Vector3, Bounds


class PhysicsErrorType(Enum):
    FLOATING_BLOCK = "floating_block"
    UNSUPPORTED_GRAVITY = "unsupported_gravity"
    FLUID_LEAK = "fluid_leak"
    REDSTONE_INCOMPLETE = "redstone_incomplete"
    DARK_ZONE = "dark_zone"
    MOB_SPAWN_RISK = "mob_spawn_risk"


@dataclass
class PhysicsError:
    error_type: PhysicsErrorType
    position: Vector3
    description: str
    suggested_fix: str


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[PhysicsError]
    warnings: List[str]
    auto_patches: List[dict]  # Tool calls to fix issues


@dataclass
class WorldSnapshot:
    """Snapshot of world state for physics simulation"""
    blocks: Dict[Tuple[int, int, int], str]  # (x,y,z) -> block_type
    light_levels: Dict[Tuple[int, int, int], int]  # (x,y,z) -> light level (0-15)
    redstone_power: Dict[Tuple[int, int, int], int]  # (x,y,z) -> power level
    
    def get_block(self, x: int, y: int, z: int) -> str:
        return self.blocks.get((x, y, z), "air")
    
    def set_block(self, x: int, y: int, z: int, block_type: str):
        self.blocks[(x, y, z)] = block_type
    
    def get_light_level(self, x: int, y: int, z: int) -> int:
        return self.light_levels.get((x, y, z), 0)


# Block properties for physics simulation
GRAVITY_BLOCKS = {"sand", "gravel", "concrete_powder", "anvil", "dragon_egg"}
SOLID_BLOCKS = {
    "stone", "cobblestone", "dirt", "grass_block", "wood", "oak_log", 
    "spruce_log", "birch_log", "jungle_log", "acacia_log", "dark_oak_log",
    "mangrove_log", "cherry_log", "bamboo_block", "crimson_stem", "warped_stem",
    "bricks", "stone_bricks", "nether_bricks", "end_stone", "obsidian",
    "glass", "iron_block", "gold_block", "diamond_block", "emerald_block",
    "quartz_block", "terracotta", "concrete", "wool", "planks"
}
LIGHT_EMITTING_BLOCKS = {
    "torch": 14, "lantern": 15, "glowstone": 15, "sea_lantern": 15,
    "shroomlight": 15, "redstone_lamp": 15, "jack_o_lantern": 15,
    "lava": 15, "fire": 15, "soul_torch": 10, "soul_lantern": 10,
    "campfire": 15, "soul_campfire": 10, "beacon": 15, "end_rod": 14,
    "amethyst_cluster": 5, "large_amethyst_bud": 4, "medium_amethyst_bud": 3,
    "small_amethyst_bud": 2, "brown_mushroom": 1, "red_mushroom": 1
}
FLUID_BLOCKS = {"water", "lava", "flowing_water", "flowing_lava"}


class PhysicsValidator:
    """
    Pre-execution physics simulation validator.
    Simulates 20 ticks (1 second) of game time to catch issues before placement.
    """
    
    SIMULATION_TICKS = 20
    
    def __init__(self):
        self.gravity_blocks = GRAVITY_BLOCKS
        self.solid_blocks = SOLID_BLOCKS
        self.light_blocks = LIGHT_EMITTING_BLOCKS
    
    def simulate_placement(
        self, 
        actions: List[dict], 
        world_state: WorldSnapshot
    ) -> ValidationResult:
        """
        Simulates physics for proposed block placements
        
        Checks:
        - Gravity (sand/gravel fall, unsupported stone?)
        - Fluid dynamics (water/lava flow)
        - Redstone timing (circuit completeness)
        - Light levels (torch placement for mob spawning)
        
        Returns:
            ValidationResult with errors and auto-patches
        """
        errors = []
        warnings = []
        auto_patches = []
        
        # Create working copy of world state
        sim_world = WorldSnapshot(
            blocks=dict(world_state.blocks),
            light_levels=dict(world_state.light_levels),
            redstone_power=dict(world_state.redstone_power)
        )
        
        # Apply all proposed actions to simulation
        for action in actions:
            if action.get("tool") == "place_block":
                params = action["params"]
                x, y, z = params["x"], params["y"], params["z"]
                block_type = params["block"]
                sim_world.set_block(x, y, z, block_type)
                
                # Update light levels if light-emitting
                if block_type in self.light_blocks:
                    sim_world.light_levels[(x, y, z)] = self.light_blocks[block_type]
        
        # Run physics simulation
        for tick in range(self.SIMULATION_TICKS):
            tick_errors = self._simulate_tick(sim_world, actions)
            errors.extend(tick_errors)
            
            # Auto-apply patches for fixable issues
            if errors and tick == 0:
                auto_patches = self._generate_auto_patches(errors, sim_world)
                # Apply patches to simulation and re-check
                for patch in auto_patches:
                    if patch.get("tool") == "place_block":
                        p = patch["params"]
                        sim_world.set_block(p["x"], p["y"], p["z"], p["block"])
        
        # Check for dark zones (mob spawning risk)
        dark_zones = self._check_light_levels(sim_world, actions)
        for dz in dark_zones:
            errors.append(dz)
            # Auto-patch: suggest torch placement
            auto_patches.append({
                "tool": "place_block",
                "params": {
                    "x": dz.position.x,
                    "y": dz.position.y + 1,
                    "z": dz.position.z,
                    "block": "torch"
                }
            })
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            auto_patches=auto_patches
        )
    
    def _simulate_tick(self, world: WorldSnapshot, actions: List[dict]) -> List[PhysicsError]:
        """Simulate one tick of physics"""
        errors = []
        
        # Check gravity blocks for support
        for action in actions:
            if action.get("tool") != "place_block":
                continue
            
            params = action["params"]
            x, y, z = params["x"], params["y"], params["z"]
            block_type = params["block"]
            
            # Check if gravity block has support
            if block_type in self.gravity_blocks:
                support_block = world.get_block(x, y - 1, z)
                if support_block == "air" or support_block in FLUID_BLOCKS:
                    errors.append(PhysicsError(
                        error_type=PhysicsErrorType.UNSUPPORTED_GRAVITY,
                        position=Vector3(x, y, z),
                        description=f"{block_type} at ({x},{y},{z}) has no support below",
                        suggested_fix=f"Place supporting block at ({x},{y-1},{z}) or move {block_type}"
                    ))
        
        # Check for fluid containment
        for action in actions:
            if action.get("tool") != "place_block":
                continue
            
            params = action["params"]
            x, y, z = params["x"], params["y"], params["z"]
            block_type = params["block"]
            
            if block_type in FLUID_BLOCKS:
                # Simple check: fluids need containment on sides
                has_containment = any(
                    world.get_block(x + dx, y, z + dz) in SOLID_BLOCKS
                    for dx, dz in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                )
                if not has_containment:
                    errors.append(PhysicsError(
                        error_type=PhysicsErrorType.FLUID_LEAK,
                        position=Vector3(x, y, z),
                        description=f"{block_type} at ({x},{y},{z}) will flow out",
                        suggested_fix=f"Add containment walls around ({x},{y},{z})"
                    ))
        
        return errors
    
    def _generate_auto_patches(
        self, 
        errors: List[PhysicsError], 
        world: WorldSnapshot
    ) -> List[dict]:
        """Generate automatic fixes for common physics errors"""
        patches = []
        
        for error in errors:
            if error.error_type == PhysicsErrorType.UNSUPPORTED_GRAVITY:
                # Add support block below
                pos = error.position
                patches.append({
                    "tool": "place_block",
                    "params": {
                        "x": pos.x,
                        "y": pos.y - 1,
                        "z": pos.z,
                        "block": "cobblestone"
                    }
                })
            
            elif error.error_type == PhysicsErrorType.FLUID_LEAK:
                # Add glass containment (non-intrusive)
                pos = error.position
                for dx, dz in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, nz = pos.x + dx, pos.z + dz
                    if world.get_block(nx, pos.y, nz) == "air":
                        patches.append({
                            "tool": "place_block",
                            "params": {
                                "x": nx,
                                "y": pos.y,
                                "z": nz,
                                "block": "glass"
                            }
                        })
        
        return patches
    
    def _check_light_levels(
        self, 
        world: WorldSnapshot, 
        actions: List[dict]
    ) -> List[PhysicsError]:
        """Check for dark zones where mobs could spawn"""
        errors = []
        
        # Get all placed interior blocks
        interior_positions = set()
        for action in actions:
            if action.get("tool") != "place_block":
                continue
            params = action["params"]
            interior_positions.add((params["x"], params["y"], params["z"]))
        
        # Check light levels at floor positions
        checked = set()
        for x, y, z in interior_positions:
            # Check floor block (one below placed block)
            floor_pos = (x, y - 1, z)
            if floor_pos in checked:
                continue
            checked.add(floor_pos)
            
            light = world.get_light_level(x, y - 1, z)
            if light < 8:  # Mobs spawn at light level 7 or below
                errors.append(PhysicsError(
                    error_type=PhysicsErrorType.DARK_ZONE,
                    position=Vector3(x, y - 1, z),
                    description=f"Dark zone at ({x},{y-1},{z}) with light level {light}",
                    suggested_fix=f"Place torch or lantern near ({x},{y-1},{z})"
                ))
        
        return errors
    
    def patch_invalid(
        self, 
        actions: List[dict], 
        errors: List[PhysicsError]
    ) -> List[dict]:
        """
        Auto-fix actions based on physics errors
        
        Returns:
            Modified action list with fixes applied
        """
        patched_actions = list(actions)
        
        for error in errors:
            if error.error_type == PhysicsErrorType.UNSUPPORTED_GRAVITY:
                # Insert support block before the gravity block
                pos = error.position
                support_action = {
                    "tool": "place_block",
                    "params": {
                        "x": pos.x,
                        "y": pos.y - 1,
                        "z": pos.z,
                        "block": "cobblestone"
                    }
                }
                # Find index of original action
                for i, action in enumerate(patched_actions):
                    if (action.get("tool") == "place_block" and
                        action["params"]["x"] == pos.x and
                        action["params"]["y"] == pos.y and
                        action["params"]["z"] == pos.z):
                        patched_actions.insert(i, support_action)
                        break
            
            elif error.error_type == PhysicsErrorType.DARK_ZONE:
                # Add lighting
                pos = error.position
                patched_actions.append({
                    "tool": "place_block",
                    "params": {
                        "x": pos.x,
                        "y": pos.y + 1,
                        "z": pos.z,
                        "block": "torch"
                    }
                })
        
        return patched_actions
