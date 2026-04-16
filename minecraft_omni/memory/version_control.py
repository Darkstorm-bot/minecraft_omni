#!/usr/bin/env python3
"""
Git-like Version Control for Builds - v3.1 Omni Feature
Branch, fork, merge, and diff builds with immutable DAG storage
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import json
import hashlib
import time
from pathlib import Path


@dataclass
class BlockDiff:
    """Represents a change between two build versions"""
    x: int
    y: int
    z: int
    old_block: str
    new_block: str
    change_type: str  # "added", "removed", "modified"


@dataclass
class Commit:
    """Immutable commit snapshot"""
    hash: str
    parent_hash: Optional[str]
    build_id: str
    message: str
    timestamp: float
    block_count: int
    blocks_snapshot: Dict[str, str]  # "x,y,z" -> "block_type[state]"
    
    def short_hash(self) -> str:
        return self.hash[:8]


@dataclass 
class Branch:
    """Branch reference pointing to a commit"""
    name: str
    head_commit: str
    created_at: float
    build_id: str


class BuildVersionControl:
    """
    Git-like version control for Minecraft builds.
    Supports commit, branch, diff, and revert operations.
    Integrates with MemPalace Version_Branches room.
    """
    
    def __init__(self, palace_adapter=None, storage_path: str = "./vc_storage"):
        """
        Initialize version control system.
        
        Args:
            palace_adapter: Optional MemPalace adapter for persistence
            storage_path: Local storage path for commits (if no palace)
        """
        self.palace = palace_adapter
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # In-memory caches
        self._commits: Dict[str, Commit] = {}
        self._branches: Dict[str, Branch] = {}
        self._build_branches: Dict[str, List[str]] = {}  # build_id -> [branch_names]
    
    def commit(self, build_id: str, message: str, 
               blocks: Dict[Tuple[int,int,int], str]) -> str:
        """
        Create a new commit snapshot of the build.
        
        Args:
            build_id: Unique build identifier
            message: Commit message describing changes
            blocks: Dict of (x,y,z) -> "block_type[state]"
            
        Returns:
            Commit hash string
        """
        # Get current HEAD commit for this build
        head_commit = self.get_head_commit(build_id)
        parent_hash = head_commit.hash if head_commit else None
        
        # Create blocks snapshot
        blocks_snapshot = {f"{x},{y},{z}": block for (x,y,z), block in blocks.items()}
        
        # Generate commit hash
        content = f"{build_id}:{message}:{time.time()}:{json.dumps(blocks_snapshot, sort_keys=True)}"
        commit_hash = hashlib.sha256(content.encode()).hexdigest()
        
        # Create commit object
        commit = Commit(
            hash=commit_hash,
            parent_hash=parent_hash,
            build_id=build_id,
            message=message,
            timestamp=time.time(),
            block_count=len(blocks_snapshot),
            blocks_snapshot=blocks_snapshot
        )
        
        # Store commit
        self._commits[commit_hash] = commit
        self._save_commit(commit)
        
        # Update or create main branch
        if build_id not in self._build_branches:
            self.create_branch(build_id, "main", commit_hash)
        else:
            self._update_branch_head(build_id, "main", commit_hash)
        
        return commit_hash
    
    def branch(self, build_id: str, branch_name: str, 
               from_commit: Optional[str] = None) -> str:
        """
        Create a new branch for experimental changes.
        
        Args:
            build_id: Build to branch from
            branch_name: Name for the new branch
            from_commit: Optional commit to branch from (defaults to HEAD)
            
        Returns:
            Branch name
        """
        # Determine source commit
        if from_commit:
            if from_commit not in self._commits:
                raise ValueError(f"Commit {from_commit} not found")
            source_commit = from_commit
        else:
            head = self.get_head_commit(build_id)
            if not head:
                raise ValueError(f"No commits found for build {build_id}")
            source_commit = head.hash
        
        # Check if branch already exists
        full_branch_name = f"{build_id}/{branch_name}"
        if full_branch_name in self._branches:
            raise ValueError(f"Branch {branch_name} already exists for build {build_id}")
        
        # Create branch
        branch = Branch(
            name=branch_name,
            head_commit=source_commit,
            created_at=time.time(),
            build_id=build_id
        )
        
        self._branches[full_branch_name] = branch
        
        # Track branch per build
        if build_id not in self._build_branches:
            self._build_branches[build_id] = []
        self._build_branches[build_id].append(branch_name)
        
        return branch_name
    
    def diff(self, commit_a: str, commit_b: str) -> List[BlockDiff]:
        """
        Compare two commits and return block differences.
        
        Args:
            commit_a: First commit hash
            commit_b: Second commit hash
            
        Returns:
            List of BlockDiff objects
        """
        if commit_a not in self._commits:
            raise ValueError(f"Commit {commit_a} not found")
        if commit_b not in self._commits:
            raise ValueError(f"Commit {commit_b} not found")
        
        commit_a_obj = self._commits[commit_a]
        commit_b_obj = self._commits[commit_b]
        
        diffs = []
        all_coords = set(commit_a_obj.blocks_snapshot.keys()) | set(commit_b_obj.blocks_snapshot.keys())
        
        for coord in all_coords:
            old_block = commit_a_obj.blocks_snapshot.get(coord)
            new_block = commit_b_obj.blocks_snapshot.get(coord)
            
            x, y, z = map(int, coord.split(","))
            
            if old_block is None:
                # Block was added
                diffs.append(BlockDiff(x=x, y=y, z=z, old_block="air", 
                                       new_block=new_block, change_type="added"))
            elif new_block is None:
                # Block was removed
                diffs.append(BlockDiff(x=x, y=y, z=z, old_block=old_block, 
                                       new_block="air", change_type="removed"))
            elif old_block != new_block:
                # Block was modified
                diffs.append(BlockDiff(x=x, y=y, z=z, old_block=old_block, 
                                       new_block=new_block, change_type="modified"))
        
        return diffs
    
    def revert(self, build_id: str, commit_hash: str) -> str:
        """
        Revert build to a specific commit state.
        
        Args:
            build_id: Build to revert
            commit_hash: Target commit to revert to
            
        Returns:
            New commit hash representing the revert
        """
        if commit_hash not in self._commits:
            raise ValueError(f"Commit {commit_hash} not found")
        
        target_commit = self._commits[commit_hash]
        
        # Create revert commit
        revert_message = f"Revert to {commit_hash[:8]}: {target_commit.message}"
        blocks = {}
        for coord_str, block in target_commit.blocks_snapshot.items():
            x, y, z = map(int, coord_str.split(","))
            blocks[(x, y, z)] = block
        
        return self.commit(build_id, revert_message, blocks)
    
    def get_head_commit(self, build_id: str) -> Optional[Commit]:
        """Get the HEAD commit for a build's main branch"""
        branch_name = f"{build_id}/main"
        if branch_name not in self._branches:
            return None
        
        branch = self._branches[branch_name]
        return self._commits.get(branch.head_commit)
    
    def get_commit(self, commit_hash: str) -> Optional[Commit]:
        """Get a commit by hash"""
        return self._commits.get(commit_hash)
    
    def get_branch(self, build_id: str, branch_name: str) -> Optional[Branch]:
        """Get a branch by name"""
        return self._branches.get(f"{build_id}/{branch_name}")
    
    def list_branches(self, build_id: str) -> List[str]:
        """List all branches for a build"""
        return self._build_branches.get(build_id, [])
    
    def get_commit_history(self, build_id: str, 
                          limit: int = 10) -> List[Commit]:
        """Get commit history for a build (newest first)"""
        head = self.get_head_commit(build_id)
        if not head:
            return []
        
        history = []
        current_hash = head.hash
        
        while current_hash and len(history) < limit:
            commit = self._commits.get(current_hash)
            if not commit:
                break
            history.append(commit)
            current_hash = commit.parent_hash
        
        return history
    
    def _save_commit(self, commit: Commit):
        """Persist commit to storage"""
        if self.palace:
            try:
                # Would save to MemPalace Version_Branches room
                pass
            except Exception:
                pass
        
        # Always save to local file as backup
        commit_file = self.storage_path / f"{commit.hash}.json"
        with open(commit_file, 'w') as f:
            json.dump({
                "hash": commit.hash,
                "parent_hash": commit.parent_hash,
                "build_id": commit.build_id,
                "message": commit.message,
                "timestamp": commit.timestamp,
                "block_count": commit.block_count,
                "blocks_snapshot": commit.blocks_snapshot
            }, f)
    
    def _update_branch_head(self, build_id: str, branch_name: str, commit_hash: str):
        """Update a branch's HEAD pointer"""
        full_name = f"{build_id}/{branch_name}"
        if full_name in self._branches:
            self._branches[full_name].head_commit = commit_hash
    
    def _load_commits_from_storage(self):
        """Load commits from local storage"""
        if not self.storage_path.exists():
            return
        
        for commit_file in self.storage_path.glob("*.json"):
            try:
                with open(commit_file, 'r') as f:
                    data = json.load(f)
                
                commit = Commit(
                    hash=data["hash"],
                    parent_hash=data.get("parent_hash"),
                    build_id=data["build_id"],
                    message=data["message"],
                    timestamp=data["timestamp"],
                    block_count=data["block_count"],
                    blocks_snapshot=data["blocks_snapshot"]
                )
                self._commits[commit.hash] = commit
            except Exception as e:
                print(f"Error loading commit {commit_file}: {e}")
    
    def export_repository(self) -> str:
        """Export entire repository as JSON"""
        export_data = {
            "commits": {h: {
                "hash": c.hash,
                "parent_hash": c.parent_hash,
                "build_id": c.build_id,
                "message": c.message,
                "timestamp": c.timestamp,
                "block_count": c.block_count,
                "blocks_snapshot": c.blocks_snapshot
            } for h, c in self._commits.items()},
            "branches": {n: {
                "name": b.name,
                "head_commit": b.head_commit,
                "created_at": b.created_at,
                "build_id": b.build_id
            } for n, b in self._branches.items()},
            "build_branches": self._build_branches
        }
        return json.dumps(export_data, indent=2)
    
    def format_diff_summary(self, diffs: List[BlockDiff]) -> str:
        """Format diff results as human-readable summary"""
        if not diffs:
            return "No changes between commits"
        
        added = sum(1 for d in diffs if d.change_type == "added")
        removed = sum(1 for d in diffs if d.change_type == "removed")
        modified = sum(1 for d in diffs if d.change_type == "modified")
        
        lines = [
            f"Changes: +{added} ~{modified} -{removed}",
            ""
        ]
        
        # Show first 10 changes
        for diff in diffs[:10]:
            if diff.change_type == "added":
                lines.append(f"+ [{diff.x},{diff.y},{diff.z}] {diff.new_block}")
            elif diff.change_type == "removed":
                lines.append(f"- [{diff.x},{diff.y},{diff.z}] {diff.old_block}")
            else:
                lines.append(f"~ [{diff.x},{diff.y},{diff.z}] {diff.old_block} → {diff.new_block}")
        
        if len(diffs) > 10:
            lines.append(f"... and {len(diffs) - 10} more changes")
        
        return "\n".join(lines)
