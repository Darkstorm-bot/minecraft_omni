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
    
    # Regex patterns for command extraction (OrderedDict to preserve order)
    PATTERNS = [
        # Specific patterns first
        (CommandType.BUILD, re.compile(
            r'!bot\s+build\s+(?:(?:me\s+)?(?:a|an|the)\s+)?(?P<target>[a-zA-Z]\w*)(?:\s+(?P<description>[\w\s]+?))?(?:\s+(?P<coords>\d+,\d+,\d+))?',
            re.IGNORECASE
        )),
        (CommandType.PREVIEW, re.compile(
            r'!bot\s+preview\s+(?:(?:a|an|the)\s+)?(?P<target>[a-zA-Z]\w*)(?:\s+(?P<coords>\d+,\d+,\d+))?',
            re.IGNORECASE
        )),
        (CommandType.UNDO, re.compile(
            r'!bot\s+undo(?:\s+last\s+(?P<count>\d+))?',
            re.IGNORECASE
        )),
        (CommandType.SWITCH_STYLE, re.compile(
            r'!bot\s+switch\s+to\s+(?P<style>[\w\s]+?)\s+style',
            re.IGNORECASE
        )),
        (CommandType.COMMIT, re.compile(
            r'!bot\s+commit\s+(?P<message>[\w\s]+)',
            re.IGNORECASE
        )),
        (CommandType.REVERT, re.compile(
            r'!bot\s+revert\s+(?P<version>[\w\-]+)',
            re.IGNORECASE
        )),
        (CommandType.DIFF, re.compile(
            r'!bot\s+diff\s+(?P<version_a>[\w\-]+)\s+(?P<version_b>[\w\-]+)',
            re.IGNORECASE
        )),
        # Relative positioning pattern (checked last as fallback for build)
        (CommandType.BUILD, re.compile(
            r'!bot\s+build\s+(?P<description>(?:\d+\s+blocks\s+)?(?:north|south|east|west|in front|behind|left|right))',
            re.IGNORECASE
        )),
    ]
    
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
            command: Raw chat command (e.g., "!bot build rocket at 100,64,200")
            player_uuid: Optional player UUID for relative positioning
            
        Returns:
            BuildIntent object or None if parsing fails
        """
        command = command.strip()
        
        # Try each pattern (PATTERNS is now a list of tuples)
        for cmd_type, pattern in self.PATTERNS:
            match = pattern.match(command)
            if match:
                return self._build_intent(cmd_type, match.groupdict(), player_uuid)
        
        return None
    
    def _build_intent(self, cmd_type: CommandType, groups: dict, player_uuid: Optional[str] = None) -> BuildIntent:
        """Construct BuildIntent from regex groups"""
        intent = BuildIntent(command_type=cmd_type, target=groups.get('target', ''))
        
        # Parse coordinates if present
        if 'coords' in groups and groups['coords']:
            coords = list(map(int, groups['coords'].split(',')))
            if len(coords) == 3:
                intent.position = Vector3(*coords)
        
        # Handle relative positioning
        if player_uuid and player_uuid in self.player_positions:
            player_pos = self.player_positions[player_uuid]
            
            # Check for directional keywords in command
            for direction, offset in self.DIRECTION_OFFSETS.items():
                if direction in groups.get('description', '').lower():
                    intent.position = player_pos + offset
                    intent.context['relative'] = True
                    break
        
        # Parse optional fields
        if 'count' in groups and groups['count']:
            intent.count = int(groups['count'])
        if 'style' in groups and groups['style']:
            intent.style = groups['style'].strip()
        if 'build_id' in groups and groups['build_id']:
            intent.build_id = groups['build_id']
        if 'version_a' in groups and groups['version_a']:
            intent.version_a = groups['version_a']
        if 'version_b' in groups and groups['version_b']:
            intent.version_b = groups['version_b']
        if 'message' in groups and groups['message']:
            intent.context['commit_message'] = groups['message']
        if 'version' in groups and groups['version']:
            intent.context['revert_version'] = groups['version']
        
        return intent
    
    def to_dict(self) -> dict:
        """Convert parser state to dictionary (for serialization)"""
        return {
            'player_positions': {k: {'x': v.x, 'y': v.y, 'z': v.z} 
                                for k, v in self.player_positions.items()}
        }
