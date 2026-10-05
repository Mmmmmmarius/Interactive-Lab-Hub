#!/usr/bin/env python3
"""Ask for a numerical input with Piper, then record the spoken answer.

Run with the Lab 3 virtual environment. Recordings stay outside the repository
unless --output explicitly selects another path.
AI assistance: Codex helped implement and test this script using the course
Piper demo and audio recording dependencies.
"""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import wave

import numpy as np
import sounddevice as sd

LAB_DIR = Path(__file__).resolve().parent.parent
VOICE = LAB_DIR / "voices" / "en_US-lessac-medium.onnx"
PROMPT = "Please say a five digit test ZIP code. You can make one up. Speak now."


def speak(text: str) -> None:
    sample_rate = json.loads(
        Path(str(VOICE) + ".json").read_text(encoding="utf-8")
    )["audio"]["sample_rate"]
    command = [sys.executable, "-m", "piper", "--model", str(VOICE),
               "--output-raw", "--", text]
    with subprocess.Popen(command, stdout=subprocess.PIPE) as synth:
        assert synth.stdout is not None
        try:
            playback = subprocess.run(
                ["aplay", "-r", str(sample_rate), "-f", "S16_LE", "-t", "raw", "-"],
                stdin=synth.stdout,
            )
        finally:
            synth.stdout.close()
        synthesis_code = synth.wait()
    if synthesis_code:
        raise subprocess.CalledProcessError(synthesis_code, command)
    playback.check_returncode()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=6.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 0 < args.seconds <= 60:
        parser.error("--seconds must be between 0 and 60")
    if not VOICE.is_file():
        parser.error(f"Piper voice is missing: {VOICE}; run the course setup first")
    output = args.output or (
        Path.home() / "course-setup-checks" / "lab3-numeric"
        / f"answer-{datetime.now():%Y%m%d-%H%M%S-%f}.wav"
    )
    output = output.expanduser().resolve()
    if output.exists():
        parser.error(f"Output already exists: {output}; choose a new path")
    print(f"Prompt: {PROMPT}", flush=True)
    speak(PROMPT)
    print(f"Recording for {args.seconds:g} seconds...", flush=True)
    rate = 16000
    audio = sd.rec(round(args.seconds * rate), samplerate=rate,
                   channels=1, dtype="int16")
    sd.wait()
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as file:
        with wave.open(file, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(rate)
            wav.writeframes(audio.astype("<i2", copy=False).tobytes())
    print(f"Saved recording: {output}")
    print(f"Duration: {len(audio) / rate:.2f}s; "
          f"peak: {np.abs(audio.astype(np.int32)).max() / 32768:.4f}")


if __name__ == "__main__":
    main()
