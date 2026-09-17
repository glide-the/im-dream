# [Input] Canonical Chat message parts/metadata and optional final-history projection fields.
# [Output] Validate v1 final projection or raise the existing field-specific ValueError.
# [Pos] Pure Chat projection contract shared by legacy persistence and strict Admin DTOs.
# [Sync] 2026-09-14: extract the existing validator without changing behavior or its legacy import alias.
from __future__ import annotations

from typing import Optional


def validate_chat_history_final_projection(
    *,
    role: str,
    parts: object,
    metadata: object,
    history_final_text: Optional[str],
    history_process_available: bool,
    history_projection_version: Optional[int],
) -> None:
    """Fail closed unless the supplied v1 projection matches canonical parts."""

    if history_projection_version is None:
        if history_final_text is not None or history_process_available is not False:
            raise ValueError("chat history projection fields are incomplete")
        return
    if (
        not isinstance(history_projection_version, int)
        or isinstance(history_projection_version, bool)
        or history_projection_version != 1
    ):
        raise ValueError("chat history projection version is unsupported")
    if role != "assistant":
        raise ValueError("chat history projection requires an assistant message")
    if not isinstance(history_final_text, str) or not history_final_text.strip():
        raise ValueError("chat history final text must be non-empty")
    if not isinstance(history_process_available, bool):
        raise ValueError("chat history process availability must be boolean")
    if not isinstance(parts, list) or not isinstance(metadata, dict):
        raise ValueError("chat history projection requires canonical message data")
    final_part_index = metadata.get("finalPartIndex")
    if (
        metadata.get("turnStatus") != "completed"
        or not isinstance(metadata.get("turnId"), str)
        or not metadata.get("turnId")
        or not isinstance(final_part_index, int)
        or isinstance(final_part_index, bool)
    ):
        raise ValueError("chat history projection requires completed turn metadata")
    last_process_index = -1
    for index, part in enumerate(parts):
        if not isinstance(part, dict) or part.get("type") not in {
            "text",
            "reasoning",
            "tool-invocation",
        }:
            raise ValueError("chat history projection parts are unsupported")
        if part.get("type") in {"reasoning", "tool-invocation"}:
            last_process_index = index
    strict_final_index = last_process_index + 1
    if len(parts) - strict_final_index != 1:
        raise ValueError("chat history final part is ambiguous")
    final_part = parts[strict_final_index]
    if (
        final_part_index != strict_final_index
        or final_part.get("type") != "text"
        or final_part.get("text") != history_final_text
        or history_process_available != (strict_final_index > 0)
    ):
        raise ValueError("chat history projection does not match canonical parts")
