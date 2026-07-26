# 🎧 Audio Escape Room Generator

A generic pipeline for creating **interactive audio escape room YouTube videos** with branching stories, chapter markers, and multi-language TTS support.

Listeners make decisions every ~10 minutes, jump between chapters via YouTube chapter links, and experience different story endings based on their choices.

---

## Quick Start

```bash
# Generate the German story "Die letzte Schicht"
python3 scripts/generate_escape_room.py --story de/letzte-schicht

# Skip TTS re-generation (use cached audio)
python3 scripts/generate_escape_room.py --story de/letzte-schicht --skip-tts

# English story (when available)
python3 scripts/generate_escape_room.py --story en/my-story
```

---

## Project Structure

```
escape-room/
├── stories/                      # Story data files (one per story)
│   ├── de/
│   │   └── letzte-schicht.py     # German crime thriller
│   ├── en/                       # Future: English stories
│   ├── fr/                       # Future: French stories
│   └── es/                       # Future: Spanish stories
├── scripts/
│   ├── generate_escape_room.py   # Main pipeline: TTS -> video -> chapters
│   └── generate_overlays.py      # Decision overlay images (optional)
├── assets/
│   ├── audio/
│   │   ├── de/                   # German TTS audio (generated)
│   │   ├── en/                   # English TTS audio (future)
│   │   └── ...
│   └── images/
│       └── thumbnail.png         # YouTube thumbnail (customize per story)
├── output/                       # Generated videos + descriptions
└── README.md
```

---

## How to Create a Story

Create a new Python file in `stories/{lang}/{story-name}.py` with these required variables:

### `STORY` — Metadata
```python
STORY = {
    "id": "my-story",
    "title": "My Story Title",
    "language": "en",
    "target_play_minutes": 30,     # Approx play-through time for one path
    "description_intro": "Short description for YouTube...",
    "tags": ["Crime", "Mystery"],
}
```

### `VOICES` — TTS Voice Configuration
```python
VOICES = {
    "narrator": {"voice": "en-US-JennyNeural", "rate": "+0%"},
    "decision": {"voice": "en-US-GuyNeural", "rate": "-15%"},
    "antagonist": {"voice": "en-US-DavisNeural", "rate": "+0%"},
}
```
Available voices: `python3 -m edge_tts --list-voices | grep "{lang}"`

### `CHAPTERS` — Story Content
```python
CHAPTERS = {
    "intro": {
        "text": "The narrated story text for this chapter...",
        "title": "Chapter Title in YouTube Chapters",
        "voice": "narrator",        # Must match a key in VOICES
    },
}
```

### `DECISIONS` — Decision Points
```python
DECISIONS = {
    "decision_1": {
        "question": "You must decide.",
        "options": "Where to go? A: Left. B: Right.",
        "pause_s": 30,
        "question_repeat": "Once more: Where to go?",
        "options_repeat": "A: Left. B: Right.",
    },
}
```

### `SEGMENTS` — Playback Order
```python
SEGMENTS = [
    "intro",                       # Narrative chapter
    ("decision_1", "gap"),         # Decision block with 2s gap before it
    "chapter_a",                   # Path A
    ("decision_2", "gap"),
    "ending_1",
    "chapter_b",                   # Path B
    ("decision_3", "gap"),
    "ending_2",
    "outro",
]
```

All paths play sequentially in the video. Listeners jump between chapters using the YouTube chapter links in the description.

---

## How Listening Works

1. The video plays linearly from start
2. At a decision point, the voice says "You must decide." then lists the options
3. **30 seconds of silence** — the listener clicks a chapter in the description
4. The question is repeated once more
5. The story continues from the chosen chapter

Reaching an ending does not stop the video — it continues with the other paths so listeners can jump back.

---

## YouTube Upload

Generated files are in `output/`:
- `{story-id}.mp4` — Video with embedded chapter markers
- `{story-id}_description.txt` — YouTube description with timestamps and hashtags

Upload the video to YouTube, paste the description, and set the thumbnail from `assets/images/thumbnail.png`.

---

## Branching Examples

All stories have up to 4 different endings. The segment order determines the YouTube chapter timestamps. For each decision, options are labeled with letters (A, B, A1, B1, etc.) matching the chapter titles in the description.

---

## Requirements

- Python 3.10+
- `edge-tts` (Microsoft Edge TTS)
- `ffmpeg` (for audio/video processing)
- `Pillow` + `numpy` (for overlay images, optional)

```bash
pip install edge-tts
# ffmpeg must be installed separately
```
