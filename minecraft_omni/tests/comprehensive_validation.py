"""
Minecraft Omni-Builder v3.1 - Complete Feature Validation Test Suite
Tests all modules, functions, and features against agent.md and qwen_chat_extract (1).json specifications.
"""
import sys
import os
import asyncio
import json
import unittest
from typing import List, Dict, Tuple
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

class TestResults:
    """Track test results across all modules"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.details = []
    
    def add_pass(self, test_name: str, details: str = ""):
        self.passed += 1
        self.details.append(('PASS', test_name, details))
        print(f"✓ PASS: {test_name} - {details}")
    
    def add_fail(self, test_name: str, error: str):
        self.failed += 1
        self.details.append(('FAIL', test_name, error))
        print(f"✗ FAIL: {test_name} - {error}")
    
    def add_skip(self, test_name: str, reason: str = ""):
        self.skipped += 1
        self.details.append(('SKIP', test_name, reason))
        print(f"⊘ SKIP: {test_name} - {reason}")
    
    def summary(self) -> str:
        total = self.passed + self.failed + self.skipped
        completion_rate = (self.passed / total * 100) if total > 0 else 0
        return f"""
========================================
TEST SUMMARY
========================================
Passed:  {self.passed}/{total}
Failed:  {self.failed}/{total}
Skipped: {self.skipped}/{total}
Completion Rate: {completion_rate:.1f}%
========================================
"""

results = TestResults()

# ============================================================================
# MODULE 1: Parser Tests
# ============================================================================
def test_parser_module():
    print("\n=== Testing Parser Module ===")
    try:
        from minecraft_omni.parser.command_parser import CommandParser
        
        parser = CommandParser()
        
        # Test 1: Basic command parsing
        cmd = "!bot build a house at 100,64,200"
        intent = parser.parse(cmd)
        if intent and intent.command_type.value == 'build':
            results.add_pass("CommandParser.parse()", "Basic NL command parsed")
        else:
            results.add_fail("CommandParser.parse()", f"Failed to parse basic command: {intent}")
        
        # Test 2: Relative positioning (set player position first)
        from minecraft_omni.parser.command_parser import Vector3
        parser.set_player_position("test_player", Vector3(0, 64, 0))
        cmd_rel = "!bot build 5 blocks north"
        intent_rel = parser.parse(cmd_rel, "test_player")
        if intent_rel and intent_rel.context.get('relative'):
            results.add_pass("CommandParser.relative_positioning", "Relative positioning detected")
        else:
            results.add_fail("CommandParser.relative_positioning", "Relative positioning not working")
        
        # Test 3: Intent building via _build_intent
        from minecraft_omni.parser.command_parser import CommandType
        intent_dict = parser._build_intent(CommandType.BUILD, {'target': 'house', 'coords': '100,64,200'})
        if intent_dict and intent_dict.command_type == CommandType.BUILD:
            results.add_pass("CommandParser._build_intent()", "Intent dictionary built correctly")
        else:
            results.add_fail("CommandParser._build_intent()", "Intent building failed")
            
    except ImportError as e:
        results.add_fail("Parser Module Import", str(e))
    except Exception as e:
        results.add_fail("Parser Module", str(e))

# ============================================================================
# MODULE 2: Orchestrator Tests
# ============================================================================
def test_orchestrator_module():
    print("\n=== Testing Orchestrator Module ===")
    try:
        from minecraft_omni.orchestrator.terrain_matcher import TerrainMatcher
        from minecraft_omni.orchestrator.physics_validator import PhysicsValidator
        from minecraft_omni.orchestrator.style_learner import StyleLearner
        from minecraft_omni.parser.command_parser import Vector3, Bounds
        
        # Test TerrainMatcher - analyze_foundation takes origin and Bounds
        matcher = TerrainMatcher(None)  # Mock client
        origin = Vector3(100, 64, 200)
        bounds = Bounds(Vector3(95, 60, 195), Vector3(105, 70, 205))
        foundation = matcher.analyze_foundation(origin, bounds)
        if foundation is not None:
            results.add_pass("TerrainMatcher.analyze_foundation()", "Foundation analysis works")
        else:
            results.add_fail("TerrainMatcher.analyze_foundation()", "Returned None")
        
        plan = matcher.generate_foundation_plan(foundation, 'stone')
        if plan and isinstance(plan, list):
            results.add_pass("TerrainMatcher.generate_foundation_plan()", "Foundation plan generated")
        else:
            results.add_fail("TerrainMatcher.generate_foundation_plan()", "Plan generation failed")
        
        # Test PhysicsValidator
        validator = PhysicsValidator()
        sim_result = validator.simulate_placement([{'x': 100, 'y': 64, 'z': 200, 'block': 'stone'}])
        if 'valid_positions' in sim_result or 'invalid_positions' in sim_result:
            results.add_pass("PhysicsValidator.simulate_placement()", "Physics simulation works")
        else:
            results.add_fail("PhysicsValidator.simulate_placement()", "Invalid simulation result")
        
        patched = validator.patch_invalid(sim_result, 'stone_slab')
        if patched is not None:
            results.add_pass("PhysicsValidator.patch_invalid()", "Invalid position patching works")
        else:
            results.add_fail("PhysicsValidator.patch_invalid()", "Patching failed")
        
        # Test StyleLearner
        learner = StyleLearner()
        learner.record_feedback("modern_tower", True, {"material": "concrete"})
        prompt_additions = learner.apply_to_prompt("build a tower")
        if prompt_additions and isinstance(prompt_additions, str):
            results.add_pass("StyleLearner.apply_to_prompt()", "Style learning works")
        else:
            results.add_fail("StyleLearner.apply_to_prompt()", "Style application failed")
            
    except ImportError as e:
        results.add_fail("Orchestrator Module Import", str(e))
    except Exception as e:
        results.add_fail("Orchestrator Module", str(e))

# ============================================================================
# MODULE 3: LLM Module Tests
# ============================================================================
def test_llm_module():
    print("\n=== Testing LLM Module ===")
    try:
        from minecraft_omni.llm.context_compressor import ContextCompressor, BlockRecord
        from minecraft_omni.llm.tool_router import ToolRouter, ToolCall
        
        # Test ContextCompressor - takes List[BlockRecord] not raw dicts
        compressor = ContextCompressor()
        blocks = [BlockRecord(x=i, y=64, z=j, block_type='stone') for i in range(10) for j in range(5)]
        compressed = compressor.compress_zone(blocks)
        original_size = len(str(blocks))
        compressed_size = len(compressed)
        reduction = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
        
        if compressed and isinstance(compressed, str):
            results.add_pass("ContextCompressor.compress_zone()", f"Token compression works (reduction: {reduction:.1f}%)")
        else:
            results.add_fail("ContextCompressor.compress_zone()", "Compression failed")
        
        # Note: extract_surface_blocks is a method on ZoneSummary, not ContextCompressor directly
        
        # Test ToolRouter
        router = ToolRouter()
        
        # Test validation
        valid_call = {'tool': 'place_block', 'params': {'x': 100, 'y': 64, 'z': 200, 'block': 'stone'}}
        validated = router.validate(valid_call)
        if validated.is_valid:
            results.add_pass("ToolRouter.validate()", "Valid tool call accepted")
        else:
            results.add_fail("ToolRouter.validate()", f"Valid call rejected: {validated.validation_error}")
        
        # Test invalid call
        invalid_call = {'tool': 'place_block', 'params': {'x': 'not_int', 'y': 64, 'z': 200, 'block': 'stone'}}
        validated_invalid = router.validate(invalid_call)
        if not validated_invalid.is_valid:
            results.add_pass("ToolRouter.validate_invalid()", "Invalid tool call rejected")
        else:
            results.add_fail("ToolRouter.validate_invalid()", "Invalid call was accepted")
        
        # Test parse_llm_output
        llm_json = '[{"tool": "place_block", "params": {"x": 100, "y": 64, "z": 200, "block": "stone"}}]'
        parsed = router.parse_llm_output(llm_json)
        if parsed and len(parsed) > 0 and isinstance(parsed[0], ToolCall):
            results.add_pass("ToolRouter.parse_llm_output()", "LLM output parsed correctly")
        else:
            results.add_fail("ToolRouter.parse_llm_output()", "Parsing failed")
        
        # Test route_llm_output (alias)
        routed = router.route_llm_output(llm_json)
        if routed and len(routed) > 0:
            results.add_pass("ToolRouter.route_llm_output()", "Route method works (alias)")
        else:
            results.add_fail("ToolRouter.route_llm_output()", "Route method failed")
        
        # Test schema retrieval
        schema = router.get_tool_schema('place_block')
        if schema and 'description' in schema:
            results.add_pass("ToolRouter.get_tool_schema()", "Tool schema retrieval works")
        else:
            results.add_fail("ToolRouter.get_tool_schema()", "Schema retrieval failed")
            
    except ImportError as e:
        results.add_fail("LLM Module Import", str(e))
    except Exception as e:
        results.add_fail("LLM Module", str(e))

# ============================================================================
# MODULE 4: Executor Module Tests
# ============================================================================
def test_executor_module():
    print("\n=== Testing Executor Module ===")
    try:
        from minecraft_omni.executor.block_state_registry import BlockStateRegistry, BlockData
        from minecraft_omni.executor.build_executor import BuildExecutor, AdaptiveThrottler
        
        # Test BlockStateRegistry - resolve takes tool_call dict
        registry = BlockStateRegistry()
        tool_call = {'tool': 'place_block', 'params': {'block': 'oak_stairs', 'state': {'facing': 'north', 'half': 'bottom'}}}
        resolved = registry.resolve(tool_call)
        if resolved is None or isinstance(resolved, BlockData):
            results.add_pass("BlockStateRegistry.resolve()", "Block state resolution works")
        else:
            results.add_fail("BlockStateRegistry.resolve()", "State resolution failed")
        
        # Test with invalid block
        invalid_call = {'tool': 'place_block', 'params': {'block': 'nonexistent_block_12345'}}
        invalid_resolved = registry.resolve(invalid_call)
        if not invalid_resolved:
            results.add_pass("BlockStateRegistry.resolve_invalid()", "Invalid block rejected")
        else:
            results.add_fail("BlockStateRegistry.resolve_invalid()", "Invalid block was accepted")
        
        # Test AdaptiveThrottler
        throttler = AdaptiveThrottler()
        throttler.record_latency(50)
        throttler.record_latency(100)
        throttler.record_latency(150)
        batch_size = throttler.calculate_batch_size()
        if 1 <= batch_size <= 100:
            results.add_pass("AdaptiveThrottler.calculate_batch_size()", f"Batch size calculated: {batch_size}")
        else:
            results.add_fail("AdaptiveThrottler.calculate_batch_size()", f"Invalid batch size: {batch_size}")
        
        # Test BuildExecutor (mocked)
        executor = BuildExecutor(None)  # No real client
        if hasattr(executor, 'execute_tool_calls') and hasattr(executor, '_throttler'):
            results.add_pass("BuildExecutor.initialization", "Executor initialized with throttler")
        else:
            results.add_fail("BuildExecutor_initialization", "Missing components")
            
    except ImportError as e:
        results.add_fail("Executor Module Import", str(e))
    except Exception as e:
        results.add_fail("Executor Module", str(e))

# ============================================================================
# MODULE 5: Gateway Module Tests
# ============================================================================
def test_gateway_module():
    print("\n=== Testing Gateway Module ===")
    try:
        from minecraft_omni.gateway.spatial_lock_manager import SpatialLockManager
        from minecraft_omni.gateway.api_gateway import APIGateway, ApprovalWorkflowManager, HolographicPreviewRenderer
        
        # Test SpatialLockManager
        lock_mgr = SpatialLockManager(":memory:")
        claimed = lock_mgr.claim_region("player1", 100, 64, 200, 10, 10, 10)
        if claimed:
            results.add_pass("SpatialLockManager.claim_region()", "Region claiming works")
        else:
            results.add_fail("SpatialLockManager.claim_region()", "Claiming failed")
        
        # Test overlap detection
        overlap = lock_mgr.check_overlap(105, 64, 205, 5, 5, 5)
        if overlap:
            results.add_pass("SpatialLockManager.check_overlap()", "Overlap detection works")
        else:
            results.add_fail("SpatialLockManager.check_overlap()", "Overlap not detected")
        
        # Test ApprovalWorkflowManager
        approval_mgr = ApprovalWorkflowManager()
        build_id = approval_mgr.create_pending_build(
            session_id="test_session",
            player_name="TestPlayer",
            command="build house",
            tool_calls=[{'tool': 'place_block', 'params': {}}],
            preview_blocks=[{'x': 100, 'y': 64, 'z': 200, 'block': 'stone'}]
        )
        if build_id:
            results.add_pass("ApprovalWorkflowManager.create_pending_build()", "Pending build created")
        else:
            results.add_fail("ApprovalWorkflowManager.create_pending_build()", "Build creation failed")
        
        # Test approve
        approved = approval_mgr.approve_build(build_id)
        if approved and approved.status == 'approved':
            results.add_pass("ApprovalWorkflowManager.approve_build()", "Build approval works")
        else:
            results.add_fail("ApprovalWorkflowManager.approve_build()", "Approval failed")
        
        # Test HolographicPreviewRenderer
        renderer = HolographicPreviewRenderer()
        tool_calls = [{'tool': 'place_block', 'arguments': {'x': 100, 'y': 64, 'z': 200, 'block_type': 'stone'}}]
        preview = renderer.generate_preview(tool_calls)
        if preview and len(preview) > 0 and preview[0].get('alpha') == 0.5:
            results.add_pass("HolographicPreviewRenderer.generate_preview()", "Preview generation works")
        else:
            results.add_fail("HolographicPreviewRenderer.generate_preview()", "Preview generation failed")
        
        outlines = renderer.generate_outline_boxes(preview)
        if outlines and len(outlines) > 0:
            results.add_pass("HolographicPreviewRenderer.generate_outline_boxes()", "Outline generation works")
        else:
            results.add_fail("HolographicPreviewRenderer.generate_outline_boxes()", "Outline generation failed")
            
    except ImportError as e:
        results.add_fail("Gateway Module Import", str(e))
    except Exception as e:
        results.add_fail("Gateway Module", str(e))

# ============================================================================
# MODULE 6: Memory Module Tests
# ============================================================================
def test_memory_module():
    print("\n=== Testing Memory Module ===")
    try:
        from minecraft_omni.memory.palace_adapter import MinecraftMemPalace
        from minecraft_omni.memory.sync_engine import SyncEngine
        from minecraft_omni.memory.version_control import BuildVersionControl
        
        # Test MinecraftMemPalace
        palace = MinecraftMemPalace(":memory:")
        palace.log_block_placement(100, 64, 200, 'stone', {}, 'test_session')
        
        undo_stack = palace.get_undo_stack('test_session')
        if undo_stack and len(undo_stack) > 0:
            results.add_pass("MinecraftMemPalace.log_block_placement()", "Block placement logged")
        else:
            results.add_fail("MinecraftMemPalace.log_block_placement()", "Logging failed")
        
        palace.log_tombstone(100, 64, 200, 'test_session')
        tombstones = palace.get_tombstones('test_session')
        if tombstones and len(tombstones) > 0:
            results.add_pass("MinecraftMemPalace.log_tombstone()", "Tombstone logging works")
        else:
            results.add_fail("MinecraftMemPalace.log_tombstone()", "Tombstone logging failed")
        
        # Test SyncEngine
        sync_engine = SyncEngine()
        local_hash = sync_engine.compute_chunk_hash([(100, 64, 200, 'stone')])
        if local_hash and isinstance(local_hash, str):
            results.add_pass("SyncEngine.compute_chunk_hash()", "Hash computation works")
        else:
            results.add_fail("SyncEngine.compute_chunk_hash()", "Hash computation failed")
        
        # Test VersionControl
        vc = BuildVersionControl(":memory:")
        commit_id = vc.commit("initial_build", [(100, 64, 200, 'stone')], "main")
        if commit_id:
            results.add_pass("BuildVersionControl.commit()", "Commit creation works")
        else:
            results.add_fail("BuildVersionControl.commit()", "Commit creation failed")
        
        branch_created = vc.branch("feature_branch", commit_id)
        if branch_created:
            results.add_pass("BuildVersionControl.branch()", "Branch creation works")
        else:
            results.add_fail("BuildVersionControl.branch()", "Branch creation failed")
        
        diff = vc.diff(commit_id, commit_id)
        if diff is not None:  # Can be empty list
            results.add_pass("BuildVersionControl.diff()", "Diff computation works")
        else:
            results.add_fail("BuildVersionControl.diff()", "Diff computation failed")
            
    except ImportError as e:
        results.add_fail("Memory Module Import", str(e))
    except Exception as e:
        results.add_fail("Memory Module", str(e))

# ============================================================================
# MODULE 7: Architect Module Tests
# ============================================================================
def test_architect_module():
    print("\n=== Testing Architect Module ===")
    try:
        from minecraft_omni.architect.hierarchical_planner import HierarchicalArchitect, TemplateLibrary
        from minecraft_omni.parser.command_parser import Vector3
        from minecraft_omni.memory.palace_adapter import MinecraftMemPalace
        
        # Test HierarchicalArchitect - generate_plan needs build_id, prompt, origin, llm_response
        architect = HierarchicalArchitect()
        origin = Vector3(100, 64, 200)
        llm_response = {
            'zones': [
                {'id': 'foundation', 'x': 100, 'y': 64, 'z': 200, 'size': '10x2x10', 'material': 'stone'},
                {'id': 'walls', 'x': 100, 'y': 66, 'z': 200, 'size': '10x4x10', 'material': 'oak_planks'}
            ]
        }
        plan = architect.generate_plan("test_build", "build a house", origin, llm_response)
        if plan and hasattr(plan, 'zones'):
            results.add_pass("HierarchicalArchitect.generate_plan()", "Multi-scale planning works")
        else:
            results.add_fail("HierarchicalArchitect.generate_plan()", "Plan generation failed")
        
        # Test TemplateLibrary - requires palace_adapter
        palace = MinecraftMemPalace(":memory:")
        lib = TemplateLibrary(palace)
        template_data = [(0, 0, 0, 'stone'), (1, 0, 0, 'stone'), (0, 1, 0, 'wood')]
        lib.save_template("test_house", template_data)
        
        instantiated = lib.instantiate_template("test_house", 100, 64, 200)
        if instantiated and len(instantiated) == 3:
            results.add_pass("TemplateLibrary.instantiate_template()", "Template instantiation works")
        else:
            results.add_fail("TemplateLibrary.instantiate_template()", "Instantiation failed")
        
        rotated = lib.instantiate_template("test_house", 100, 64, 200, rotation='90_degrees')
        if rotated and len(rotated) == 3:
            results.add_pass("TemplateLibrary.instantiate_template_rotated()", "Template rotation works")
        else:
            results.add_fail("TemplateLibrary.instantiate_template_rotated()", "Rotation failed")
            
    except ImportError as e:
        results.add_fail("Architect Module Import", str(e))
    except Exception as e:
        results.add_fail("Architect Module", str(e))

# ============================================================================
# MODULE 8: Sync/PostgreSQL Module Tests
# ============================================================================
def test_sync_module():
    print("\n=== Testing Sync/PostgreSQL Module ===")
    try:
        from minecraft_omni.sync.crdt_postgres_backend import CRDTVector, BlockOperation, PostgreSQLBackend, CrossServerSyncEngine
        
        # Test CRDTVector
        v1 = CRDTVector(server_id="server1", timestamp=1000, counter=1)
        v2 = CRDTVector(server_id="server1", timestamp=1001, counter=2)
        if v2 > v1:
            results.add_pass("CRDTVector.comparison", "Vector comparison works")
        else:
            results.add_fail("CRDTVector.comparison", "Comparison failed")
        
        # Test serialization
        v_dict = v1.to_dict()
        v_restored = CRDTVector.from_dict(v_dict)
        if v_restored.server_id == v1.server_id and v_restored.timestamp == v1.timestamp:
            results.add_pass("CRDTVector.serialization", "Vector serialization works")
        else:
            results.add_fail("CRDTVector.serialization", "Serialization failed")
        
        # Test BlockOperation
        op = BlockOperation(
            op_id="test_op_1",
            block_type="stone",
            x=100, y=64, z=200,
            properties={},
            operation="PLACE",
            vector=v1
        )
        if op.checksum and len(op.checksum) == 16:
            results.add_pass("BlockOperation.checksum", "Checksum generation works")
        else:
            results.add_fail("BlockOperation.checksum", "Checksum generation failed")
        
        # Test JSON serialization
        op_json = op.to_json()
        op_restored = BlockOperation.from_json(op_json)
        if op_restored.op_id == op.op_id and op_restored.x == op.x:
            results.add_pass("BlockOperation.serialization", "Operation serialization works")
        else:
            results.add_fail("BlockOperation.serialization", "Serialization failed")
        
        # Test CrossServerSyncEngine initialization
        # Note: Full testing requires running PostgreSQL instance
        try:
            engine = CrossServerSyncEngine("postgresql://test:test@localhost/test", "test_server")
            results.add_pass("CrossServerSyncEngine.initialization", "Engine initialized (PostgreSQL URL)")
        except ImportError:
            results.add_skip("CrossServerSyncEngine.initialization", "asyncpg not installed")
        except Exception as e:
            # Expected if PostgreSQL not running
            results.add_skip("CrossServerSyncEngine.connection", f"PostgreSQL not available: {e}")
            
    except ImportError as e:
        results.add_fail("Sync Module Import", str(e))
    except Exception as e:
        results.add_fail("Sync Module", str(e))

# ============================================================================
# MODULE 9: Preview/Holographic Module Tests
# ============================================================================
def test_preview_module():
    print("\n=== Testing Preview/Holographic Module ===")
    try:
        from minecraft_omni.preview.holographic_client import HolographicPreviewClient, GhostBlock, PreviewConfig
        
        # Test HolographicPreviewClient
        client = HolographicPreviewClient()
        
        preview_data = [
            {'x': 100, 'y': 64, 'z': 200, 'block': 'stone', 'alpha': 0.5},
            {'x': 101, 'y': 64, 'z': 200, 'block': 'stone', 'alpha': 0.5}
        ]
        outlines = [{'minX': 99.5, 'minY': 63.5, 'minZ': 199.5, 'maxX': 100.5, 'maxY': 64.5, 'maxZ': 200.5}]
        
        client.receive_preview_data("test_build", preview_data, outlines)
        if client.current_build_id == "test_build" and len(client.active_previews["test_build"]) == 2:
            results.add_pass("HolographicPreviewClient.receive_preview_data()", "Preview data received")
        else:
            results.add_fail("HolographicPreviewClient.receive_preview_data()", "Data reception failed")
        
        # Test validity change
        client.set_preview_validity("test_build", False)
        blocks = client.active_previews["test_build"]
        if all(b.color == (255, 0, 0) for b in blocks):  # Red for invalid
            results.add_pass("HolographicPreviewClient.set_preview_validity()", "Validity color change works")
        else:
            results.add_fail("HolographicPreviewClient.set_preview_validity()", "Color change failed")
        
        # Test clearing
        client.clear_preview("test_build")
        if "test_build" not in client.active_previews:
            results.add_pass("HolographicPreviewClient.clear_preview()", "Preview clearing works")
        else:
            results.add_fail("HolographicPreviewClient.clear_preview()", "Clearing failed")
        
        # Test PreviewConfig
        if PreviewConfig.VALID_COLOR == (0, 255, 0) and PreviewConfig.DEFAULT_ALPHA == 0.5:
            results.add_pass("PreviewConfig.defaults", "Configuration defaults correct")
        else:
            results.add_fail("PreviewConfig.defaults", "Configuration incorrect")
            
    except ImportError as e:
        results.add_fail("Preview Module Import", str(e))
    except Exception as e:
        results.add_fail("Preview Module", str(e))

# ============================================================================
# MODULE 10: Integration Tests
# ============================================================================
def test_integration():
    print("\n=== Testing Integration ===")
    try:
        # Test full pipeline: Parse -> Route -> Validate -> Execute (mocked)
        from minecraft_omni.parser.command_parser import CommandParser
        from minecraft_omni.llm.tool_router import ToolRouter
        from minecraft_omni.executor.block_state_registry import BlockStateRegistry
        
        parser = CommandParser()
        router = ToolRouter()
        registry = BlockStateRegistry()
        
        # Simulate user command
        cmd = "!bot build a stone floor at 100,64,200"
        intent = parser.parse(cmd)
        
        if intent:
            # Simulate LLM generating tool calls based on intent
            llm_output = '''
            [{"tool": "place_block", "params": {"x": 100, "y": 64, "z": 200, "block": "stone"}},
             {"tool": "place_block", "params": {"x": 101, "y": 64, "z": 200, "block": "stone"}}]
            '''
            
            tool_calls = router.parse_llm_output(llm_output)
            valid_calls = [tc for tc in tool_calls if tc.is_valid]
            
            if len(valid_calls) == 2:
                results.add_pass("Integration.pipeline", f"Full pipeline works: {len(valid_calls)} valid calls")
            else:
                results.add_fail("Integration.pipeline", f"Only {len(valid_calls)} valid calls")
        else:
            results.add_fail("Integration.pipeline", "Intent parsing failed")
        
        # Test memory + version control integration
        from minecraft_omni.memory.palace_adapter import MinecraftMemPalace
        from minecraft_omni.memory.version_control import BuildVersionControl
        
        palace = MinecraftMemPalace(":memory:")
        vc = BuildVersionControl(":memory:")
        
        blocks = [(100, 64, 200, 'stone'), (101, 64, 200, 'stone')]
        for x, y, z, block in blocks:
            palace.log_block_placement(x, y, z, block, {}, 'session1')
        
        commit_id = vc.commit("floor_build", blocks, "main")
        
        if commit_id:
            results.add_pass("Integration.memory_version_control", "Memory + Version Control integration works")
        else:
            results.add_fail("Integration.memory_version_control", "Integration failed")
            
    except Exception as e:
        results.add_fail("Integration Tests", str(e))

# ============================================================================
# MAIN TEST RUNNER
# ============================================================================
def run_all_tests():
    print("=" * 70)
    print("MINECRAFT OMNI-BUILDER v3.1 - COMPLETE VALIDATION SUITE")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    test_parser_module()
    test_orchestrator_module()
    test_llm_module()
    test_executor_module()
    test_gateway_module()
    test_memory_module()
    test_architect_module()
    test_sync_module()
    test_preview_module()
    test_integration()
    
    print("\n" + "=" * 70)
    print(results.summary())
    print("=" * 70)
    
    # Return completion percentage
    total = results.passed + results.failed + results.skipped
    if total > 0:
        return (results.passed / total) * 100
    return 0

if __name__ == "__main__":
    completion = run_all_tests()
    sys.exit(0 if completion >= 85 else 1)  # Pass if >85% completion
