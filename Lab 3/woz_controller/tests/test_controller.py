from __future__ import annotations

import json
from pathlib import Path
import sys
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from audio_backend import DryRunBackend  # noqa: E402
from controller import ConversationState, ScriptLibrary, TalkingBoxController  # noqa: E402
from server import ControllerHTTPServer, dispatch_action  # noqa: E402


def wait_until(test, timeout=2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if test():
            return
        time.sleep(0.01)
    raise AssertionError("Timed out waiting for controller state")


class StateTests(unittest.TestCase):
    def test_timer_snapshot_counts_down_and_claims_once(self):
        state = ConversationState()
        state.start_work(0.001)
        time.sleep(0.07)
        self.assertTrue(state.reminder_due())
        self.assertTrue(state.claim_reminder())
        self.assertFalse(state.claim_reminder())
        self.assertEqual(state.snapshot()["work"]["remaining_seconds"], 0)

    def test_morning_scene_reaches_thinking_with_transcript(self):
        script = ScriptLibrary(ROOT / "talking-box-dialogue.json")
        script.timing["self_talk_pause_seconds"] = 0
        controller = TalkingBoxController(DryRunBackend(
            delay=0.001, transcripts=["", "It is too early for this much confidence."]), script)
        self.addCleanup(controller.close)
        controller.set_automatic_reply(False)
        self.assertTrue(controller.start_morning())
        wait_until(lambda: not controller.state.snapshot()["active_action"])
        state = controller.state.snapshot()
        self.assertEqual(state["status"], "thinking")
        self.assertIn("confidence", state["transcript"])
        self.assertIn("daily dose", state["last_spoken"])

    def test_emergency_stop_returns_to_quiet(self):
        script = ScriptLibrary(ROOT / "talking-box-dialogue.json")
        controller = TalkingBoxController(DryRunBackend(delay=0.5), script)
        self.addCleanup(controller.close)
        self.assertTrue(controller.listen_once())
        wait_until(lambda: controller.state.snapshot()["status"] == "listening")
        controller.stop()
        self.assertEqual(controller.state.snapshot()["status"], "quiet")


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        script = ScriptLibrary(ROOT / "talking-box-dialogue.json")
        controller = TalkingBoxController(DryRunBackend(delay=0.001), script)
        try:
            cls.server = ControllerHTTPServer(("127.0.0.1", 0), controller)
        except PermissionError as error:
            controller.close()
            raise unittest.SkipTest(f"Local sockets unavailable: {error}")
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.controller.close()
        cls.server.shutdown()
        cls.server.server_close()

    def request(self, path, body=None):
        data = None
        headers = {}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=data,
            headers=headers,
            method="POST" if body is not None else "GET",
        )
        with urlopen(request, timeout=2) as response:
            return response.status, response.read(), response.headers

    def test_pages_and_state_are_served(self):
        status, payload, headers = self.request("/wizard")
        self.assertEqual(status, 200)
        self.assertIn(b"Talking Box Controller", payload)
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        status, payload, _headers = self.request("/api/state")
        self.assertEqual(status, 200)
        self.assertIn("status", json.loads(payload))

    def test_transcript_update_round_trip(self):
        status, _payload, _headers = self.request(
            "/api/transcript", {"text": "Corrected words"}
        )
        self.assertEqual(status, 200)
        _status, payload, _headers = self.request("/api/state")
        self.assertEqual(json.loads(payload)["transcript"], "Corrected words")

    def test_invalid_custom_reply_is_rejected(self):
        with self.assertRaises(HTTPError) as caught:
            self.request("/api/speak", {"text": ""})
        self.assertEqual(caught.exception.code, 400)


class RouteTests(unittest.TestCase):
    def setUp(self):
        script = ScriptLibrary(ROOT / "talking-box-dialogue.json")
        self.controller = TalkingBoxController(DryRunBackend(delay=0.001), script)

    def tearDown(self):
        self.controller.close()

    def test_transcript_update_round_trip_without_socket(self):
        self.assertTrue(
            dispatch_action(
                self.controller,
                "/api/transcript",
                {"text": "Corrected words"},
            )
        )
        self.assertEqual(
            self.controller.state.snapshot()["transcript"],
            "Corrected words",
        )

    def test_invalid_custom_reply_is_rejected_without_socket(self):
        with self.assertRaisesRegex(ValueError, "1 to 300"):
            dispatch_action(self.controller, "/api/speak", {"text": ""})

    def test_work_scene_starts_timer(self):
        self.assertTrue(
            dispatch_action(self.controller, "/api/work/start", {"minutes": 0.05})
        )
        wait_until(lambda: not self.controller.state.snapshot()["active_action"])
        state = self.controller.state.snapshot()
        self.assertTrue(state["work"]["running"])
        self.assertEqual(state["status"], "quiet")

    def test_quiet_cancels_active_action(self):
        self.controller.backend = DryRunBackend(delay=0.5)
        self.assertTrue(dispatch_action(self.controller, "/api/listen", {}))
        wait_until(lambda: self.controller.state.snapshot()["status"] == "listening")
        self.assertTrue(dispatch_action(self.controller, "/api/quiet", {}))
        self.assertEqual(self.controller.state.snapshot()["status"], "quiet")


if __name__ == "__main__":
    unittest.main()
