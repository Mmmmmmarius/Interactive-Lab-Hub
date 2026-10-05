#!/usr/bin/env python3
"""Local Flower turn loop, with a manual wizard fallback and no Muse transport."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import threading
import time
from typing import Any, Callable

STATUSES = {"quiet", "listening", "thinking", "speaking", "paused"}


class ConversationState:
    def __init__(self, backend_name: str = "unknown") -> None:
        self._lock = threading.RLock()
        self._deadline_monotonic: float | None = None
        self._data: dict[str, Any] = {
            "status": "quiet", "phase": "idle", "mode": "flower", "backend": backend_name,
            "automatic_reply": True,
            "muse": {"available": False, "wake_interface": "reserved"},
            "transcript": "", "last_spoken": "", "last_error": "",
            "active_action": "",
            "work": {"running": False, "deadline": None,
                     "reminder_sent": False, "reminder_spoken": False, "paused_remaining": None},
            "events": [],
        }
        self.log("Controller ready in Flower mode")

    def log(self, message: str) -> None:
        with self._lock:
            stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
            self._data["events"].insert(0, {"time": stamp, "message": message})
            del self._data["events"][20:]

    def set_status(self, status: str) -> None:
        if status not in STATUSES:
            raise ValueError(f"Unknown status: {status}")
        with self._lock:
            self._data["status"] = status
        self.log(f"State: {status.title()}")

    def set_phase(self, phase: str) -> None:
        with self._lock:
            self._data["phase"] = phase

    def set_transcript(self, transcript: str) -> None:
        with self._lock:
            self._data["transcript"] = transcript.strip()
        self.log("Transcript updated" if transcript.strip() else "Transcript cleared")

    def set_last_spoken(self, text: str) -> None:
        with self._lock:
            self._data["last_spoken"] = text.strip()

    def set_error(self, message: str) -> None:
        with self._lock:
            self._data["last_error"] = message.strip()
        if message:
            self.log(f"Error: {message}")

    def set_active_action(self, action: str) -> None:
        with self._lock:
            self._data["active_action"] = action

    def set_automatic_reply(self, enabled: bool) -> None:
        with self._lock:
            self._data["automatic_reply"] = enabled
        self.log("Fixed replies enabled" if enabled else "Wizard replies enabled")

    def start_work(self, minutes: float) -> None:
        if not math.isfinite(minutes) or minutes <= 0:
            raise ValueError("Work duration must be positive and finite")
        with self._lock:
            self._deadline_monotonic = time.monotonic() + minutes * 60
            self._data["work"] = {
                "running": True, "deadline": time.time() + minutes * 60,
                "reminder_sent": False, "reminder_spoken": False, "paused_remaining": None,
            }
        self.log(f"Work timer started for {minutes:g} minutes")

    def stop_work(self) -> None:
        with self._lock:
            self._deadline_monotonic = None
            self._data["work"].update(running=False, deadline=None, paused_remaining=None,
                                      reminder_sent=False, reminder_spoken=False)
        self.log("Work session closed")

    def pause_work(self) -> None:
        with self._lock:
            work = self._data["work"]
            if work["running"]:
                work["paused_remaining"] = max(0.0, self._deadline_monotonic - time.monotonic())
                work["running"] = False
                work["deadline"] = None
                self._deadline_monotonic = None

    def resume_work(self) -> None:
        with self._lock:
            work = self._data["work"]
            remaining = work["paused_remaining"]
            if remaining is not None:
                self._deadline_monotonic = time.monotonic() + remaining
                work.update(running=True, deadline=time.time() + remaining, paused_remaining=None)

    def reminder_due(self) -> bool:
        with self._lock:
            work = self._data["work"]
            return bool(work["running"] and not work["reminder_sent"]
                        and self._deadline_monotonic is not None
                        and time.monotonic() >= self._deadline_monotonic)

    def claim_reminder(self) -> bool:
        with self._lock:
            work = self._data["work"]
            if not work["running"] or work["reminder_sent"]:
                return False
            work["reminder_sent"] = True
        self.log("Work reminder triggered")
        return True

    def rearm_reminder(self) -> None:
        with self._lock:
            if not self._data["work"]["reminder_spoken"]:
                self._data["work"]["reminder_sent"] = False

    def mark_reminder_spoken(self) -> None:
        with self._lock:
            self._data["work"]["reminder_spoken"] = True

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            result = deepcopy(self._data)
            remaining = (max(0.0, self._deadline_monotonic - time.monotonic())
                         if self._deadline_monotonic is not None
                         else result["work"]["paused_remaining"])
        result["work"]["remaining_seconds"] = round(remaining) if remaining is not None else None
        return result


class ScriptLibrary:
    def __init__(self, path: Path) -> None:
        data = json.loads(path.read_text(encoding="utf-8"))
        self.timing = data["timing"]
        self.lines: dict[str, str] = {}
        for scene in data["scenes"]:
            for panel in scene["panels"]:
                if "box" in panel:
                    self.lines[f"panel_{panel['panel']}"] = panel["box"]


class TalkingBoxController:
    def __init__(self, backend: Any, script: ScriptLibrary,
                 scheduler_interval: float = 0.05) -> None:
        self.backend, self.script = backend, script
        backend_name = {"DryRunBackend": "dry-run", "PiAudioBackend": "pi"}.get(
            type(backend).__name__, "simulated events")
        self.state = ConversationState(backend_name)
        self._action_lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._cancel = threading.Event()
        self._paused = False
        self._closed = threading.Event()
        self._scheduler = threading.Thread(target=self._schedule,
                                           args=(scheduler_interval,), daemon=True)
        self._scheduler.start()

    def _schedule(self, interval: float) -> None:
        while not self._closed.wait(max(interval, 0.01)):
            self.maybe_trigger_work_reminder()

    def _current(self, cancel: threading.Event) -> bool:
        return self._cancel is cancel and not cancel.is_set() and not self._closed.is_set()

    def _update(self, cancel: threading.Event, **fields: str) -> bool:
        with self._action_lock:
            if not self._current(cancel):
                return False
            for key, value in fields.items():
                getattr(self.state, f"set_{key}")(value)
            return True

    def _start(self, name: str, target: Callable[[threading.Event], None]) -> bool:
        with self._action_lock:
            if self._paused or self._closed.is_set() or (self._thread and self._thread.is_alive()):
                return False
            cancel = self._cancel = threading.Event()
            self.state.set_error("")
            self.state.set_active_action(name)

            def run() -> None:
                try:
                    target(cancel)
                except Exception as error:
                    with self._action_lock:
                        if self._current(cancel):
                            self.state.set_error(f"{type(error).__name__}: {error}")
                            self.state.set_status("quiet")
                            self.state.set_phase("error; wizard can retry")
                            if name == "work reminder":
                                self.state.rearm_reminder()
                finally:
                    with self._action_lock:
                        if self._cancel is cancel:
                            self.state.set_active_action("")

            self._thread = threading.Thread(target=run, name=name, daemon=True)
            self._thread.start()
            return True

    def _speak(self, text: str, cancel: threading.Event) -> None:
        if self._update(cancel, status="speaking", phase="playback", last_spoken=text):
            # One action owns audio: no input stream is opened until speak returns.
            self.backend.speak(text, cancel)

    def _listen(self, cancel: threading.Event) -> str:
        if not self._update(cancel, status="listening", phase="waiting_for_start"):
            return ""
        transcript = self.backend.listen(
            cancel,
            lambda: self._update(cancel, status="thinking", phase="transcribing"),
            start_timeout=float(self.script.timing["speech_start_timeout_seconds"]),
            min_silence=float(self.script.timing["min_silence_seconds"]),
            on_started=lambda: self._update(cancel, phase="capturing_speech"),
        )
        if not self._current(cancel):
            return ""
        if transcript:
            self._update(cancel, transcript=transcript, status="thinking", phase="awaiting_wizard")
        else:
            self._update(cancel, status="quiet", phase="idle")
            with self._action_lock:
                if self._current(cancel):
                    self.state.log("No speech started in the response window")
        return transcript

    def _reply_loop(self, cancel: threading.Event, transcript: str,
                    reply: str | None = None) -> None:
        while transcript and self._current(cancel):
            if not self.state.snapshot()["automatic_reply"]:
                return
            self._speak(reply or self.script.lines["panel_3"], cancel)
            transcript = self._listen(cancel)
            reply = None

    def _utterance(self, text: str, cancel: threading.Event,
                   reply: str | None = None) -> str:
        self._speak(text, cancel)
        transcript = self._listen(cancel)
        self._reply_loop(cancel, transcript, reply)
        return transcript

    def start_morning(self) -> bool:
        def action(cancel: threading.Event) -> None:
            if self._utterance(self.script.lines["panel_1"], cancel):
                return
            if cancel.wait(self.script.timing["self_talk_pause_seconds"]):
                return
            self._utterance(self.script.lines["panel_2"], cancel)
        return self._start("morning scene", action)

    def listen_once(self) -> bool:
        return self._start("listen", lambda cancel: self._listen(cancel))

    def speak(self, text: str, return_to_quiet: bool = True) -> bool:
        # Legacy argument retained for callers; every output gets a response window.
        del return_to_quiet
        return self._start("speak", lambda cancel: self._utterance(text, cancel))

    def start_work(self, minutes: float) -> bool:
        if not math.isfinite(minutes) or not 0.05 <= minutes <= 180:
            raise ValueError("Timer must be between 0.05 and 180 minutes")
        def action(cancel: threading.Event) -> None:
            self._utterance(self.script.lines["panel_4"], cancel)
            with self._action_lock:
                if self._current(cancel):
                    self.state.start_work(minutes)
        return self._start("start work session", action)

    def trigger_work_reminder(self) -> bool:
        with self._action_lock:
            work = self.state.snapshot()["work"]
            if not work["running"] or work["reminder_sent"]:
                return False
            def action(cancel: threading.Event) -> None:
                with self._action_lock:
                    if not self._current(cancel) or not self.state.claim_reminder():
                        return
                # Wizard decides whether an ambiguous answer accepts the walk.
                self._speak(self.script.lines["panel_5"], cancel)
                with self._action_lock:
                    if not self._current(cancel):
                        return
                    self.state.mark_reminder_spoken()
                self._reply_loop(cancel, self._listen(cancel))
            return self._start("work reminder", action)

    def maybe_trigger_work_reminder(self) -> None:
        with self._action_lock:
            state = self.state.snapshot()
            if (not self._paused and state["status"] == "quiet"
                    and not state["last_error"] and self.state.reminder_due()):
                self.trigger_work_reminder()

    def accept_break(self) -> bool:
        with self._action_lock:
            def action(cancel: threading.Event) -> None:
                with self._action_lock:
                    if not self._current(cancel):
                        return
                    self.state.stop_work()
                self._utterance(self.script.lines["panel_6"], cancel)
            return self._start("accept break", action)

    def defer_break(self) -> None:
        self.stop()
        self.state.log("Break reminder deferred")

    def set_automatic_reply(self, enabled: bool) -> None:
        self.state.set_automatic_reply(enabled)

    def request_muse_wake(self, wake_word: str) -> bool:
        # Future independent wake-word input can call this. No pairing, imports,
        # network clients, wake-word detection, or user-data transmission exist.
        del wake_word
        self.state.log("Muse wake interface reserved; Flower mode remains active")
        return False

    def _cancel_action(self) -> None:
        self._cancel.set()
        stop = getattr(self.backend, "stop", None)
        if callable(stop):
            try:
                stop()
            except Exception as error:
                self.state.set_error(f"Stop failed: {type(error).__name__}: {error}")
        if self._thread and self._thread.is_alive():
            self.state.set_active_action("cancelling; wait for audio worker")

    def stop(self) -> None:
        with self._action_lock:
            self._cancel_action()
            self._paused = False
            self.state.stop_work()
            self.state.set_status("quiet")
            self.state.set_phase("idle")
            self.state.log("Stop pressed; timer cancelled")

    def pause(self) -> None:
        with self._action_lock:
            self._paused = True
            self._cancel_action()
            self.state.rearm_reminder()
            self.state.pause_work()
            self.state.set_status("paused")
            self.state.set_phase("paused")
            self.state.log("Paused; interrupted turn is discarded")

    def resume(self) -> None:
        with self._action_lock:
            if not self._paused:
                return
            self._paused = False
            self.state.resume_work()
            self.state.set_status("quiet")
            self.state.set_phase("idle")
            self.state.log("Resumed; start a fresh turn with controls")

    def reset(self) -> None:
        with self._action_lock:
            self.stop()
            self.state.set_error("")
            self.state.set_transcript("")
            self.state.set_last_spoken("")
            self.state.set_automatic_reply(True)
            self.state.log("Reset to default Flower mode")

    def close(self) -> None:
        self._closed.set()
        self.stop()
        self._scheduler.join(timeout=1)
        thread = self._thread
        if thread and thread is not threading.current_thread():
            thread.join(timeout=1)
