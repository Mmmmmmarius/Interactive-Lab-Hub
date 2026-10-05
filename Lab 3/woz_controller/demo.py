#!/usr/bin/env python3
"""Silent, virtual-clock walkthrough using the actual controller and preset pools."""
from datetime import datetime
from http.server import ThreadingHTTPServer
import argparse
import threading
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from audio_backend import DryRunBackend
from controller import ScriptLibrary, TalkingBoxController
from server import ControllerHandler, ROOT


class DemoBackend(DryRunBackend):
    """Visible pacing only. No audio, speech recognition, or hardware simulation."""
    def __init__(self):
        super().__init__(delay=1.8, transcripts=[])

    def listen(self, cancel, on_thinking, *, start_timeout=2, min_silence=.8,
               on_started=None):
        # A queued line stands in for a user starting within the response window.
        if cancel.wait(start_timeout):
            return ""
        with self._lock:
            text = self._transcripts.popleft() if self._transcripts else ""
        if not text:
            return ""
        if on_started:
            on_started()
        if cancel.wait(min_silence):
            return ""
        on_thinking()
        return "" if cancel.wait(.6) else text


class DemoSession:
    def __init__(self):
        self.lock = threading.RLock()
        self.controller = None
        self.restart()

    def restart(self):
        if self.controller:
            self.controller.close()
        self.now = datetime(2026, 10, 4, 10, 29, 59, tzinfo=ZoneInfo("America/New_York"))
        self.backend = DemoBackend()
        self.controller = TalkingBoxController(self.backend,
            ScriptLibrary(ROOT / "talking-box-dialogue.json"), clock=lambda: self.now)

    def snapshot(self):
        with self.lock:
            return {"now": self.now.isoformat(), "state": self.controller.state.snapshot()}

    def step(self, action, transcript=""):
        if action not in {"next", "quiet", "reset"}:
            raise ValueError("Unknown demo step")
        if not isinstance(transcript, str) or len(transcript) > 300:
            raise ValueError("Use a simulated reply of at most 300 characters")
        with self.lock:
            if action == "reset":
                self.restart()
                return
            controller = self.controller
            # Share the real controller's lock so a scheduled action cannot race a jump.
            with controller._action_lock:
                if (controller._thread and controller._thread.is_alive()):
                    raise ValueError("Wait until the current exchange is finished")
                if action == "quiet":
                    self.now = self.now.replace(hour=20, minute=0, second=0)
                else:
                    next_at = controller.daily.snapshot()["next_at"]
                    if not next_at:
                        raise ValueError("Enable the schedule or reset the demo")
                    if transcript.strip():
                        self.backend.queue_transcript(transcript)
                    self.now = datetime.fromisoformat(next_at)
                controller.maybe_trigger_daily()

    def close(self):
        self.controller.close()


class DemoServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, session):
        self.session = session
        super().__init__(address, DemoHandler)

    @property
    def controller(self):
        return self.session.controller


class DemoHandler(ControllerHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path in {"/", "/demo"}:
            self.send_demo_file("demo.html", "text/html; charset=utf-8")
        elif path == "/demo.js":
            self.send_demo_file("demo.js", "application/javascript; charset=utf-8")
        elif path == "/demo.css":
            self.send_demo_file("demo.css", "text/css; charset=utf-8")
        elif path == "/api/demo":
            self._json(self.server.session.snapshot())
        else:
            super().do_GET()

    def send_demo_file(self, filename, content_type):
        payload = (ROOT / "static" / filename).read_bytes()
        self._headers(200, content_type)
        self.wfile.write(payload)

    def do_POST(self):
        if urlparse(self.path).path != "/api/demo":
            return super().do_POST()
        try:
            data = self._read_json()
            self.server.session.step(data.get("action"), data.get("transcript", ""))
            self._json({"ok": True})
        except (ValueError, TypeError) as error:
            self._json({"ok": False, "error": str(error)}, 400)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=18766)
    args = parser.parse_args()
    session = DemoSession()
    server = DemoServer(("127.0.0.1", args.port), session)
    print(f"Silent demo: http://127.0.0.1:{args.port}/demo", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        session.close()
        server.server_close()


if __name__ == "__main__":
    main()
