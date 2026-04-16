"""
MemPalace Adapter: Memory Storage & Retrieval
---------------------------------------------
Connects to MemPalace (https://github.com/MemPalace/mempalace) for:
- Persistent build history
- Undo/Redo stacks
- Style learning storage
- Cross-session context

API Reference: https://mempalace.io/docs
"""

import requests
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class BlockOperation:
    """Represents a single block placement/destruction"""
    x: int
    y: int
    z: int
    block_type: str
    action: str  # 'place' or 'destroy'
    timestamp: float
    session_id: str
    metadata: Dict[str, Any] = None

@dataclass
class Tombstone:
    """Undo marker for block operations"""
    operation_id: str
    original_state: Dict[str, Any]
    timestamp: float


class MinecraftMemPalace:
    """
    Adapter for MemPalace API
    Handles all memory operations for the Omni-Builder
    """
    
    def __init__(self, api_url: str, api_key: str, project_id: str):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.project_id = project_id
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'X-Project-ID': self.project_id
        }
        
        logger.info(f"MemPalace adapter initialized for project: {project_id}")
    
    def test_connection(self) -> bool:
        """Test connectivity to MemPalace API"""
        try:
            response = requests.get(
                f"{self.api_url}/api/v1/status",
                headers=self.headers,
                timeout=5
            )
            if response.status_code == 200:
                logger.info("MemPalace connection successful")
                return True
            else:
                logger.warning(f"MemPalace returned status {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            logger.error("Cannot connect to MemPalace API")
            return False
        except Exception as e:
            logger.error(f"MemPalace test failed: {e}")
            return False
    
    def log_block_placement(self, operation: BlockOperation) -> str:
        """
        Log a block placement to MemPalace
        Returns operation ID for undo tracking
        """
        try:
            payload = {
                'type': 'block_operation',
                'data': asdict(operation),
                'session_id': self.session_id
            }
            
            response = requests.post(
                f"{self.api_url}/api/v1/memory/log",
                headers=self.headers,
                json=payload,
                timeout=5
            )
            
            if response.status_code == 201:
                op_id = response.json().get('operation_id')
                logger.debug(f"Logged block placement: {op_id}")
                return op_id
            else:
                logger.error(f"Failed to log placement: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error logging placement: {e}")
            return None
    
    def log_tombstone(self, tombstone: Tombstone) -> bool:
        """Log an undo operation (tombstone)"""
        try:
            payload = {
                'type': 'tombstone',
                'data': asdict(tombstone),
                'session_id': self.session_id
            }
            
            response = requests.post(
                f"{self.api_url}/api/v1/memory/tombstone",
                headers=self.headers,
                json=payload,
                timeout=5
            )
            
            return response.status_code == 201
            
        except Exception as e:
            logger.error(f"Error logging tombstone: {e}")
            return False
    
    def get_undo_stack(self, limit: int = 50) -> List[Tombstone]:
        """Retrieve recent undo operations"""
        try:
            response = requests.get(
                f"{self.api_url}/api/v1/memory/undo",
                headers=self.headers,
                params={'limit': limit, 'session_id': self.session_id},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json().get('operations', [])
                return [Tombstone(**item) for item in data]
            else:
                logger.warning(f"Failed to fetch undo stack: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching undo stack: {e}")
            return []
    
    def store_style_preference(self, style_name: str, preferences: Dict[str, Any]) -> bool:
        """Save user style preferences for learning"""
        try:
            payload = {
                'type': 'style_preference',
                'data': {
                    'style_name': style_name,
                    'preferences': preferences
                }
            }
            
            response = requests.post(
                f"{self.api_url}/api/v1/memory/styles",
                headers=self.headers,
                json=payload,
                timeout=5
            )
            
            return response.status_code == 201
            
        except Exception as e:
            logger.error(f"Error storing style: {e}")
            return False
    
    def get_style_preference(self, style_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored style preferences"""
        try:
            response = requests.get(
                f"{self.api_url}/api/v1/memory/styles/{style_name}",
                headers=self.headers,
                timeout=5
            )
            
            if response.status_code == 200:
                return response.json().get('preferences')
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error fetching style: {e}")
            return None
    
    def sync_session(self) -> bool:
        """Force sync of current session to persistent storage"""
        try:
            response = requests.post(
                f"{self.api_url}/api/v1/sync",
                headers=self.headers,
                json={'session_id': self.session_id},
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Error syncing session: {e}")
            return False
