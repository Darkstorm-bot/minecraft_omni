"""
Minecraft Omni-Builder v3.1
===========================

Production-ready AI building assistant for Minecraft with:
- Local LLM support (Ollama, LM Studio)
- Spatial memory synchronization
- Multiplayer collision prevention
- Physics validation
- Holographic preview with approval workflow
- Cross-server CRDT sync with PostgreSQL backend

Architecture Layers:
1. Parser - Natural language command parsing
2. Gateway - API endpoints and spatial locking
3. Orchestrator - Terrain matching and physics validation
4. LLM - Context compression and tool routing
5. Executor - Block state validation and build execution
6. Memory - MemPalace storage and version control
7. Architect - Hierarchical planning
8. Sync - Cross-server CRDT synchronization
9. Preview - Holographic ghost block rendering
"""

__version__ = "3.1.0"
__author__ = "Darkstorm-bot"
__all__ = [
    "parser",
    "gateway",
    "orchestrator",
    "llm",
    "executor",
    "memory",
    "architect",
    "sync",
    "preview",
]
