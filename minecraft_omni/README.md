# Minecraft Omni-Builder v3.1

Natural language Minecraft building with local LLMs, spatial memory sync, physics validation, and multiplayer collaboration.

## Features

### v3.0 Core Features
- **Context Compressor**: 80% token reduction for 7B models
- **BlockStateRegistry**: Validates block types and states
- **SpatialLockManager**: Prevents build conflicts
- **UndoJournal**: Command pattern rollback
- **SyncEngine**: Bidirectional world sync
- **Alembic Migrations**: Database schema versioning

### v3.1 Omni Extensions
- **PhysicsValidator**: Pre-execution simulation (gravity, fluids, lighting)
- **ToolCalling Architecture**: JSON schema validation (no exec())
- **TerrainMatcher**: World-aware placement, auto-foundations
- **CRDT Collaboration**: Real-time multiplayer editing
- **Holographic Previews**: Ghost block visualization
- **Style Learning**: Player preference adaptation
- **Cross-Server Sync**: PostgreSQL-backed distributed state
- **Version Control**: Git-like branching for builds

## Architecture

```
┌─────────────────────────────────────────────────┐
│           INTERFACE LAYER                        │
│  Minecraft Chat | Web Dashboard | CLI Tool      │
└───────────────────┬─────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│           API GATEWAY (FastAPI)                  │
│  Auth | RateLimit | SpatialLock | Throttling    │
└───────────────────┬─────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│         OMNI-ORCHESTRATOR v3.1                   │
│  CommandParser → TerrainMatcher → Architect     │
│  PhysicsValidator | StyleLearner | VersionCtrl  │
└───────────────────┬─────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│         INTELLIGENCE (Ollama LLMs)               │
│  qwen2.5-coder:7b | llama3.1:8b | deepseek:16b │
│  Tool Calling: place_block, fill_region, etc.   │
└───────────────────┬─────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│         MEMORY (MemPalace v3.1)                  │
│  Spatial Registry | Undo Journal | Preferences  │
│  Version Branches | CRDT Sync                    │
└───────────────────┬─────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│         MINECRAFT BRIDGE (PaperMC)               │
│  WebSocket | WorldEdit | Event API              │
│  Ghost Blocks | Physics Sim | Block Scanning    │
└─────────────────────────────────────────────────┘
```

## Installation

### Requirements
- Python 3.10+
- Ollama (local LLM server)
- PaperMC 1.20.4+ with WorldEdit
- PostgreSQL 14+ (optional, for cross-server sync)
- 8GB VRAM / 32GB RAM recommended

### Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Pull Ollama models
ollama pull qwen2.5-coder:7b
ollama pull llama3.1:8b
ollama pull deepseek-coder-v2:16b-lite-q4_0

# Initialize MemPalace
mkdir -p ~/minecraft_palace

# Configure Ollama (~/.ollama/config.json)
{
  "num_gpu": 25,
  "num_thread": 8,
  "context_length": 8192
}
```

## Usage

### Chat Commands

```
!bot build me a rocket at 100,64,200
!bot preview a castle here
!bot approve
!bot discard
!bot undo last 3
!bot switch to medieval style
!bot like
!bot dislike
!bot commit initial design
!bot diff v1 v2
!bot revert roof-fix
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| /command | POST | Primary chat entry (!bot ...) |
| /build | POST | Direct build with lock check |
| /preview | POST | Spawn holographic ghost blocks |
| /approve | POST | Convert preview to real blocks |
| /discard | POST | Remove preview blocks |
| /build/{id}/undo | POST | Rollback N batches |
| /build/{id}/commit | POST | Git-like commit |
| /style/profile | GET/PUT | Player preferences |

## Project Structure

```
minecraft_omni/
├── parser/
│   └── command_parser.py      # NL → BuildIntent
├── orchestrator/
│   ├── terrain_matcher.py     # World-aware placement
│   └── physics_validator.py   # Pre-exec simulation
├── llm/
│   ├── context_compressor.py  # Token reduction
│   └── tool_router.py         # JSON tool calling
├── executor/
│   ├── block_state_registry.py # Block validation
│   └── build_executor.py       # WS execution
├── gateway/
│   └── (spatial_lock_manager.py)
├── memory/
│   └── palace_adapter.py      # MemPalace integration
├── config/
│   └── blocks.json            # Dynamic block registry
├── tests/
│   ├── mocks/                 # Test mocks
│   └── integration/           # Integration tests
└── requirements.txt
```

## Testing

```bash
# Run test suite
pytest tests/ --mock-world --deterministic-llm --physics-sim

# Run specific tests
pytest tests/integration/test_build_flow.py
```

## Performance Targets

| Metric | Target | Mechanism |
|--------|--------|-----------|
| Command parsing | < 50ms | Cached regex |
| Context compression | 80% reduction | Surface-only extraction |
| Physics simulation | < 100ms | 20-tick local sim |
| LLM generation | 50 tok/s | Tool calling |
| Block placement | 50-100/tick | Adaptive throttling |
| Holographic preview | < 1s spawn | Client-side rendering |
| CRDT merge latency | < 50ms | Y.js/Automerge |

## Error Handling

| Failure | Solution |
|---------|----------|
| LLM invalid JSON | Schema validation → Retry (3x) → Fallback |
| Physics violation | Reject → Auto-patch → Re-simulate |
| Terrain collision | TerrainMatcher auto-adjusts Y |
| TPS drop < 15 | AdaptiveThrottler: 100→50→10 blocks/tick |
| Manual block break | Tombstone log → Hash mismatch → Resync |
| Concurrent edit conflict | CRDT merge → Timestamp resolution |

## License

MIT License

## Version

3.1.0-Omni (Production Ready)
