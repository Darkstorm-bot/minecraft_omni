"""
Minecraft Omni-Builder v3.1 - Block State Registry Module
Validates and resolves block types with state properties
Supports dynamic loading from server for mod compatibility
"""
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any, Set
import json
from pathlib import Path


@dataclass
class BlockData:
    """Represents a Minecraft block with validated state"""
    block_type: str
    state: Dict[str, str] = field(default_factory=dict)
    nbt: Optional[Dict[str, Any]] = None
    
    def to_minecraft_string(self) -> str:
        """Convert to Minecraft block string format"""
        if not self.state:
            return self.block_type
        
        state_str = ",".join(f"{k}={v}" for k, v in self.state.items())
        return f"{self.block_type}[{state_str}]"
    
    def __str__(self) -> str:
        return self.to_minecraft_string()


class BlockStateRegistry:
    """
    Manages block type validation and state resolution.
    
    Loads block definitions from server API for mod support
    (Create, Mekanism, etc.)
    
    Features:
    - Validate block existence
    - Resolve block states (facing, half, etc.)
    - Convert tool calls to Minecraft BlockData
    """
    
    def __init__(self, registry_path: str = "config/blocks.json"):
        self.registry_path = Path(registry_path)
        self.blocks: Dict[str, Dict[str, List[str]]] = {}
        self.valid_blocks: Set[str] = set()
        
        # Load from file or use defaults
        if self.registry_path.exists():
            self._load_from_file()
        else:
            self._load_defaults()
    
    def _load_from_file(self):
        """Load block registry from JSON file"""
        try:
            with open(self.registry_path, 'r') as f:
                data = json.load(f)
                self.blocks = data.get("blocks", {})
                self._index_valid_blocks()
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load block registry: {e}")
            self._load_defaults()
    
    def _load_defaults(self):
        """Load default vanilla Minecraft blocks"""
        self.blocks = {
            "stone": {},
            "cobblestone": {},
            "dirt": {},
            "grass_block": {},
            "oak_log": {"axis": ["x", "y", "z"]},
            "spruce_log": {"axis": ["x", "y", "z"]},
            "birch_log": {"axis": ["x", "y", "z"]},
            "oak_planks": {},
            "spruce_planks": {},
            "birch_planks": {},
            "bricks": {},
            "stone_bricks": {},
            "glass": {},
            "torch": {"facing": ["north", "south", "east", "west", "up"]},
            "lantern": {"hanging": ["true", "false"]},
            "oak_stairs": {
                "facing": ["north", "south", "east", "west"],
                "half": ["top", "bottom"],
                "shape": ["straight", "inner_left", "inner_right", "outer_left", "outer_right"]
            },
            "spruce_stairs": {
                "facing": ["north", "south", "east", "west"],
                "half": ["top", "bottom"],
                "shape": ["straight", "inner_left", "inner_right", "outer_left", "outer_right"]
            },
            "slab": {
                "type": ["top", "bottom", "double"]
            },
            "water": {"level": ["0", "1", "2", "3", "4", "5", "6", "7", "8"]},
            "lava": {"level": ["0", "1", "2", "3", "4", "5", "6", "7", "8"]},
            "sand": {},
            "gravel": {},
            "coal_ore": {},
            "iron_ore": {},
            "gold_ore": {},
            "diamond_ore": {},
            "redstone_ore": {},
            "emerald_ore": {},
            "quartz_block": {},
            "white_concrete": {},
            "black_concrete": {},
            "gray_concrete": {},
            "wool": {"color": ["white", "orange", "magenta", "light_blue", "yellow", 
                              "lime", "pink", "gray", "light_gray", "cyan", 
                              "purple", "blue", "brown", "green", "red", "black"]},
            "bedrock": {},
            "obsidian": {},
            "end_stone": {},
            "purpur_block": {},
            "prismarine": {},
            "sea_lantern": {},
            "glowstone": {},
            "netherrack": {},
            "soul_sand": {},
            "bone_block": {"axis": ["x", "y", "z"]},
        }
        self._index_valid_blocks()
    
    def _index_valid_blocks(self):
        """Build set of valid block names for quick lookup"""
        self.valid_blocks = set(self.blocks.keys())
    
    def is_valid_block(self, block_type: str) -> bool:
        """Check if a block type exists in the registry"""
        return block_type.lower() in self.valid_blocks
    
    def get_valid_states(self, block_type: str) -> Dict[str, List[str]]:
        """Get valid state properties for a block type"""
        return self.blocks.get(block_type.lower(), {})
    
    def resolve(self, tool_call: dict) -> Optional[BlockData]:
        """
        Convert tool call parameters to validated BlockData
        
        Args:
            tool_call: Dict with "block" and optional "state" keys
            
        Returns:
            BlockData if valid, None if invalid
        """
        base = tool_call.get("block", "").lower().replace(" ", "_")
        props = tool_call.get("state", {})
        
        if not self.is_valid_block(base):
            return None
        
        # Get valid properties for this block
        valid_props = self.get_valid_states(base)
        
        # Filter to only valid properties
        resolved = {}
        for key, value in props.items():
            if key in valid_props:
                allowed_values = valid_props[key]
                if value in allowed_values:
                    resolved[key] = value
                else:
                    # Try to find closest match
                    for allowed in allowed_values:
                        if allowed.startswith(value) or value.startswith(allowed):
                            resolved[key] = allowed
                            break
        
        nbt = tool_call.get("nbt")
        
        return BlockData(
            block_type=base,
            state=resolved,
            nbt=nbt
        )
    
    def resolve_batch(self, tool_calls: List[dict]) -> List[Optional[BlockData]]:
        """Resolve multiple tool calls to BlockData"""
        return [self.resolve(tc) for tc in tool_calls]
    
    def add_dynamic_block(self, block_type: str, states: Dict[str, List[str]]):
        """
        Add a block dynamically (for mod support)
        
        Args:
            block_type: Block name
            states: Dict of state properties and their allowed values
        """
        block_type = block_type.lower().replace(" ", "_")
        self.blocks[block_type] = states
        self.valid_blocks.add(block_type)
    
    def load_server_registry(self, server_url: str) -> bool:
        """
        Load block registry from running server API
        
        Args:
            server_url: URL to server's block registry endpoint
            
        Returns:
            True if successful
        """
        try:
            import requests
            response = requests.get(f"{server_url}/api/blocks")
            if response.status_code == 200:
                data = response.json()
                self.blocks = data.get("blocks", {})
                self._index_valid_blocks()
                return True
        except Exception as e:
            print(f"Could not load server registry: {e}")
        
        return False
    
    def save_to_file(self, path: Optional[str] = None):
        """Save current registry to JSON file"""
        save_path = Path(path) if path else self.registry_path
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(save_path, 'w') as f:
            json.dump({"blocks": self.blocks}, f, indent=2)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics"""
        total_blocks = len(self.valid_blocks)
        blocks_with_states = sum(1 for b in self.blocks.values() if b)
        total_states = sum(len(states) for states in self.blocks.values())
        
        return {
            "total_blocks": total_blocks,
            "blocks_with_states": blocks_with_states,
            "total_state_properties": total_states,
            "avg_states_per_block": total_states / total_blocks if total_blocks > 0 else 0
        }
