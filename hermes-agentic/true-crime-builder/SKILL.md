---
name: true-crime-builder
description: "End-to-end true crime documentary builder — scriptwriting, TTS narration, Pexels imagery, Ken Burns animations, subtitle captions, thumbnail generation, YouTube upload. 10-15 minute landscape videos."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [true-crime, documentary, youtube, video, automation, tts, ken-burns, pexels, captions, thumbnails]
    category: social-media
    related_skills: [youtube-shorts-builder]
---

# true-crime-builder v1.0

End-to-end pipeline for producing 10–15 minute true crime documentary videos in landscape 16:9 format for YouTube.

## Architecture

```
Research → Script (LLM or manual) → TTS (edge-tts) → Pexels Images (100+ landscape)
    → Ken Burns (zoompan) → Cascaded Xfade (batches of 10) → Subtitle Captions
    → Thumbnail (PIL overlay) → YouTube Upload (custom description + tags) → Playlist
```

## When to Use

- Building true crime documentary videos for YouTube
- 10–15 minute narrative videos with Ken Burns animations
- Need auto-generated thumbnails and subtitle captions
- Daily production of long-form content

## Scripts

| Script | Purpose |
|--------|---------|
| `/opt/data/build_tc_video.py` | Full pipeline: TTS → Pexels → Ken Burns → Captions → Thumbnail |
| `/opt/data/upload_true_crime.py` | Upload with custom description, tags, thumbnail, playlist |
| `/opt/data/true_crime_script.txt` | Script text (input) |
| `/opt/data/true_crime_description.txt` | YouTube description with hashtags |

## Pipeline Steps

### Step 1: Script
Write a compelling narrative script (~1700–2500 words for 10–15 minutes at ~3.4 wps with +10% TTS rate). Structure:
- **Hook (first 30s):** Grab attention with the mystery
- **Investigation (middle 70%):** Timeline, evidence, suspects, twists
- **Resolution (last 10%):** What we know, what remains unknown

### Step 2: TTS
```
/opt/data/home/.local/bin/edge-tts --voice en-US-BrianNeural --rate +10% \
  -f /opt/data/true_crime_script.txt --write-media /tmp/true_crime_audio.mp3
```

### Step 3: Build Video
```
python3 /opt/data/build_tc_video.py \
  /opt/data/true_crime_script.txt \
  "Video Title Here" \
  /tmp/true_crime_final.mp4
```

The script handles:
- Pexels image search + download (100+ landscape images from 18 diverse queries)
- Ken Burns zoompan (1.0→1.08×, Hermite easing, 30fps internal)
- Cascaded xfade crossfades (batches of 10 to avoid OOM)
- Subtitle-bar captions (semi-transparent black bar, white text, 32px)
- Thumbnail generation (dark background + title + TRUE CRIME badge)

### Step 4: Upload
```
/opt/hermes/.venv/bin/python3 /opt/data/upload_true_crime.py \
  /tmp/true_crime_final.mp4 \
  "Video Title Here" \
  /tmp/true_crime_thumb.jpg
```

Uploads with:
- Custom description (from `/opt/data/true_crime_description.txt`)
- Proper hashtags: #TrueCrime #UnsolvedMystery #ColdCase etc.
- Custom thumbnail
- Added to "True Crime & Disasters" playlist

## YouTube Playlist

- **Name:** True Crime & Disasters
- **ID:** `PLbgCBs2RbYFQZ-vOZNdfYcsZqfCxKLONb`
- **Channel:** Tell Me More AI! (@tellmemoreai)

## Key Design Decisions

### Caption Style (Subtitle Bar)
Unlike the TikTok pill captions used in Shorts, true crime documentaries use a **subtitle bar**:
- Semi-transparent black bar at bottom of frame (180 alpha)
- White text, 32px DejaVu Sans Bold
- Centered horizontally
- Single line visible (active line only)
- Same word-level timing engine as Shorts pipeline

### Thumbnails
Auto-generated with PIL:
- Dark background (15, 15, 25)
- Title in large white text, word-wrapped
- Red "TRUE CRIME" badge below title
- 1280×720 JPEG

### Memory Safety (Cascaded Xfade)
⚠️ **Critical:** Never xfade-concat more than 10 segments at once on RPi (8GB RAM).
The pipeline merges in batches of 10, then concat-demuxes the batch outputs.
Peak RAM: ~700MB (vs 4.9GB+ for 55-segment single-pass xfade).

## Pexels Image Queries

Diversify queries for visual variety (18 queries × 7 images = ~126 for 10-min video):

| Category | Queries |
|----------|---------|
| Crime/mystery | dark night house fire, police investigation crime scene, detective evidence board |
| Atmosphere | mystery fog abandoned building, empty road night fog, cemetery fog grave |
| Period detail | vintage 1940s family portrait, small town main street 1940s, telephone vintage 1940s |
| Location | west virginia mountains forest |
| Evidence | newspaper headline crime, courtroom judge gavel, missing person poster, typewriter old document |
| Aftermath | burned ruins house debris, flames fire dark |
| Clues | old billboard highway, letters mailbox old photograph |

## Build Time Budget (RPi 8GB, ~10-min video)

| Step | Time |
|------|------|
| TTS (edge-tts) | ~3 min |
| Pexels download (120 images) | ~2 min |
| Ken Burns (120 segments × 6s) | ~12 min |
| Cascaded xfade (12 batches) | ~5 min |
| Caption rendering (PIL + qtrle) | ~3 min |
| Final compose | ~2 min |
| **Total** | **~27 min** |

## Output

- **Resolution:** 1920×1080 (16:9 landscape)
- **FPS:** 24
- **Codec:** H.264 (yuv420p) + AAC 128k
- **Duration:** 10–15 minutes
- **Size:** ~200–300 MB

## Tags & Hashtags

Use for YouTube SEO:
- Primary: #TrueCrime #UnsolvedMystery #TrueCrimeStory #Documentary
- Case-specific: #SodderChildren #ColdCase #MissingChildren
- Discovery: #WestVirginia #Mystery #Unsolved

## Prerequisites

- ffmpeg + ffprobe (system)
- Python 3.10+ with Pillow (system Python)
- edge-tts at `/opt/data/home/.local/bin/edge-tts`
- Pexels API key in `/opt/data/.env`
- YouTube Data API v3 + OAuth (see `youtube-shorts-builder` references)
- `/opt/data/google_client_secret.json` for OAuth

## Pitfalls

1. **TTS timeout:** edge-tts with 1700+ word scripts can take >120s. Use `timeout=300`.
2. **OOM on xfade:** Maximum 10 segments per xfade batch on RPi 8GB.
3. **Pexels rate limit:** 200 req/h. 120 images from 18 queries ≈ 140 req. OK.
4. **Emoji in title:** Security scanner blocks emoji. Use plain ASCII titles.
5. **qtrle encoding:** Use `qtrle -pix_fmt argb`, NOT `prores_ks` (timeout on RPi).
6. **Caption rendering performance:** 12fps captions for 10-min video ≈ 7,200 PNG frames. Allow 3 min.
