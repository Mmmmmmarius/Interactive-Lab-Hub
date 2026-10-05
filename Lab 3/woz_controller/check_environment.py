#!/usr/bin/env python3
"""Read-only Pi prerequisites check: no model load, recording, or playback."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import sys


def inspect(lab: Path) -> dict:
    modules = {name: importlib.util.find_spec(name) is not None
               for name in ("numpy", "sherpa_onnx", "sounddevice", "faster_whisper", "piper")}
    voice = lab / "voices/en_US-lessac-medium.onnx"
    vad = lab / "models/silero_vad.onnx"
    config = Path(str(voice) + ".json")
    files = {str(path): path.is_file() for path in (voice, vad, config)}
    sample_rate, error = None, None
    if config.is_file():
        try:
            sample_rate = json.loads(config.read_text())["audio"]["sample_rate"]
        except (ValueError, KeyError, TypeError) as exc:
            error = f"Voice config error: {exc}"
    playback = shutil.which("aplay")
    return {"python": sys.version.split()[0], "lab_dir": str(lab),
            "packages": modules, "files": files, "aplay": playback,
            "input_format": "16000 Hz mono float32", "voice_sample_rate": sample_rate,
            "error": error, "offline_whisper_cache": "not loaded; verify with a live local turn",
            "ok": all(modules.values()) and all(files.values()) and bool(playback) and error is None}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lab-dir", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    report = inspect(args.lab_dir.resolve())
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
