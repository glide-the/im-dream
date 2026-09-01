"""
[Input] Serialized Writing EditorState containing TextCell and WritingSuggestionCell records.
[Output] Verify backend Session summaries and aggregate prose extraction ignore suggestions.
[Pos] Writing Session JSON compatibility regression in backend/tests.
[Sync] 2026-09-01: lock suggestion Cells out of first-line, word, and downstream prose inputs.
"""

from __future__ import annotations

import json

import database


def test_session_text_extraction_uses_only_text_cells() -> None:
    editor_state = {
        "id": "session-writing",
        "writingThreadId": "thread-writing",
        "cells": [
            {"id": "text-1", "type": "text", "content": "第一段正文"},
            {
                "id": "suggestion-1",
                "type": "writing-suggestion",
                "content": "这段建议绝不能进入摘要、字数或下一次正文上下文。",
                "status": "completed",
                "anchor": {"textCellId": "text-1", "textSnapshot": "第一段正文"},
                "createdAt": "2026-09-01T00:00:00Z",
                "updatedAt": "2026-09-01T00:00:01Z",
            },
            {"id": "text-2", "type": "text", "content": "第二段正文"},
        ],
    }

    first_line, full_text = database._extract_session_text(json.dumps(editor_state))

    assert first_line == "第一段正文"
    assert full_text == "第一段正文\n\n第二段正文"
    assert "建议" not in full_text
