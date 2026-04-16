#!/usr/bin/env python3
"""
Style Learner Module - v3.1 Omni Feature
Long-term preference learning across build sessions
"""

from typing import Dict, List, Literal, Optional
from dataclasses import dataclass, field
import json
import time


@dataclass
class StyleProfile:
    """Player's building style preferences"""
    player_uuid: str
    preferred_blocks: List[str] = field(default_factory=list)
    avoided_blocks: List[str] = field(default_factory=list)
    symmetry_preference: float = 0.5  # 0=asymmetric, 1=perfect symmetry
    color_palette: List[str] = field(default_factory=list)
    architectural_style: str = "default"
    
    def summary(self) -> str:
        """Generate a summary string for LLM prompts"""
        parts = []
        if self.preferred_blocks:
            parts.append(f"prefers {', '.join(self.preferred_blocks[:5])}")
        if self.avoided_blocks:
            parts.append(f"avoids {', '.join(self.avoided_blocks[:5])}")
        if self.symmetry_preference > 0.7:
            parts.append("likes symmetry")
        elif self.symmetry_preference < 0.3:
            parts.append("prefers asymmetric designs")
        if self.architectural_style != "default":
            parts.append(f"style: {self.architectural_style}")
        return "; ".join(parts) if parts else "no strong preferences"


class StyleLearner:
    """
    Long-term preference learning across build sessions.
    Integrates with MemPalace Preference_Learning room.
    """
    
    def __init__(self, palace_adapter=None):
        """
        Initialize StyleLearner with optional palace adapter.
        If no adapter provided, uses in-memory storage.
        """
        self.palace = palace_adapter
        self._memory_profiles: Dict[str, StyleProfile] = {}
    
    def record_feedback(self, player_uuid: str, build_id: str, 
                       feedback: Literal["like", "dislike"]) -> bool:
        """
        Called on !bot like or !bot dislike commands.
        Extracts features from the build and updates player profile.
        
        Args:
            player_uuid: Player's unique identifier
            build_id: ID of the build being rated
            feedback: "like" or "dislike"
            
        Returns:
            True if feedback was recorded successfully
        """
        # Extract features from build (would query MemPalace in production)
        features = self._extract_features(build_id)
        
        # Get or create player profile
        profile = self.get_profile(player_uuid)
        
        # Update profile based on feedback
        if feedback == "like":
            # Reinforce used blocks as preferred
            for block in features.get("blocks_used", []):
                if block not in profile.preferred_blocks:
                    profile.preferred_blocks.append(block)
                if block in profile.avoided_blocks:
                    profile.avoided_blocks.remove(block)
            
            # Adjust symmetry preference based on build
            if features.get("symmetry_score", 0.5) > 0.7:
                profile.symmetry_preference = min(1.0, profile.symmetry_preference + 0.1)
            elif features.get("symmetry_score", 0.5) < 0.3:
                profile.symmetry_preference = max(0.0, profile.symmetry_preference - 0.1)
                
        else:  # dislike
            # Mark used blocks as potentially avoided
            for block in features.get("blocks_used", [])[:3]:  # Top 3 most used
                if block not in profile.avoided_blocks:
                    profile.avoided_blocks.append(block)
        
        # Save profile
        return self._save_profile(player_uuid, profile)
    
    def apply_to_prompt(self, player_uuid: str, base_prompt: str) -> str:
        """
        Inject preferences into LLM prompt.
        
        Args:
            player_uuid: Player's unique identifier
            base_prompt: Original build request
            
        Returns:
            Enhanced prompt with player preferences
        """
        profile = self.get_profile(player_uuid)
        summary = profile.summary()
        
        if summary == "no strong preferences":
            return base_prompt
        
        return f"{base_prompt}\n\n[Player Preferences: {summary}]"
    
    def get_profile(self, player_uuid: str) -> StyleProfile:
        """Get or create a player's style profile"""
        if self.palace:
            try:
                return self.palace.get_style_profile(player_uuid)
            except Exception:
                pass
        
        if player_uuid not in self._memory_profiles:
            self._memory_profiles[player_uuid] = StyleProfile(player_uuid=player_uuid)
        
        return self._memory_profiles[player_uuid]
    
    def _extract_features(self, build_id: str) -> Dict:
        """
        Extract features from a build for learning.
        In production, queries MemPalace spatial_registry.
        """
        # Placeholder - would query MemPalace in production
        return {
            "blocks_used": ["oak_planks", "stone_bricks", "glass"],
            "symmetry_score": 0.6,
            "color_palette": ["brown", "gray", "white"],
            "architectural_elements": ["pillars", "arches"]
        }
    
    def _save_profile(self, player_uuid: str, profile: StyleProfile) -> bool:
        """Save player profile to storage"""
        if self.palace:
            try:
                return self.palace.update_style_profile(player_uuid, profile)
            except Exception:
                pass
        
        self._memory_profiles[player_uuid] = profile
        return True
    
    def update_style_profile(self, player_uuid: str, features: Dict, 
                            feedback: Literal["like", "dislike"]) -> StyleProfile:
        """
        Direct profile update method for API integration.
        
        Args:
            player_uuid: Player's unique identifier
            features: Dict with block types, symmetry score, etc.
            feedback: "like" or "dislike"
            
        Returns:
            Updated StyleProfile
        """
        profile = self.get_profile(player_uuid)
        
        # Update based on features
        if feedback == "like":
            for block in features.get("preferred_blocks", []):
                if block not in profile.preferred_blocks:
                    profile.preferred_blocks.append(block)
        else:
            for block in features.get("avoided_blocks", []):
                if block not in profile.avoided_blocks:
                    profile.avoided_blocks.append(block)
        
        if "symmetry_preference" in features:
            profile.symmetry_preference = features["symmetry_preference"]
        
        if "architectural_style" in features:
            profile.architectural_style = features["architectural_style"]
        
        self._save_profile(player_uuid, profile)
        return profile
    
    def get_all_profiles(self) -> Dict[str, StyleProfile]:
        """Get all stored player profiles"""
        if self.palace:
            # Would query all profiles from MemPalace
            pass
        return self._memory_profiles.copy()
    
    def export_profiles(self) -> str:
        """Export all profiles as JSON for backup/migration"""
        export_data = {}
        for uuid, profile in self._memory_profiles.items():
            export_data[uuid] = {
                "player_uuid": profile.player_uuid,
                "preferred_blocks": profile.preferred_blocks,
                "avoided_blocks": profile.avoided_blocks,
                "symmetry_preference": profile.symmetry_preference,
                "color_palette": profile.color_palette,
                "architectural_style": profile.architectural_style
            }
        return json.dumps(export_data, indent=2)
    
    def import_profiles(self, json_data: str) -> int:
        """Import profiles from JSON backup"""
        try:
            data = json.loads(json_data)
            count = 0
            for uuid, profile_data in data.items():
                profile = StyleProfile(
                    player_uuid=profile_data["player_uuid"],
                    preferred_blocks=profile_data.get("preferred_blocks", []),
                    avoided_blocks=profile_data.get("avoided_blocks", []),
                    symmetry_preference=profile_data.get("symmetry_preference", 0.5),
                    color_palette=profile_data.get("color_palette", []),
                    architectural_style=profile_data.get("architectural_style", "default")
                )
                self._memory_profiles[uuid] = profile
                count += 1
            return count
        except Exception as e:
            print(f"Error importing profiles: {e}")
            return 0
