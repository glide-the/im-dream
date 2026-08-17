"""Story Workspace MCP remains an optional two-tool preview seam."""

from __future__ import annotations

import json
from pathlib import Path

from libs.claude_agent_kit.server.story_workspace_tool import (
    STORY_WORKSPACE_DREAM_TOOL_SPECS,
    story_workspace_allowed_tool_names,
    story_workspace_handle_dream_tool,
)


def test_only_run_and_stage_preview_tools_are_exposed() -> None:
    assert tuple(STORY_WORKSPACE_DREAM_TOOL_SPECS) == (
        "write_dream_run",
        "write_dream_stage",
    )
    assert story_workspace_allowed_tool_names() == [
        "mcp__story_workspace__write_dream_run",
        "mcp__story_workspace__write_dream_stage",
    ]
    for specification in STORY_WORKSPACE_DREAM_TOOL_SPECS.values():
        assert specification.input_schema["additionalProperties"] is False


def test_removed_workflow_tools_fail_closed() -> None:
    for name in ("bind_first_episode", "record_episode_workflow_completion"):
        assert json.loads(story_workspace_handle_dream_tool(name, {})) == {
            "error": "DREAM_WRITE_REJECTED"
        }


def test_preview_tools_do_not_advance_workflow_lifecycle() -> None:
    source = Path(
        "libs/claude_agent_kit/server/story_workspace_tool.py"
    ).read_text(encoding="utf-8")
    assert "_advance_workflow_lifecycle" not in source
    assert "StoryWorkspaceDreamWorkflowLifecycleService" not in source
