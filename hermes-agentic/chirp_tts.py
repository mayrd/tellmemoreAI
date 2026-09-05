#!/usr/bin/env python3
"""Chirp 3 HD TTS via Gemini API — drop-in replacement for edge-tts CLI.

Pure stdlib (urllib) so it runs with any Python 3.10+ interpreter.
Requires GEMINI_API_KEY in /opt/data/.env (or env var).

Usage:
    python3 chirp_tts.py --voice Puck --text "Hello world" --output out.mp3
    python3 chirp_tts.py --voice Puck --text "..." --output out.mp3 --model gemini-3.1-flash-tts-preview

Output: MP3 (16-bit PCM from API, transcoded via ffmpeg). Prints the audio
duration in seconds to stdout on success.
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile

DEFAULT_MODEL = "gemini-3.1-flash-tts-preview"


def _load_key():
    key = os.environ.get("GEMINI_API_KEY", "")
    if key:
        return key
    for path in ("/opt/data/.env", os.path.expanduser("~/.env")):
        try:
            with open(path) as f:
                for line in f:
                    if line.startswith("GEMINI_API_KEY="):
                        return line.split("=", 1)[1].strip()
        except OSError:
            continue
    raise RuntimeError("GEMINI_API_KEY not found (env or /opt/data/.env)")


def synthesize(text, voice="Puck", output_path=None, model=DEFAULT_MODEL, timeout=120):
    """Synthesize text with a Chirp 3 HD voice via the Gemini API.

    Returns (audio_path, duration_seconds).
    """
    import urllib.request
    import urllib.error

    key = _load_key()
    if output_path is None:
        fd, output_path = tempfile.mkstemp(prefix="chirp_", suffix=".mp3")
        os.close(fd)

    payload = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}},
        },
    }
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.load(resp)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Gemini TTS HTTP {e.code}: {e.read().decode()[:400]}")

    try:
        parts = result["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError):
        raise RuntimeError(f"Gemini TTS unexpected response: {json.dumps(result)[:400]}")

    raw = None
    for part in parts:
        if "inlineData" in part:
            raw = base64.b64decode(part["inlineData"]["data"])
            break
    if raw is None:
        raise RuntimeError(f"Gemini TTS: no audio in response: {json.dumps(result)[:400]}")

    # API returns raw 16-bit PCM (audio/l16; rate=24000; channels=1) -> MP3 via ffmpeg
    pcm_path = output_path + ".pcm"
    with open(pcm_path, "wb") as f:
        f.write(raw)
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error",
             "-f", "s16le", "-ar", "24000", "-ac", "1",
             "-i", pcm_path, "-b:a", "192k", output_path],
            check=True, capture_output=True, text=True,
        )
    finally:
        try:
            os.remove(pcm_path)
        except OSError:
            pass

    # Duration via ffprobe
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", output_path],
        capture_output=True, text=True,
    )
    duration = float(probe.stdout.strip()) if probe.returncode == 0 else 0.0
    return output_path, duration


def main():
    ap = argparse.ArgumentParser(description="Chirp 3 HD TTS via Gemini API")
    ap.add_argument("--voice", default="Puck", help="Chirp 3 voice name (default: Puck)")
    ap.add_argument("--text", required=True, help="Text to synthesize")
    ap.add_argument("--output", required=True, help="Output MP3 path")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    args = ap.parse_args()

    path, duration = synthesize(args.text, voice=args.voice, output_path=args.output, model=args.model)
    print(f"OK {args.voice}: {duration:.1f}s -> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
