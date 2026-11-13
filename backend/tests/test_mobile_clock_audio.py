# [Input] Public platform descriptors and real MCP factories with synthetic media.
# [Output] Provider-free discovery, schema and metadata-result contracts.
# [Pos] No media reads, audio engine, models, services or database operations.
import json
import unittest

from mcp import types as mcp_types
from pydantic import ValidationError

from libs.claude_agent_kit.server.editor_mcp_server import create_editor_mcp_server, create_mobile_clock_audio_mcp_server
from libs.claude_agent_kit.server.mobile_clock_audio import PlatformToolDescriptor, MobileClockAudioInput, handle_mobile_clock_audio, prepare_audio_question, AUDIO_PLAYBACK_QUESTION, MOBILE_CLOCK_AUDIO_TOOL


AUDIO = {"items": [{"title": "散步片段", "resource_uri": "workspace://files/audio/walk.m4a", "duration_seconds": 12.5}], "reason": "播放已整理的声音"}


class TestAudioProtocol(unittest.TestCase):
    def test_selection_rejects_unknown_types_and_client_definitions(self):
        self.assertEqual(PlatformToolDescriptor(type="mobile_clock_audio").type, "mobile_clock_audio")
        for value in ({"type": "web_search"}, {"type": "mobile_clock_audio", "url": "https://example.test"}, {"type": "mobile_clock_audio", "parameters": {}}):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                PlatformToolDescriptor.model_validate(value)

    def test_result_describes_intent_without_claiming_actual_playback(self):
        result = json.loads(handle_mobile_clock_audio({**AUDIO, "answers": {AUDIO_PLAYBACK_QUESTION: "播放"}}))
        self.assertEqual(result["status"], "playback_requested")
        self.assertEqual(result["type"], "mobile_clock_audio")
        self.assertEqual(result["items"], AUDIO["items"])
        self.assertEqual(result["queue_mode"], "replace")

    def test_invalid_media_never_becomes_a_request(self):
        for uri in ("https://example.test/a.mp3", "file:///private/a.mp3", "workspace://files/../a.mp3", "workspace://files/a/../../a.mp3", "workspace://files/%2e%2e/a.mp3", "workspace://files/a\\b.mp3"):
            with self.subTest(uri=uri), self.assertRaises(ValidationError):
                MobileClockAudioInput.model_validate({**AUDIO, "items": [{"title": "audio", "resource_uri": uri}]})
        for change in ({"items": []}, {"reason": " "}, {"target_device": "other"}, {"items": [{"title": "audio", "resource_uri": "workspace://files/a.mp3", "duration_seconds": float("inf")}]}):
            with self.subTest(change=change), self.assertRaises(ValidationError):
                MobileClockAudioInput.model_validate({**AUDIO, **change})


class TestAudioMcp(unittest.IsolatedAsyncioTestCase):
    async def listing(self, server):
        result = await server.request_handlers[mcp_types.ListToolsRequest](mcp_types.ListToolsRequest(method="tools/list"))
        return result.root.tools

    async def test_audio_factory_is_separate_from_editor(self):
        editor_tools = await self.listing(create_editor_mcp_server())
        self.assertNotIn("ask_user", [tool.name for tool in editor_tools])
        tools = await self.listing(create_mobile_clock_audio_mcp_server())
        self.assertEqual([tool.name for tool in tools], ["ask_user"])
        self.assertIn("items", tools[0].inputSchema["properties"])
        self.assertIn("reason", tools[0].inputSchema["required"])

    async def test_real_mcp_handler_returns_metadata_and_errors(self):
        server = create_mobile_clock_audio_mcp_server()
        handler = server.request_handlers[mcp_types.CallToolRequest]
        request = mcp_types.CallToolRequest(method="tools/call", params=mcp_types.CallToolRequestParams(name="ask_user", arguments={**AUDIO, "answers": {AUDIO_PLAYBACK_QUESTION: "播放"}}))
        result = (await handler(request)).root
        self.assertFalse(result.isError)
        self.assertEqual(json.loads(result.content[0].text)["status"], "playback_requested")
        bad = mcp_types.CallToolRequest(method="tools/call", params=mcp_types.CallToolRequestParams(name="ask_user", arguments={"items": []}))
        self.assertTrue((await handler(bad)).root.isError)


class TestAudioQuestionAnswer(unittest.IsolatedAsyncioTestCase):
    async def test_original_ask_user_store_validates_and_maps_answer(self):
        from claude_agent.tool_confirmation_store import ToolConfirmationStore, ToolConfirmationResult, ToolConfirmationInvalidDecision
        store = ToolConfirmationStore(thread_id="audio-thread", turn_id="audio-turn")
        question_input = prepare_audio_question({**AUDIO, "answers": {AUDIO_PLAYBACK_QUESTION: "播放"}})
        self.assertNotIn("answers", question_input)
        policy = store.policy_from_payload({"tool_call_id": "audio-call", "tool_name": MOBILE_CLOCK_AUDIO_TOOL, "input": question_input})
        self.assertEqual(policy.kind, "ask_user")
        store.register_pending(policy)
        try:
            for answers in (None, {"q0": "invented"}):
                with self.assertRaises(ToolConfirmationInvalidDecision):
                    await store.resolve_exact(thread_id="audio-thread", turn_id="audio-turn", tool_call_id="audio-call", result=ToolConfirmationResult(True, answers=answers))
            resolved = await store.resolve_exact(thread_id="audio-thread", turn_id="audio-turn", tool_call_id="audio-call", result=ToolConfirmationResult(True, answers={"q0": "不播放"}))
            self.assertEqual(resolved.result.answers, {AUDIO_PLAYBACK_QUESTION: "不播放"})
            output = json.loads(handle_mobile_clock_audio({**question_input, "answers": resolved.result.answers}))
            self.assertEqual(output["status"], "declined")
        finally:
            store.cancel_all()

    async def test_unanswered_tool_cannot_emit_playback_request(self):
        with self.assertRaises(ValueError):
            handle_mobile_clock_audio(AUDIO)
