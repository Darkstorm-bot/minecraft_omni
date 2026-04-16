"""
Minecraft Omni-Builder v3.1 - Hierarchical Planner Module
Multi-scale build planning with template injection system
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum

from parser.command_parser import Vector3, Bounds


class PlanningScale(Enum):
    """Planning granularity levels"""
    CONCEPT = "concept"       # High-level intent
    ZONES = "zones"          # Major sections (exterior, interior)
    COMPONENTS = "components" # Individual parts (walls, roof)
    DETAILS = "details"      # Block-level placement


@dataclass
class Zone:
    """Represents a major section of a build"""
    name: str
    bounds: Bounds
    purpose: str
    components: List["Component"] = field(default_factory=list)
    material_palette: List[str] = field(default_factory=list)


@dataclass
class Component:
    """Represents a build component within a zone"""
    name: str
    description: str
    block_count_estimate: int
    tool_calls: List[Dict] = field(default_factory=list)


@dataclass
class BuildPlan:
    """Complete hierarchical build plan"""
    build_id: str
    prompt: str
    origin: Vector3
    scale: PlanningScale
    zones: List[Zone] = field(default_factory=list)
    templates_used: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class TemplateLibrary:
    """
    Manages reusable build templates stored in MemPalace

    Templates are stored as relative coordinates that can be
    instantiated at any position with optional rotation.
    """

    def __init__(self, palace_adapter: Any):
        self.palace = palace_adapter
        self.template_cache: Dict[str, Dict] = {}

    def save_template(
        self,
        region: Bounds,
        name: str,
        player_uuid: str,
        blocks: List[Dict]
    ) -> bool:
        """
        Store a template from existing build region

        Args:
            region: Bounding box of the template
            name: Template name
            player_uuid: Owner's UUID
            blocks: List of block dicts with relative coords

        Returns:
            True if saved successfully
        """
        template_data = {
            "name": name,
            "owner": player_uuid,
            "bounds": {
                "x_min": region.min_pos.x,
                "y_min": region.min_pos.y,
                "z_min": region.min_pos.z,
                "x_max": region.max_pos.x,
                "y_max": region.max_pos.y,
                "z_max": region.max_pos.z,
            },
            "blocks": blocks,  # Relative coordinates
            "block_count": len(blocks),
        }

        # Store in palace under Templates wing
        # In production, use palace.save_template() method
        self.template_cache[name] = template_data

        print(f"Saved template '{name}' with {len(blocks)} blocks")
        return True

    def instantiate_template(
        self,
        name: str,
        position: Vector3,
        rotation: int = 0,
        scale: float = 1.0
    ) -> Optional[List[Dict]]:
        """
        Retrieve and transform template to world coordinates

        Args:
            name: Template name
            position: World position for placement origin
            rotation: Y-axis rotation in degrees (0, 90, 180, 270)
            scale: Optional scale factor

        Returns:
            List of tool calls for block placement, or None if not found
        """
        template = self.template_cache.get(name)
        if not template:
            print(f"Template '{name}' not found")
            return None

        tool_calls = []

        for block in template["blocks"]:
            # Get relative coordinates
            rx = block.get("x", 0)
            ry = block.get("y", 0)
            rz = block.get("z", 0)
            block_type = block.get("type", "stone")
            state = block.get("state", {})

            # Apply rotation around Y axis
            if rotation == 90:
                rx, rz = -rz, rx
            elif rotation == 180:
                rx, rz = -rx, -rz
            elif rotation == 270:
                rx, rz = rz, -rx

            # Apply scale
            if scale != 1.0:
                rx = int(rx * scale)
                ry = int(ry * scale)
                rz = int(rz * scale)

            # Translate to world position
            wx = position.x + rx
            wy = position.y + ry
            wz = position.z + rz

            # Handle facing rotation in block state
            rotated_state = self._rotate_block_state(state, rotation)

            tool_calls.append({
                "tool": "place_block",
                "params": {
                    "x": wx,
                    "y": wy,
                    "z": wz,
                    "block": block_type,
                    "state": rotated_state,
                }
            })

        return tool_calls

    def _rotate_block_state(
        self,
        state: Dict[str, str],
        rotation: int
    ) -> Dict[str, str]:
        """Rotate directional block states (stairs, logs, etc.)"""
        if not state or "facing" not in state:
            return state

        facing = state.get("facing", "")
        directions = ["north", "east", "south", "west"]

        if facing in directions:
            idx = directions.index(facing)
            rotation_steps = rotation // 90
            new_idx = (idx + rotation_steps) % 4
            return {**state, "facing": directions[new_idx]}

        return state

    def list_templates(self, player_uuid: Optional[str] = None) -> List[str]:
        """List available templates, optionally filtered by owner"""
        if player_uuid:
            return [
                name for name, data in self.template_cache.items()
                if data.get("owner") == player_uuid
            ]
        return list(self.template_cache.keys())

    def get_template_info(self, name: str) -> Optional[Dict]:
        """Get metadata about a template"""
        template = self.template_cache.get(name)
        if template:
            return {
                "name": template["name"],
                "owner": template["owner"],
                "block_count": template["block_count"],
                "bounds": template["bounds"],
            }
        return None


class HierarchicalArchitect:
    """
    Generates multi-scale build plans through hierarchical decomposition

    Flow: Concept → Zones → Components → Details → Tool Calls
    """

    def __init__(self, template_library: Optional[TemplateLibrary] = None):
        self.template_lib = template_library

    def generate_plan(
        self,
        build_id: str,
        prompt: str,
        origin: Vector3,
        llm_response: Dict
    ) -> BuildPlan:
        """
        Generate hierarchical build plan from LLM output

        Args:
            build_id: Unique build identifier
            prompt: Original user prompt
            origin: Build origin coordinates
            llm_response: Structured response from LLM router

        Returns:
            Complete BuildPlan object
        """
        plan = BuildPlan(
            build_id=build_id,
            prompt=prompt,
            origin=origin,
            scale=PlanningScale.CONCEPT,
        )

        # Parse zones from LLM response
        zones_data = llm_response.get("zones", [])
        for zone_data in zones_data:
            zone = self._parse_zone(zone_data, origin)
            plan.zones.append(zone)

        # Check for template injections
        templates_requested = llm_response.get("templates", [])
        for tpl_name in templates_requested:
            if self.template_lib:
                plan.templates_used.append(tpl_name)

        plan.scale = PlanningScale.ZONES
        plan.metadata["generated_at"] = __import__("time").time()

        return plan

    def _parse_zone(self, zone_data: Dict, origin: Vector3) -> Zone:
        """Parse zone data into Zone object"""
        bounds_data = zone_data.get("bounds", {})

        bounds = Bounds(
            min_pos=Vector3(
                origin.x + bounds_data.get("x_min", 0),
                origin.y + bounds_data.get("y_min", 0),
                origin.z + bounds_data.get("z_min", 0)
            ),
            max_pos=Vector3(
                origin.x + bounds_data.get("x_max", 10),
                origin.y + bounds_data.get("y_max", 10),
                origin.z + bounds_data.get("z_max", 10)
            )
        )

        zone = Zone(
            name=zone_data.get("name", "Unknown"),
            bounds=bounds,
            purpose=zone_data.get("purpose", ""),
            material_palette=zone_data.get("materials", []),
        )

        # Parse components
        for comp_data in zone_data.get("components", []):
            component = Component(
                name=comp_data.get("name", "Component"),
                description=comp_data.get("description", ""),
                block_count_estimate=comp_data.get("block_count", 0),
                tool_calls=comp_data.get("tool_calls", []),
            )
            zone.components.append(component)

        return zone

    def refine_to_details(self, plan: BuildPlan) -> BuildPlan:
        """Refine plan from zones/components to block-level details"""
        plan.scale = PlanningScale.DETAILS

        # Expand all components into detailed tool calls
        for zone in plan.zones:
            for component in zone.components:
                if not component.tool_calls:
                    # Generate tool calls from component description
                    component.tool_calls = self._generate_component_tool_calls(
                        component, zone
                    )

        return plan

    def _generate_component_tool_calls(
        self,
        component: Component,
        zone: Zone
    ) -> List[Dict]:
        """Generate block placement tool calls for a component"""
        # This would typically call an LLM to generate detailed placements
        # For now, return empty list (LLM routing handles this)
        return []

    def estimate_complexity(self, plan: BuildPlan) -> Dict[str, Any]:
        """Estimate build complexity metrics"""
        total_blocks = sum(
            comp.block_count_estimate
            for zone in plan.zones
            for comp in zone.components
        )

        zone_count = len(plan.zones)
        component_count = sum(len(zone.components) for zone in plan.zones)

        # Estimate LLM tokens needed
        estimated_tokens = total_blocks // 10  # Rough heuristic

        return {
            "total_blocks": total_blocks,
            "zone_count": zone_count,
            "component_count": component_count,
            "estimated_tokens": estimated_tokens,
            "complexity": "high" if total_blocks > 5000 else "medium" if total_blocks > 500 else "low",
        }
