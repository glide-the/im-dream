#!/usr/bin/env python3
# [Input] Consume one complete Claude Agent text response and the strict Story bundle contract.
# [Output] Return a validated Story proposal or None without performing I/O or persistence.
# [Pos] Pure Story Workspace parsing boundary used by Dream Agent orchestration.
# [Sync] 2026-09-15: remove retired Dream SQL persistence; Admin Registry109 owns writes.
# [Sync] 2026-08-01: add task_204 payload contract, parsing, and transactional persistence.

"""Parse Claude Agent output into the Story Workspace proposal contract."""

from __future__ import annotations

import json
import logging
from typing import Optional

from pydantic import ValidationError

from story_workspace.contracts import StoryWorkspaceAgentStoryPayload


logger = logging.getLogger(__name__)


def parse_agent_story_output(
    raw_text: str,
) -> Optional[StoryWorkspaceAgentStoryPayload]:
    """Parse an entire JSON response as a story bundle; ordinary chat is ignored.

    A single ``json`` fenced block is accepted because Agent runners commonly
    wrap structured output that way. Explanatory prose or keyword matches never
    trigger persistence.
    """

    candidate = (raw_text or "").strip()
    if candidate.startswith("```json") and candidate.endswith("```"):
        candidate = candidate[len("```json") : -len("```")].strip()
    if not candidate.startswith("{"):
        return None

    try:
        decoded = json.loads(candidate)
    except (TypeError, ValueError) as exc:
        logger.warning("Agent story output ignored stage=json_parse error=%s", exc)
        return None
    if not isinstance(decoded, dict):
        logger.warning("Agent story output ignored stage=shape expected=object")
        return None

    try:
        return StoryWorkspaceAgentStoryPayload.model_validate(decoded)
    except ValidationError as exc:
        logger.warning("Agent story output ignored stage=validation error=%s", exc)
        return None
