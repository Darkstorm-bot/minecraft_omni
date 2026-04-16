**User:**

Now create Agent.md with all improvent and with the context from qwen_chat_extreact

**Kimi:**

I'll create the comprehensive **Agent.md** integrating all v3.0 production features and v3.1 Omni-tier improvements from the Qwen conversation context.

\# Minecraft Omni-Builder Agent Architecture  
<br/>\*\*Version\*\*: 3.1.0 (Omni-Tier)  
\*\*Status\*\*: Production-Ready + Omni Extensions  
\*\*Purpose\*\*: Natural language Minecraft building with local LLMs, spatial memory sync, physics validation, and multiplayer collaboration  
\*\*Hardware Target\*\*: 32GB RAM, 8GB VRAM (RTX 4070)  
<br/>\*\*Changelog\*\*:  
\- v2.0 → v3.0: Added ContextCompressor, BlockStateRegistry, SpatialLockManager, UndoJournal, SyncEngine, Alembic migrations  
\- v3.0 → v3.1: Added PhysicsValidator, ToolCalling architecture, TerrainMatcher, CRDT collaboration, holographic previews, style learning, cross-server sync  
<br/>\---  
<br/>\## 1. System Overview

┌─────────────────────────────────────────────────────────────────────────────┐ │ MINECRAFT OMNI-BUILDER v3.1 │ ├─────────────────────────────────────────────────────────────────────────────┤ │ │ │ LAYER 1: INTERFACE │ │ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐ │ │ │ Minecraft │ │ Web Dashboard│ │ CLI Tool │ │ Holographic │ │ │ │ Chat (!bot) │ │ (React/Vue) │ │ (mempalace) │ │ Preview (Ghost) │ │ │ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────────────────┘ │ │ │ │ │ │ │ LAYER 2: API GATEWAY (FastAPI + Middleware) │ │ ┌────────────────────────────────────────────────────────────────────┐ │ │ │ /command /build /preview /approve /lock /undo /sync /mcp │ │ │ │ Auth: UUID + Session + RateLimit (5 cmd/min, 3 concurrent) │ │ │ │ Throttle: AdaptiveThrottler (TPS-aware: 100→50→10 blocks/tick) │ │ │ │ Lock: SpatialLockManager / CRDTLockManager (v3.1) │ │ │ └────────────────────┬───────────────────────────────────────────────┘ │ │ │ │ │ LAYER 3: ORCHESTRATION (Omni-Intelligence) │ │ ┌────────────────────┴───────────────────────────────────────────────┐ │ │ │ OMNI-ORCHESTRATOR v3.1 │ │ │ │ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │ │ │ │ │ Command │ │ Hierarchical │ │ Terrain │ │ │ │ │ │ Parser │→ │ Architect │→ │ Matcher │ │ │ │ │ └──────────────┘ └──────────────┘ └──────────────┘ │ │ │ │ ↓ ↓ ↓ │ │ │ │ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │ │ │ │ │ Physics │ │ Style │ │ Version │ │ │ │ │ │ Validator │ │ Learner │ │ Control │ │ │ │ │ │ (Simulator) │ │ (Preferences)│ │ (Git-like) │ │ │ │ │ └──────────────┘ └──────────────┘ └──────────────┘ │ │ │ └────────────────────────────────────────────────────────────────────┘ │ │ │ │ │ LAYER 4: INTELLIGENCE (LLM Cluster + Tool Calling) │ │ ┌────────────────────┴───────────────────────────────────────────────┐ │ │ │ Ollama Endpoint (localhost:11434) │ │ │ │ ├── qwen2.5-coder:7b (Fast/Structural, Tool calling) │ │ │ │ ├── llama3.1:8b (Balanced/Creative) │ │ │ │ └── deepseek-coder-v2:16b (Complex/Architectural) │ │ │ │ │ │ │ │ Pre-Processor: ContextCompressor (80% token reduction) │ │ │ │ Output Format: JSON Tool Calls (NOT raw Python) │ │ │ │ Tools: place*block, fill_region, set_palette, carve_terrain │ │ │ └────────────────────────────────────────────────────────────────────┘ │ │ │ │ │ LAYER 5: MEMORY (MemPalace v3.1 + Distributed Sync) │ │ ┌────────────────────┴───────────────────────────────────────────────┐ │ │ │ WING: Build_Session*\[ID\] │ │ │ │ ├── ROOM: Exterior/Interior/Spatial/Design │ │ │ │ ├── ROOM: Undo_Journal (Command pattern logs) │ │ │ │ ├── ROOM: Tombstone_Log (Manual breaks + Sync drift) │ │ │ │ ├── ROOM: Preference_Learning (Style profiles) │ │ │ │ ├── ROOM: Version_Branches (Git-like DAG) │ │ │ │ ├── KG: Component_Graph (Entity relationships) │ │ │ │ ├── SYNC: Bidirectional Event Stream │ │ │ │ └── BACKEND: PostgreSQL/CRDT (Cross-server, v3.1) │ │ │ └────────────────────────────────────────────────────────────────────┘ │ │ │ │ │ LAYER 6: MINECRAFT BRIDGE (PaperMC + Physics Engine) │ │ ┌────────────────────┴───────────────────────────────────────────────┐ │ │ │ WebSocket Client ←→ PaperMC Plugin │ │ │ │ Functions: │ │ │ │ - scan_area() with topography data │ │ │ │ - place_blocks() with BlockState validation │ │ │ │ - on_block_change() (Break/Place events) │ │ │ │ - spawn_ghost_blocks() (Holographic preview) │ │ │ │ - get_physics_state() (Gravity, fluid, redstone sim) │ │ │ │ - register_dynamic_blocks() (Mod support: Create, Mekanism) │ │ │ └────────────────────────────────────────────────────────────────────┘ │ │ │ └─────────────────────────────────────────────────────────────────────────────┘

\---  
<br/>\## 2. Core Components (v3.0 + v3.1)  
<br/>\### 2.1 Command Parser  
\*\*File\*\*: \`parser/command_parser.py\`  
\*\*Purpose\*\*: Natural language → structured intent with relative positioning  
<br/>\*\*Supported Patterns\*\*:  
\- \`!bot build me a rocket in front of me\`  
\- \`!bot preview a castle here\` (v3.1 - Holographic)  
\- \`!bot approve\` / \`!bot discard\` (v3.1 - Workflow)  
\- \`!bot undo last 3\` (v3.0 - Command pattern)  
\- \`!bot switch to medieval style\` (v3.1 - Style learning)  
<br/>\---  
<br/>\### 2.2 Terrain Matcher (v3.1 Omni)  
\*\*File\*\*: \`orchestrator/terrain_matcher.py\`  
\*\*Purpose\*\*: World-aware placement, prevents clipping into mountains  
<br/>\`\`\`python  
class TerrainMatcher:  
def analyze_foundation(self, origin: Vector3, bounds: Bounds) -> TerrainProfile:  
"""  
Scan chunk topography via scan_area()  
Returns: elevation map, biome type, obstruction list  
"""  
<br/>def generate_foundation_plan(self, profile: TerrainProfile) -> List\[ToolCall\]:  
"""  
Auto-generate pylings/fill for uneven terrain  
Returns: Tool calls for terraforming layer  
"""  
<br/>def adjust_origin_y(self, origin: Vector3, profile: TerrainProfile) -> Vector3:  
"""  
Dynamic y=0 adjustment per biome  
Desert: y-1 (sand compacts), Mountain: y+5 (pilings)  
"""

**Integration**: Runs before HierarchicalArchitect, modifies origin/bounds in build plan

### 2.3 Physics Validator (v3.1 Critical)

**File**: orchestrator/physics_validator.py  
**Purpose**: Pre-execution simulation, prevents floating blocks & broken redstone

class PhysicsValidator:  
SIMULATION_TICKS = 20 # 1 second of game time  
<br/>def simulate_placement(self, actions: List\[ToolCall\], world_state: WorldSnapshot) -> ValidationResult:  
"""  
Simulates:  
\- Gravity (sand/gravel fall, unsupported stone?)  
\- Fluid dynamics (water/lava flow)  
\- Redstone timing (circuit completeness)  
\- Light levels (torch placement for mob spawning)  
"""  
<br/>def patch_invalid(self, actions: List\[ToolCall\], errors: List\[PhysicsError\]) -> List\[ToolCall\]:  
"""  
Auto-fix: Add support blocks, adjust redstone repeaters,  
place torches in dark zones  
"""

**Blocking**: Invalid actions rejected before WebSocket send, returned to LLM for correction with error context

### 2.4 Context Compressor (v3.0)

**File**: llm/context_compressor.py  
**Purpose**: Solve 4K token limit on 7B models

class ContextCompressor:  
@staticmethod  
def compress_zone(spatial_data: List\[BlockRecord\], max_tokens: int = 2000) -> str:  
\# 1. Surface-only extraction (interior blocks hidden)  
surface = \[b for b in spatial_data if b.is_surface\]  
<br/>\# 2. Semantic clustering  
clusters = defaultdict(list)  
for b in surface:  
clusters\[b.block_type\].append(f"({b.x},{b.y},{b.z})")  
<br/>\# 3. Pattern summarization (80% reduction)  
summary = \[\]  
for btype, coords in clusters.items():  
if len(coords) > 20:  
summary.append(f"{len(coords)}x {btype} forming structural shell")  
else:  
summary.append(f"{btype} at {coords\[:5\]}")  
<br/>return "\\n".join(summary)

### 2.5 Tool Calling Architecture (v3.1 Security)

**File**: llm/tool_router.py  
**Purpose**: Replace raw Python exec() with validated JSON schema

**Schema Definition**:

TOOLS = {  
"place_block": {  
"description": "Place single block with state",  
"parameters": {  
"x": int, "y": int, "z": int,  
"block": str,  
"state": dict, # {"facing": "north", "half": "bottom"}  
"nbt": Optional\[dict\]  
}  
},  
"fill_region": {  
"description": "Fill 3D region with block type",  
"parameters": {  
"min": \[int, int, int\],  
"max": \[int, int, int\],  
"block": str,  
"replace": Optional\[str\] # Target block to replace only  
}  
},  
"carve_terrain": {  
"description": "Remove blocks (terraforming)",  
"parameters": {  
"min": \[int, int, int\],  
"max": \[int, int, int\],  
"replace_with": str # Default "air"  
}  
},  
"set_lighting": {  
"description": "Place light sources",  
"parameters": {  
"positions": List\[\[int, int, int\]\],  
"level": int # 0-15  
}  
}  
}

**Workflow**: 1. LLM outputs JSON tool call (NOT Python code) 2. ToolRouter.validate() against schema using Pydantic 3. PhysicsValidator.simulate() pre-checks validity 4. BlockStateRegistry.resolve() converts to Minecraft BlockData 5. BuildExecutor.apply_actions() sends via WebSocket

**Security**: No exec(), no code injection, deterministic action space

### 2.6 Block State Registry (v3.0)

**File**: executor/block_state_registry.py

class BlockStateRegistry:  
def \__init_\_(self, registry_path: str = "config/blocks.json"):  
\# Load from server API for mod support (Create, Mekanism)  
self.dynamic_registry = self.\_load_server_registry()  
<br/>def resolve(self, tool_call: dict) -> BlockData:  
"""  
Convert "oak_stairs\[facing=north,half=bottom\]"  
to Minecraft BlockData with validation  
"""  
base = tool_call\["block"\]  
props = tool_call.get("state", {})  
<br/>\# Validate against server registry  
valid_props = self.dynamic_registry.get(base, {})  
resolved = {k: v for k, v in props.items()  
if k in valid_props and v in valid_props\[k\]}  
<br/>return BlockData(base, resolved)

### 2.7 Spatial Lock Manager (v3.0) / CRDT Lock Manager (v3.1)

**File**: gateway/spatial_lock_manager.py

**v3.0 (Blocking Locks)**:

class SpatialLockManager:  
def claim_region(self, x1, z1, x2, z2, player_uuid, ttl_sec=300) -> Tuple\[bool, str\]:  
if self.db.check_overlap(x1, z1, x2, z2):  
return False, "Region occupied by Player A's build. Suggested: +50X"  
self.db.insert_lock(x1, z1, x2, z2, player_uuid, ttl_sec)  
return True, "Claimed"

**v3.1 (CRDT Collaborative)**:

class CRDTLockManager:  
"""  
Real-time collaborative editing without blocking  
Uses Y.js/Automerge CRDT for conflict resolution  
"""  
def merge_concurrent_edits(self, region: Bounds, edits: List\[PlayerEdit\]) -> MergedEdit:  
"""  
Timestamp + priority-based merge  
Conflicts: Higher player_level wins, then timestamp  
"""

### 2.8 MemPalace Adapter + Sync Engine (v3.0)

**File**: memory/palace_adapter.py, memory/sync_engine.py

class MinecraftMemPalace:  
def log_block_placement(self, block_type, x, y, z, room_name, context):  
"""Verbatim storage + Undo journal entry"""  
self.db.insert("spatial_registry",  
(build_id, x, y, z, block_type, room_name, context, time.time()))  
self.db.insert("undo_stack",  
(build_id, "PLACE", json.dumps(\[x,y,z,block_type\]), time.time()))  
<br/>def log_tombstone(self, x, y, z, timestamp, reason="manual_break"):  
"""Bidirectional sync: Track manual block breaks"""  
self.db.insert("tombstones", (x, y, z, timestamp, reason))  
self.spatial_registry.mark_invalid(x, y, z)  
<br/>def get_style_profile(self, player_uuid: str) -> StyleProfile:  
"""  
v3.1: Learn player preferences from past builds  
Returns: preferred_blocks, avoided_blocks, symmetry_preference  
"""  
return self.palace.get_room("Preference_Learning").get_profile(player_uuid)

**SyncEngine**:

class SyncEngine:  
async def bidirectional_listener(self):  
"""Listen for plugin block_change events"""  
async for event in ws_stream:  
if event.type == "BLOCK_BREAK":  
self.palace.log_tombstone(event.x, event.y, event.z, event.ts)  
await self.check_hash_consistency(event.region)  
<br/>async def consistency_check(self, region: Bounds, interval_minutes=5):  
"""Hash-based validation, triggers partial resync on drift"""  
current_hash = await mc_client.get_chunk_hash(region)  
if current_hash != self.palace.stored_hash:  
await self.rebuild_spatial_index(region)

### 2.9 Style Learner (v3.1 Omni)

**File**: orchestrator/style_learner.py

class StyleLearner:  
"""  
Long-term preference learning across build sessions  
"""  
def record_feedback(self, player_uuid: str, build_id: str, feedback: Literal\["like", "dislike"\]):  
"""Called on !bot like or !bot dislike"""  
features = self.extract_features(build_id) # Block types, symmetry, etc.  
self.palace.get_room("Preference_Learning").update_profile(player_uuid, features, feedback)  
<br/>def apply_to_prompt(self, player_uuid: str, base_prompt: str) -> str:  
"""  
Inject preferences into LLM prompt:  
"Player prefers spruce over oak, avoids glass, likes symmetry"  
"""  
profile = self.palace.get_style_profile(player_uuid)  
return f"{base_prompt}\\n\[Player Preferences: {profile.summary()}\]"

### 2.10 Version Control (v3.1 Omni)

**File**: memory/version_control.py

Git-like version control for builds:

class BuildVersionControl:  
def commit(self, build_id: str, message: str) -> CommitHash:  
"""Snapshot current state to DAG"""  
<br/>def branch(self, build_id: str, branch_name: str) -> BranchRef:  
"""Fork build for experimental changes"""  
<br/>def diff(self, commit_a: str, commit_b: str) -> List\[BlockDiff\]:  
"""!bot diff v1 v2 - Show block changes between versions"""  
<br/>def revert(self, build_id: str, commit_hash: str):  
"""!bot revert roof-fix - Rollback to specific commit"""

## 3\. Data Flows

### 3.1 Standard Build Flow (v3.0+v3.1)

Player: "!bot build rocket at 100,64,200"  
↓  
1\. CommandParser → BuildIntent(target="rocket", pos=relative_calculated)  
↓  
2\. SpatialLockManager.claim_region() → ✅ Claimed (or suggest offset)  
↓  
3\. TerrainMatcher.analyze_foundation()  
→ Detects hill at 100,64,200  
→ Generates pilings plan (y-adjust)  
↓  
4\. HierarchicalArchitect.generate_zones()  
→ Rocket: Nose, Tank, Engine (zones)  
↓  
5\. ContextCompressor → 80% token reduction  
↓  
6\. LLM Router (deepseek-coder-v2)  
→ Output: JSON Tool Calls (NOT Python)  
→ \[{"tool": "place_block", "params": {...}}, ...\]  
↓  
7\. PhysicsValidator.simulate()  
→ Check: Floating blocks? Unsupported sand? Dark zones?  
→ Auto-patches: Add torch, add support block  
↓  
8\. BlockStateRegistry.resolve()  
→ Validate "oak_stairs\[facing=north\]"  
↓  
9\. AdaptiveThrottler (TPS check: 19.2 → allow 100 blocks/tick)  
↓  
10\. BuildExecutor.place_blocks() via WebSocket  
↓  
11\. MemPalace.log_block_placement() + Undo_Journal entry  
↓  
12\. Player: "!bot undo" → BuildUndoStack.undo() → Delete blocks + Tombstone log

### 3.2 Holographic Preview Flow (v3.1)

Player: "!bot preview castle at 100,64,200"  
↓  
1\. Same steps 1-7 above (planning + physics validation)  
↓  
2\. BuildExecutor.spawn_ghost_blocks(alpha=0.3, client_only=True)  
→ Blocks visible but not physical (no collision)  
↓  
3\. Player walks through preview, inspects from angles  
↓  
4\. Player: "!bot approve"  
→ Ghost blocks converted to real blocks  
→ OR "!bot discard" → Remove ghosts

### 3.3 Collaborative Build Flow (v3.1 CRDT)

Player A: "!bot build west wing of castle"  
Player B: "!bot build east wing of castle" (concurrent, adjacent)  
↓  
CRDTLockManager.merge_concurrent_edits()  
↓  
Conflict at boundary (x=150):  
\- Player A placed wall at 150,64,200 at T=100  
\- Player B placed window at 150,64,200 at T=102  
↓  
Resolution: Timestamp wins (Player B), but check compatibility  
\- Window in wall? Valid. Merge: Wall with window block.  
\- Wall vs Air? Invalid. Keep wall (structural integrity rule).  
↓  
Both players see real-time updates via WebSocket broadcast

## 4\. API Specification (v3.1)

| Endpoint           | Method    | Description                       |
| ------------------ | --------- | --------------------------------- |
| /command           | POST      | Primary chat entry (!bot …)       |
| /build             | POST      | Direct build with lock check      |
| /preview           | POST      | Spawn holographic ghost blocks    |
| /approve           | POST      | Convert preview to real blocks    |
| /discard           | POST      | Remove preview blocks             |
| /build/{id}/undo   | POST      | Rollback N batches                |
| /build/{id}/commit | POST      | Git-like commit (v3.1)            |
| /build/{id}/diff   | GET       | Compare versions (v3.1)           |
| /style/profile     | GET/PUT   | Player preference learning (v3.1) |
| /lock/claim        | POST      | Manual region reservation         |
| /sync/trigger      | POST      | Force consistency check           |
| /metrics           | GET       | Prometheus telemetry              |
| /ws/minecraft      | WebSocket | Bidirectional + preview protocol  |

## 5\. Memory Schema (MemPalace v3.1)

Wing: "Build_Session_Castle_001"  
├── metadata: {  
│ player_uuid, origin, dimension,  
│ schema_version: "3.1", git_head: "abc123"  
│ }  
├── Room: "Exterior_Shell" → Block placements  
├── Room: "Interior_Rooms" → Block placements  
├── Room: "Spatial_Registry" → Chunk indices  
├── Room: "Design_Context" → Rationale logs  
├── Room: "Undo_Journal" → Command patterns (place/delete pairs)  
├── Room: "Tombstone_Log" → Manual breaks + sync drifts  
├── Room: "Preference_Learning" (v3.1) → Player style profiles  
├── Room: "Version_Branches" (v3.1) → Git-like DAG storage  
├── Room: "Preview_States" (v3.1) → Pending ghost block data  
└── Knowledge Graph: Component connections + CRDT merge history

## 6\. Installation & Setup

### 6.1 System Requirements

- Python 3.10+
- Ollama (local LLM server)
- PaperMC 1.20.4+ with WorldEdit
- PostgreSQL 14+ (v3.1 cross-server sync, optional for single-server)
- 8GB VRAM / 32GB RAM

### 6.2 Dependencies

pip install fastapi uvicorn websockets numpy mempalace alembic prometheus-client  
pip install pydantic y-py # v3.1 CRDT support  
pip install chromadb # Vector search

### 6.3 Ollama Configuration (8GB VRAM optimized)

ollama pull qwen2.5-coder:7b  
ollama pull llama3.1:8b  
ollama pull deepseek-coder-v2:16b-lite-q4_0  
<br/>\# ~/.ollama/config.json  
{  
"num_gpu": 25, # Hybrid offload  
"num_thread": 8,  
"context_length": 8192 # For city-scale prompts  
}

### 6.4 Database Setup

\# Initialize MemPalace  
mempalace init ~/minecraft_palace --version 3.1  
<br/>\# Alembic migrations (v3.0+)  
alembic upgrade head  
<br/>\# PostgreSQL for cross-server (v3.1)  
createdb mc_omni_shared

### 6.5 Dynamic Block Registry (Mod Support)

\# Extract blocks from running server (vanilla or modded)  
python -m scripts.load_block_registry \\  
\--server <http://localhost:25565> \\  
\--output config/blocks.json \\  
\--mods create,mekanism # v3.1 mod support

## 7\. Error Handling & Recovery Matrix

| Failure                  | Layer | Solution                                                              |
| ------------------------ | ----- | --------------------------------------------------------------------- |
| LLM invalid JSON         | 4     | Schema validation → Retry with error context (3x) → Fallback template |
| Physics violation        | 3     | Reject → Auto-patch → Re-simulate → Success or human review           |
| Terrain collision        | 3     | TerrainMatcher auto-adjusts Y or requests !bot flatten first          |
| TPS drop < 15            | 2     | AdaptiveThrottler: 100→50→10 blocks/tick, pause non-essential         |
| WebSocket disconnect     | 6     | Queue persistence → SQLite → Resume on reconnect                      |
| Manual block break       | 5     | Tombstone log → Hash mismatch → Partial resync                        |
| Concurrent edit conflict | 2     | CRDT merge → Timestamp/priority resolution → Broadcast update         |
| Cross-server drift       | 5     | PostgreSQL CRDT sync → Vector clock reconciliation                    |

## 8\. Performance Targets (v3.1)

| Metric              | Target        | Mechanism                          |
| ------------------- | ------------- | ---------------------------------- |
| Command parsing     | < 50ms        | Cached regex + lightweight intent  |
| Context compression | 80% reduction | Surface-only + semantic clustering |
| Physics simulation  | < 100ms       | 20-tick local simulation           |
| LLM generation      | 50 tok/s      | Tool-calling reduces output tokens |
| Block placement     | 50-100/tick   | Adaptive throttling                |
| Holographic preview | < 1s spawn    | Client-side ghost rendering        |
| CRDT merge latency  | < 50ms        | Y.js/Automerge wasm                |
| Spatial query (R@5) | \> 96%        | ChromaDB + SQLite index            |
| Cross-server sync   | < 500ms       | PostgreSQL NOTIFY + WebSocket      |

## 9\. Testing Architecture

\# tests/mocks.py  
class MockMinecraftClient:  
def \__init_\_(self):  
self.world = defaultdict(lambda: "air")  
self.physics = MockPhysicsEngine()  
<br/>async def place_blocks(self, blocks):  
for b in blocks:  
\# Simulate physics  
if not self.physics.is_supported(b):  
raise PhysicsError("Floating block")  
self.world\[(b.x,b.y,b.z)\] = b.type  
<br/>class DeterministicLLM:  
"""Returns canned responses for regression testing"""  
def generate(self, prompt, seed=42):  
return CANNED_RESPONSES\[seed % len(CANNED_RESPONSES)\]  
<br/>class BuildValidator:  
def check_integrity(self, schematic):  
errors = \[\]  
if has_floating_blocks(schematic):  
errors.append("UNSTABLE_SUPPORT")  
if not has_lighting(schematic):  
errors.append("DARK_ZONE")  
if has_fluid_leak(schematic):  
errors.append("FLUID_LEAK")  
return errors  
<br/>\# CI Pipeline  
pytest tests/integration/test_build_flow.py \\  
\--mock-world \\  
\--deterministic-llm \\  
\--physics-sim

## 10\. Deployment Checklist

- ☐ Ollama models pulled (7B, 8B, 16B) & VRAM allocated
- ☐ PaperMC plugin with Event API + WorldEdit
- ☐ SpatialLockManager SQLite initialized
- ☐ Dynamic block registry loaded (vanilla/modded)
- ☐ MemPalace v3.1 schema migrated (Alembic)
- ☐ PostgreSQL sync backend (if cross-server)
- ☐ Prometheus metrics endpoint exposed
- ☐ PhysicsValidator test suite passing
- ☐ Mock testing suite passing
- ☐ Rate limits & blacklists configured
- ☐ Preview workflow (!bot preview/approve) enabled
- ☐ CRDT collaboration (if multiplayer server cluster)
- ☐ Backup strategy (MemPalace + PostgreSQL WAL)

**Document Version**: 3.1.0-Omni  
**Last Updated**: 2026-04-16  
**Schema Migration**: Use alembic revision -m "v3.1_omni_features" for upgrades \`\`\`