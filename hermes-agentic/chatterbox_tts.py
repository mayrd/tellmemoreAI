#!/usr/bin/env python3
"""Chatterbox TTS adapter — drop-in replacement for edge-tts / chirp_tts / kokoro_tts.

Pure stdlib. Locates a Python interpreter with chatterbox-tts installed (env
CHATTERBOX_PYTHON or CHATTERBOX_VENV), runs chatterbox_run.py as a subprocess
(WAV out), transcodes to MP3 via ffmpeg and reports duration via ffprobe.

Chatterbox is a GPU-class model: on plain CPUs it runs at ~14x realtime (turbo)
to ~65x realtime (500M) — fine for occasional use, impractical for daily batch
production without CUDA. Model selection: CHATTERBOX_MODEL=turbo|default,
CHATTERBOX_DEVICE=cpu|cuda. Voice cloning: pass --voice /path/to/ref.wav
(10s+ of the target voice); default is the model's built-in voice.

Usage:
    python3 chatterbox_tts.py --text "Hello world" --output out.mp3
"""

import argparse
import os
import subprocess
import sys
import tempfile


def _find_chatterbox_python():
    env = os.environ.get("CHATTERBOX_PYTHON", "").strip()
    if env:
        return env
    venv = os.environ.get("CHATTERBOX_VENV", "").strip()
    if venv:
        candidate = os.path.join(venv, "bin", "python")
        if os.path.exists(candidate):
            return candidate
    return None


def synthesize(text, voice=None, output_path=None, timeout=1800):
    """Synthesize text with Chatterbox (built-in voice or --voice ref WAV).

    Returns (audio_path, duration_seconds). Raises RuntimeError with install
    instructions if no chatterbox-enabled Python is configured.
    """
    python = _find_chatterbox_python()
    if python is None:
        raise RuntimeError(
            "Chatterbox TTS selected but no chatterbox Python found. Set "
            "CHATTERBOX_PYTHON=/path/to/chatterbox-venv/bin/python (or CHATTERBOX_VENV=...). "
            "Install: uv venv chatterbox-env && uv pip install --python chatterbox-env/bin/python chatterbox-tts. "
            "A CUDA GPU is strongly recommended (CPU is 14-65x realtime)."
        )

    if output_path is None:
        fd, output_path = tempfile.mkstemp(prefix="chatterbox_", suffix=".mp3")
        os.close(fd)

    run_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chatterbox_run.py")
    wav_path = output_path + ".wav"
    cmd = [python, run_py, "--text", text, "--output", wav_path]
    if voice and os.path.exists(voice):
        cmd += ["--ref", voice]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            raise RuntimeError(f"chatterbox failed (rc={result.returncode}): {result.stderr.strip() or result.stdout.strip()}")
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
    ap = argparse.ArgumentParser(description="Chatterbox TTS (local, GPU recommended)")
    ap.add_argument("--voice", default=None, help="Optional reference WAV for voice cloning")
    ap.add_argument("--text", required=True)
    ap.add_argument("--output", required=True, help="Output MP3 path")
    args = ap.parse_args()
    try:
        path, duration = synthesize(args.text, voice=args.voice, output_path=args.output)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    print(f"OK: {duration:.1f}s -> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
