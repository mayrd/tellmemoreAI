#!/usr/bin/env python3
"""Kokoro TTS adapter — drop-in replacement for edge-tts / chirp_tts CLIs.

Pure stdlib. Locates a Python interpreter with kokoro installed (env
KOKORO_PYTHON or KOKORO_VENV), runs kokoro_run.py as a subprocess (WAV out),
transcodes to MP3 via ffmpeg and reports duration via ffprobe.

Usage:
    python3 kokoro_tts.py --voice af_heart --text "Hello world" --output out.mp3
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

DEFAULT_VOICE = "af_heart"


def _find_kokoro_python():
    env = os.environ.get("KOKORO_PYTHON", "").strip()
    if env:
        return env
    venv = os.environ.get("KOKORO_VENV", "").strip()
    if venv:
        candidate = os.path.join(venv, "bin", "python")
        if os.path.exists(candidate):
            return candidate
    # Common convention: KOKORO_VENV_HOME/<name>/bin/python
    home = os.environ.get("KOKORO_VENV_HOME", "").strip()
    if home and os.path.isdir(home):
        for name in sorted(os.listdir(home)):
            candidate = os.path.join(home, name, "bin", "python")
            if os.path.exists(candidate):
                return candidate
    return None


def synthesize(text, voice=DEFAULT_VOICE, output_path=None, timeout=300):
    """Synthesize text with a local Kokoro voice.

    Returns (audio_path, duration_seconds). Raises RuntimeError with install
    instructions if no kokoro-enabled Python is configured.
    """
    python = _find_kokoro_python()
    if python is None:
        raise RuntimeError(
            "Kokoro TTS selected but no kokoro Python found. Set KOKORO_PYTHON=/path/to/kokoro-venv/bin/python "
            "(or KOKORO_VENV=/path/to/kokoro-venv). Install: uv venv kokoro-env && uv pip install --python "
            "kokoro-env/bin/python kokoro soundfile numpy && uv pip install --python kokoro-env/bin/python "
            "https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/"
            "en_core_web_sm-3.8.0-py3-none-any.whl"
        )

    if output_path is None:
        fd, output_path = tempfile.mkstemp(prefix="kokoro_", suffix=".mp3")
        os.close(fd)

    run_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kokoro_run.py")
    wav_path = output_path + ".wav"
    try:
        result = subprocess.run(
            [python, run_py, "--text", text, "--voice", voice, "--output", wav_path],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0:
            raise RuntimeError(f"kokoro failed (rc={result.returncode}): {result.stderr.strip() or result.stdout.strip()}")
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", wav_path, "-b:a", "192k", output_path],
            check=True, capture_output=True, text=True,
        )
    finally:
        try:
            os.remove(wav_path)
        except OSError:
            pass

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", output_path],
        capture_output=True, text=True,
    )
    duration = float(probe.stdout.strip()) if probe.returncode == 0 else 0.0
    return output_path, duration


def main():
    ap = argparse.ArgumentParser(description="Kokoro TTS (local)")
    ap.add_argument("--voice", default=DEFAULT_VOICE, help=f"Kokoro voice (default: {DEFAULT_VOICE})")
    ap.add_argument("--text", required=True)
    ap.add_argument("--output", required=True, help="Output MP3 path")
    args = ap.parse_args()
    try:
        path, duration = synthesize(args.text, voice=args.voice, output_path=args.output)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    print(f"OK {args.voice}: {duration:.1f}s -> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
