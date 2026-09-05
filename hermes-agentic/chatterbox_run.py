#!/usr/bin/env python3
"""Chatterbox TTS synthesis helper — run with a Python that has chatterbox-tts installed.

Invoked as a subprocess by chatterbox_tts.py. Heavy deps (torch, torchaudio,
transformers) live in a separate venv, so the main pipeline stays lightweight.

Setup (once, into a venv of your choice):
    uv venv chatterbox-env
    uv pip install --python chatterbox-env/bin/python chatterbox-tts

Model selection via env:
    CHATTERBOX_MODEL=turbo   (default) — ResembleAI/chatterbox-turbo (350M, 1 step, narration-tuned)
    CHATTERBOX_MODEL=default           — ResembleAI/chatterbox (500M, 10 steps, highest quality)
    CHATTERBOX_DEVICE=cpu    (default) or cuda (recommended — CPU is 10-60x realtime)

The proprietary watermarker (perth) is not bundled with the public package; this
script auto-patches the installed chatterbox module to fall back to the bundled
DummyWatermarker (idempotent, no-op watermark).

Voice cloning: pass --ref /path/to/reference.wav (10s+ clean speech of the target
voice). Without it, the model's built-in voice is used.

Usage (normally called by chatterbox_tts.py, not by hand):
    chatterbox_run.py --text "Hello world" [--ref voice.wav] --output out.wav
"""

import argparse
import os
import sys


def _ensure_watermarker_patch():
    """Replace the proprietary perth watermarker with the bundled dummy when absent."""
    try:
        import perth
    except ImportError:
        return  # older package layout without perth at all
    if perth.PerthImplicitWatermarker is not None:
        return  # real watermarker available
    try:
        import chatterbox
    except ImportError:
        return
    base = os.path.dirname(chatterbox.__file__)
    for fname in ("tts.py", "tts_turbo.py"):
        path = os.path.join(base, fname)
        try:
            with open(path) as f:
                src = f.read()
        except OSError:
            continue
        if "PerthImplicitWatermarker()" in src and "or perth.DummyWatermarker" not in src:
            src = src.replace(
                "perth.PerthImplicitWatermarker()",
                "(perth.PerthImplicitWatermarker or perth.DummyWatermarker)()",
            )
            with open(path, "w") as f:
                f.write(src)
            print(f"patched watermarker fallback in {fname}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description="Chatterbox TTS")
    ap.add_argument("--text", required=True, help="Text to synthesize")
    ap.add_argument("--ref", default=None, help="Optional reference WAV for voice cloning (10s+)")
    ap.add_argument("--output", required=True, help="Output WAV path")
    args = ap.parse_args()

    _ensure_watermarker_patch()

    model_kind = os.environ.get("CHATTERBOX_MODEL", "turbo").lower()
    device = os.environ.get("CHATTERBOX_DEVICE", "cpu")
    if device not in ("cpu", "cuda", "mps"):
        device = "cpu"

    try:
        if model_kind == "default":
            from chatterbox.tts import ChatterboxTTS
            model = ChatterboxTTS.from_pretrained(device=device)
        else:
            from chatterbox.tts_turbo import ChatterboxTurboTTS
            model = ChatterboxTurboTTS.from_pretrained(device=device)
    except ImportError as e:
        print(f"ERROR: chatterbox-tts not installed for {sys.executable}: {e}", file=sys.stderr)
        sys.exit(3)

    import torchaudio

    kwargs = {}
    if args.ref and os.path.exists(args.ref):
        kwargs["audio_prompt_path"] = args.ref
    wav = model.generate(args.text, **kwargs)
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    torchaudio.save(args.output, wav, model.sr)
    print(f"OK {model_kind}: {wav.shape[-1] / model.sr:.1f}s -> {args.output}")


if __name__ == "__main__":
    sys.exit(main())
