"""Deterministic frame/primitive tests; no microphone, speaker, or model is used."""
from __future__ import annotations

from collections import deque
import io
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from audio_backend import DryRunBackend, PiAudioBackend
from turn_capture import AudioFrame, TurnCapture


class TurnCaptureTests(unittest.TestCase):
    def test_no_response_expires_after_start_window(self):
        capture = TurnCapture()
        for index in range(64):
            capture.feed(AudioFrame(index * .032, (index + 1) * .032, [0]), speech=False)
        self.assertTrue(capture.done)
        self.assertTrue(capture.timed_out)
        self.assertFalse(capture.started)
        self.assertEqual(capture.samples, [])

    def test_inclusive_boundary_and_late_confirmation(self):
        for onset, expected in ((1.99, True), (2.0, True), (2.01, False)):
            with self.subTest(onset=onset):
                capture = TurnCapture(onset_grace=.064)
                capture.feed(AudioFrame(1.95, 2.0, ["pre-roll"]), speech=False)
                capture.feed(AudioFrame(2.032, 2.064, ["start"]), speech=True, speech_onset=onset)
                self.assertEqual(capture.started, expected)
                if expected:
                    self.assertEqual(capture.samples, [["pre-roll"], ["start"]])
                    self.assertFalse(capture.done)
                else:
                    capture.feed(AudioFrame(2.064, 2.096, ["late"]), speech=True, speech_onset=2.01)
                    self.assertTrue(capture.timed_out)

    def test_long_sentence_has_no_total_timeout_and_keeps_all_frames(self):
        capture = TurnCapture()
        for index in range(2000):  # 64 simulated seconds, exceeding old 38s limit.
            capture.feed(AudioFrame(index * .032, (index + 1) * .032, [index]), speech=True)
            self.assertFalse(capture.done)
        for index in range(2000, 2025):
            capture.feed(AudioFrame(index * .032, (index + 1) * .032, [index]), speech=False)
        self.assertTrue(capture.done)
        self.assertEqual(len(capture.samples), 2025)
        self.assertEqual(capture.samples[0], [0])

    def test_short_pause_does_not_end_sentence(self):
        capture = TurnCapture()
        capture.feed(AudioFrame(0, .1, [1]), speech=True)
        capture.feed(AudioFrame(.1, .8, [0]), speech=False)
        self.assertFalse(capture.done)
        capture.feed(AudioFrame(.8, .9, [1]), speech=True)
        capture.feed(AudioFrame(.9, 1.7, [0]), speech=False)
        self.assertTrue(capture.done)

    def test_pre_roll_is_bounded_before_onset(self):
        capture = TurnCapture(pre_roll=.1)
        for index in range(10):
            capture.feed(AudioFrame(index * .1, (index + 1) * .1, [index]), speech=False)
        capture.feed(AudioFrame(1.0, 1.1, ["voice"]), speech=True)
        self.assertLessEqual(len(capture.samples), 3)
        self.assertEqual(capture.samples[-1], ["voice"])

    def test_invalid_settings_and_timestamps_are_rejected(self):
        for settings in ({"start_timeout": -1}, {"min_silence": 0}, {"onset_grace": float("nan")}):
            with self.assertRaises(ValueError):
                TurnCapture(**settings)
        capture = TurnCapture()
        capture.feed(AudioFrame(0, .1, []), speech=False)
        with self.assertRaises(ValueError):
            capture.feed(AudioFrame(.05, .2, []), speech=False)


class DryRunTests(unittest.TestCase):
    def test_finite_queue_callbacks_and_manual_input(self):
        backend = DryRunBackend(delay=0, transcripts=["first", "", "second"])
        callbacks = []
        listen = lambda: backend.listen(threading.Event(), lambda: callbacks.append("thinking"),
                                       on_started=lambda: callbacks.append("started"))
        self.assertEqual(listen(), "first")
        self.assertEqual(callbacks, ["started", "thinking"])
        self.assertEqual(listen(), "")
        self.assertEqual(listen(), "second")
        self.assertEqual(listen(), "")
        backend.queue_transcript(" next ")
        self.assertEqual(listen(), "next")

    def test_cancel_does_not_consume_transcript(self):
        backend = DryRunBackend(delay=0, transcripts=["hello"])
        cancelled = threading.Event()
        cancelled.set()
        callback = Mock()
        self.assertEqual(backend.listen(cancelled, callback, on_started=callback), "")
        callback.assert_not_called()
        self.assertEqual(backend.listen(threading.Event(), callback), "hello")

    def test_manual_transcript_limit_matches_controller(self):
        backend = DryRunBackend(delay=0, transcripts=[])
        backend.queue_transcript("x" * 10000)
        self.assertEqual(len(backend.listen(threading.Event(), Mock())), 10000)
        with self.assertRaises(ValueError):
            backend.queue_transcript("x" * 10001)


class FakeBlock:
    def __init__(self, samples):
        self.samples = samples

    def __getitem__(self, key):
        return self.samples


class FakeNumpy:
    float32 = "float32"

    @staticmethod
    def ascontiguousarray(samples, dtype):
        return samples

    @staticmethod
    def concatenate(chunks):
        return [sample for chunk in chunks for sample in chunk]


class FakeDetector:
    """Mock the verified two-window native confirmation, preserving state on flush."""
    def __init__(self):
        self.speech = False
        self.model_speech = False
        self.positive_count = 0
        self.silence_count = 0
        self.queued = 0
        self.flush_count = 0
        self.sample_count = 0
        self.current_segment = SimpleNamespace(start=-1)
        self.reset_count = 0

    def reset(self):
        reset_count = self.reset_count + 1
        self.__init__()
        self.reset_count = reset_count

    def accept_waveform(self, samples):
        self.sample_count += len(samples)
        if samples[0]:
            self.positive_count += 1
            self.silence_count = 0
            self.model_speech = self.model_speech or self.positive_count >= 2
        else:
            self.positive_count = 0
            self.silence_count += 1
            if self.silence_count >= 2:
                self.model_speech = False
        if self.model_speech and not self.speech:
            self.current_segment = SimpleNamespace(start=max(0, self.sample_count - 1025))
        self.speech = self.model_speech

    def is_speech_detected(self):
        return self.speech

    def flush(self):
        self.flush_count += 1
        self.queued += 1
        self.speech = False  # Flush clears wrapper detection, preserving model state.

    def empty(self):
        return self.queued == 0

    def pop(self):
        self.queued -= 1


class FakeSD:
    class CallbackAbort(Exception):
        pass

    def __init__(self, events, adc_origin=100.0):
        self.events = deque(events)
        self.adc_origin = adc_origin
        self.stream = None
        self.opened = threading.Event()

    def InputStream(self, **kwargs):
        self.stream = FakeStream(self, kwargs)
        self.opened.set()
        return self.stream


class FakeStream:
    time = 100.0

    def __init__(self, sd, kwargs):
        self.sd = sd
        self.kwargs = kwargs
        self.active = False
        self.closed = False
        self.abort_count = 0

    def start(self):
        self.active = True

    def deliver(self):
        if self.sd.events and self.active:
            start, speech, status = self.sd.events.popleft()
            try:
                self.kwargs["callback"](FakeBlock([float(speech)] * 512), 512,
                                         SimpleNamespace(inputBufferAdcTime=self.sd.adc_origin + start), status)
            except self.sd.CallbackAbort:
                self.active = False
                self.kwargs["finished_callback"]()

    def abort(self):
        self.abort_count += 1
        self.active = False
        self.kwargs["finished_callback"]()

    def close(self):
        self.closed = True


class DrivenQueue(queue.Queue):
    """Deliver one captured frame per consumer request, independent of wall time."""
    def __init__(self, sd):
        super().__init__(maxsize=64)
        self.sd = sd

    def get(self, *args, **kwargs):
        self.sd.stream.deliver()
        return super().get(*args, **kwargs)


def events_for(start=0.0, speech_frames=8, tail=30):
    count = round(start / .032)
    return [(i * .032, count <= i < count + speech_frames, False)
            for i in range(count + speech_frames + tail)]


class CaptureBackendTests(unittest.TestCase):
    def setUp(self):
        self.backend = PiAudioBackend(Path("/not-used"))

    def listen_mock(self, events, transcript="complete words", cancel=None, callbacks=None, adc_origin=100.0):
        cancel = cancel or threading.Event()
        callbacks = callbacks if callbacks is not None else []
        sd = FakeSD(events, adc_origin=adc_origin)
        detector = FakeDetector()
        model = Mock()
        model.transcribe.return_value = (iter([SimpleNamespace(text=transcript)]), None)
        self.backend._prepared_audio = None
        with patch.object(self.backend, "_audio_modules", return_value=(FakeNumpy, None, sd)), \
             patch.object(self.backend, "_new_detector", return_value=(detector, 512)), \
             patch.object(self.backend, "_whisper_model", return_value=model), \
             patch("audio_backend.queue.Queue", return_value=DrivenQueue(sd)):
            result = self.backend.listen(cancel, lambda: callbacks.append("thinking"),
                                         on_started=lambda: callbacks.append("started"))
        return result, sd, detector, model, callbacks

    def test_real_adapter_uses_capture_time_and_pre_roll_for_near_boundary(self):
        result, sd, detector, model, callbacks = self.listen_mock(events_for(start=1.984))
        self.assertEqual(result, "complete words")
        self.assertEqual(callbacks, ["started", "thinking"])
        self.assertGreater(detector.flush_count, 0)
        self.assertTrue(sd.stream.closed)
        audio = model.transcribe.call_args.args[0]
        self.assertIn(0.0, audio[:512])
        self.assertIn(1.0, audio)
        self.assertIsNone(self.backend._active_stream)

    def test_real_adapter_rejects_onset_after_window(self):
        result, sd, detector, model, callbacks = self.listen_mock(events_for(start=2.048))
        self.assertEqual(result, "")
        self.assertEqual(callbacks, [])
        model.transcribe.assert_not_called()
        self.assertTrue(sd.stream.closed)

    def test_first_adc_sample_before_stream_open_time_is_valid(self):
        for adc_origin in (99.8, -1.0):
            with self.subTest(adc_origin=adc_origin):
                result, sd, _detector, _model, callbacks = self.listen_mock(
                    events_for(), adc_origin=adc_origin,
                )
                self.assertEqual(result, "complete words")
                self.assertEqual(callbacks, ["started", "thinking"])
                self.assertTrue(sd.stream.closed)

    def test_real_adapter_full_long_sentence_retained(self):
        result, sd, detector, model, callbacks = self.listen_mock(events_for(speech_frames=1400))
        self.assertEqual(result, "complete words")
        audio = model.transcribe.call_args.args[0]
        self.assertEqual(audio.count(1.0), 1400 * 512)
        self.assertEqual(callbacks, ["started", "thinking"])
        self.assertTrue(sd.stream.closed)

    def test_real_adapter_no_response_has_no_recognition(self):
        result, sd, detector, model, callbacks = self.listen_mock([(i * .032, False, False) for i in range(70)])
        self.assertEqual(result, "")
        self.assertEqual(callbacks, [])
        model.transcribe.assert_not_called()
        self.assertTrue(sd.stream.closed)

    def test_blank_recognition_is_error_and_next_turn_recovers(self):
        with self.assertRaisesRegex(RuntimeError, "recognizer returned no words"):
            self.listen_mock(events_for(), transcript="  ")
        self.assertIsNone(self.backend._active_stream)
        self.assertFalse(self.backend._operation_lock.locked())
        self.assertEqual(self.listen_mock(events_for())[0], "complete words")

    def test_callback_failure_closes_stream_and_releases_operation(self):
        with self.assertRaisesRegex(RuntimeError, "Microphone capture failed"):
            self.listen_mock([(0, False, "input overflow")])
        self.assertIsNone(self.backend._active_stream)
        self.assertFalse(self.backend._operation_lock.locked())
        self.assertEqual(self.listen_mock(events_for())[0], "complete words")

    def test_pre_cancel_never_imports_or_opens_audio(self):
        cancel = threading.Event()
        cancel.set()
        with patch.object(self.backend, "_audio_modules") as modules:
            self.assertEqual(self.backend.listen(cancel, Mock()), "")
        modules.assert_not_called()

    def test_stop_unblocks_missing_callback_and_next_turn_recovers(self):
        sd = FakeSD([])
        outcomes = []
        with patch.object(self.backend, "_audio_modules", return_value=(FakeNumpy, None, sd)), \
             patch.object(self.backend, "_new_detector", return_value=(FakeDetector(), 512)):
            worker = threading.Thread(target=lambda: outcomes.append(self.backend.listen(threading.Event(), Mock())))
            worker.start()
            self.assertTrue(sd.opened.wait(1))
            self.backend.stop()
            worker.join(1)
            self.assertFalse(worker.is_alive())
        self.assertEqual(outcomes, [""])
        self.assertTrue(sd.stream.closed)
        self.assertEqual(self.listen_mock(events_for())[0], "complete words")

    def test_cancel_during_native_recognition_discards_result_and_holds_lock(self):
        entered, release = threading.Event(), threading.Event()
        sd = FakeSD(events_for())
        cancel = threading.Event()
        outcomes = []
        model = Mock()
        def transcribe(*args, **kwargs):
            entered.set()
            release.wait(1)
            return iter([SimpleNamespace(text="late words")]), None
        model.transcribe.side_effect = transcribe
        with patch.object(self.backend, "_audio_modules", return_value=(FakeNumpy, None, sd)), \
             patch.object(self.backend, "_new_detector", return_value=(FakeDetector(), 512)), \
             patch.object(self.backend, "_whisper_model", return_value=model), \
             patch("audio_backend.queue.Queue", return_value=DrivenQueue(sd)):
            worker = threading.Thread(target=lambda: outcomes.append(self.backend.listen(cancel, Mock())))
            worker.start()
            self.assertTrue(entered.wait(1))
            cancel.set()
            self.backend.stop()
            self.assertTrue(sd.stream.closed)
            self.assertTrue(self.backend._operation_lock.locked())
            release.set()
            worker.join(1)
        self.assertEqual(outcomes, [""])
        self.assertFalse(self.backend._operation_lock.locked())

    def test_model_load_explicitly_prohibits_downloads(self):
        factory = Mock(return_value=object())
        with patch.dict(sys.modules, {"faster_whisper": SimpleNamespace(WhisperModel=factory)}):
            first = self.backend._whisper_model()
            self.assertIs(self.backend._whisper_model(), first)
        factory.assert_called_once_with("tiny.en", device="cpu", compute_type="int8", local_files_only=True)

    def test_prepare_caches_dependencies_and_detector_without_opening_input(self):
        sd = FakeSD([])
        detector = FakeDetector()
        with patch.object(self.backend, "_audio_modules", return_value=(FakeNumpy, None, sd)) as modules, \
             patch.object(self.backend, "_new_detector", return_value=(detector, 512)) as factory:
            self.backend.prepare()
            self.backend.prepare()
        modules.assert_called_once()
        factory.assert_called_once()
        self.assertIsNone(sd.stream)

    def test_cached_detector_reset_and_recognition_failure_recover_next_turn(self):
        sd = FakeSD(events_for())
        detector = FakeDetector()
        model = Mock()
        model.transcribe.side_effect = [RuntimeError("Whisper failed"),
                                       (iter([SimpleNamespace(text="recovered")]), None)]
        with patch.object(self.backend, "_audio_modules", return_value=(FakeNumpy, None, sd)) as modules, \
             patch.object(self.backend, "_new_detector", return_value=(detector, 512)) as factory, \
             patch.object(self.backend, "_whisper_model", return_value=model), \
             patch("audio_backend.queue.Queue", side_effect=lambda **kwargs: DrivenQueue(sd)):
            self.backend.prepare()
            self.assertIsNone(sd.stream)
            with self.assertRaisesRegex(RuntimeError, "Whisper failed"):
                self.backend.listen(threading.Event(), Mock())
            self.assertTrue(sd.stream.closed)
            sd.events = deque(events_for())
            self.assertEqual(self.backend.listen(threading.Event(), Mock()), "recovered")
        modules.assert_called_once()
        factory.assert_called_once()
        self.assertEqual(detector.reset_count, 2)
        self.assertFalse(self.backend._operation_lock.locked())

    def test_detector_has_small_positive_gates_and_bounded_native_storage(self):
        config = SimpleNamespace(silero_vad=SimpleNamespace(window_size=512), sample_rate=0)
        factory = Mock()
        sherpa = SimpleNamespace(VadModelConfig=lambda: config, VoiceActivityDetector=factory)
        with patch.object(Path, "is_file", return_value=True):
            self.backend._new_detector(sherpa)
        self.assertEqual(config.sample_rate, 16000)
        self.assertEqual(config.silero_vad.min_speech_duration, 1 / 16000)
        self.assertEqual(config.silero_vad.min_silence_duration, 1 / 16000)
        factory.assert_called_once_with(config, buffer_size_in_seconds=2)


class FakeProcess:
    def __init__(self, code=None, pid=100001, stubborn=False):
        self.code = code
        self.pid = pid
        self.stubborn = stubborn
        self.stdout = io.BytesIO(b"silent mock bytes")
        self.stdin = self.stderr = None
        self.wait_count = 0

    def poll(self):
        return self.code

    def wait(self, timeout=None):
        self.wait_count += 1
        if self.code is None:
            raise subprocess.TimeoutExpired("mock", timeout)
        return self.code

    def signal(self, sig):
        if sig == 9 or not self.stubborn:
            self.code = -sig


class SpeechPipelineTests(unittest.TestCase):
    def setUp(self):
        # Model the Pi's POSIX API locally even when these fake-child tests run
        # on Windows. Replace only this module's references, not global os or
        # signal attributes. Never signal a real process from a pipeline test.
        for target, replacement in (
            ("audio_backend.os", SimpleNamespace(killpg=Mock(
                side_effect=AssertionError("Unexpected unmocked process signal")))),
            ("audio_backend.signal", SimpleNamespace(SIGTERM=15, SIGKILL=9)),
        ):
            platform_api = patch(target, replacement)
            platform_api.start()
            self.addCleanup(platform_api.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.backend = PiAudioBackend(Path(self.temp.name))
        self.backend.voice.parent.mkdir()
        self.backend.voice.write_bytes(b"mock model")
        Path(str(self.backend.voice) + ".json").write_text('{"audio":{"sample_rate":22050}}')
        preparation = patch.object(self.backend, "_prepare_input")
        preparation.start()
        self.addCleanup(preparation.stop)

    def test_playback_spawn_failure_reaps_already_started_synth(self):
        synth = FakeProcess()
        with patch("audio_backend.subprocess.Popen", side_effect=[synth, FileNotFoundError("aplay")]), \
             patch("audio_backend.os.killpg", side_effect=lambda pid, sig: synth.signal(sig)):
            with self.assertRaisesRegex(FileNotFoundError, "aplay"):
                self.backend.speak("mock only", threading.Event())
        self.assertIsNotNone(synth.code)
        self.assertGreater(synth.wait_count, 0)
        self.assertTrue(synth.stdout.closed)
        self.assertEqual(self.backend._processes, [])
        self.assertFalse(self.backend._operation_lock.locked())

    def test_early_playback_failure_terminates_synth_immediately(self):
        synth, playback = FakeProcess(), FakeProcess(code=1, pid=100002)
        with patch("audio_backend.subprocess.Popen", side_effect=[synth, playback]), \
             patch("audio_backend.os.killpg", side_effect=lambda pid, sig: synth.signal(sig)):
            with self.assertRaisesRegex(RuntimeError, "aplay=1"):
                self.backend.speak("mock only", threading.Event())
        self.assertIsNotNone(synth.code)
        self.assertEqual(self.backend._processes, [])

    def test_cleanup_escalates_to_kill_and_reaps_stubborn_child(self):
        synth = FakeProcess(stubborn=True)
        self.backend._track(synth)
        with patch("audio_backend.os.killpg", side_effect=lambda pid, sig: synth.signal(sig)) as signals:
            self.backend._cleanup_processes([synth])
        self.assertEqual([call.args[1] for call in signals.call_args_list], [15, 9])
        self.assertEqual(synth.wait_count, 2)
        self.assertEqual(self.backend._processes, [])

    def test_pre_cancel_never_starts_output(self):
        cancel = threading.Event()
        cancel.set()
        with patch("audio_backend.subprocess.Popen") as popen:
            self.backend.speak("mock only", cancel)
        popen.assert_not_called()

    def test_input_preparation_failure_preserves_manual_speech_fallback(self):
        synth, playback = FakeProcess(code=0), FakeProcess(code=0, pid=100002)
        with patch.object(self.backend, "_prepare_input", side_effect=RuntimeError("VAD failed")), \
             patch("audio_backend.subprocess.Popen", side_effect=[synth, playback]):
            self.backend.speak("mock manual reply", threading.Event())
            with self.assertRaisesRegex(RuntimeError, "VAD failed"):
                self.backend.listen(threading.Event(), Mock())
        self.assertGreater(synth.wait_count, 0)
        self.assertGreater(playback.wait_count, 0)
        self.assertFalse(self.backend._operation_lock.locked())

    def test_input_preparation_precedes_output_start(self):
        calls = []
        synth, playback = FakeProcess(code=0), FakeProcess(code=0, pid=100002)
        processes = deque([synth, playback])
        def launch(*args, **kwargs):
            calls.append("output")
            return processes.popleft()
        with patch.object(self.backend, "_prepare_input", side_effect=lambda: calls.append("prepare")), \
             patch("audio_backend.subprocess.Popen", side_effect=launch):
            self.backend.speak("mock only", threading.Event())
        self.assertEqual(calls, ["prepare", "output", "output"])

    def test_output_and_input_are_exclusive_and_cancel_recovers(self):
        synth, playback = FakeProcess(), FakeProcess(pid=100002)
        processes = {synth.pid: synth, playback.pid: playback}
        launched = threading.Event()
        def launch(*args, **kwargs):
            if not launched.is_set():
                launched.set()
                return synth
            return playback
        errors = []
        output_cancel = threading.Event()
        input_cancel = threading.Event()
        modules = Mock(side_effect=AssertionError("microphone attempted during playback"))
        def run_output():
            try:
                self.backend.speak("mock only", output_cancel)
            except Exception as error:
                errors.append(error)
        with patch("audio_backend.subprocess.Popen", side_effect=launch), \
             patch("audio_backend.os.killpg", side_effect=lambda pid, sig: processes[pid].signal(sig)), \
             patch.object(self.backend, "_audio_modules", modules):
            output = threading.Thread(target=run_output)
            output.start()
            self.assertTrue(launched.wait(1))
            listener = threading.Thread(target=lambda: self.backend.listen(input_cancel, Mock()))
            listener.start()
            time.sleep(.06)
            modules.assert_not_called()
            input_cancel.set()
            output_cancel.set()
            self.backend.stop()
            output.join(1)
            listener.join(1)
            self.assertFalse(output.is_alive())
            self.assertFalse(listener.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(self.backend._processes, [])
        self.assertFalse(self.backend._operation_lock.locked())


if __name__ == "__main__":
    unittest.main()
