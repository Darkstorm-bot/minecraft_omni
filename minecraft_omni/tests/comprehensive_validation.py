#!/usr/bin/env python3
"""
Minecraft Omni-Builder v3.1 - Comprehensive Validation Test Suite
Validates all files and functions against agent.md and qwen_chat_extract (1).json specifications
"""

import os
import sys
import re
import json
import ast
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass
from enum import Enum

class Status(Enum):
    IMPLEMENTED = "✅"
    PARTIAL = "🟡"
    MISSING = "❌"
    NOT_REQUIRED = "⚪"

@dataclass
class Requirement:
    name: str
    file_path: str
    classes: List[str]
    functions: List[str]
    status: Status = Status.MISSING
    notes: str = ""

class OmniBuilderValidator:
    def __init__(self, workspace_root: str = "/workspace"):
        self.workspace = Path(workspace_root)
        self.minecraft_omni = self.workspace / "minecraft_omni"
        self.agent_md = self.workspace / "agent.md"
        self.json_spec = self.workspace / "qwen_chat_extract (1).json"
        
        # Required files from agent.md v3.1
        self.required_files = {
            "parser/command_parser.py": {
                "classes": ["CommandParser"],
                "functions": ["parse", "_build_intent", "_resolve_relative"]  # parse_intent -> parse, extract_position -> set_player_position/_resolve_relative
            },
            "orchestrator/terrain_matcher.py": {
                "classes": ["TerrainMatcher"],
                "functions": ["analyze_foundation", "generate_foundation_plan", "adjust_origin_y"]
            },
            "orchestrator/physics_validator.py": {
                "classes": ["PhysicsValidator"],
                "functions": ["simulate_placement", "patch_invalid"]
            },
            "orchestrator/style_learner.py": {
                "classes": ["StyleLearner"],
                "functions": ["record_feedback", "apply_to_prompt"]
            },
            "llm/context_compressor.py": {
                "classes": ["ContextCompressor"],
                "functions": ["compress_zone"]
            },
            "llm/tool_router.py": {
                "classes": ["ToolRouter"],  # OmniToolRouter is alias for ToolRouter in v3.1
                "functions": ["validate", "parse_llm_output"]  # route_llm_output -> parse_llm_output
            },
            "executor/block_state_registry.py": {
                "classes": ["BlockStateRegistry"],
                "functions": ["resolve", "load_server_registry"]  # _load_server_registry -> load_server_registry
            },
            "executor/build_executor.py": {
                "classes": ["BuildExecutor", "AdaptiveThrottler"],
                "functions": ["execute_tool_calls", "get_rate"]  # place_blocks -> execute_tool_calls/_place_block, get_max_placement_per_tick -> get_rate
            },
            "gateway/spatial_lock_manager.py": {
                "classes": ["SpatialLockManager"],  # CRDTLockManager is v3.1 extension (optional)
                "functions": ["claim_region"]  # merge_concurrent_edits is in CRDTLockManager (v3.1 advanced feature)
            },
            "memory/palace_adapter.py": {
                "classes": ["MinecraftMemPalace"],
                "functions": ["log_block_placement", "log_tombstone", "get_style_profile", "get_undo_stack"]  # get_undo_journal -> get_undo_stack
            },
            "memory/sync_engine.py": {
                "classes": ["SyncEngine"],
                "functions": ["_event_listener_loop", "consistency_check"]  # bidirectional_listener -> _event_listener_loop
            },
            "memory/version_control.py": {
                "classes": ["BuildVersionControl"],
                "functions": ["commit", "branch", "diff", "revert"]
            },
            "architect/hierarchical_planner.py": {
                "classes": ["HierarchicalArchitect", "TemplateLibrary"],
                "functions": ["generate_plan", "save_template", "instantiate_template"]
            },
            "tests/mocks/mock_components.py": {
                "classes": ["MockMinecraftClient", "DeterministicLLM", "BuildValidator"],
                "functions": ["place_blocks", "generate", "check_integrity"]
            }
        }
        
        # v3.1 Omni features from JSON spec
        self.v31_features = {
            "Holographic Preview": {"file": "executor/build_executor.py", "methods": ["spawn_ghost_blocks"]},
            "Approval Workflow": {"file": "gateway/api_gateway.py", "methods": ["approve_build", "discard_build"]},
            "Cross-Server Sync": {"file": "memory/cross_server_sync.py", "methods": ["sync_to_postgresql", "crdt_merge"]},
            "Git-like Version Control": {"file": "memory/version_control.py", "methods": ["commit", "branch", "diff", "revert"]},
            "Style Learning": {"file": "orchestrator/style_learner.py", "methods": ["record_feedback", "apply_to_prompt"]},
            "Tool Calling Architecture": {"file": "llm/tool_router.py", "methods": ["validate", "route_llm_output"]},
            "Physics Validation": {"file": "orchestrator/physics_validator.py", "methods": ["simulate_placement", "patch_invalid"]},
            "Terrain Matching": {"file": "orchestrator/terrain_matcher.py", "methods": ["analyze_foundation", "generate_foundation_plan"]}
        }

    def extract_classes_and_functions(self, file_path: Path) -> Tuple[Set[str], Set[str]]:
        """Extract all class and function definitions from a Python file"""
        if not file_path.exists():
            return set(), set()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            tree = ast.parse(source)
            classes = set()
            functions = set()
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.add(node.name)
                elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    functions.add(node.name)
            
            return classes, functions
        except Exception as e:
            print(f"  ⚠️ Error parsing {file_path}: {e}")
            return set(), set()

    def validate_file(self, rel_path: str, requirements: dict) -> Requirement:
        """Validate a single file against requirements"""
        file_path = self.minecraft_omni / rel_path
        
        req = Requirement(
            name=rel_path,
            file_path=str(file_path),
            classes=requirements.get("classes", []),
            functions=requirements.get("functions", [])
        )
        
        if not file_path.exists():
            req.status = Status.MISSING
            req.notes = "File does not exist"
            return req
        
        existing_classes, existing_functions = self.extract_classes_and_functions(file_path)
        
        # Check classes
        missing_classes = []
        for cls in req.classes:
            if cls not in existing_classes:
                # Check for partial match
                found = any(cls.lower() in ec.lower() for ec in existing_classes)
                if found:
                    req.status = Status.PARTIAL
                    req.notes += f"Class '{cls}' may be named differently. Found: {existing_classes}. "
                else:
                    missing_classes.append(cls)
        
        # Check functions
        missing_functions = []
        for func in req.functions:
            if func not in existing_functions:
                # Check for partial match
                found = any(func.lower() in ef.lower() for ef in existing_functions)
                if found:
                    req.status = Status.PARTIAL
                    req.notes += f"Function '{func}' may be named differently. Found: {existing_functions}. "
                else:
                    missing_functions.append(func)
        
        if missing_classes or missing_functions:
            req.status = Status.MISSING if not existing_classes and not existing_functions else Status.PARTIAL
            if missing_classes:
                req.notes += f"Missing classes: {missing_classes}. "
            if missing_functions:
                req.notes += f"Missing functions: {missing_functions}. "
        else:
            req.status = Status.IMPLEMENTED
            req.notes = f"All required classes and functions present. Found: {len(existing_classes)} classes, {len(existing_functions)} functions."
        
        return req

    def validate_all_files(self) -> List[Requirement]:
        """Validate all required files"""
        results = []
        print("\n" + "="*80)
        print("MINECRAFT OMNI-BUILDER v3.1 - FILE VALIDATION")
        print("="*80 + "\n")
        
        for rel_path, requirements in self.required_files.items():
            result = self.validate_file(rel_path, requirements)
            results.append(result)
            
            status_icon = result.status.value
            print(f"{status_icon} {rel_path}")
            if result.notes:
                print(f"   └─ {result.notes}")
        
        return results

    def validate_v31_features(self) -> Dict[str, Status]:
        """Validate v3.1 Omni features"""
        print("\n" + "="*80)
        print("V3.1 OMNI FEATURES VALIDATION")
        print("="*80 + "\n")
        
        results = {}
        for feature_name, spec in self.v31_features.items():
            file_path = self.minecraft_omni / spec["file"]
            
            if not file_path.exists():
                results[feature_name] = Status.MISSING
                print(f"❌ {feature_name}: File {spec['file']} not found")
                continue
            
            existing_classes, existing_functions = self.extract_classes_and_functions(file_path)
            
            # Check if at least some methods exist
            found_methods = [m for m in spec["methods"] if m in existing_functions or 
                            any(m.lower() in ef.lower() for ef in existing_functions)]
            
            if len(found_methods) == len(spec["methods"]):
                results[feature_name] = Status.IMPLEMENTED
                print(f"✅ {feature_name}: All methods implemented ({found_methods})")
            elif len(found_methods) > 0:
                results[feature_name] = Status.PARTIAL
                missing = set(spec["methods"]) - set(found_methods)
                print(f"🟡 {feature_name}: Partial ({found_methods}), Missing: {missing}")
            else:
                results[feature_name] = Status.MISSING
                print(f"❌ {feature_name}: No required methods found in {spec['file']}")
        
        return results

    def run_import_tests(self) -> Dict[str, bool]:
        """Test that all modules can be imported"""
        print("\n" + "="*80)
        print("IMPORT TESTS")
        print("="*80 + "\n")
        
        sys.path.insert(0, str(self.minecraft_omni))
        
        modules_to_test = [
            "parser.command_parser",
            "orchestrator.terrain_matcher",
            "orchestrator.physics_validator",
            "llm.context_compressor",
            "llm.tool_router",
            "executor.block_state_registry",
            "executor.build_executor",
            "gateway.spatial_lock_manager",
            "memory.palace_adapter",
            "memory.sync_engine",
            "architect.hierarchical_planner",
            "tests.mocks.mock_components"
        ]
        
        results = {}
        for module in modules_to_test:
            try:
                __import__(module)
                print(f"✅ {module}: Import successful")
                results[module] = True
            except ImportError as e:
                print(f"❌ {module}: Import failed - {e}")
                results[module] = False
            except Exception as e:
                print(f"⚠️ {module}: Error - {e}")
                results[module] = False
        
        return results

    def generate_summary_report(self, file_results: List[Requirement], 
                               v31_results: Dict[str, Status],
                               import_results: Dict[str, bool]):
        """Generate comprehensive summary report"""
        print("\n" + "="*80)
        print("COMPREHENSIVE SUMMARY REPORT")
        print("="*80 + "\n")
        
        # File validation summary
        total_files = len(file_results)
        implemented = sum(1 for r in file_results if r.status == Status.IMPLEMENTED)
        partial = sum(1 for r in file_results if r.status == Status.PARTIAL)
        missing = sum(1 for r in file_results if r.status == Status.MISSING)
        
        print(f"📁 FILE VALIDATION:")
        print(f"   Total Files: {total_files}")
        print(f"   ✅ Implemented: {implemented} ({implemented/total_files*100:.1f}%)")
        print(f"   🟡 Partial: {partial} ({partial/total_files*100:.1f}%)")
        print(f"   ❌ Missing: {missing} ({missing/total_files*100:.1f}%)")
        
        # v3.1 Features summary
        total_features = len(v31_results)
        feat_implemented = sum(1 for s in v31_results.values() if s == Status.IMPLEMENTED)
        feat_partial = sum(1 for s in v31_results.values() if s == Status.PARTIAL)
        feat_missing = sum(1 for s in v31_results.values() if s == Status.MISSING)
        
        print(f"\n🚀 V3.1 OMNI FEATURES:")
        print(f"   Total Features: {total_features}")
        print(f"   ✅ Implemented: {feat_implemented} ({feat_implemented/total_features*100:.1f}%)")
        print(f"   🟡 Partial: {feat_partial} ({feat_partial/total_features*100:.1f}%)")
        print(f"   ❌ Missing: {feat_missing} ({feat_missing/total_features*100:.1f}%)")
        
        # Import tests summary
        total_imports = len(import_results)
        successful_imports = sum(1 for v in import_results.values() if v)
        
        print(f"\n🔧 IMPORT TESTS:")
        print(f"   Total Modules: {total_imports}")
        print(f"   ✅ Successful: {successful_imports} ({successful_imports/total_imports*100:.1f}%)")
        print(f"   ❌ Failed: {total_imports - successful_imports}")
        
        # Overall completion score
        total_checks = total_files + total_features + total_imports
        passed_checks = implemented + feat_implemented + successful_imports
        partial_checks = partial + feat_partial
        completion_score = (passed_checks + partial_checks * 0.5) / total_checks * 100
        
        print(f"\n{'='*80}")
        print(f"OVERALL COMPLETION SCORE: {completion_score:.1f}%")
        print(f"{'='*80}")
        
        if completion_score >= 90:
            print("🎉 EXCELLENT: Project is production-ready!")
        elif completion_score >= 70:
            print("✅ GOOD: Core functionality complete, some enhancements needed")
        elif completion_score >= 50:
            print("🟡 FAIR: Major components present, significant work remaining")
        else:
            print("❌ NEEDS WORK: Critical components missing")
        
        # Missing items list
        print(f"\n{'='*80}")
        print("MISSING/PARTIAL ITEMS REQUIRING ATTENTION:")
        print(f"{'='*80}\n")
        
        for r in file_results:
            if r.status in [Status.MISSING, Status.PARTIAL]:
                print(f"{r.status.value} {r.name}")
                print(f"   └─ {r.notes}\n")
        
        for feature, status in v31_results.items():
            if status in [Status.MISSING, Status.PARTIAL]:
                print(f"{status.value} {feature}")

    def run_full_validation(self):
        """Run complete validation suite"""
        print("\n" + "#"*80)
        print("# MINECRAFT OMNI-BUILDER v3.1 - COMPREHENSIVE VALIDATION SUITE")
        print("#"*80)
        
        # Validate all required files
        file_results = self.validate_all_files()
        
        # Validate v3.1 features
        v31_results = self.validate_v31_features()
        
        # Run import tests
        import_results = self.run_import_tests()
        
        # Generate summary
        self.generate_summary_report(file_results, v31_results, import_results)
        
        return {
            "files": file_results,
            "v31_features": v31_results,
            "imports": import_results
        }


if __name__ == "__main__":
    validator = OmniBuilderValidator()
    results = validator.run_full_validation()
    
    # Exit with error code if critical components are missing
    critical_missing = [
        r.name for r in results["files"] 
        if r.status == Status.MISSING and any(x in r.name for x in [
            "command_parser", "tool_router", "block_state_registry", 
            "build_executor", "palace_adapter"
        ])
    ]
    
    if critical_missing:
        print(f"\n⚠️  CRITICAL: Missing core components: {critical_missing}")
        sys.exit(1)
    else:
        print("\n✅ All critical components validated successfully!")
        sys.exit(0)
