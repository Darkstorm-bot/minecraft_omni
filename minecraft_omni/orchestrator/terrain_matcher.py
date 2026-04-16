"""
Minecraft Omni-Builder v3.1 - Terrain Matcher Module
World-aware placement that prevents clipping into mountains and auto-generates foundations
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum

from parser.command_parser import Vector3, Bounds


class BiomeType(Enum):
    PLAINS = "plains"
    DESERT = "desert"
    MOUNTAIN = "mountain"
    FOREST = "forest"
    OCEAN = "ocean"
    SWAMP = "swamp"
    SNOW = "snow"


@dataclass
class TerrainProfile:
    """Represents scanned terrain characteristics"""
    elevation_map: Dict[Tuple[int, int], int]  # (x,z) -> y_height
    biome_type: BiomeType
    obstructions: List[Vector3]
    avg_height: float
    height_variance: float
    slope_angle: float  # degrees
    
    def get_height_at(self, x: int, z: int) -> int:
        return self.elevation_map.get((x, z), int(self.avg_height))


@dataclass
class FoundationPlan:
    """Auto-generated terraforming instructions"""
    fill_regions: List[Tuple[Bounds, str]]  # (region, block_type)
    carve_regions: List[Tuple[Bounds, str]]  # (region, replace_with)
    piling_positions: List[Tuple[int, int, int, str]]  # (x,y,z,block_type)
    adjusted_origin: Vector3


class TerrainMatcher:
    """
    Analyzes terrain and generates foundation plans for builds.
    Prevents structures from clipping into mountains or floating over valleys.
    """
    
    # Height adjustment per biome
    BIOME_Y_OFFSET = {
        BiomeType.DESERT: -1,   # Sand compacts, dig slightly deeper
        BiomeType.MOUNTAIN: 5,  # Build on pilings for stability
        BiomeType.PLAINS: 0,
        BiomeType.FOREST: 0,
        BiomeType.OCEAN: 10,    # Build above water level
        BiomeType.SWAMP: 2,     # Slight elevation for drainage
        BiomeType.SNOW: 0,
    }
    
    def __init__(self, minecraft_client=None):
        self.mc_client = minecraft_client
    
    def analyze_foundation(self, origin: Vector3, bounds: Bounds) -> TerrainProfile:
        """
        Scan chunk topography via scan_area()
        
        Returns:
            TerrainProfile with elevation map, biome type, obstruction list
        """
        if self.mc_client is None:
            # Mock data for testing
            return self._mock_terrain_profile(origin, bounds)
        
        # Real implementation would call Minecraft bridge
        elevation_map = {}
        obstructions = []
        heights = []
        
        min_x = min(origin.x, bounds.min_pos.x) if bounds else origin.x
        max_x = max(origin.x, bounds.max_pos.x) if bounds else origin.x
        min_z = min(origin.z, bounds.min_pos.z) if bounds else origin.z
        max_z = max(origin.z, bounds.max_pos.z) if bounds else origin.z
        
        for x in range(min_x - 5, max_x + 6):
            for z in range(min_z - 5, max_z + 6):
                # Get highest non-air block at this x,z
                height = self._get_surface_y(x, z)
                elevation_map[(x, z)] = height
                heights.append(height)
                
                # Check for obstructions (trees, existing structures)
                if self._has_obstruction(x, height, z):
                    obstructions.append(Vector3(x, height, z))
        
        avg_height = sum(heights) / len(heights) if heights else origin.y
        variance = sum((h - avg_height) ** 2 for h in heights) / len(heights) if heights else 0
        biome = self._detect_biome(origin, elevation_map)
        slope = self._calculate_slope(elevation_map)
        
        return TerrainProfile(
            elevation_map=elevation_map,
            biome_type=biome,
            obstructions=obstructions,
            avg_height=avg_height,
            height_variance=variance,
            slope_angle=slope
        )
    
    def generate_foundation_plan(self, profile: TerrainProfile, bounds: Bounds) -> FoundationPlan:
        """
        Auto-generate pylings/fill for uneven terrain
        
        Returns:
            FoundationPlan with terraforming instructions
        """
        fill_regions = []
        carve_regions = []
        piling_positions = []
        
        # Calculate target height based on biome
        base_y = int(profile.avg_height) + self.BIOME_Y_OFFSET.get(profile.biome_type, 0)
        
        # Check if terrain is flat enough
        if profile.height_variance < 4:
            # Relatively flat - minor adjustments only
            adjusted_origin = Vector3(bounds.min_pos.x, base_y, bounds.min_pos.z)
            return FoundationPlan(
                fill_regions=[],
                carve_regions=[],
                piling_positions=[],
                adjusted_origin=adjusted_origin
            )
        
        # Uneven terrain - need pilings or terraforming
        min_x = bounds.min_pos.x
        max_x = bounds.max_pos.x
        min_z = bounds.min_pos.z
        max_z = bounds.max_pos.z
        
        # Strategy 1: Corner pilings for elevated structures
        corners = [
            (min_x, min_z),
            (min_x, max_z),
            (max_x, min_z),
            (max_x, max_z)
        ]
        
        for cx, cz in corners:
            ground_height = profile.get_height_at(cx, cz)
            piling_height = base_y - ground_height
            
            if piling_height > 0:
                # Need pilings to reach target height
                for py in range(ground_height, base_y):
                    piling_positions.append((cx, py, cz, "stone_bricks"))
            elif piling_height < 0:
                # Need to carve down
                carve_bounds = Bounds(
                    Vector3(cx, base_y, cz),
                    Vector3(cx, ground_height, cz)
                )
                carve_regions.append((carve_bounds, "air"))
        
        # Strategy 2: Fill low spots under structure footprint
        for x in range(min_x, max_x + 1, 3):  # Grid pattern every 3 blocks
            for z in range(min_z, max_z + 1, 3):
                ground_height = profile.get_height_at(x, z)
                if ground_height < base_y - 1:
                    # Fill gap with supporting blocks
                    fill_bounds = Bounds(
                        Vector3(x, ground_height + 1, z),
                        Vector3(x, base_y - 1, z)
                    )
                    fill_regions.append((fill_bounds, "cobblestone"))
        
        adjusted_origin = Vector3(bounds.min_pos.x, base_y, bounds.min_pos.z)
        
        return FoundationPlan(
            fill_regions=fill_regions,
            carve_regions=carve_regions,
            piling_positions=piling_positions,
            adjusted_origin=adjusted_origin
        )
    
    def adjust_origin_y(self, origin: Vector3, profile: TerrainProfile) -> Vector3:
        """
        Dynamic y=0 adjustment per biome
        
        Desert: y-1 (sand compacts)
        Mountain: y+5 (pilings)
        
        Returns:
            Adjusted Vector3 with corrected Y coordinate
        """
        y_offset = self.BIOME_Y_OFFSET.get(profile.biome_type, 0)
        return Vector3(origin.x, origin.y + y_offset, origin.z)
    
    def _get_surface_y(self, x: int, z: int) -> int:
        """Get the Y coordinate of the surface block at given X,Z"""
        if self.mc_client:
            return self.mc_client.get_highest_block_at(x, z)
        return 64  # Default sea level for mocks
    
    def _has_obstruction(self, x: int, y: int, z: int) -> bool:
        """Check if there's an obstruction at the given position"""
        if self.mc_client:
            block = self.mc_client.get_block_at(x, y, z)
            return block not in ["air", "grass", "short_grass", "fern"]
        return False
    
    def _detect_biome(self, origin: Vector3, elevation_map: Dict) -> BiomeType:
        """Detect biome type from terrain characteristics"""
        if self.mc_client:
            return BiomeType(self.mc_client.get_biome_at(origin.x, origin.z))
        
        # Heuristic detection from elevation
        avg_height = sum(elevation_map.values()) / len(elevation_map) if elevation_map else 64
        
        if avg_height > 100:
            return BiomeType.MOUNTAIN
        elif avg_height < 50:
            return BiomeType.OCEAN
        else:
            return BiomeType.PLAINS
    
    def _calculate_slope(self, elevation_map: Dict) -> float:
        """Calculate average slope angle in degrees"""
        if len(elevation_map) < 2:
            return 0.0
        
        import math
        slopes = []
        
        coords = list(elevation_map.keys())
        for i in range(len(coords) - 1):
            x1, z1 = coords[i]
            x2, z2 = coords[i + 1]
            
            dx = abs(x2 - x1)
            dz = abs(z2 - z1)
            dh = abs(elevation_map[(x2, z2)] - elevation_map[(x1, z1)])
            
            horizontal_dist = math.sqrt(dx**2 + dz**2)
            if horizontal_dist > 0:
                angle = math.degrees(math.atan(dh / horizontal_dist))
                slopes.append(angle)
        
        return sum(slopes) / len(slopes) if slopes else 0.0
    
    def _mock_terrain_profile(self, origin: Vector3, bounds: Bounds) -> TerrainProfile:
        """Generate mock terrain data for testing"""
        elevation_map = {}
        for x in range(origin.x - 10, origin.x + 11):
            for z in range(origin.z - 10, origin.z + 11):
                # Simulate slight hill
                import math
                dist = math.sqrt((x - origin.x)**2 + (z - origin.z)**2)
                height = 64 + int(5 * math.sin(dist / 5))
                elevation_map[(x, z)] = height
        
        return TerrainProfile(
            elevation_map=elevation_map,
            biome_type=BiomeType.PLAINS,
            obstructions=[],
            avg_height=64.0,
            height_variance=12.5,
            slope_angle=5.0
        )
