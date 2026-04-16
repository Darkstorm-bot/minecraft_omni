"""
Minecraft Omni-Builder v3.1 - Tool Router Module
Replaces raw Python exec() with validated JSON schema tool calling
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from pydantic import BaseModel, validator, ValidationError
import json


# Tool definitions matching agent.md specification
TOOLS = {
    "place_block": {
        "description": "Place single block with state",
        "parameters": {
            "x": int,
            "y": int,
            "z": int,
            "block": str,
            "state": dict,  # {"facing": "north", "half": "bottom"}
            "nbt": Optional[dict]
        }
    },
    "fill_region": {
        "description": "Fill 3D region with block type",
        "parameters": {
            "min": [int, int, int],
            "max": [int, int, int],
            "block": str,
            "replace": Optional[str]  # Target block to replace only
        }
    },
    "carve_terrain": {
        "description": "Remove blocks (terraforming)",
        "parameters": {
            "min": [int, int, int],
            "max": [int, int, int],
            "replace_with": str  # Default "air"
        }
    },
    "set_lighting": {
        "description": "Place light sources",
        "parameters": {
            "positions": List[List[int]],
            "level": int  # 0-15
        }
    },
    "spawn_ghost_blocks": {
        "description": "Create holographic preview blocks (v3.1)",
        "parameters": {
            "blocks": List[Dict],  # [{x,y,z,block_type,alpha}]
            "client_only": bool,
            "alpha": float  # 0.0-1.0 transparency
        }
    }
}


# Pydantic models for validation
class PlaceBlockParams(BaseModel):
    x: int
    y: int
    z: int
    block: str
    state: Optional[Dict[str, str]] = None
    nbt: Optional[Dict[str, Any]] = None
    
    @validator('block')
    def validate_block_name(cls, v):
        if not v or len(v) > 64:
            raise ValueError("Invalid block name")
        return v.lower().replace(" ", "_")


class FillRegionParams(BaseModel):
    min: Tuple[int, int, int]
    max: Tuple[int, int, int]
    block: str
    replace: Optional[str] = None
    
    @validator('max')
    def validate_bounds(cls, v, values):
        if 'min' in values:
            for i in range(3):
                if v[i] < values['min'][i]:
                    raise ValueError(f"max[{i}] must be >= min[{i}]")
        return v


class CarveTerrainParams(BaseModel):
    min: Tuple[int, int, int]
    max: Tuple[int, int, int]
    replace_with: str = "air"


class SetLightingParams(BaseModel):
    positions: List[Tuple[int, int, int]]
    level: int
    
    @validator('level')
    def validate_light_level(cls, v):
        if not 0 <= v <= 15:
            raise ValueError("Light level must be 0-15")
        return v


class SpawnGhostBlocksParams(BaseModel):
    blocks: List[Dict[str, Any]]
    client_only: bool = True
    alpha: float = 0.3
    
    @validator('alpha')
    def validate_alpha(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Alpha must be 0.0-1.0")
        return v


@dataclass
class ToolCall:
    """Validated tool call ready for execution"""
    tool_name: str
    params: Dict[str, Any]
    is_valid: bool = True
    validation_error: Optional[str] = None


class ToolRouter:
    """
    Routes LLM output to validated tool calls.
    
    Security: No exec(), no code injection, deterministic action space.
    All tool calls are validated against Pydantic schemas before execution.
    """
    
    VALIDATORS = {
        "place_block": PlaceBlockParams,
        "fill_region": FillRegionParams,
        "carve_terrain": CarveTerrainParams,
        "set_lighting": SetLightingParams,
        "spawn_ghost_blocks": SpawnGhostBlocksParams
    }
    
    def __init__(self, block_registry=None):
        self.block_registry = block_registry
        self.tool_schemas = TOOLS
    
    def validate(self, tool_call: Dict[str, Any]) -> ToolCall:
        """
        Validate a tool call against its schema
        
        Args:
            tool_call: Dict with "tool" and "params" keys
            
        Returns:
            ToolCall with validation status
        """
        tool_name = tool_call.get("tool")
        params = tool_call.get("params", {})
        
        if tool_name not in self.VALIDATORS:
            return ToolCall(
                tool_name=tool_name,
                params=params,
                is_valid=False,
                validation_error=f"Unknown tool: {tool_name}"
            )
        
        try:
            validator_class = self.VALIDATORS[tool_name]
            validated_params = validator_class(**params)
            
            # Additional block registry validation for place_block
            if tool_name == "place_block" and self.block_registry:
                block_type = validated_params.block
                if not self.block_registry.is_valid_block(block_type):
                    return ToolCall(
                        tool_name=tool_name,
                        params=params,
                        is_valid=False,
                        validation_error=f"Unknown block type: {block_type}"
                    )
            
            return ToolCall(
                tool_name=tool_name,
                params=validated_params.dict(),
                is_valid=True
            )
            
        except ValidationError as e:
            return ToolCall(
                tool_name=tool_name,
                params=params,
                is_valid=False,
                validation_error=str(e)
            )
        except Exception as e:
            return ToolCall(
                tool_name=tool_name,
                params=params,
                is_valid=False,
                validation_error=f"Validation error: {str(e)}"
            )
    
    def parse_llm_output(self, llm_response: str) -> List[ToolCall]:
        """
        Parse LLM JSON output into validated tool calls
        
        Args:
            llm_response: Raw LLM response (JSON string or text with embedded JSON)
            
        Returns:
            List of validated ToolCall objects
        """
        tool_calls = []
        
        # Try to extract JSON from response
        json_data = self._extract_json(llm_response)
        
        if not json_data:
            return [ToolCall(
                tool_name="unknown",
                params={"raw": llm_response},
                is_valid=False,
                validation_error="Could not parse JSON from LLM response"
            )]
        
        # Handle single tool call or list
        if isinstance(json_data, dict):
            json_data = [json_data]
        
        for item in json_data:
            if isinstance(item, dict):
                tool_call = self.validate(item)
                tool_calls.append(tool_call)
        
        return tool_calls
    
    def _extract_json(self, text: str) -> Optional[Any]:
        """Extract JSON object/array from text response"""
        # Try parsing entire text as JSON first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Look for JSON array in text
        start_idx = text.find('[')
        end_idx = text.rfind(']')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            try:
                return json.loads(text[start_idx:end_idx + 1])
            except json.JSONDecodeError:
                pass
        
        # Look for JSON object in text
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            try:
                return json.loads(text[start_idx:end_idx + 1])
            except json.JSONDecodeError:
                pass
        
        return None
    
    def get_tool_schema(self, tool_name: str) -> Optional[Dict]:
        """Get schema definition for a tool"""
        return self.tool_schemas.get(tool_name)
    
    def get_all_tools_description(self) -> str:
        """
        Get formatted tool descriptions for LLM system prompt
        
        Returns:
            String describing all available tools and their parameters
        """
        lines = ["Available Tools:"]
        
        for tool_name, schema in self.tool_schemas.items():
            lines.append(f"\n{tool_name}:")
            lines.append(f"  Description: {schema['description']}")
            lines.append("  Parameters:")
            
            for param_name, param_type in schema["parameters"].items():
                type_str = str(param_type)
                if hasattr(param_type, '__origin__'):
                    type_str = str(param_type)
                lines.append(f"    - {param_name}: {type_str}")
        
        return "\n".join(lines)
    
    def create_retry_prompt(
        self, 
        failed_call: ToolCall, 
        original_intent: str
    ) -> str:
        """
        Create retry prompt with error context for LLM
        
        Args:
            failed_call: The failed tool call
            original_intent: Original user intent
            
        Returns:
            Formatted retry prompt
        """
        return f"""
The previous tool call failed validation:

Tool: {failed_call.tool_name}
Parameters: {json.dumps(failed_call.params, indent=2)}
Error: {failed_call.validation_error}

Original Intent: {original_intent}

Please correct the tool call parameters and try again.
Use the following schema:
{self.get_tool_schema(failed_call.tool_name)}
"""
