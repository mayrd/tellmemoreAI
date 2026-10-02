---
name: tellmemoreai-shorts
description: "Agent instructions for producing YouTube Shorts with the Tell Me More AI! pipeline — research, scriptwriting, Pexels sourcing, Ken Burns animation, TikTok captions, TTS, and upload."
version: 1.0.0
author: Tell Me More AI! / Hermes Agent
license: MIT
platforms: [linux]
---

# Tell Me More AI! — Shorts Production SKILL.md

**Use this file to instruct an AI agent how to produce YouTube Shorts with this codebase.**

This SKILL.md is the canonical agent reference for the `hermes-agentic/` scripts.
Give it to your agent as a system prompt or skill file. It contains every step,
flag, pitfall, and design decision an agent needs to run the pipeline autonomously.

## Architecture

```
Research → Script (curiosity-gap) → Pexels Videos+Images → Ken Burns → Crossfade → Captions → Upload
                                                                                                       ↓
                                                                                              Analytics (weekly)
                                                                                                       ↓
                                                                                              Style improvements
```

## When to Use

- Creating YouTube Shorts automatically on a schedule
- Producing short-form video with images + videos + animated captions
- Building a self-improving content loop (analytics → better content)
- Agent-driven social media automation

## Pipeline Steps

### Step 1: Research & Topic Selection

```
- Pick a trending topic in science, space, tech, psychology, or history
- NEVER pick a topic already in youtube_shorts_topics.json
- Format: curiosity-gap (hook → build-up → reveal)
- Hook (0-3s): provocative question, NEVER reveal answer
- Build-up: context, details, deepen mystery
- Reveal (last 5-8s): payoff only at the end
```

### Step 2: Fetch Mixed Assets

```
- Search Pexels for portrait photos + videos matching the topic
- Use pexels.py (curl-backed, avoids Python urllib 403)
- Download N portrait images + M portrait videos
- Quality: HD > SD, portrait orientation preferred
- ALL fetched images must be used as segments (never silently discard)
```

**Beat-aware sourcing (`--queries`) — one image query per story beat.** A single query
cannot tell the story: `--query "geyser snow winter"` for a story about salty ice grains
in Saturn's E ring produced Icelandic geysers on snow. Pass one query per sentence in
narration order; image 1 is the hook and should be the most impressive shot of the story.

```
--queries "nasa:saturn portrait | nasa:enceladus plume | pexels:ice crystal macro | pexels:scientist microscope laboratory | nasa:dark side moon enceladus"
```

- Prefix `nasa:` uses the NASA Image and Video Library (nasa_images.py, public domain,
  no key) — for space/astronomy topics stock photos only offer decor, so the pipeline
  used to fall back to metaphors. Titles that look like data plots (spectrum/chart/
  model/movie/...) are filtered out automatically; verify the hook frame anyway.
- Pexels candidates are re-ranked by their `alt` text (the wrapper drops `alt`, so the
  raw endpoint is used) and every beat logs its image title, so the run log shows whether
  the images match the narration.
- `--image-fit auto|crop|pad|blur` handles non-9:16 sources: `zoompan` scales the zoom
  window hard to the output size, so a 16:9 image would be squeezed. `auto` crops very
  wide panoramas, pads mostly black space images on black bars, and puts colourful
  landscape material over a blurred full-frame copy.
- Hook check (cheap, catches the most common miss): extract the first frame
  (`ffmpeg -y -ss 1 -i out.mp4 -frames:v 1 frame.jpg`) and look at it. If it is mostly
  black or feels empty, change the hook query and re-render the visuals only — keep the
  audio (`--audio existing.m4a`) so the TTS step (minutes) is skipped.

### Step 3: Generate TTS Audio

Three interchangeable backends via `--tts` (default `edge`):
- `edge` — edge-tts with --rate +10%, voice en-US-BrianNeural (free, no key)
- `chirp` — Gemini Chirp 3 HD (natural), default voice Puck, needs GEMINI_API_KEY (see chirp_tts.py)
- `kokoro` — local Kokoro-82M via its own venv (KOKORO_PYTHON env), default voice af_heart (see kokoro_tts.py)
- `chatterbox` — local Chatterbox via its own venv (CHATTERBOX_PYTHON env), GPU recommended, voice cloning via --voice ref.wav (see chatterbox_tts.py)
- Measure duration with ffprobe
- Enforce 60s hard limit: ≤160 words (chirp) / ≤180 words (edge +10%)

### Step 4: Prepare Segments (Interleaved)

```
- Videos: normalize to 1080x1920, 24fps, yuv420p; loop short clips
- Images: Ken Burns zoompan (1.0→1.08x) with Hermite easing (3t²-2t³)
- 30fps internal for Ken Burns, 24fps for video segments
- Interleave: video → image → video → image...
- Forward+backward cycling to avoid stale repeats
```

### Step 5: Crossfade Concatenation

```
- xfade filter chain: 0.5s crossfade between ALL segments
- Output: single video track (no audio)
```

### Step 6: Render Captions

```
- Split script into phrases at punctuation + conjunctions
- Word-level contiguous timing (no gaps)
- Single-line pill style:
  - Active line: white text (255,255,255), 54px font
  - Solid black pill background (alpha 200)
  - Position: ~72% of frame height
  - Text vertically centered using font metrics
- Encode as qtrle with alpha — NEVER use prores_ks (timeout risk)
- Captions at 12fps; ffmpeg interpolates to 24fps
```

### Step 7: Final Compose & Upload

```
- Overlay captions onto crossfaded video
- Mux with TTS audio → H.264 MP4 (yuv420p, AAC 128k, faststart)
- Upload via youtube_upload.py with AI content flags:
  containsSyntheticAudio: true
  containsSyntheticVideo: true
- Append topic to youtube_shorts_topics.json with uploaded_at timestamp
```

## Scripts

| Script | Purpose |
|--------|---------|
| `generate_shorts_v2.py` | **V2 mixed-media** — Pexels videos + images, Ken Burns, crossfade, captions, TTS |
| `generate_shorts.py` | V1 images-only — Pexels images, Ken Burns, crossfade, captions, TTS |
| `pexels.py` | Pexels API client — search + download photos/videos (use curl, not urllib) |
| `ken_burns.py` | Ken Burns effect via ffmpeg zoompan (Hermite easing, 30fps internal) |
| `crossfade_transitions.py` | xfade-based crossfade concatenation |
| `youtube_upload.py` | YouTube Data API v3 upload with AI content flags |
| `youtube_analytics.py` | YouTube Analytics API — channel, video, retention, weekly reports |

## CLI Usage

```bash
# V2: Mixed media (videos + images) with captions
python3 generate_shorts_v2.py \
  --query "topic keywords for Pexels" \
  --output /tmp/short.mp4 \
  --images 5 \
  --videos 3 \
  --crossfade 0.6 \
  --voice en-US-BrianNeural

# V1: Images only (faster, no video downloads)
python3 generate_shorts.py \
  --query "brain science discovery" \
  --output /tmp/short.mp4 \
  --script "Your curiosity-gap script text here..." \
  --images 6

# One image query per story beat (image 1 = hook), stock + public-domain NASA imagery
python3 generate_shorts_v2.py \
  --queries "nasa:saturn portrait | nasa:enceladus plume | pexels:ice crystal macro" \
  --output /tmp/short.mp4 \
  --images 3 --videos 0 --image-fit auto

# Re-render visuals only, keeping the existing voice track (skips the TTS step)
python3 generate_shorts_v2.py \
  --queries "nasa:dark side moon enceladus" \
  --output /tmp/short_fix.mp4 \
  --script "$(cat script.txt)" \
  --images 5 --audio /tmp/audio.m4a

# Upload (always use the canonical upload script)
python3 youtube_upload.py /tmp/short.mp4 "Video Title Here"

# Analytics (run after uploads)
python3 youtube_analytics.py --report weekly
```

## Key Design Decisions

### Caption Rendering — Single-Line (v7)
- Only ONE line visible: the active/spoken line
- No next-line preview, no yellow glow, no border
- White text on black pill background at 72% frame height
- Contiguous word timing — punctuation pauses absorbed into phrase-ending words
- Monotonic guard prevents active line from decreasing

### Ken Burns Animation — Smooth Zoom
- Hermite smoothstep easing (`3t²-2t³`), NOT linear
- Zoom range: 1.0→1.08x, 30fps internal rendering
- Pan range: 0.06 (subtle motion, reads well on large screens)
- Alternating zoom-in / zoom-out between images

### Mixed Media Sourcing
- Pexels API (free tier: 200 req/h). Key in `.env` as `PEXELS_API_KEY`
- Always use `curl` via subprocess with User-Agent header — Python `urllib` gets 403
- Video normalization: all clips → 1080x1920, 24fps, yuv420p before xfade
- Short videos looped via `-stream_loop -1`
- ALL fetched images used — never cap at `max(2, ceil(duration/BG_DURATION))`

### Curiosity-Gap Format (non-negotiable)
1. Hook (0-3s): provocative question — NEVER reveal answer here
2. Build-up: context, details, misdirection
3. Reveal (last 5-8s): payoff at the end

## Output Spec

| Property | Value |
|----------|-------|
| Resolution | 1080×1920 (9:16 portrait) |
| FPS | 24 |
| Codec | H.264 yuv420p + AAC 128k |
| Duration | Matches TTS audio (max 60s) |
| Size | ~2-5 MB per 20s, ~35-40 MB per 40s |

## Prerequisites

- Python 3.10+ with Pillow, httpx, python-dotenv
- ffmpeg + ffprobe (system)
- One TTS backend: `edge-tts` (`pip install edge-tts`) and/or `GEMINI_API_KEY` (Chirp 3 HD) and/or kokoro venv — see "Step 3: Generate TTS Audio"
- Pexels API key (free tier at pexels.com/api)
- YouTube Data API v3 + OAuth client secrets

## Analytics (Self-Improving Loop)

| Command | Output |
|---------|--------|
| `--report channel` | Daily breakdown: views, watch time, subs, avg duration |
| `--report video --video-id XXX` | Per-video metrics + traffic sources |
| `--report retention --video-id XXX` | Audience retention curve |
| `--report weekly` | Full weekly: channel totals + all videos ranked |

### Key Metrics
- **Avg view duration** → #1 quality signal. Target 30s+
- **Retention at 20-30%** → where most drop-offs happen
- **Subscribers gained** → correlates with emotional impact
- **Traffic sources** → "Suggested" and "Browse" = algorithm promotion

Use weekly analytics to update:
- Topic selection (which categories perform best)
- Script structure (which hooks retain viewers)
- Visual pacing (which segment durations work)
- Voice/audio choices

## Topic Deduplication (MANDATORY)

- Check `youtube_shorts_topics.json` before every production run
- Structure: `{"topics": [{"query": "...", "date": "...", "uploaded_at": "..."}]}`
- Always include `uploaded_at` as ISO timestamp when appending
- Never produce on a topic already covered

## Self-Improving Schedule

| Time | Category |
|------|----------|
| 08:00 | General science / curiosity |
| 13:00 | Space / technology |
| 18:00 | Biology / psychology / history |

Weekly: Monday analytics → update style preferences → next week's content improves.

## Pitfalls

1. **Caption encoding:** Use `qtrle -pix_fmt argb`, NOT `prores_ks`. ProRes times out on slow machines.
2. **Python venv:** build scripts need Pillow — ensure it's installed in the active Python. Install with `pip install Pillow` if missing.
3. **edge-tts:** Must be installed separately (`pip install edge-tts`). Check path with `which edge-tts`.
4. **Pexels 403:** Always use `curl` via subprocess with `-H "User-Agent: ..."`, not `urllib.request`.
5. **All fetched images must be used:** `segment_count = n_fetched_images`, never `max(2, ...)`.
6. **Topics JSON structure:** `{"topics": [...]}`, not a flat list. May contain wrapper prefix — strip before parsing.
7. **OAuth token expiry:** `invalid_grant` = permanently dead refresh token. Re-auth required. OAuth consent screen must be in "Production" mode to prevent 7-day token expiry.
8. **ffmpeg zoompan:** Use `on` (output frame), not `n`. Correct: `z='if(eq(on,0),1.0,1.0+0.12*on/83)'`.
9. **ffmpeg 7.x silent audio:** Use `aevalsrc=0:c=mono:s=24000:d=N` instead of `anullsrc`.
10. **Video normalization:** All Pexels videos must be normalized to target resolution/fps/pixfmt before xfade.
11. **Duration coverage:** Generate frames for full audio duration. Last caption visible for final 2-3 seconds.
12. **YouTube 60s hard limit:** Shorts over 60s are rejected. Estimate: ~3.4 words/second at default TTS rate. ≤204 words for 60s, ≤187 words for 55s.
13. **generate_shorts.py flags:** Accepts `--query`, `--output`, `--script`, `--images`, `--voice`. Does NOT accept `--topic` or positional output path.
14. **youtube_upload.py:** Takes exactly two positional args: `filepath` and `title`. Description is auto-generated. No `--description` flag.
15. **AI content flags:** YouTube requires `containsSyntheticAudio: true` and `containsSyntheticVideo: true` on upload. Set by default in youtube_upload.py.
16. **Title length:** YouTube titles up to ~90 chars upload fine. The "And [hook]" suffix pattern is safe.
17. **Batch updates hit quota:** YouTube API daily quota is ~10,000 units. Each `videos.update` costs ~50 units. Batch 30+ videos cautiously.
18. **Write temp files to `/tmp/`:** Never write to system-protected directories.
19. **Pexels key loading:** From `PEXELS_API_KEY` env var or `.env` file. No hardcoded keys.
20. **One query for the whole short ≠ storytelling:** images sourced from a single metaphorical query can look great and still be off-topic (geysers on snow for a Saturn-moon story). Use `--queries` with one query per narration beat; check the per-beat titles in the log and the first frame before uploading.
21. **`zoompan` squeezes non-9:16 images:** it scales the zoom window hard to `s=WxH`, so 16:9 sources come out distorted. `--image-fit auto` handles this (crop / black bars / blurred background) — never feed a landscape image straight into the Ken Burns step.
22. **24 kHz mono audio:** TTS backends deliver it, and Telegram/YouTube sometimes drop the track in that shape. The final compose always encodes 48 kHz stereo (`-ar 48000 -ac 2`).
23. **NASA search returns data plots first:** searching `enceladus plume` tops out with the VIMS spectrum. `nasa_images.search_images()` filters those titles; still verify the hook frame, and prefer high-resolution releases (many old Cassini JPEGs are only ~1000 px wide and get soft when scaled to 1920).
