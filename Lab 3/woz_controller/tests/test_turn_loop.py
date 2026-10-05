"""Deterministic controller checks using events only; no audio devices are opened.

The backend delivers artificial speech-start, speech-end and recognition events.
It does not establish that microphone/VAD timing or speaker isolation works on Pi.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path
import sys
import threading
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from controller import ScriptLibrary, TalkingBoxController  # noqa: E402


def wait_until(predicate, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.005)
    raise AssertionError("Timed out waiting for a simulated controller event")


class EventBackend:
    """Artificial turns, including optionally blocked and late backend returns."""

    def __init__(self, outcomes=(), block_listen=None, block_speak=None, speak_errors=None):
        self.outcomes = deque(outcomes)
        self.block_listen = block_listen
        self.block_speak = block_speak
        self.listen_entered = threading.Event()
        self.speak_entered = threading.Event()
        self.release_listen = threading.Event()
        self.release_speak = threading.Event()
        self.trace = []
        self.listen_calls = []
        self.phase_observations = []
        self.simulated_audio = []
        self.controller = None
        self.overlaps = []
        self._lock = threading.Lock()
        self._audio_active = None
        self._speak_count = 0
        self.speak_errors = speak_errors or {}

    def _enter(self, operation):
        with self._lock:
            if self._audio_active is not None:
                self.overlaps.append((self._audio_active, operation))
                raise AssertionError("Playback and listening overlapped")
            self._audio_active = operation

    def _exit(self):
        with self._lock:
            self._audio_active = None

    def _phase(self, callback):
        if callback is not None:
            callback()
            if self.controller is not None:
                state = self.controller.state.snapshot()
                self.phase_observations.append((state["status"], state["phase"]))

    def speak(self, text, cancel):
        self._enter("speak")
        try:
            self._speak_count += 1
            self.trace.append(("speak", text))
            self.speak_entered.set()
            if self._speak_count in self.speak_errors:
                raise self.speak_errors[self._speak_count]
            if self._speak_count == self.block_speak:
                if not self.release_speak.wait(3):
                    raise AssertionError("Test did not release simulated playback")
        finally:
            self._exit()

    def listen(
        self,
        cancel,
        on_thinking,
        *,
        start_timeout=2.0,
        min_silence=0.8,
        on_started=None,
    ):
        self._enter("listen")
        try:
            call = {"start_timeout": start_timeout, "min_silence": min_silence}
            self.listen_calls.append(call)
            self.trace.append(("listen", call))
            self.listen_entered.set()
            outcome = self.outcomes.popleft() if self.outcomes else ""
            if len(self.listen_calls) == self.block_listen:
                # Intentionally ignore cancellation to emulate a backend that
                # returns and invokes callbacks after its action was cancelled.
                if not self.release_listen.wait(3):
                    raise AssertionError("Test did not release simulated listening")
            if isinstance(outcome, dict):
                self.simulated_audio.append(outcome)
                outcome = outcome["text"]
            if outcome or isinstance(outcome, Exception):
                self._phase(on_started)
                self._phase(on_thinking)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome
        finally:
            self._exit()

    def stop(self):
        self.trace.append(("stop", None))

    @property
    def spoken(self):
        return [value for operation, value in self.trace if operation == "speak"]


class TurnLoopTests(unittest.TestCase):
    def setUp(self):
        self.controllers = []

    def tearDown(self):
        for controller in self.controllers:
            controller.backend.release_listen.set()
            controller.backend.release_speak.set()
            controller.stop()
            close = getattr(controller, "close", None)
            if close is not None:
                close()

    def make_controller(self, backend=None):
        backend = backend or EventBackend()
        script = ScriptLibrary(ROOT / "talking-box-dialogue.json")
        script.timing["self_talk_pause_seconds"] = 0
        controller = TalkingBoxController(backend, script, scheduler_interval=0.005)
        backend.controller = controller
        self.controllers.append(controller)
        return controller, backend

    def wait_idle(self, controller):
        wait_until(lambda: not controller.state.snapshot()["active_action"])

    def start_short_work(self, controller, seconds):
        # Public controls have a 3-second minimum; inject only the deadline to
        # exercise the same background scheduler quickly without audio hardware.
        self.assertTrue(controller.start_work(0.05))
        self.wait_idle(controller)
        controller.state.start_work(seconds / 60)

    def test_default_mode_and_reserved_muse_wake_are_local_only(self):
        controller, backend = self.make_controller()
        state = controller.state.snapshot()
        self.assertEqual(state["mode"], "flower")
        self.assertTrue(state["automatic_reply"])
        self.assertFalse(controller.request_muse_wake("future independent wake phrase"))
        self.assertEqual(controller.state.snapshot()["mode"], "flower")
        self.assertEqual(backend.trace, [])

    def test_no_response_still_opens_window_after_each_morning_line(self):
        controller, backend = self.make_controller(EventBackend(["", ""]))
        self.assertTrue(controller.start_morning())
        self.wait_idle(controller)
        self.assertEqual(
            backend.spoken,
            [controller.script.lines["panel_1"], controller.script.lines["panel_2"]],
        )
        self.assertEqual([event[0] for event in backend.trace], ["speak", "listen", "speak", "listen"])
        self.assertEqual(len(backend.listen_calls), 2)
        for call in backend.listen_calls:
            self.assertEqual(call, {"start_timeout": 2.0, "min_silence": 0.8})
        self.assertEqual(controller.state.snapshot()["status"], "quiet")

    def test_simulated_boundary_start_and_long_sentence_are_not_truncated(self):
        sentence = " ".join(f"word{number}" for number in range(400))
        for speech_start in (1.999, 2.0):
            with self.subTest(simulated_start_seconds=speech_start):
                backend = EventBackend([{"text": sentence, "start_seconds": speech_start, "duration_seconds": 18.0}])
                controller, backend = self.make_controller(backend)
                self.assertTrue(controller.listen_once())
                self.wait_idle(controller)
                self.assertEqual(backend.listen_calls[0]["start_timeout"], 2.0)
                self.assertEqual(controller.state.snapshot()["transcript"], sentence)
                self.assertEqual(controller.state.snapshot()["status"], "thinking")
                self.assertIn(("listening", "capturing_speech"), backend.phase_observations)
                self.assertIn(("thinking", "transcribing"), backend.phase_observations)
                self.assertEqual(backend.spoken, [])

    def test_multiple_automatic_turns_finish_after_silence(self):
        controller, backend = self.make_controller(EventBackend(["", "First reply", "Second reply", "Third reply", ""]))
        self.assertTrue(controller.start_morning())
        self.wait_idle(controller)
        self.assertEqual(
            backend.spoken,
            [controller.script.lines["panel_1"], controller.script.lines["panel_2"]]
            + [controller.script.lines["panel_3"]] * 3,
        )
        self.assertEqual(len(backend.listen_calls), len(backend.spoken))
        self.assertEqual([event[0] for event in backend.trace], ["speak", "listen"] * 5)
        self.assertEqual(backend.overlaps, [])
        self.assertEqual(controller.state.snapshot()["status"], "quiet")

    def test_recognition_failure_can_recover_with_manual_reply(self):
        controller, backend = self.make_controller(EventBackend([RuntimeError("simulated recognition failure"), ""]))
        self.assertTrue(controller.listen_once())
        self.wait_idle(controller)
        state = controller.state.snapshot()
        self.assertEqual(state["status"], "quiet")
        self.assertIn("simulated recognition failure", state["last_error"])
        self.assertTrue(controller.speak("Manual fixed-dialogue fallback."))
        self.wait_idle(controller)
        self.assertEqual(backend.spoken, ["Manual fixed-dialogue fallback."])
        self.assertEqual(len(backend.listen_calls), 2)
        self.assertEqual(controller.state.snapshot()["last_error"], "")
        self.assertEqual(controller.state.snapshot()["status"], "quiet")

    def test_manual_reply_mode_retains_transcript_without_automatic_speech(self):
        controller, backend = self.make_controller(EventBackend(["Review these words first."]))
        controller.set_automatic_reply(False)
        self.assertTrue(controller.speak("Wizard-selected opening."))
        self.wait_idle(controller)
        state = controller.state.snapshot()
        self.assertFalse(state["automatic_reply"])
        self.assertEqual(state["status"], "thinking")
        self.assertEqual(state["transcript"], "Review these words first.")
        self.assertEqual(backend.spoken, ["Wizard-selected opening."])
        self.assertEqual(len(backend.listen_calls), 1)
        controller.reset()
        self.assertTrue(controller.state.snapshot()["automatic_reply"])

    def test_playback_failure_can_recover_with_a_fresh_turn(self):
        backend = EventBackend([""], speak_errors={1: RuntimeError("simulated speaker failure")})
        controller, backend = self.make_controller(backend)
        self.assertTrue(controller.speak("First output fails."))
        self.wait_idle(controller)
        self.assertEqual(controller.state.snapshot()["status"], "quiet")
        self.assertIn("simulated speaker failure", controller.state.snapshot()["last_error"])
        self.assertEqual(backend.listen_calls, [])
        self.assertTrue(controller.speak("Retry succeeds."))
        self.wait_idle(controller)
        self.assertEqual(backend.spoken, ["First output fails.", "Retry succeeds."])
        self.assertEqual(len(backend.listen_calls), 1)
        self.assertEqual(controller.state.snapshot()["last_error"], "")
        self.assertEqual(controller.state.snapshot()["status"], "quiet")

    def test_playback_has_no_simultaneous_listening_or_second_action(self):
        controller, backend = self.make_controller(EventBackend([""], block_speak=1))
        self.assertTrue(controller.speak("Artificial playback only."))
        self.assertTrue(backend.speak_entered.wait(1))
        self.assertEqual(controller.state.snapshot()["status"], "speaking")
        self.assertEqual(backend.listen_calls, [])
        self.assertFalse(controller.listen_once())
        backend.release_speak.set()
        self.wait_idle(controller)
        self.assertEqual([event[0] for event in backend.trace], ["speak", "listen"])
        self.assertEqual(backend.overlaps, [])

    def test_cancelled_actions_ignore_late_transcript_callbacks_and_errors(self):
        for action_name in ("stop", "pause", "reset"):
            for late_outcome in ("Stale words must never be published", RuntimeError("stale backend failure")):
                with self.subTest(action=action_name, late_outcome=str(late_outcome)):
                    controller, backend = self.make_controller(EventBackend([late_outcome, ""], block_listen=1))
                    self.assertTrue(controller.listen_once())
                    self.assertTrue(backend.listen_entered.wait(1))
                    getattr(controller, action_name)()
                    expected_status = "paused" if action_name == "pause" else "quiet"
                    self.assertEqual(controller.state.snapshot()["status"], expected_status)
                    # No replacement action may overlap a still-running backend.
                    self.assertFalse(controller.speak("Too early replacement."))
                    backend.release_listen.set()
                    wait_until(lambda: backend._audio_active is None)
                    self.wait_idle(controller)
                    state = controller.state.snapshot()
                    self.assertEqual(state["status"], expected_status)
                    self.assertEqual(state["transcript"], "")
                    self.assertEqual(state["last_error"], "")
                    if action_name == "pause":
                        controller.resume()
                    self.assertTrue(controller.speak("Safe replacement."))
                    self.wait_idle(controller)
                    self.assertEqual(backend.spoken, ["Safe replacement."])
                    self.assertEqual(backend.overlaps, [])

    def test_reset_clears_transcript_errors_and_work_timer(self):
        controller, backend = self.make_controller(EventBackend(["Retained manual transcript"]))
        self.assertTrue(controller.listen_once())
        self.wait_idle(controller)
        controller.state.set_error("Previous recoverable error")
        controller.state.start_work(10)
        controller.reset()
        state = controller.state.snapshot()
        self.assertEqual(state["status"], "quiet")
        self.assertEqual(state["transcript"], "")
        self.assertEqual(state["last_error"], "")
        self.assertEqual(state["active_action"], "")
        self.assertFalse(state["work"]["running"])

    def test_work_reminder_runs_without_state_http_requests(self):
        controller, backend = self.make_controller(EventBackend(["", ""]))
        self.start_short_work(controller, 0.12)
        # Poll only the fake output: no GET, state refresh or explicit timer tick.
        wait_until(lambda: controller.script.lines["panel_5"] in backend.spoken)
        self.wait_idle(controller)
        self.assertEqual(backend.spoken, [controller.script.lines["panel_4"], controller.script.lines["panel_5"]])
        self.assertEqual(len(backend.listen_calls), 2)
        self.assertEqual(backend.spoken.count(controller.script.lines["panel_5"]), 1)

    def test_due_reminder_waits_for_busy_turn_to_finish(self):
        controller, backend = self.make_controller(EventBackend(["", "", ""], block_listen=2))
        self.start_short_work(controller, 0.12)
        self.assertTrue(controller.listen_once())
        self.assertTrue(backend.listen_entered.wait(1))
        wait_until(lambda: len(backend.listen_calls) == 2)
        time.sleep(0.18)
        self.assertNotIn(controller.script.lines["panel_5"], backend.spoken)
        self.assertFalse(controller.state.snapshot()["work"]["reminder_sent"])
        backend.release_listen.set()
        wait_until(lambda: controller.script.lines["panel_5"] in backend.spoken)
        self.wait_idle(controller)
        self.assertEqual(backend.overlaps, [])
        self.assertEqual(backend.spoken.count(controller.script.lines["panel_5"]), 1)

    def test_pause_freezes_work_timer_until_resumed(self):
        controller, backend = self.make_controller(EventBackend(["", ""]))
        self.start_short_work(controller, 0.24)
        controller.pause()
        self.assertEqual(controller.state.snapshot()["status"], "paused")
        time.sleep(0.30)
        self.assertNotIn(controller.script.lines["panel_5"], backend.spoken)
        controller.resume()
        self.assertEqual(controller.state.snapshot()["status"], "quiet")
        time.sleep(0.06)
        self.assertNotIn(controller.script.lines["panel_5"], backend.spoken)
        wait_until(lambda: controller.script.lines["panel_5"] in backend.spoken)
        self.wait_idle(controller)
        self.assertEqual(backend.spoken.count(controller.script.lines["panel_5"]), 1)

    def test_pause_during_incomplete_reminder_retries_after_resume(self):
        controller, backend = self.make_controller(EventBackend(["", ""], block_speak=2))
        self.start_short_work(controller, 0.05)
        reminder = controller.script.lines["panel_5"]
        wait_until(lambda: len(backend.spoken) == 2)
        work = controller.state.snapshot()["work"]
        self.assertTrue(work["reminder_sent"])
        self.assertFalse(work["reminder_spoken"])

        controller.pause()
        state = controller.state.snapshot()
        self.assertEqual(state["status"], "paused")
        self.assertFalse(state["work"]["running"])
        self.assertIsNotNone(state["work"]["paused_remaining"])
        self.assertIsNone(state["work"]["deadline"])
        self.assertFalse(state["work"]["reminder_sent"])
        self.assertFalse(state["work"]["reminder_spoken"])
        backend.release_speak.set()
        self.wait_idle(controller)
        # A delayed playback return must not mark the interrupted reminder as
        # delivered or open a listening window while the controller is paused.
        state = controller.state.snapshot()
        self.assertEqual((state["status"], state["phase"]), ("paused", "paused"))
        self.assertFalse(state["work"]["reminder_spoken"])
        self.assertEqual(len(backend.listen_calls), 1)

        controller.resume()
        wait_until(lambda: backend.spoken.count(reminder) == 2)
        self.wait_idle(controller)
        state = controller.state.snapshot()
        self.assertEqual(state["status"], "quiet")
        self.assertTrue(state["work"]["reminder_sent"])
        self.assertTrue(state["work"]["reminder_spoken"])
        self.assertEqual(len(backend.listen_calls), 2)
        self.assertEqual(backend.overlaps, [])
        controller.stop()
        state = controller.state.snapshot()
        self.assertFalse(state["work"]["running"])
        self.assertFalse(state["work"]["reminder_sent"])
        self.assertFalse(state["work"]["reminder_spoken"])

    def test_pause_after_completed_reminder_does_not_repeat_after_resume(self):
        backend = EventBackend(["", "Stale response from cancelled reminder"], block_listen=2)
        controller, backend = self.make_controller(backend)
        self.start_short_work(controller, 0.05)
        reminder = controller.script.lines["panel_5"]
        wait_until(lambda: len(backend.listen_calls) == 2)
        state = controller.state.snapshot()
        self.assertTrue(state["work"]["reminder_sent"])
        self.assertTrue(state["work"]["reminder_spoken"])

        controller.pause()
        backend.release_listen.set()
        self.wait_idle(controller)
        state = controller.state.snapshot()
        self.assertEqual((state["status"], state["phase"]), ("paused", "paused"))
        self.assertEqual(state["transcript"], "")
        self.assertEqual(state["last_error"], "")
        self.assertTrue(state["work"]["reminder_sent"])
        self.assertTrue(state["work"]["reminder_spoken"])

        controller.resume()
        # The original deadline has already passed, so a duplicate would be
        # emitted on these scheduler ticks if the completed flag were rearmed.
        time.sleep(0.06)
        state = controller.state.snapshot()
        self.assertEqual((state["status"], state["phase"]), ("quiet", "idle"))
        self.assertEqual(state["transcript"], "")
        self.assertEqual(backend.spoken.count(reminder), 1)
        self.assertEqual(len(backend.spoken), 2)
        self.assertEqual(len(backend.listen_calls), 2)
        self.assertEqual(backend.overlaps, [])
        controller.reset()
        state = controller.state.snapshot()
        self.assertFalse(state["work"]["running"])
        self.assertFalse(state["work"]["reminder_sent"])
        self.assertFalse(state["work"]["reminder_spoken"])

    def test_stop_clears_work_timer(self):
        controller, backend = self.make_controller(EventBackend([""]))
        self.start_short_work(controller, 0.12)
        controller.stop()
        self.assertFalse(controller.state.snapshot()["work"]["running"])
        time.sleep(0.18)
        self.assertNotIn(controller.script.lines["panel_5"], backend.spoken)


if __name__ == "__main__":
    unittest.main()
