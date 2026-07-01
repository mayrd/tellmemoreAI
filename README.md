# Tell Me More AI!

> An AI-automated YouTube channel — now agentic.

This is the production pipeline for [Tell Me More AI!](https://youtube.com/@tellmemoreai) —
a YouTube channel powered by [Hermes Agent](https://hermes-agent.nousresearch.com).

## The Evolution: From Script to Agent

> **Note:** The original hard-coded Python pipeline has been moved to [`legacy/`](legacy/).
> The channel is now fully agentic.

### Then (legacy/)

| Script | What it did |
|--------|-------------|
| `ideagenerator.py` | Searched Wikipedia for podcast topics |
| `podcastgenerator.py` | Used Selenium to generate NotebookLM podcasts |
| `podcast2video.py` | Generated slide-show videos + thumbnails |
| `genai.py` / `wiki.py` / `media.py` | AI helpers, Wikipedia scraping, media utils |
| `yt.py` / `custom_thumbnail.py` | YouTube upload, custom thumbnails |

### Now ([`hermes-agentic/`](hermes-agentic/))

A self-improving AI agent produces **3 Shorts/day**:

1. **Research** → AI picks trending topics, checks dedup
2. **Script** → Curiosity-gap format (hook / build-up / reveal)
3. **Visuals** → Pexels videos + images with Ken Burns + crossfade
4. **Captions** → TikTok-style animated word highlighting
5. **TTS** → edge-tts narration
6. **Upload** → Scheduled YouTube Shorts with AI content flags
7. **Improve** → Weekly analytics feed back into the style guide

No human involved — the agent self-improves every week.

## Quick Start

See [`hermes-agentic/`](hermes-agentic/) for the Shorts pipeline scripts.

These scripts are designed to be called by Hermes Agent, but can also
be run standalone for testing and debugging.


## True Crime Documentaries

The agent also produces **true crime documentary videos** (10-15 minute landscape format)
using the same Ken Burns, Pexels, and TTS infrastructure as the Shorts pipeline.

See [`hermes-agentic/true-crime-builder/`](hermes-agentic/true-crime-builder/) for the full skill documentation.

| Script | Purpose |
|--------|---------|
| `scripts/build_tc_video.py` | Full pipeline: TTS → Pexels → Ken Burns → Captions → Thumbnail |
| `scripts/upload_true_crime.py` | Upload with custom description, tags, thumbnail, playlist |

Produces 1920×1080 landscape videos with:
- Ken Burns animated imagery from Pexels (100+ landscape photos)
- Cascaded crossfade transitions (disk-buffered, no OOM)
- Subtitle-bar captions with word-level timing
- Auto-generated thumbnails with title + TRUE CRIME badge
- YouTube playlist integration

## Legacy Code

The original pipeline that used NotebookLM for podcast generation,
Selenium browser automation, and slide-show video creation lives in
[`legacy/`](legacy/). It is preserved for reference but no longer
active in production.
