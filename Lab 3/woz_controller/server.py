#!/usr/bin/env python3
"""Loopback-only web controller for the Talking Box prototype."""

from __future__ import annotations

import argparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from audio_backend import DryRunBackend, PiAudioBackend
from controller import ScriptLibrary, TalkingBoxController


ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
CONTENT_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
}


def dispatch_action(
    controller: TalkingBoxController,
    path: str,
    data: dict[str, Any],
) -> bool:
    """Apply one API action and return whether it was accepted."""
    accepted = True
    if path == "/api/morning":
        accepted = controller.start_morning()
    elif path == "/api/self-talk":
        accepted = controller.start_self_talk()
    elif path == "/api/schedule":
        enabled = data.get("enabled")
        if not isinstance(enabled, bool):
            raise ValueError("enabled must be true or false")
        controller.set_daily_enabled(enabled)
    elif path == "/api/listen":
        accepted = controller.listen_once()
    elif path == "/api/transcript":
        text = data.get("text", "")
        if not isinstance(text, str) or len(text) > 10000:
            raise ValueError("Correction must be text up to 10000 characters")
        controller.state.set_transcript(text)
    elif path == "/api/speak":
        text = str(data.get("text", "")).strip()
        if not text or len(text) > 300:
            raise ValueError("Reply must contain 1 to 300 characters")
        accepted = controller.speak(text)
    elif path == "/api/work/start":
        minutes = float(data.get("minutes", 45))
        if not math.isfinite(minutes) or not 0.05 <= minutes <= 180:
            raise ValueError("Timer must be between 0.05 and 180 minutes")
        accepted = controller.start_work(minutes)
    elif path == "/api/work/expire":
        accepted = controller.trigger_work_reminder()
    elif path == "/api/work/accept":
        accepted = controller.accept_break()
    elif path == "/api/work/defer":
        controller.defer_break()
    elif path == "/api/quiet":
        controller.stop()
    elif path == "/api/stop":
        controller.stop()
    elif path == "/api/pause":
        controller.pause()
    elif path == "/api/resume":
        controller.resume()
    elif path == "/api/reset":
        controller.reset()
    elif path == "/api/replies":
        enabled = data.get("automatic")
        if not isinstance(enabled, bool):
            raise ValueError("automatic must be true or false")
        controller.set_automatic_reply(enabled)
    elif path == "/api/simulate":
        if not isinstance(controller.backend, DryRunBackend):
            raise ValueError("Simulated input is only available in dry-run mode")
        text = data.get("text", "")
        if not isinstance(text, str) or len(text) > 10000:
            raise ValueError("Simulated input must be text up to 10000 characters")
        controller.backend.queue_transcript(text)
    elif path == "/api/muse/wake":
        controller.request_muse_wake(str(data.get("word", "")))
    else:
        raise LookupError(path)
    return accepted


class ControllerHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], controller: TalkingBoxController):
        super().__init__(address, ControllerHandler)
        self.controller = controller


class ControllerHandler(BaseHTTPRequestHandler):
    server: ControllerHTTPServer

    def log_message(self, format_string: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format_string % args}")

    def _headers(self, status: int, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'")
        self.end_headers()

    def _json(self, data: Any, status: int = HTTPStatus.OK) -> None:
        payload = json.dumps(data, ensure_ascii=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(payload)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length < 0 or length > 65536:
            raise ValueError("Request is too large")
        if not length:
            return {}
        data = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("JSON body must be an object")
        return data

    def _serve_static(self, name: str) -> None:
        allowed = {
            "wizard.html",
            "participant.html",
            "styles.css",
            "wizard.js",
            "participant.js",
        }
        if name not in allowed:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        path = STATIC / name
        payload = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", CONTENT_TYPES[path.suffix])
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in {"/", "/wizard"}:
            self._serve_static("wizard.html")
        elif path == "/participant":
            self._serve_static("participant.html")
        elif path.startswith("/static/"):
            self._serve_static(path.removeprefix("/static/"))
        elif path == "/api/state":
            self._json(self.server.controller.state.snapshot())
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            data = self._read_json()
            try:
                accepted = dispatch_action(self.server.controller, path, data)
            except LookupError:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            if not accepted:
                self._json({"ok": False, "error": "Another action is active"}, HTTPStatus.CONFLICT)
                return
            self._json({"ok": True, "state": self.server.controller.state.snapshot()})
        except (ValueError, TypeError, OverflowError, json.JSONDecodeError) as error:
            self._json({"ok": False, "error": str(error)}, HTTPStatus.BAD_REQUEST)


def build_controller(backend_name: str, model: str) -> TalkingBoxController:
    script = ScriptLibrary(ROOT / "talking-box-dialogue.json")
    if backend_name == "pi":
        backend = PiAudioBackend(ROOT.parent, model_name=model)
    else:
        backend = DryRunBackend()
    return TalkingBoxController(backend, script)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--backend", choices=("dry-run", "pi"), default="dry-run")
    parser.add_argument("--model", choices=("tiny.en", "base.en"), default="tiny.en")
    args = parser.parse_args()
    if args.host != "127.0.0.1":
        parser.error("The controller must remain bound to 127.0.0.1")
    server = ControllerHTTPServer(
        (args.host, args.port),
        build_controller(args.backend, args.model),
    )
    print(f"Talking Box controller: http://{args.host}:{args.port}/wizard")
    print(f"Participant view:       http://{args.host}:{args.port}/participant")
    print(f"Backend: {args.backend}")
    if args.backend == "dry-run":
        print("Silent accelerated simulation; no microphone, playback, or model loading")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.controller.close()
        server.server_close()


if __name__ == "__main__":
    main()
