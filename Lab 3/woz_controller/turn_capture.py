"""Pure frame-timed turn capture, used by the Pi backend and simulated tests.

Times are seconds since microphone start, measured when audio was captured.
The inclusive start deadline applies to speech onset only. Onset confirmation
may arrive during ``onset_grace``; it does not extend the allowed onset time.
No total utterance deadline is imposed after speech starts.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import math
from typing import Any


@dataclass(frozen=True)
class AudioFrame:
    start: float
    end: float
    samples: Any


class TurnCapture:
    def __init__(
        self, *, start_timeout: float = 2.0, min_silence: float = 0.8,
        onset_grace: float = 0.0, pre_roll: float = 0.25,
    ) -> None:
        for name, value in (("start_timeout", start_timeout), ("min_silence", min_silence),
                            ("onset_grace", onset_grace), ("pre_roll", pre_roll)):
            if not math.isfinite(value) or value < 0 or (name == "min_silence" and value == 0):
                raise ValueError(f"{name} must be finite and {'positive' if name == 'min_silence' else 'nonnegative'}")
        self.start_timeout = start_timeout
        self.min_silence = min_silence
        self.onset_grace = onset_grace
        self.pre_roll = pre_roll
        self.started = False
        self.done = False
        self.timed_out = False
        self.onset: float | None = None
        self.last_frame_end = 0.0
        self._last_speech_end = 0.0
        self._pre_roll: deque[AudioFrame] = deque()
        self.samples: list[Any] = []

    def feed(self, frame: AudioFrame, *, speech: bool, speech_onset: float | None = None) -> None:
        if self.done:
            return
        if (not math.isfinite(frame.start) or not math.isfinite(frame.end)
                or frame.start < 0 or frame.end <= frame.start
                or frame.start < self.last_frame_end - 1e-7):
            raise ValueError("Audio frames must have ordered, finite capture timestamps")
        self.last_frame_end = frame.end
        if speech_onset is not None and (
            not math.isfinite(speech_onset) or speech_onset < 0 or speech_onset > frame.end
        ):
            raise ValueError("Speech onset must be a finite capture time within the received audio")
        if not self.started:
            self._pre_roll.append(frame)
            while self._pre_roll and self._pre_roll[0].end < frame.end - self.pre_roll:
                self._pre_roll.popleft()
            onset = frame.start if speech_onset is None else speech_onset
            if speech and onset <= self.start_timeout + 1e-9:
                self.started = True
                self.onset = onset
                self.samples.extend(previous.samples for previous in self._pre_roll)
                self._pre_roll.clear()
                self._last_speech_end = frame.end
            elif frame.end > self.start_timeout + self.onset_grace + 1e-9:
                self.done = self.timed_out = True
                self._pre_roll.clear()
            return
        self.samples.append(frame.samples)
        if speech:
            self._last_speech_end = frame.end
        elif frame.end - self._last_speech_end >= self.min_silence - 1e-9:
            self.done = True
