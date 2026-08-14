from pathlib import Path
import unittest

from speech_recognition import init_speech_recognition


class _WebSocket:
    def __init__(self) -> None:
        self.closed: tuple[int, str] | None = None

    async def close(self, *, code: int, reason: str) -> None:
        self.closed = (code, reason)


class DeferredSpeechRecognitionTests(unittest.IsolatedAsyncioTestCase):
    async def test_compatibility_boundary_closes_without_accepting_audio(self):
        websocket = _WebSocket()

        await init_speech_recognition(websocket)  # type: ignore[arg-type]

        self.assertEqual(
            websocket.closed,
            (1008, "Speech recognition is not enabled"),
        )

    def test_server_route_is_fail_closed_and_provider_free(self):
        backend = Path(__file__).resolve().parents[1]
        module_source = (backend / "speech_recognition.py").read_text("utf-8")
        server_source = (backend / "server.py").read_text("utf-8")

        self.assertNotIn("dashscope", module_source.lower())
        route = server_source.split(
            '@app.websocket("/ws/speech-recognition")',
            1,
        )[1].split("registry = get_registry()", 1)[0]
        self.assertIn("websocket.close", route)
        self.assertNotIn("websocket.accept", route)
        self.assertNotIn("init_speech_recognition", route)


if __name__ == "__main__":
    unittest.main()
