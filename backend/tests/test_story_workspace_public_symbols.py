"""Static DEC-004 guard for Task3 Story Workspace public symbols."""

from __future__ import annotations

import ast
from pathlib import Path
import unittest


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def public_definitions(relative_path: str) -> dict[str, str]:
    tree = ast.parse((BACKEND_ROOT / relative_path).read_text(encoding="utf-8"))
    definitions: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                definitions[node.name] = (
                    "class" if isinstance(node, ast.ClassDef) else "function"
                )
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and not target.id.startswith("_"):
                    definitions[target.id] = "constant"
    return definitions


def dream_route_functions(relative_path: str) -> set[str]:
    tree = ast.parse((BACKEND_ROOT / relative_path).read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not decorator.args:
                continue
            route = decorator.args[0]
            if isinstance(route, ast.Constant) and isinstance(route.value, str):
                if "/dream-" in route.value:
                    names.add(node.name)
    return names


class StoryWorkspacePublicSymbolTests(unittest.TestCase):
    def test_thread_factory_has_one_public_turn_start_entry(self) -> None:
        tree = ast.parse(
            (BACKEND_ROOT / "claude_agent/thread_factory.py").read_text(
                encoding="utf-8"
            )
        )
        factory = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef)
            and node.name == "ClaudeAgentThreadFactory"
        )
        methods = {
            node.name
            for node in factory.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        self.assertIn("run_streaming", methods)
        self.assertNotIn("run_events", methods)
        self.assertIn("_run_streaming_frames", methods)
        self.assertIn("_run_turn_task", methods)

    def test_dream_confirmation_module_uses_dec_004_prefixes(self) -> None:
        definitions = public_definitions(
            "services/story_workspace/dream_confirmation_service.py"
        )
        for name, kind in definitions.items():
            with self.subTest(name=name, kind=kind):
                if kind == "function":
                    self.assertTrue(name.startswith("story_workspace_"), name)
                elif kind == "constant" and name.isupper():
                    self.assertTrue(name.startswith("STORY_WORKSPACE_"), name)
                else:
                    self.assertTrue(name.startswith("StoryWorkspace"), name)

    def test_dream_file_public_constant_uses_dec_004_prefix(self) -> None:
        definitions = public_definitions(
            "services/story_workspace/dream_file_service.py"
        )
        self.assertIn("STORY_WORKSPACE_DREAM_PLATFORM_SUPPORTED", definitions)
        self.assertNotIn("DREAM_PLATFORM_SUPPORTED", definitions)

    def test_dream_mcp_public_functions_use_dec_004_prefixes(self) -> None:
        tool_definitions = public_definitions(
            "libs/claude_agent_kit/server/story_workspace_tool.py"
        )
        server_definitions = public_definitions(
            "libs/claude_agent_kit/server/story_workspace_mcp_server.py"
        )
        for name, kind in {**tool_definitions, **server_definitions}.items():
            with self.subTest(name=name, kind=kind):
                if kind == "function":
                    self.assertTrue(name.startswith("story_workspace_"), name)
                elif kind == "constant" and name.isupper():
                    self.assertTrue(name.startswith("STORY_WORKSPACE_"), name)
                else:
                    self.assertTrue(name.startswith("StoryWorkspace"), name)
        self.assertNotIn("allowed_story_workspace_tool_names", tool_definitions)
        self.assertNotIn("handle_story_workspace_dream_tool", tool_definitions)
        self.assertNotIn("create_story_workspace_mcp_server", server_definitions)

    def test_application_service_factories_are_explicit(self) -> None:
        gateway = public_definitions("services/deck/story_workflow_application.py")
        candidates = {
            name
            for name, kind in gateway.items()
            if kind == "function" and name.startswith("get_")
        }
        self.assertEqual(
            candidates,
            {
                "get_story_workflow_run_application_service",
                "get_dream_artifact_application_service",
                "get_episode_application_service",
                "get_dream_confirmation_application_service",
            },
        )
        self.assertNotIn("get_story_workflow_application_gateway", gateway)

    def test_all_dream_router_handlers_use_dec_004_prefix(self) -> None:
        names = dream_route_functions("routers/story_workspace.py")
        self.assertGreaterEqual(len(names), 2)
        for name in names:
            with self.subTest(name=name):
                self.assertTrue(name.startswith("story_workspace_"), name)

    def test_task3_server_lifecycle_functions_use_dec_004_prefix(self) -> None:
        server = public_definitions("server.py")
        candidates = {
            name
            for name, kind in server.items()
            if kind == "function" and "dream_confirmation_coordinator" in name
        }
        self.assertGreaterEqual(len(candidates), 2)
        for name in candidates:
            with self.subTest(name=name):
                self.assertTrue(name.startswith("story_workspace_"), name)


if __name__ == "__main__":
    unittest.main()
