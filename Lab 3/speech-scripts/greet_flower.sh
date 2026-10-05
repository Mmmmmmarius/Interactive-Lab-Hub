#!/usr/bin/env bash
# Personal Lab 3 greeting, using Piper streaming audio.
# Dialogue adapted from manaporkun/talking-flower, character/SOUL.md,
# "After being ignored", commit 5fac8c241850c7d59b2b3dfecea38fe978713f6c.
# Source: https://github.com/manaporkun/talking-flower/blob/5fac8c241850c7d59b2b3dfecea38fe978713f6c/character/SOUL.md
# Source license: MIT; Copyright (c) 2026 Orkun.
# Adaptation: add the user's name and their chosen "Kept you waiting, huh?".
# AI assistance: Codex helped implement and verify this shell script.

set -euo pipefail

usage() {
    printf 'Usage: %s [NAME]\nDefault name: Elias\n' "$(basename "$0")"
}

if [[ $# -gt 1 ]]; then
    usage >&2
    exit 2
fi
if [[ ${1-} == '--help' || ${1-} == '-h' ]]; then
    usage
    exit 0
fi

NAME="${1-Elias}"
if [[ -z ${NAME//[[:space:]]/} ]]; then
    printf 'Please provide a nonempty name.\n' >&2
    exit 2
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
LAB_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
PYTHON="$LAB_DIR/.venv/bin/python3"
VOICE="$LAB_DIR/voices/en_US-lessac-medium.onnx"

if [[ ! -x "$PYTHON" || ! -r "$VOICE" || ! -r "$VOICE.json" ]]; then
    printf 'Lab 3 Python environment or Piper voice is missing. Run the course setup first.\n' >&2
    exit 1
fi
if ! command -v aplay >/dev/null 2>&1; then
    printf 'aplay is missing. Install the course audio dependencies first.\n' >&2
    exit 1
fi

RATE="$("$PYTHON" -X utf8 -c 'import json, sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["audio"]["sample_rate"])' "$VOICE.json")"
GREETING="Oh! You're back, $NAME! Kept you waiting, huh? I was starting to think you forgot I existed."
printf 'Greeting: %s\n' "$GREETING"

"$PYTHON" -X utf8 -m piper --model "$VOICE" --output-raw -- "$GREETING" \
    | aplay -r "$RATE" -c 1 -f S16_LE -t raw -
