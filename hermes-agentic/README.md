# Hermes Agentic — Shorts Production Pipeline

YouTube Shorts pipeline driven by [Hermes Agent](https://hermes-agent.nousresearch.com) —
a self-improving AI agent that researches topics, generates curiosity-gap scripts,
produces Ken Burns videos with TikTok-style captions, and uploads them on schedule.

## What it does

```
Research → Script (curiosity-gap) → Pexels Videos+Images → Ken Burns → Crossfade → Captions → Upload
                                                                                           ↓
                                                                                  Analytics (weekly)
                                                                                           ↓
                                                                                  Self-improving style updates
```

## Scripts

| Script | Purpose |
|--------|---------|
| `generate_shorts_v2.py` | **V2 mixed-media** — Pexels videos + images, Ken Burns, crossfade, TikTok captions, TTS |
| `generate_shorts.py` | V1 images-only — Pexels images, Ken Burns, crossfade, captions, TTS |
| `pexels.py` | Pexels API client — search + download photos/videos |
| `ken_burns.py` | Ken Burns effect via ffmpeg zoompan (Hermite easing) |
| `crossfade_transitions.py` | xfade-based crossfade concatenation |
| `youtube_upload.py` | YouTube Data API v3 upload with AI content flags |
| `youtube_analytics.py` | YouTube Analytics API — channel, video, retention, weekly reports |

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt edge-tts
apt install ffmpeg

# 2. Configure
cp .env.example .env
# → Add PEXELS_API_KEY, YT_CLIENT_SECRETS, YT_CHANNEL_ID

# 3. Generate a Short
python3 generate_shorts_v2.py \
  --query "science topic" \
  --output /tmp/short.mp4 \
  --images 5 \
  --videos 3 \
  --voice en-US-BrianNeural
```

## Choose your TTS voice

The generators accept `--tts` with **three interchangeable backends** — pick whatever fits
your setup (cloud key, local model, or none):

| `--tts` | Backend | Voice quality | Needs |
|---------|---------|---------------|-------|
| `edge` (default) | Microsoft Edge Neural (cloud, free) | good | `pip install edge-tts` |
| `chirp` | Gemini Chirp 3 HD (cloud API) | **natural / best** | `GEMINI_API_KEY` |
| `kokoro` | Kokoro-82M (fully local) | good, runs offline | kokoro venv (see below) |

```bash
# Chirp 3 HD (Google Gemini) — natural narration voice
python3 generate_shorts_v2.py --query "..." --output short.mp4 --script "..." --tts chirp
#   → voice auto-defaults to "Puck"; other Chirp voices: Kore, Charon, Leda, Fenrir, Aoede

# Kokoro — local, offline (torch stays in its own venv)
export KOKORO_PYTHON=/path/to/kokoro-venv/bin/python   # or KOKORO_VENV=/path/to/kokoro-venv
python3 generate_shorts_v2.py --query "..." --output short.mp4 --script "..." --tts kokoro
#   → voice auto-defaults to "af_heart"; other voices: am_michael, bf_emma, am_fenrir, ...

# Edge — no key required
python3 generate_shorts_v2.py --query "..." --output short.mp4 --script "..." --tts edge
```

Chirp requires a Gemini API key: `cp .env.example .env` → add `GEMINI_API_KEY=...`
(the `chirp_tts.py` module is stdlib-only and reads the key from the env var or `.env`).

Kokoro setup (one time, any venv): `uv venv kokoro-env && uv pip install --python
kokoro-env/bin/python kokoro soundfile numpy` plus the spaCy model
`en_core_web_sm` (see `kokoro_run.py` docstring for the exact wheel URL).

**Word-rate calibration** differs per backend: ~2.7 words/s (chirp), ~2.7–3.0 words/s
(edge +10%), ~2.4–2.6 words/s (kokoro natural). YouTube Shorts cap is 60 s — size your
script accordingly.

## Driven by Hermes Agent

This code is designed to be orchestrated by Hermes Agent — a self-improving AI agent
that runs the full pipeline autonomously:

- **3 Shorts/day** on schedule (08:00 / 13:00 / 18:00)
- **Topic dedup** across all published videos
- **Curiosity-gap scripts** with hook/build-up/reveal structure
- **Weekly analytics** that feed back into style improvements
- **Mixed media** blending Pexels videos with Ken Burns images

The agent's full production skill lives in `youtube-shorts-builder` and the
style guide in `youtube-short-style`. These skills evolve autonomously based on
analytics — every Monday's report updates the style guide with what works.

## The shift

Previously this channel was driven by a hard-coded Python pipeline (`legacy/`).
The agentic approach replaces fixed scripts with:
- **AI-driven decisions** (topic selection, script writing, visual choices)
- **Self-improvement** (analytics → style updates → better content)
- **Autonomous scheduling** (3 shots/day, no human intervention)
- **Edge case handling** (caption rendering, encoding pitfalls, API quotas)

## Requirements

- Python 3.10+
- ffmpeg + ffprobe
- One TTS backend: `edge-tts` (default, free) and/or `GEMINI_API_KEY` for Chirp 3 HD
  and/or a local kokoro venv — see "Choose your TTS voice"
- Pexels API key (free tier)
- YouTube Data API v3 with OAuth
- Pillow, httpx, python-dotenv

## True Crime Builder

See [`true-crime-builder/`](true-crime-builder/) for the 10-15 minute true crime documentary pipeline:
- `scripts/build_tc_video.py` — Full pipeline with Ken Burns, cascaded xfade, captions, thumbnails
- `scripts/upload_true_crime.py` — Upload with custom description, tags, and playlist integration
- `SKILL.md` — Complete Hermes Agent skill documentation

**v1.1 (July 2026):** Fixed final compose timeout (300→900s), added V4L2 hardware encoder auto-detection, `ultrafast` preset for RPi.
