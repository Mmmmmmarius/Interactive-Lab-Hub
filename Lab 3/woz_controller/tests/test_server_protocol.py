"""HTTP protocol checks without binding sockets or opening audio devices.

BaseHTTPRequestHandler receives an in-memory accepted connection. The audio
backend below supplies artificial events only; these checks are not Pi trials.
"""
from __future__ import annotations

from collections import deque
from contextlib import redirect_stdout
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import re
import sys
import threading
import time
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from audio_backend import DryRunBackend  # noqa: E402
from controller import ScriptLibrary, TalkingBoxController  # noqa: E402
from console import command  # noqa: E402
from server import ControllerHandler  # noqa: E402


def wait_until(predicate, timeout=2):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.002)
    raise AssertionError("Timed out waiting for an artificial controller event")


class ProtocolBackend(DryRunBackend):
    """Artificial audio events accepted by the dry-run simulation endpoint."""
    def __init__(self):
        self.pending = deque()
        self.spoken = []
        self.listen_entered = threading.Event()
        self.release_listen = threading.Event()
        self.block_listen = False
        self._lock = threading.Lock()

    def queue_transcript(self, text):
        with self._lock:
            self.pending.append(text)

    def speak(self, text, cancel):
        if not cancel.is_set():
            self.spoken.append(text)

    def listen(self, cancel, on_thinking, *, start_timeout=2,
               min_silence=0.8, on_started=None):
        del start_timeout, min_silence
        self.listen_entered.set()
        if self.block_listen:
            while not self.release_listen.wait(0.002):
                if cancel.is_set():
                    return ""
        if cancel.is_set():
            return ""
        with self._lock:
            text = self.pending.popleft() if self.pending else ""
        if text:
            if on_started is not None:
                on_started()
            on_thinking()
        return text

    def stop(self):
        pass


class MemoryConnection:
    """Enough accepted-socket behavior for the stdlib HTTP request handler."""
    def __init__(self, request):
        self.request = io.BytesIO(request)
        self.response = io.BytesIO()

    def makefile(self, mode, _buffering=-1):
        if mode != "rb":
            raise AssertionError(f"Unexpected socket mode: {mode}")
        return self.request

    def sendall(self, payload):
        self.response.write(payload)


class SilentHandler(ControllerHandler):
    def log_message(self, *_args):
        pass


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.backend = ProtocolBackend()
        script = ScriptLibrary(ROOT / "talking-box-dialogue.json")
        script.timing["self_talk_pause_seconds"] = 0
        self.controller = TalkingBoxController(self.backend, script,
                                              scheduler_interval=10)

    def tearDown(self):
        self.backend.release_listen.set()
        self.controller.close()

    def request(self, path, body=None, *, method=None, raw_body=None,
                content_length=None):
        method = method or ("POST" if body is not None or raw_body is not None else "GET")
        payload = raw_body if raw_body is not None else (
            json.dumps(body).encode("utf-8") if body is not None else b"")
        headers = [f"{method} {path} HTTP/1.0", "Host: 127.0.0.1"]
        if method == "POST":
            headers.extend(["Content-Type: application/json",
                            f"Content-Length: {len(payload) if content_length is None else content_length}"])
        connection = MemoryConnection(("\r\n".join(headers) + "\r\n\r\n").encode("ascii") + payload)
        SilentHandler(connection, ("127.0.0.1", 43210),
                      SimpleNamespace(controller=self.controller))
        head, payload = connection.response.getvalue().split(b"\r\n\r\n", 1)
        lines = head.decode("iso-8859-1").split("\r\n")
        status = int(lines[0].split()[1])
        response_headers = dict(line.split(": ", 1) for line in lines[1:])
        if response_headers.get("Content-Type", "").startswith("application/json"):
            payload = json.loads(payload)
        return status, payload, response_headers

    def post(self, path, body=None):
        return self.request(path, {} if body is None else body, method="POST")

    def wait_idle(self):
        wait_until(lambda: not self.controller.state.snapshot()["active_action"])
        # Final state publication precedes worker exit by a few instructions.
        thread = self.controller._thread
        if thread is not None:
            thread.join(timeout=1)

    def test_state_and_both_pages_use_real_http_response_headers(self):
        for path, marker in (("/wizard", b"Talking Box Controller"),
                             ("/participant", b"participant-state"),
                             ("/static/wizard.js", b"/api/pause")):
            with self.subTest(path=path):
                status, body, headers = self.request(path)
                self.assertEqual(status, 200)
                self.assertIn(marker, body)
                self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
                self.assertEqual(headers["Content-Length"], str(len(body)))
        status, state, headers = self.request("/api/state")
        self.assertEqual(status, 200)
        self.assertEqual(state["mode"], "flower")
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_unknown_routes_and_static_traversal_return_404(self):
        for path, method in (("/missing", "GET"), ("/api/missing", "POST"),
                             ("/static/../controller.py", "GET")):
            with self.subTest(path=path):
                self.assertEqual(self.request(path, method=method)[0], 404)

    def test_pause_resume_reset_preserve_timer_and_restore_defaults(self):
        self.controller.state.start_work(1)
        self.controller.state.set_transcript("Artificial words")
        self.controller.state.set_last_spoken("Artificial output")
        self.controller.state.set_error("Artificial prior error")
        self.controller.set_automatic_reply(False)
        status, result, _ = self.post("/api/pause")
        self.assertEqual(status, 200)
        self.assertEqual(result["state"]["status"], "paused")
        self.assertFalse(result["state"]["work"]["running"])
        self.assertIsNotNone(result["state"]["work"]["paused_remaining"])
        for path in ("/api/listen", "/api/speak"):
            self.assertEqual(self.post(path, {"text": "Blocked while paused"})[0], 409)
        status, result, _ = self.post("/api/resume")
        self.assertEqual(status, 200)
        self.assertEqual(result["state"]["status"], "quiet")
        self.assertTrue(result["state"]["work"]["running"])
        status, result, _ = self.post("/api/reset")
        self.assertEqual(status, 200)
        state = result["state"]
        self.assertEqual(state["status"], "quiet")
        self.assertEqual(state["transcript"], "")
        self.assertEqual(state["last_spoken"], "")
        self.assertEqual(state["last_error"], "")
        self.assertTrue(state["automatic_reply"])
        self.assertFalse(state["work"]["running"])

    def test_resume_during_unpaused_turn_does_not_publish_false_quiet(self):
        self.backend.block_listen = True
        self.assertEqual(self.post("/api/listen")[0], 200)
        self.assertTrue(self.backend.listen_entered.wait(1))
        self.assertEqual(self.controller.state.snapshot()["status"], "listening")
        self.post("/api/resume")
        state = self.controller.state.snapshot()
        self.assertEqual(state["status"], "listening")
        self.assertEqual(state["phase"], "waiting_for_start")
        self.assertEqual(self.post("/api/stop")[0], 200)
        self.wait_idle()
        self.assertEqual(self.controller.state.snapshot()["status"], "quiet")

    def test_manual_reply_mode_and_simulated_transcript_complete_fresh_turns(self):
        self.assertEqual(self.post("/api/replies", {"automatic": False})[0], 200)
        long_sentence = " ".join(f"word{number}" for number in range(400))
        self.assertEqual(self.post("/api/simulate", {"text": long_sentence})[0], 200)
        self.assertEqual(self.post("/api/speak", {"text": "Artificial greeting"})[0], 200)
        self.wait_idle()
        state = self.controller.state.snapshot()
        self.assertEqual(state["transcript"], long_sentence)
        self.assertEqual(state["phase"], "awaiting_wizard")
        self.assertEqual(self.backend.spoken, ["Artificial greeting"])
        self.assertEqual(self.post("/api/transcript", {"text": "Corrected artificial words"})[0], 200)
        self.assertEqual(self.post("/api/speak", {"text": "Artificial wizard reply"})[0], 200)
        self.wait_idle()
        self.assertEqual(self.backend.spoken, ["Artificial greeting", "Artificial wizard reply"])
        self.assertEqual(self.controller.state.snapshot()["status"], "quiet")

    def test_muse_wake_remains_reserved_without_mode_or_audio_changes(self):
        status, result, _ = self.post("/api/muse/wake", {"word": "future independent phrase"})
        self.assertEqual(status, 200)
        self.assertEqual(result["state"]["mode"], "flower")
        self.assertFalse(result["state"]["muse"]["available"])
        self.assertEqual(self.backend.spoken, [])
        self.assertFalse(self.backend.listen_entered.is_set())

    def test_long_transcript_correction_is_preserved_and_invalid_edit_is_rejected(self):
        long_sentence = " ".join(f"word{number}" for number in range(400))
        self.controller.state.set_transcript(long_sentence)
        status, result, _ = self.post("/api/transcript", {"text": long_sentence})
        self.assertEqual(status, 200)
        self.assertEqual(result["state"]["transcript"], long_sentence)
        for invalid in ("x" * 10001, None, [], 1):
            with self.subTest(edit_type=type(invalid).__name__):
                status, result, _ = self.post("/api/transcript", {"text": invalid})
                self.assertEqual(status, 400)
                self.assertFalse(result["ok"])
                self.assertEqual(self.controller.state.snapshot()["transcript"], long_sentence)

    def test_actual_dry_backend_accepts_the_interface_simulated_input_limit(self):
        self.controller.backend = DryRunBackend(delay=0, transcripts=[])
        long_sentence = "x" * 10000
        self.assertEqual(self.post("/api/simulate", {"text": long_sentence})[0], 200)
        self.assertEqual(self.post("/api/listen")[0], 200)
        self.wait_idle()
        self.assertEqual(self.controller.state.snapshot()["transcript"], long_sentence)

    def test_simulated_input_is_rejected_for_non_dry_backend(self):
        self.controller.backend = SimpleNamespace()
        self.assertEqual(self.post("/api/simulate", {"text": "Artificial words"})[0], 400)
        self.assertEqual(self.controller.state.snapshot()["status"], "quiet")

    def test_invalid_json_and_lengths_return_400_without_poisoning_state(self):
        for raw, length in ((b"{", None), (b"[]", None), (b"null", None),
                            (b"\xff", None), (b"{}", "bad"),
                            (b"{}", -1), (b"{}", 65537)):
            with self.subTest(raw=raw, length=length):
                status, result, _ = self.request("/api/replies", raw_body=raw,
                                                 content_length=length)
                self.assertEqual(status, 400)
                self.assertFalse(result["ok"])
                self.assertEqual(self.controller.state.snapshot()["last_error"], "")
                self.assertTrue(self.controller.state.snapshot()["automatic_reply"])
        self.assertEqual(self.post("/api/listen")[0], 200)
        self.wait_idle()

    def test_invalid_action_fields_return_400_then_valid_action_still_runs(self):
        cases = [("/api/speak", {"text": ""}),
                 ("/api/speak", {"text": "x" * 301}),
                 ("/api/simulate", {"text": []}),
                 ("/api/simulate", {"text": "x" * 10001})]
        cases += [("/api/replies", {"automatic": value}) for value in (None, 1, "false", [])]
        cases += [("/api/work/start", {"minutes": value}) for value in
                  (None, [], "invalid", 0, 181, float("inf"), float("nan"))]
        for path, body in cases:
            with self.subTest(path=path, body=body):
                status, result, _ = self.post(path, body)
                self.assertEqual(status, 400)
                self.assertFalse(result["ok"])
                state = self.controller.state.snapshot()
                self.assertEqual(state["status"], "quiet")
                self.assertEqual(state["last_error"], "")
                self.assertFalse(state["work"]["running"])
        self.assertEqual(self.post("/api/speak", {"text": "Valid artificial recovery"})[0], 200)
        self.wait_idle()
        self.assertEqual(self.backend.spoken, ["Valid artificial recovery"])

    def test_huge_json_integer_is_a_bad_request_instead_of_dropped_connection(self):
        status, result, _ = self.post("/api/work/start", {"minutes": 10 ** 400})
        self.assertEqual(status, 400)
        self.assertFalse(result["ok"])
        self.assertEqual(self.controller.state.snapshot()["status"], "quiet")

    def test_console_commands_use_same_dispatch_and_recover_from_invalid_input(self):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertTrue(command(self.controller, "auto off"))
            self.assertTrue(command(self.controller, "simulate Artificial console words"))
            self.assertTrue(command(self.controller, "say Artificial console greeting"))
            self.wait_idle()
            self.assertEqual(self.controller.state.snapshot()["transcript"], "Artificial console words")
            self.assertEqual(self.controller.state.snapshot()["phase"], "awaiting_wizard")
            self.assertTrue(command(self.controller, "pause"))
            self.assertEqual(self.controller.state.snapshot()["status"], "paused")
            self.assertTrue(command(self.controller, "resume"))
            self.assertEqual(self.controller.state.snapshot()["status"], "quiet")
            for invalid in ("auto maybe", "work invalid", "say", "unknown"):
                with self.subTest(command=invalid), self.assertRaises(ValueError):
                    command(self.controller, invalid)
            self.assertTrue(command(self.controller, "reset"))
            self.assertTrue(self.controller.state.snapshot()["automatic_reply"])
            self.assertTrue(command(self.controller, "status"))
            self.assertFalse(command(self.controller, "quit"))
        self.assertIn("Accepted", output.getvalue())
        self.assertIn('"mode": "flower"', output.getvalue())


class IdCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []

    def handle_starttag(self, _tag, attrs):
        self.ids.extend(value for name, value in attrs if name == "id")


class StaticWiringTests(unittest.TestCase):
    def test_every_javascript_id_selector_exists_once_in_its_page(self):
        for name in ("wizard", "participant"):
            with self.subTest(page=name):
                parser = IdCollector()
                parser.feed((ROOT / "static" / f"{name}.html").read_text())
                self.assertEqual(len(parser.ids), len(set(parser.ids)))
                javascript = (ROOT / "static" / f"{name}.js").read_text()
                selectors = re.findall(r'querySelector\([\'\"]#([^\'\"]+)[\'\"]\)', javascript)
                self.assertTrue(selectors)
                for selector in selectors:
                    self.assertEqual(parser.ids.count(selector), 1, selector)


if __name__ == "__main__":
    unittest.main()
