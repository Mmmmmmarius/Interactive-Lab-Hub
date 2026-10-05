#!/usr/bin/env python3
"""Offline audio backends. Importing this module never opens an audio device."""

from __future__ import annotations

from collections import deque
from contextlib import contextmanager
import json
import os
from pathlib import Path
import queue
import signal
import subprocess
import sys
import threading
import time
from typing import Any, Callable, Iterable, Iterator

from turn_capture import AudioFrame, TurnCapture


class DryRunBackend:
    """Accelerated, silent simulation with a finite transcript queue."""

    def __init__(self, delay: float = 0.05, transcripts: Iterable[str] | None = None) -> None:
        self.delay = max(0.0, delay)
        self._lock = threading.Lock()
        self._generation = 0
        self._transcripts: deque[str] = deque()
        initial = transcripts if transcripts is not None else [os.environ.get(
            "TALKING_BOX_DRY_TRANSCRIPT", "It is too early for this much confidence.",
        )]
        for transcript in initial:
            self.queue_transcript(transcript)

    def queue_transcript(self, text: str) -> None:
        """Add one simulated turn; an empty string represents no response."""
        if not isinstance(text, str) or len(text) > 10000:
            raise ValueError("Simulated transcript must be a string of up to 10000 characters")
        with self._lock:
            self._transcripts.append(text.strip())

    def stop(self) -> None:
        with self._lock:
            self._generation += 1

    def _wait(self, cancel: threading.Event) -> bool:
        with self._lock:
            generation = self._generation
        deadline = time.monotonic() + self.delay
        while not cancel.is_set():
            with self._lock:
                if generation != self._generation:
                    return False
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return True
            cancel.wait(min(0.05, remaining))
        return False

    def speak(self, text: str, cancel: threading.Event) -> None:
        del text
        self._wait(cancel)

    def listen(
        self, cancel: threading.Event, on_thinking: Callable[[], None], *,
        start_timeout: float = 2.0, min_silence: float = 0.8,
        on_started: Callable[[], None] | None = None,
    ) -> str:
        TurnCapture(start_timeout=start_timeout, min_silence=min_silence)
        if not self._wait(cancel):
            return ""
        with self._lock:
            transcript = self._transcripts.popleft() if self._transcripts else ""
        if not transcript:
            return ""
        if on_started is not None:
            on_started()
        if cancel.is_set():
            return ""
        on_thinking()
        return "" if cancel.is_set() else transcript


class PiAudioBackend:
    """Piper output and 16 kHz mono, VAD-ended local Whisper input.

    An operation lock keeps the microphone closed throughout output and decoding.
    Cancellation of native Whisper takes effect when its current call returns;
    its result is discarded, and the lock stays held until that happens.
    """

    def __init__(self, lab_dir: Path, model_name: str = "tiny.en") -> None:
        self.lab_dir = lab_dir.resolve()
        self.model_name = model_name
        self.voice = self.lab_dir / "voices" / "en_US-lessac-medium.onnx"
        self.vad_model = self.lab_dir / "models" / "silero_vad.onnx"
        self._operation_lock = threading.Lock()
        self._resource_lock = threading.Lock()
        self._processes: list[subprocess.Popen[bytes]] = []
        self._active_stream: Any = None
        self._operation_stop: threading.Event | None = None
        self._whisper: Any = None
        self._prepared_audio: tuple[Any, Any, Any, Any, int] | None = None

    @contextmanager
    def _operation(self, cancel: threading.Event) -> Iterator[threading.Event | None]:
        while not cancel.is_set():
            if self._operation_lock.acquire(timeout=0.05):
                break
        else:
            yield None
            return
        stopped = threading.Event()
        try:
            with self._resource_lock:
                self._operation_stop = stopped
            yield stopped
        finally:
            with self._resource_lock:
                self._operation_stop = None
            self._operation_lock.release()

    @staticmethod
    def _cancelled(cancel: threading.Event, stopped: threading.Event) -> bool:
        return cancel.is_set() or stopped.is_set()

    def _track(self, process: subprocess.Popen[bytes]) -> None:
        with self._resource_lock:
            self._processes.append(process)

    @staticmethod
    def _signal_process(process: subprocess.Popen[bytes], sig: int) -> None:
        if process.poll() is not None:
            return
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            pass
        except OSError:
            try:
                (process.kill if sig == signal.SIGKILL else process.terminate)()
            except ProcessLookupError:
                pass

    def stop(self) -> None:
        """Request cancellation without waiting for native recognition to finish."""
        with self._resource_lock:
            stopped = self._operation_stop
            stream = self._active_stream
            processes = list(self._processes)
            if stopped is not None:
                stopped.set()
        if stream is not None:
            try:
                stream.abort()
            except Exception:
                # Cleanup in the operation thread still closes the stream.
                pass
        for process in reversed(processes):
            self._signal_process(process, signal.SIGTERM)

    def _cleanup_processes(self, processes: list[subprocess.Popen[bytes]]) -> None:
        """Terminate, kill if necessary, and reap every owned pipeline child."""
        errors = []
        for process in reversed(processes):
            self._signal_process(process, signal.SIGTERM)
        for process in reversed(processes):
            try:
                try:
                    process.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    self._signal_process(process, signal.SIGKILL)
                    process.wait(timeout=1.0)
            except Exception as error:
                errors.append(error)
            finally:
                for name in ("stdin", "stdout", "stderr"):
                    pipe = getattr(process, name, None)
                    if pipe is not None:
                        try:
                            pipe.close()
                        except Exception as error:
                            errors.append(error)
        with self._resource_lock:
            # Keep any unreaped child visible for a subsequent stop attempt.
            self._processes = [p for p in self._processes if p not in processes or p.poll() is None]
        if errors:
            raise RuntimeError(f"Could not reap audio pipeline child: {errors[0]}") from errors[0]

    def speak(self, text: str, cancel: threading.Event) -> None:
        with self._operation(cancel) as stopped:
            if stopped is None or self._cancelled(cancel, stopped):
                return
            # Load input dependencies/model before output, leaving only a reset
            # and device-open step between the end of playback and listening.
            try:
                self._prepare_input()
            except Exception:
                # Input failure must not prevent a manual/scripted Piper reply.
                # listen() retries preparation and reports the actual failure.
                pass
            if self._cancelled(cancel, stopped):
                return
            if not self.voice.is_file():
                raise FileNotFoundError(f"Piper voice is missing: {self.voice}")
            voice_config = Path(str(self.voice) + ".json")
            sample_rate = json.loads(voice_config.read_text(encoding="utf-8"))["audio"]["sample_rate"]
            processes: list[subprocess.Popen[bytes]] = []
            try:
                synth = subprocess.Popen(
                    [sys.executable, "-m", "piper", "--model", str(self.voice),
                     "--output-raw", "--", text],
                    stdout=subprocess.PIPE, start_new_session=True,
                )
                processes.append(synth)
                self._track(synth)
                if synth.stdout is None:
                    raise RuntimeError("Piper did not provide its output pipe")
                if self._cancelled(cancel, stopped):
                    return
                playback = subprocess.Popen(
                    ["aplay", "-r", str(sample_rate), "-f", "S16_LE", "-t", "raw", "-"],
                    stdin=synth.stdout, start_new_session=True,
                )
                processes.append(playback)
                self._track(playback)
                synth.stdout.close()
                while True:
                    if self._cancelled(cancel, stopped):
                        return
                    synth_code, playback_code = synth.poll(), playback.poll()
                    if synth_code not in (None, 0) or playback_code not in (None, 0):
                        raise RuntimeError(
                            f"Speech pipeline failed: piper={synth_code}, aplay={playback_code}"
                        )
                    if synth_code is not None and playback_code is not None:
                        return
                    cancel.wait(0.05)
            finally:
                self._cleanup_processes(processes)

    @staticmethod
    def _audio_modules() -> tuple[Any, Any, Any]:
        import numpy as np
        import sherpa_onnx
        import sounddevice as sd
        return np, sherpa_onnx, sd

    def _new_detector(self, sherpa_onnx: Any) -> tuple[Any, int]:
        if not self.vad_model.is_file():
            raise FileNotFoundError(f"Silero VAD model is missing: {self.vad_model}")
        config = sherpa_onnx.VadModelConfig()
        config.silero_vad.model = str(self.vad_model)
        config.sample_rate = 16000
        # Native gating confirms onset over two windows. The shared helper owns
        # the endpoint duration; tiny positive native values satisfy validation.
        config.silero_vad.min_speech_duration = 1 / config.sample_rate
        config.silero_vad.min_silence_duration = 1 / config.sample_rate
        detector = sherpa_onnx.VoiceActivityDetector(config, buffer_size_in_seconds=2)
        return detector, config.silero_vad.window_size

    def _prepare_input(self) -> tuple[Any, Any, Any, Any, int]:
        if self._prepared_audio is None:
            np, sherpa_onnx, sd = self._audio_modules()
            detector, window_size = self._new_detector(sherpa_onnx)
            self._prepared_audio = np, sherpa_onnx, sd, detector, window_size
        return self._prepared_audio

    def prepare(self, cancel: threading.Event | None = None) -> None:
        """Preload local input dependencies/model without opening any device."""
        cancel = cancel if cancel is not None else threading.Event()
        with self._operation(cancel) as stopped:
            if stopped is not None and not self._cancelled(cancel, stopped):
                self._prepare_input()

    def _capture_audio(
        self, np: Any, sd: Any, detector: Any, window_size: int,
        cancel: threading.Event, stopped: threading.Event,
        start_timeout: float, min_silence: float,
        on_started: Callable[[], None] | None,
    ) -> Any:
        sample_rate = 16000
        duration = window_size / sample_rate
        capture = TurnCapture(
            start_timeout=start_timeout, min_silence=min_silence,
            onset_grace=2 * duration, pre_roll=0.25,
        )
        frames: queue.Queue[AudioFrame] = queue.Queue(maxsize=64)
        callback_errors: list[Exception] = []
        finished = threading.Event()
        origin: float | None = None
        fallback_time = 0.0

        def callback(indata: Any, count: int, timing: Any, status: Any) -> None:
            nonlocal fallback_time, origin
            try:
                if self._cancelled(cancel, stopped):
                    raise sd.CallbackAbort
                if status:
                    raise RuntimeError(f"Microphone capture failed: {status}")
                adc_time = float(timing.inputBufferAdcTime)
                if adc_time:
                    if origin is None:
                        origin = adc_time - fallback_time
                    frame_start = adc_time - origin
                else:
                    frame_start = fallback_time
                frame_end = frame_start + count / sample_rate
                fallback_time = frame_end
                frames.put_nowait(AudioFrame(frame_start, frame_end, indata[:, 0].copy()))
            except sd.CallbackAbort:
                raise
            except Exception as error:
                callback_errors.append(error)
                raise sd.CallbackAbort

        stream = None
        try:
            stream = sd.InputStream(
                samplerate=sample_rate, channels=1, dtype="float32",
                blocksize=window_size, callback=callback, finished_callback=finished.set,
            )
            with self._resource_lock:
                self._active_stream = stream
            wall_start = time.monotonic()
            if self._cancelled(cancel, stopped):
                return None
            stream.start()
            prior_speech = False
            while not self._cancelled(cancel, stopped):
                if callback_errors:
                    raise callback_errors[0]
                try:
                    frame = frames.get(timeout=0.05)
                except queue.Empty:
                    if self._cancelled(cancel, stopped):
                        return None
                    if callback_errors:
                        raise callback_errors[0]
                    if finished.is_set() or not stream.active:
                        raise RuntimeError("Microphone stream stopped before a complete turn")
                    if time.monotonic() - wall_start > capture.last_frame_end + 1.0:
                        raise RuntimeError("Microphone stopped delivering audio frames")
                    continue
                samples = np.ascontiguousarray(frame.samples, dtype=np.float32)
                detector.accept_waveform(samples)
                speech = detector.is_speech_detected()
                # The native segment sample offset includes onset pre-roll and
                # supports both V4 and V5 overlapping windows. It is estimated
                # at VAD-window precision, not an exact phoneme timestamp.
                onset = max(0.0, detector.current_segment.start / sample_rate) if speech and not prior_speech else None
                was_started = capture.started
                capture.feed(frame, speech=speech, speech_onset=onset)
                prior_speech = speech
                # Release native segment storage without resetting model state.
                # Complete audio lives in TurnCapture, avoiding a native buffer
                # cap or maximum-utterance threshold change on long turns.
                if speech:
                    detector.flush()
                while not detector.empty():
                    detector.pop()
                if capture.started and not was_started and on_started is not None:
                    on_started()
                if capture.done:
                    return np.concatenate(capture.samples) if capture.started else None
            return None
        finally:
            if stream is not None:
                try:
                    stream.abort()
                finally:
                    try:
                        stream.close()
                    finally:
                        with self._resource_lock:
                            if self._active_stream is stream:
                                self._active_stream = None

    def _whisper_model(self) -> Any:
        if self._whisper is None:
            from faster_whisper import WhisperModel
            self._whisper = WhisperModel(
                self.model_name, device="cpu", compute_type="int8", local_files_only=True,
            )
        return self._whisper

    def listen(
        self, cancel: threading.Event, on_thinking: Callable[[], None], *,
        start_timeout: float = 2.0, min_silence: float = 0.8,
        on_started: Callable[[], None] | None = None,
    ) -> str:
        TurnCapture(start_timeout=start_timeout, min_silence=min_silence)
        with self._operation(cancel) as stopped:
            if stopped is None or self._cancelled(cancel, stopped):
                return ""
            np, _sherpa_onnx, sd, detector, window_size = self._prepare_input()
            detector.reset()
            audio = self._capture_audio(
                np, sd, detector, window_size, cancel, stopped,
                start_timeout, min_silence, on_started,
            )
            if self._cancelled(cancel, stopped) or audio is None:
                return ""
            on_thinking()
            if self._cancelled(cancel, stopped):
                return ""
            model = self._whisper_model()
            if self._cancelled(cancel, stopped):
                return ""
            segments, _info = model.transcribe(audio, beam_size=5, language="en")
            words = []
            for segment in segments:
                if self._cancelled(cancel, stopped):
                    return ""
                words.append(segment.text.strip())
            if self._cancelled(cancel, stopped):
                return ""
            result = " ".join(words).strip()
            if not result:
                raise RuntimeError("Speech captured but recognizer returned no words")
            return result
