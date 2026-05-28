# [Input] Consume editor_index.py, editor_tool.py helpers.
# [Output] Unit tests for editor virtual index read helpers and MCP tool handlers.
# [Sync] 2026-05-28: initial test suite — editor_index and editor_tool.

"""Unit tests for the .editor/ virtual index and EditorEngine MCP read tools."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Adjust PYTHONPATH so we can import from the libs tree when running from
# the backend/ root via ``python3 -m pytest tests/``.
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from libs.claude_agent_kit.server.editor_index import (
    EDITOR_RESOURCES,
    get_editor_resource_data,
    is_editor_index_path,
    resolve_editor_resource,
)
from libs.claude_agent_kit.server.editor_tool import (
    _list_comments,
    _list_segments,
    _read_comment,
    _read_segment,
    _read_session_meta,
    allowed_editor_tool_names,
    handle_editor_read_tool,
)


# ---------------------------------------------------------------------------
# editor_index tests
# ---------------------------------------------------------------------------


class TestIsEditorIndexPath(unittest.TestCase):
    def test_recognises_dot_editor_prefix(self):
        self.assertTrue(is_editor_index_path(".editor/cells.json"))

    def test_recognises_absolute_path_under_editor(self):
        self.assertTrue(is_editor_index_path("/workspace/.editor/session.json"))

    def test_false_for_unrelated_path(self):
        self.assertFalse(is_editor_index_path("src/main.py"))

    def test_false_for_none_like_empty(self):
        self.assertFalse(is_editor_index_path(""))


class TestResolveEditorResource(unittest.TestCase):
    def test_resolves_cells(self):
        self.assertEqual(resolve_editor_resource(".editor/cells.json"), "cells")

    def test_resolves_session(self):
        self.assertEqual(resolve_editor_resource(".editor/session.json"), "session")

    def test_unknown_returns_none(self):
        self.assertIsNone(resolve_editor_resource(".editor/unknown.json"))

    def test_non_editor_path_returns_none(self):
        self.assertIsNone(resolve_editor_resource("README.md"))


class TestGetEditorResourceData(unittest.TestCase):
    _STATE = {
        "id": "sess-1",
        "cells": [{"id": "c1", "type": "text", "content": "Hello"}],
        "commentors": [{"id": "cm1", "phrase": "Hello"}],
        "tasks": [{"id": "t1", "title": "Do stuff"}],
        "selectedState": "neutral",
        "createdAt": "2026-01-01T00:00:00Z",
    }

    def test_full_state_returns_whole_dict(self):
        result = get_editor_resource_data(".editor/full_state.json", self._STATE)
        self.assertEqual(result, self._STATE)

    def test_cells_slice(self):
        result = get_editor_resource_data(".editor/cells.json", self._STATE)
        self.assertEqual(result, {"cells": self._STATE["cells"]})

    def test_session_slice(self):
        result = get_editor_resource_data(".editor/session.json", self._STATE)
        self.assertIn("id", result)
        self.assertIn("selectedState", result)
        self.assertNotIn("cells", result)

    def test_commentors_slice(self):
        result = get_editor_resource_data(".editor/commentors.json", self._STATE)
        self.assertEqual(result, {"commentors": self._STATE["commentors"]})

    def test_unknown_resource_returns_empty(self):
        result = get_editor_resource_data(".editor/unknown.json", self._STATE)
        self.assertEqual(result, {})


# ---------------------------------------------------------------------------
# editor_tool tests
# ---------------------------------------------------------------------------


class TestAllowedEditorToolNames(unittest.TestCase):
    def test_returns_mcp_prefixed_names(self):
        names = allowed_editor_tool_names()
        self.assertIn("mcp__editor__list_segments", names)
        self.assertIn("mcp__editor__read_segment", names)
        self.assertIn("mcp__editor__read_session_meta", names)
        self.assertIn("mcp__editor__list_comments", names)
        self.assertIn("mcp__editor__read_comment", names)

    def test_all_five_tools_present(self):
        self.assertEqual(len(allowed_editor_tool_names()), 5)


_SAMPLE_STATE = {
    "id": "session-abc",
    "selectedState": "happy",
    "createdAt": "2026-05-01T10:00:00Z",
    "cells": [
        {"id": "c1", "type": "text", "content": "Once upon a time"},
        {"id": "c2", "type": "component", "widgetType": "image", "data": {"voiceId": "v1"}},
    ],
    "commentors": [
        {
            "id": "cm1",
            "phrase": "Once upon",
            "voiceId": "v1",
            "appliedAt": "2026-05-01T11:00:00Z",
            "feedback": "starred",
            "text": "Great opening",
            "conversation": [],
        },
        {
            "id": "cm2",
            "phrase": "a time",
            "voiceId": "v2",
            "appliedAt": "2026-05-01T12:00:00Z",
            "feedback": "pending",
            "text": "Consider rephrasing",
            "conversation": [],
        },
    ],
}


class TestListSegments(unittest.TestCase):
    def test_returns_all_segments(self):
        result = json.loads(_list_segments(_SAMPLE_STATE))
        self.assertTrue(result["ok"])
        self.assertEqual(result["totalSegments"], 2)

    def test_text_cell_has_preview_and_length(self):
        result = json.loads(_list_segments(_SAMPLE_STATE))
        text_seg = next(s for s in result["segments"] if s["id"] == "c1")
        self.assertEqual(text_seg["type"], "text")
        self.assertIn("preview", text_seg)
        self.assertIn("length", text_seg)

    def test_component_cell_has_widget_type(self):
        result = json.loads(_list_segments(_SAMPLE_STATE))
        comp_seg = next(s for s in result["segments"] if s["id"] == "c2")
        self.assertEqual(comp_seg["widgetType"], "image")

    def test_empty_state_returns_zero_segments(self):
        result = json.loads(_list_segments({}))
        self.assertTrue(result["ok"])
        self.assertEqual(result["totalSegments"], 0)


class TestReadSegment(unittest.TestCase):
    def test_returns_cell_by_id(self):
        result = json.loads(_read_segment(_SAMPLE_STATE, "c1"))
        self.assertTrue(result["ok"])
        self.assertEqual(result["cell"]["id"], "c1")

    def test_returns_error_for_missing_id(self):
        result = json.loads(_read_segment(_SAMPLE_STATE, "nonexistent"))
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "cell_not_found")

    def test_empty_cell_id_returns_error(self):
        result = json.loads(_read_segment(_SAMPLE_STATE, ""))
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "cellId_required")


class TestReadSessionMeta(unittest.TestCase):
    def test_returns_session_fields(self):
        result = json.loads(_read_session_meta(_SAMPLE_STATE))
        self.assertTrue(result["ok"])
        self.assertEqual(result["id"], "session-abc")
        self.assertEqual(result["selectedState"], "happy")
        self.assertIn("createdAt", result)

    def test_empty_state_returns_none_values(self):
        result = json.loads(_read_session_meta({}))
        self.assertTrue(result["ok"])
        self.assertIsNone(result["id"])


class TestListComments(unittest.TestCase):
    def test_returns_all_by_default(self):
        result = json.loads(_list_comments(_SAMPLE_STATE, "all"))
        self.assertTrue(result["ok"])
        self.assertEqual(result["totalComments"], 2)

    def test_filters_starred(self):
        result = json.loads(_list_comments(_SAMPLE_STATE, "starred"))
        self.assertEqual(result["totalComments"], 1)
        self.assertEqual(result["comments"][0]["id"], "cm1")

    def test_filters_pending(self):
        result = json.loads(_list_comments(_SAMPLE_STATE, "pending"))
        self.assertEqual(result["totalComments"], 1)
        self.assertEqual(result["comments"][0]["id"], "cm2")

    def test_unknown_filter_treated_as_all(self):
        result = json.loads(_list_comments(_SAMPLE_STATE, "bogus"))
        self.assertEqual(result["filter"], "all")
        self.assertEqual(result["totalComments"], 2)


class TestReadComment(unittest.TestCase):
    def test_returns_comment_by_id(self):
        result = json.loads(_read_comment(_SAMPLE_STATE, "cm1"))
        self.assertTrue(result["ok"])
        self.assertEqual(result["comment"]["id"], "cm1")

    def test_returns_error_for_missing_id(self):
        result = json.loads(_read_comment(_SAMPLE_STATE, "none"))
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "comment_not_found")

    def test_empty_comment_id_returns_error(self):
        result = json.loads(_read_comment(_SAMPLE_STATE, ""))
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "commentId_required")


class TestHandleEditorReadToolDispatch(unittest.TestCase):
    """Integration tests for handle_editor_read_tool via INK_EDITOR_STATE_FILE."""

    def _write_state_file(self, state: dict) -> str:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as fh:
            json.dump(state, fh)
            return fh.name

    def test_list_segments_via_state_file(self):
        path = self._write_state_file(_SAMPLE_STATE)
        try:
            with patch.dict(os.environ, {"INK_EDITOR_STATE_FILE": path}):
                result = json.loads(handle_editor_read_tool("list_segments", {}))
            self.assertTrue(result["ok"])
            self.assertEqual(result["totalSegments"], 2)
        finally:
            os.unlink(path)

    def test_read_session_meta_via_state_file(self):
        path = self._write_state_file(_SAMPLE_STATE)
        try:
            with patch.dict(os.environ, {"INK_EDITOR_STATE_FILE": path}):
                result = json.loads(handle_editor_read_tool("read_session_meta", {}))
            self.assertTrue(result["ok"])
            self.assertEqual(result["id"], "session-abc")
        finally:
            os.unlink(path)

    def test_unknown_tool_returns_error(self):
        with patch.dict(os.environ, {"INK_EDITOR_STATE_FILE": ""}):
            result = json.loads(handle_editor_read_tool("no_such_tool", {}))
        self.assertFalse(result["ok"])
        self.assertIn("unknown_tool", result["error"])

    def test_missing_env_returns_empty_state_gracefully(self):
        env = {k: v for k, v in os.environ.items() if k != "INK_EDITOR_STATE_FILE"}
        with patch.dict(os.environ, env, clear=True):
            result = json.loads(handle_editor_read_tool("list_segments", {}))
        self.assertTrue(result["ok"])
        self.assertEqual(result["totalSegments"], 0)


if __name__ == "__main__":
    unittest.main()
