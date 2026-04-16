"""
Minecraft Omni-Builder v3.1 - Command Parser Module
Converts natural language commands to structured BuildIntent objects
"""
import re
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from enum import Enum


class CommandType(Enum):
    BUILD = "build"
    PREVIEW = "preview"
    APPROVE = "approve"
    DISCARD = "discard"
    UNDO = "undo"
    FLATTEN = "flatten"
    SWITCH_STYLE = "switch_style"
    LIKE = "like"
    DISLIKE = "dislike"
    DIFF = "diff"
    REVERT = "revert"
    COMMIT = "commit"


@dataclass
class Vector3:
    x: int
    y: int
    z: int
    
    def __add__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __sub__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)


@dataclass
class Bounds:
    min_pos: Vector3
    max_pos: Vector3
    
    @property
    def volume(self) -> int:
        dx = abs(self.max_pos.x - self.min_pos.x) + 1
        dy = abs(self.max_pos.y - self.min_pos.y) + 1
        dz = abs(self.max_pos.z - self.min_pos.z) + 1
        return dx * dy * dz


@dataclass
class BuildIntent:
    command_type: CommandType
    target: str  # e.g., "rocket", "castle"
    position: Optional[Vector3] = None
    bounds: Optional[Bounds] = None
    style: Optional[str] = None
    count: int = 1  # For undo N operations
    build_id: Optional[str] = None
    version_a: Optional[str] = None
    version_b: Optional[str] = None
    context: dict = field(default_factory=dict)


class CommandParser:
    """
    Parses Minecraft chat commands into structured intents.
    Supports relative positioning (in front of me, here, at x,y,z)
    """
    
    # Regex patterns for command extraction
    PATTERNS = {
        CommandType.BUILD: re.compile(
            r'!bot\s+build\s+(?:me\s+)?(?P<target>[a-zA-Z]\w*)(?:\s+(?:me\s+)?(?:a|an|the)?\s*(?P<description>[\w\s]+?))?(?:\s+(?:at|here|in front of me|behind me|left of me|right of me))?(?:\s+(?P<coords>\d+,\d+,\d+))?',
            re.IGNORECASE
        ),
        CommandType.PREVIEW: re.compile(
            r'!bot\s+preview\s+(?:(?:a|an|the)\s+)?(?P<target>[a-zA-Z]\w*)(?:\s+(?:at|here))?(?:\s+(?P<coords>\d+,\d+,\d+))?',
            re.IGNORECASE
        ),
        CommandType.UNDO: re.compile(
            r'!bot\s+undo(?:\s+last\s+(?P<count>\d+))?',
            re.IGNORECASE
        ),
        CommandType.SWITCH_STYLE: re.compile(
            r'!bot\s+switch\s+to\s+(?P<style>[\w\s]+?)\s+style',
            re.IGNORECASE
        ),
        CommandType.COMMIT: re.compile(
            r'!bot\s+commit\s+(?P<message>[\w\s]+)',
            re.IGNORECASE
        ),
        CommandType.REVERT: re.compile(
            r'!bot\s+revert\s+(?P<version>[\w\-]+)',
            re.IGNORECASE
        ),
        CommandType.DIFF: re.compile(
            r'!bot\s+diff\s+(?P<version_a>[\w\-]+)\s+(?P<version_b>[\w\-]+)',
            re.IGNORECASE
        ),
    }
    
    DIRECTION_OFFSETS = {
        "north": Vector3(0, 0, -1),
        "south": Vector3(0, 0, 1),
        "east": Vector3(1, 0, 0),
        "west": Vector3(-1, 0, 0),
    }
    
    def __init__(self):
        self.player_positions = {}  # UUID -> Vector3
    
    def set_player_position(self, player_uuid: str, pos: Vector3):
        """Track player position for relative commands"""
        self.player_positions[player_uuid] = pos
    
    def parse(self, command: str, player_uuid: Optional[str] = None) -> Optional[BuildIntent]:
        """
        Parse a chat command string into BuildIntent
        
        Args:
            command: Raw chat message (e.g., "!bot build rocket at 100,64,200")
            player_uuid: Player's UUID for relative positioning
            
        Returns:
            BuildIntent or None if command not recognized
        """
        command = command.strip()
        
        # Check for simple commands without regex
        if command.lower() in ["!bot approve", "!bot approve"]:
            return BuildIntent(command_type=CommandType.APPROVE, target="")
        if command.lower() in ["!bot discard", "!bot discard"]:
            return BuildIntent(command_type=CommandType.DISCARD, target="")
        if command.lower() in ["!bot like", "!bot like"]:
            return BuildIntent(command_type=CommandType.LIKE, target="")
        if command.lower() in ["!bot dislike", "!bot dislike"]:
            return BuildIntent(command_type=CommandType.DISLIKE, target="")
        
        # Try each pattern
        for cmd_type, pattern in self.PATTERNS.items():
            match = pattern.match(command)
            if match:
                groups = match.groupdict()
                return self._build_intent(cmd_type, groups, player_uuid)
        
        return None
    
    def _build_intent(self, cmd_type: CommandType, groups: dict, player_uuid: Optional[str]) -> BuildIntent:
        """Construct BuildIntent from regex groups"""
        intent = BuildIntent(command_type=cmd_type, target=groups.get("target", ""))
        
        # Parse coordinates if present
        coords_str = groups.get("coords")
        if coords_str:
            try:
                x, y, z = map(int, coords_str.split(","))
                intent.position = Vector3(x, y, z)
            except ValueError:
                pass
        
        # Handle relative positioning
        elif player_uuid and player_uuid in self.player_positions:
            player_pos = self.player_positions[player_uuid]
            intent.position = self._resolve_relative(groups.get("target", ""), player_pos)
        
        # Parse count for undo
        if cmd_type == CommandType.UNDO and groups.get("count"):
            intent.count = int(groups["count"])
        
        # Parse style
        if cmd_type == CommandType.SWITCH_STYLE and groups.get("style"):
            intent.style = groups["style"].strip()
        
        # Parse versions
        if cmd_type == CommandType.DIFF:
            intent.version_a = groups.get("version_a")
            intent.version_b = groups.get("version_b")
        
        if cmd_type == CommandType.REVERT:
            intent.version_a = groups.get("version")
        
        if cmd_type == CommandType.COMMIT:
            intent.context["message"] = groups.get("message", "")
        
        return intent
    
    def _resolve_relative(self, target: str, player_pos: Vector3) -> Vector3:
        """
        Resolve relative positioning keywords
        Currently supports basic "here" interpretation
        """
        target_lower = target.lower()
        
        if "in front" in target_lower:
            # Would need player rotation for accurate direction
            return player_pos + Vector3(0, 0, -5)
        elif "behind" in target_lower:
            return player_pos + Vector3(0, 0, 5)
        elif "left" in target_lower:
            return player_pos + Vector3(-5, 0, 0)
        elif "right" in target_lower:
            return player_pos + Vector3(5, 0, 0)
        else:
            # Default: slight offset in front
            return player_pos + Vector3(0, 0, -3)
