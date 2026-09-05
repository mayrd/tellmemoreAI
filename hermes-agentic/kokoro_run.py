#!/usr/bin/env python3
"""Kokoro TTS synthesis helper — run with a Python interpreter that has kokoro installed.

This script is invoked as a subprocess by kokoro_tts.py (which runs with any plain
Python). Keeping the heavy dependencies (torch, kokoro, spaCy) in a separate venv
means the main pipeline scripts stay lightweight.

Installation (once, into a venv of your choice):
    uv venv kokoro-env && uv pip install --python kokoro-env/bin/python kokoro soundfile numpy
    uv pip install --python kokoro-env/bin/python \\
        https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl
    # optional but recommended for out-of-dictionary English words: install espeak-ng

Usage (normally called by kokoro_tts.py, not by hand):
    kokoro_run.py --text "Hello world" --voice af_heart --output out.wav
"""

import argparse
import sys

LANG_CODE = "a"  # 'a' = American English (kokoro lang codes: a/b/e/f/h/i/j/p/z)


def main():
    ap = argparse.ArgumentParser(description="Kokoro TTS synthesis (EN)")
    ap.add_argument("--text", required=True, help="Text to synthesize")
    ap.add_argument("--voice", default="af_heart", help="Kokoro voice (e.g. af_heart, am_michael, bf_emma)")
    ap.add_argument("--output", required=True, help="Output WAV path")
    args = ap.parse_args()

    try:
        from kokoro import KPipeline
        import soundfile as sf
    except ImportError as e:
        print(f"ERROR: kokoro/soundfile not installed for {sys.executable}: {e}", file=sys.stderr)
        sys.exit(3)
    try:
        import numpy as np  # noqa: F401  (imported early so the concatenate below never surprises)
    except ImportError as e:
        print(f"ERROR: numpy missing: {e}", file=sys.stderr)
        sys.exit(4)
    try:
        import spacy  # noqa: F401
        import en_core_web_sm  # noqa: F401
    except ImportError:
        print("ERROR: spaCy model en_core_web_sm missing — install it (see module docstring).", file=sys.stderr)
        sys.exit(5)

    pipe = KPipeline(lang_code=LANG_CODE)
    chunks = []
    for _gs, _ps, audio in pipe(args.text, voice=args.voice):
        chunks.append(audio)
    audio = np.concatenate(chunks) if len(chunks) > 1 else chunks[0]
    sf.write(args.output, audio, 24000)
    print(f"OK {args.voice}: {len(audio) / 24000:.1f}s -> {args.output}")


if __name__ == "__main__":
    sys.exit(main())
