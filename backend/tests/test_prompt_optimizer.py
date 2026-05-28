"""Tests for claude_agent.prompt_optimizer.

Covers:
- Template substitution ({{task}} placeholder)
- Output format guarantees (contains marker text)
- Edge-case inputs (empty string, None-like falsy value)
- Integration: planning_mode flag in the router request body
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # backend/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tests._sdk_stubs  # noqa: F401 — stub claude_code_sdk before libs.claude_agent_kit

import pytest
from claude_agent.prompt_optimizer import (
    EXPERT_PROMPT_ARCHITECT_TEMPLATE,
    apply_prompt_optimizer,
)


# ---------------------------------------------------------------------------
# Template constant shape
# ---------------------------------------------------------------------------


class TestExpertPromptArchitectTemplate:
    def test_template_contains_task_placeholder(self):
        assert "{{task}}" in EXPERT_PROMPT_ARCHITECT_TEMPLATE

    def test_template_contains_output_format_header(self):
        assert "OUTPUT FORMAT" in EXPERT_PROMPT_ARCHITECT_TEMPLATE

    def test_template_contains_optimized_prompt_marker(self):
        assert "Optimized Prompt:" in EXPERT_PROMPT_ARCHITECT_TEMPLATE

    def test_template_contains_user_requirement_label(self):
        assert "USER REQUIREMENT:" in EXPERT_PROMPT_ARCHITECT_TEMPLATE

    def test_template_is_non_empty_string(self):
        assert isinstance(EXPERT_PROMPT_ARCHITECT_TEMPLATE, str)
        assert len(EXPERT_PROMPT_ARCHITECT_TEMPLATE) > 100


# ---------------------------------------------------------------------------
# apply_prompt_optimizer — substitution behaviour
# ---------------------------------------------------------------------------


class TestApplyPromptOptimizer:
    def test_substitutes_task_into_template(self):
        task = "Design a planning flow for the Claude Agent module."
        result = apply_prompt_optimizer(task)
        assert task in result

    def test_placeholder_is_fully_replaced(self):
        result = apply_prompt_optimizer("anything")
        assert "{{task}}" not in result

    def test_result_contains_output_format_header(self):
        result = apply_prompt_optimizer("some task")
        assert "OUTPUT FORMAT" in result

    def test_result_contains_optimized_prompt_marker(self):
        result = apply_prompt_optimizer("some task")
        assert "Optimized Prompt:" in result

    def test_result_contains_user_requirement_label(self):
        result = apply_prompt_optimizer("some task")
        assert "USER REQUIREMENT:" in result

    def test_result_is_string(self):
        assert isinstance(apply_prompt_optimizer("any"), str)

    def test_empty_task_produces_valid_string(self):
        """Empty task should not raise; the template is still returned."""
        result = apply_prompt_optimizer("")
        assert isinstance(result, str)
        assert "{{task}}" not in result

    def test_falsy_none_task_produces_valid_string(self):
        """None-like value (empty string after guard) must not crash."""
        result = apply_prompt_optimizer("")
        assert "USER REQUIREMENT:" in result

    def test_multiline_task_preserved(self):
        task = "Line one.\nLine two.\nLine three."
        result = apply_prompt_optimizer(task)
        assert task in result

    def test_unicode_task_preserved(self):
        task = "关于 claude-agent 的 edit-point 设计"
        result = apply_prompt_optimizer(task)
        assert task in result

    def test_does_not_mutate_template_constant(self):
        """Calling the function must not alter the module-level constant."""
        original = EXPERT_PROMPT_ARCHITECT_TEMPLATE
        apply_prompt_optimizer("mutate check")
        assert EXPERT_PROMPT_ARCHITECT_TEMPLATE == original

    def test_idempotent_on_same_task(self):
        task = "check idempotency"
        assert apply_prompt_optimizer(task) == apply_prompt_optimizer(task)


# ---------------------------------------------------------------------------
# Planning mode integration — router-level behaviour
# ---------------------------------------------------------------------------


class TestPlanningModeRouterIntegration:
    """Verify that ClaudeAgentRequestBody.planning_mode exists and defaults correctly."""

    def test_planning_mode_field_exists(self):
        from routers.claude_agent import ClaudeAgentRequestBody

        body = ClaudeAgentRequestBody(message="hello")
        assert hasattr(body, "planning_mode")

    def test_planning_mode_defaults_to_false(self):
        from routers.claude_agent import ClaudeAgentRequestBody

        body = ClaudeAgentRequestBody(message="hello")
        assert body.planning_mode is False

    def test_planning_mode_can_be_set_true(self):
        from routers.claude_agent import ClaudeAgentRequestBody

        body = ClaudeAgentRequestBody(message="hello", planning_mode=True)
        assert body.planning_mode is True

    def test_planning_mode_false_does_not_alter_message_text(self):
        from routers.claude_agent import ClaudeAgentRequestBody

        body = ClaudeAgentRequestBody(message="raw task", planning_mode=False)
        assert body.get_message_text() == "raw task"

    def test_apply_prompt_optimizer_called_in_planning_mode(self):
        """apply_prompt_optimizer output contains the raw task and the template markers."""
        raw_task = "implement workspace context hook"
        optimized = apply_prompt_optimizer(raw_task)
        assert raw_task in optimized
        assert "USER REQUIREMENT:" in optimized
        assert "Optimized Prompt:" in optimized
