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

## Legacy Code

The original pipeline that used NotebookLM for podcast generation,
Selenium browser automation, and slide-show video creation lives in
[`legacy/`](legacy/). It is preserved for reference but no longer
active in production.
