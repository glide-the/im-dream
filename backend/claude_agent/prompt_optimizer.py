#!/usr/bin/env python3
# [Input] docs/design/claude-agent/claude-agent-prompt-optimization.md
# [Output] Expert Prompt Architect template and apply_prompt_optimizer helper.
# [Pos] prompt-optimizer utility in backend/claude_agent
# [Sync] 2026-05-28: initial implementation per design doc.

"""Planning-turn prompt optimizer.

Applies the Expert Prompt Architect template to a raw user planning task so
that the agent receives a clearer, more structured input before
``assemble_context`` builds the full executable context.

Usage::

    from claude_agent.prompt_optimizer import apply_prompt_optimizer

    optimized = apply_prompt_optimizer(raw_task)
    # optimized is passed as the text in ClaudeAgentRunRequest.message_parts
"""

EXPERT_PROMPT_ARCHITECT_TEMPLATE: str = (
    "You are an Expert Prompt Architect.\n"
    "Convert the user's requirement into a highly detailed, optimized,\n"
    "ready-to-use prompt for ANY purpose (image, video, writing, SEO, coding,\n"
    "learning, research, etc.).\n"
    "Instructions\n"
    "Identify what the user is trying to achieve.\n"
    "Without asking questions (unless unclear), transform it into a precise,\n"
    "high-value, professional prompt tailored to the correct output type.\n"
    "Add missing but useful details (style, tone, constraints, structure, clarity).\n"
    "Ensure the prompt is copy-paste ready for the intended AI tool.\n"
    "Deliver:\n"
    "Optimized Prompt - the final refined prompt\n"
    "Optional Enhancers - optional add-ons that the user can include\n"
    "\n"
    "OUTPUT FORMAT\n"
    "Optimized Prompt:\n"
    "[Expert-level prompt based on the requirement]\n"
    "\n"
    "USER REQUIREMENT:        {{task}}"
)


def apply_prompt_optimizer(task: str) -> str:
    """Return the Expert Prompt Architect template with *task* substituted.

    The returned string is intended to replace the user message text for a
    planning turn so that the agent first acts as an Expert Prompt Architect
    and produces a refined prompt before executing the plan.

    Args:
        task: Raw user planning requirement exactly as received.

    Returns:
        Template text with ``{{task}}`` replaced by *task*.  Returns the
        template with an empty requirement string when *task* is falsy so
        that callers receive a well-formed string in all cases.
    """
    return EXPERT_PROMPT_ARCHITECT_TEMPLATE.replace("{{task}}", task or "")
