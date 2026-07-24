# Multi-Language Support for Audio Escape Room

The pipeline supports multiple languages. To add a new language:

1. Create a language pack `languages/{lang}/story.py` (copy from `languages/de/story.py`)
2. Translate all text content
3. Update voice mappings in `languages/{lang}/voices.py`
4. Run: `python3 scripts/generate_escape_room.py --language {lang}`

## Available Languages

| Code | Language | Status | Voices |
|------|----------|--------|--------|
| `de` | Deutsch | ✅ Published | KatjaNeural (narrator), ConradNeural (decisions), KillianNeural (antagonist) |
| `en` | English | 🚧 Planned | To be defined |
| `fr` | Français | 🚧 Planned | To be defined |
| `es` | Español | 🚧 Planned | To be defined |

## Voice Selection by Language

Voices are selected dynamically based on language configuration in `scripts/generate_escape_room.py`:

```python
LANGUAGE_CONFIG = {
    "de": {
        "narrator": "de-DE-KatjaNeural",
        "decision": "de-DE-ConradNeural",
        "antagonist": "de-DE-KillianNeural",
        "decision_rate": "-15%",
    },
}
```

## Adding English

1. Create `languages/en/story.py` — translate all `CHAPTERS` and `VIDEO_SEGMENTS`
2. Add voice config:
   ```python
   "en": {
       "narrator": "en-US-JennyNeural",
       "decision": "en-US-GuyNeural",
       "antagonist": "en-US-DavisNeural",
       "decision_rate": "-15%",
   }
   ```
3. Generate: `python3 scripts/generate_escape_room.py --language en`
4. Upload to YouTube with English title/description
