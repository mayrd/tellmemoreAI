#!/usr/bin/env python3
"""
generate_shorts.py — End-to-end YouTube Shorts generation pipeline.

Orchestrates the full workflow:
  1. Fetch assets from Pexels (images + optional videos)
  2. Apply Ken Burns pan-and-zoom effect to images
  3. Compose everything with crossfade transitions into a final 9:16 vertical video

Usage:
    python3 generate_shorts.py --query "nature" --output nature_short.mp4
    python3 generate_shorts.py --query "ocean waves" --duration 30 --voice en-US-BrianNeural

Requirements:
    - FFmpeg + ffprobe (system)
    - Python 3.10+ with Pillow
    - edge-tts (for voiceover)
    - Pexels API key (env var PEXELS_API_KEY or in ~/.env / /opt/data/.env)

Output:
    - Final MP4 video (1080x1920, < 60s) ready for YouTube Shorts upload
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import shutil
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# ── Add script directory to path for local imports ──
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

# ── Defaults ──
DEFAULT_RESOLUTION = (1080, 1920)
DEFAULT_FPS = 24
DEFAULT_SEGMENT_DURATION = 3.5
DEFAULT_CROSSFADE_DURATION = 0.5
DEFAULT_KB_ZOOM = (1.0, 1.08)
DEFAULT_VOICE = "en-US-BrianNeural"
DEFAULT_SCRIPT_TEMPLATE = (
    "Did you know? Here are some fascinating facts about {query}. "
    "Nature never ceases to amaze us with its incredible diversity. "
    "From the smallest organisms to the largest creatures, "
    "every living thing plays a vital role in our ecosystem. "
    "Let's explore more about this amazing topic!"
)
EDGE_TTS_PATH = os.environ.get("EDGE_TTS_PATH", "/opt/data/home/.local/bin/edge-tts")
MAX_DURATION = 60  # YouTube Shorts limit

# ── Caption style constants (v7 Single-Line) ──
FONT_FILE = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
CAPTION_FPS = 12

# Position: active line at 72% of frame height (well above YT title bar)
TARGET_Y = 0.72

PILL_PAD_X = 24
PILL_PAD_Y = 12
PILL_RADIUS = 18
PILL_ALPHA_ACTIVE = 200

FONT_SIZE_ACTIVE = 54

# Active line: clean white, no border, no glow
COLOR_ACTIVE_TEXT = (255, 255, 255)
COLOR_ACTIVE_SHADOW = (0, 0, 0, 140)
COLOR_PILL_BG = (0, 0, 0)
MARGIN = 60


def _probe_duration(path: str) -> float:
    """Get video/audio duration via ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
        capture_output=True, text=True, timeout=15,
    )
    return float(json.loads(result.stdout)["format"]["duration"])


def _run_ffmpeg(cmd: List[str], timeout: int = 120, label: str = "") -> None:
    """Run ffmpeg and raise on failure."""
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg failed{f' ({label})' if label else ''}:\n{result.stderr[-800:]}"
        )


def _get_env_path() -> str:
    """Locate .env file with API keys."""
    for p in [os.path.join(os.path.expanduser("~"), ".env"), "/opt/data/.env"]:
        if os.path.exists(p):
            return p
    return ""


class StepTimer:
    """Track per-step timing for pipeline diagnostics."""

    def __init__(self):
        self.steps: List[Tuple[str, float]] = []

    def run(self, label, fn, *args, **kwargs):
        t0 = time.time()
        print(f"\n{'='*60}")
        print(f"  STEP: {label}")
        print(f"{'='*60}")
        result = fn(*args, **kwargs)
        elapsed = time.time() - t0
        self.steps.append((label, elapsed))
        print(f"  -> {label} done in {elapsed:.1f}s")
        return result

    def summary(self):
        print(f"\n{'='*60}")
        print(f"  PIPELINE TIMING SUMMARY")
        print(f"{'='*60}")
        for label, elapsed in self.steps:
            print(f"  {label}: {elapsed:.1f}s")
        total = sum(e for _, e in self.steps)
        print(f"  TOTAL: {total:.1f}s")


def step_fetch_assets(query: str, n_images: int = 6, n_videos: int = 0) -> Dict:
    """Step 1: Fetch photos (and optionally videos) from Pexels.

    Args:
        query: Search topic/keywords.
        n_images: Number of images to fetch.
        n_videos: Number of videos to fetch (0 = images only).

    Returns:
        Dict with keys: images (list of local paths), videos (list of local paths),
        photo_metadata (list of dicts from API).
    """
    from pexels import search_photos, search_videos, download_photo, download_video

    result = {"images": [], "videos": [], "photo_metadata": []}

    # Fetch photos with extra for safety
    print(f"  Searching Pexels for '{query}' ({n_images} images)...")
    photos = search_photos(query, n=n_images + 4)
    if not photos:
        raise RuntimeError(f"No Pexels results for '{query}'")
    photos = photos[:n_images]
    print(f"  Found {len(photos)} photos")

    # Download photos
    tmp_dir = tempfile.mkdtemp(prefix="shorts_assets_")
    result["_tmp_dir"] = tmp_dir

    for i, photo in enumerate(photos):
        path = os.path.join(tmp_dir, f"img_{i:03d}.jpg")
        try:
            download_photo(photo["url"], path)
            result["images"].append(path)
            result["photo_metadata"].append(photo)
        except Exception as e:
            print(f"  Warning: failed to download image {i}: {e}", file=sys.stderr)

    print(f"  Downloaded {len(result['images'])} images to {tmp_dir}")

    # Optionally fetch videos
    if n_videos > 0:
        print(f"  Searching Pexels for '{query}' ({n_videos} videos)...")
        videos = search_videos(query, n=n_videos + 2)
        videos = videos[:n_videos]
        print(f"  Found {len(videos)} videos")

        for i, video in enumerate(videos):
            path = os.path.join(tmp_dir, f"vid_{i:03d}.mp4")
            try:
                download_video(video["url"], path)
                result["videos"].append(path)
            except Exception as e:
                print(f"  Warning: failed to download video {i}: {e}", file=sys.stderr)

        print(f"  Downloaded {len(result['videos'])} videos")

    return result


def step_ken_burns(
    image_paths: List[str],
    segment_duration: float,
    zoom_range: Tuple[float, float],
    resolution: Tuple[int, int],
    fps: int,
    crossfade_duration: float,
    audio_path: Optional[str] = None,
) -> str:
    """Step 2: Apply Ken Burns effect to images and compose with crossfades.

    Args:
        image_paths: List of local image paths.
        segment_duration: Duration per image segment in seconds.
        zoom_range: (start_zoom, end_zoom) for Ken Burns.
        resolution: Target (width, height).
        fps: Target frames per second.
        crossfade_duration: Crossfade duration between segments.
        audio_path: Optional audio file to mux.

    Returns:
        Path to the composed video file.
    """
    from ken_burns import images_to_video

    print(f"  Applying Ken Burns to {len(image_paths)} images...")
    print(f"  Segment duration: {segment_duration}s, zoom: {zoom_range}, fps: {fps}")
    print(f"  Crossfade: {crossfade_duration}s")

    output_path = tempfile.mktemp(prefix="shorts_kb_", suffix=".mp4")

    result = images_to_video(
        image_paths=image_paths,
        output_path=output_path,
        segment_duration=segment_duration,
        zoom_range=zoom_range,
        resolution=resolution,
        fps=fps,
        crossfade_duration=crossfade_duration,
        audio_path=audio_path,
    )

    dur = _probe_duration(result)
    size_mb = os.path.getsize(result) / (1024 * 1024)
    print(f"  Ken Burns video: {dur:.1f}s, {size_mb:.1f} MB")

    return result


def step_generate_tts(script_text: str, voice: str, tts: str = "edge") -> Tuple[str, float]:
    """Generate TTS audio using edge-tts (default) or Gemini Chirp 3 HD (--tts chirp).

    Args:
        script_text: Script text for voiceover.
        voice: edge-tts voice name (or Chirp 3 voice for --tts chirp).
        tts: 'edge' or 'chirp'.

    Returns:
        Tuple of (audio_path, duration_seconds).
    """
    if tts == "chirp":
        import chirp_tts
        audio_path = tempfile.mktemp(prefix="shorts_tts_", suffix=".mp3")
        print(f"  Generating Chirp 3 TTS ({voice})...")
        audio_path, duration = chirp_tts.synthesize(script_text, voice=voice, output_path=audio_path)
        print(f"  TTS audio: {duration:.1f}s -> {audio_path}")
        return audio_path, duration

    if tts == "kokoro":
        import kokoro_tts
        audio_path = tempfile.mktemp(prefix="shorts_tts_", suffix=".mp3")
        print(f"  Generating Kokoro TTS ({voice})...")
        audio_path, duration = kokoro_tts.synthesize(script_text, voice=voice, output_path=audio_path)
        print(f"  TTS audio: {duration:.1f}s -> {audio_path}")
        return audio_path, duration

    if tts == "chatterbox":
        import chatterbox_tts
        audio_path = tempfile.mktemp(prefix="shorts_tts_", suffix=".mp3")
        print(f"  Generating Chatterbox TTS (GPU recommended)...")
        audio_path, duration = chatterbox_tts.synthesize(script_text, voice=voice, output_path=audio_path)
        print(f"  TTS audio: {duration:.1f}s -> {audio_path}")
        return audio_path, duration

    audio_path = tempfile.mktemp(prefix="shorts_tts_", suffix=".mp3")
    print(f"  Generating TTS ({voice})...")

    cmd = [
        EDGE_TTS_PATH, "--voice", voice,
        "--rate", "+10%",
        "--text", script_text,
        "--write-media", audio_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"edge-tts failed: {result.stderr}")

    duration = _probe_duration(audio_path)
    print(f"  TTS audio: {duration:.1f}s -> {audio_path}")
    return audio_path, duration


def step_compose_final(
    video_path: str,
    audio_path: str,
    output_path: str,
    resolution: Tuple[int, int],
    fps: int,
) -> str:
    """Step 3: Compose final video — overlay audio onto Ken Burns video.

    If the audio is longer than the video, the video is extended by slowing
    down slightly. If shorter, the video is trimmed.

    Args:
        video_path: Path to the Ken Burns video (no audio).
        audio_path: Path to the TTS audio.
        output_path: Final output path.
        resolution: Target (width, height).
        fps: Target frames per second.

    Returns:
        Path to the final output video.
    """
    w, h = resolution
    audio_dur = _probe_duration(audio_path)
    video_dur = _probe_duration(video_path)

    print(f"  Composing final: video={video_dur:.1f}s, audio={audio_dur:.1f}s")

    # If durations differ significantly, adjust video speed to match audio
    ratio = video_dur / audio_dur if audio_dur > 0 else 1.0

    if abs(ratio - 1.0) > 0.05:
        # Adjust video speed to match audio duration
        speed = ratio
        # Clamp to reasonable range (0.5x - 2.0x)
        speed = max(0.5, min(2.0, speed))
        atempo = speed
        # atempo filter only supports 0.5-2.0, chain if needed
        if speed < 0.5:
            atempo_chain = f"atempo=0.5,atempo={speed/0.5}"
        elif speed > 2.0:
            atempo_chain = f"atempo=2.0,atempo={speed/2.0}"
        else:
            atempo_chain = f"atempo={speed:.4f}"

        vf = f"setpts={1/speed:.4f}*PTS"
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-vf", vf,
            "-af", atempo_chain,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            "-movflags", "+faststart",
            output_path,
        ]
    else:
        # Durations match closely — simple mux
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            "-movflags", "+faststart",
            output_path,
        ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"Final compose failed:\n{result.stderr[-1000:]}")

    final_dur = _probe_duration(output_path)
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"  Final video: {final_dur:.1f}s, {size_mb:.1f} MB -> {output_path}")

    return output_path


# ══════════════════════════════════════════════════════════════
# Caption rendering (v3 TikTok-style fancy captions)
# ══════════════════════════════════════════════════════════════

def _split_phrases(text: str) -> List[str]:
    """Split text into display phrases on punctuation and conjunctions."""
    raw_chunks = re.split(r'(?<=[,;:.!?])\s+', text)
    chunks = [c.strip() for c in raw_chunks if c.strip()]
    phrases = []
    conjunctions = {'and', 'but', 'or', 'so', 'yet', 'with', 'while',
                    'which', 'that', 'than', 'also', 'because', 'when'}

    for chunk in chunks:
        words = chunk.split()
        if len(words) <= 4:
            phrases.append(" ".join(words))
        elif len(words) <= 6:
            split_at = -1
            for i, w in enumerate(words):
                if w.lower() in conjunctions and 2 <= i <= len(words) - 2:
                    split_at = i
                    break
            if split_at > 0:
                phrases.append(" ".join(words[:split_at]))
                phrases.append(" ".join(words[split_at:]))
            else:
                mid = len(words) // 2
                phrases.append(" ".join(words[:mid]))
                phrases.append(" ".join(words[mid:]))
        else:
            i = 0
            while i < len(words):
                if len(words) - i <= 4:
                    phrases.append(" ".join(words[i:]))
                    break
                ba = i + 3
                for j in range(i + 2, min(i + 5, len(words))):
                    if words[j].lower() in conjunctions:
                        ba = j
                        break
                phrases.append(" ".join(words[i:ba]))
                i = ba
    return phrases


def _wrap_text(text: str, font, max_width: int) -> List[str]:
    """Word-wrap text to fit within max_width."""
    words = text.split()
    lines = []
    current = []
    for w in words:
        test = " ".join(current + [w])
        if font.getbbox(test)[2] <= max_width:
            current.append(w)
        else:
            if current:
                lines.append(" ".join(current))
            current = [w]
    if current:
        lines.append(" ".join(current))
    return lines


def _draw_rounded_rect(draw, xy, radius, fill=None, outline=None, outline_width=0):
    """Draw a rounded rectangle."""
    x0, y0, x1, y1 = xy
    r = radius
    if fill:
        draw.rectangle([x0 + r, y0, x1 - r, y1], fill=fill)
        draw.rectangle([x0, y0 + r, x1, y1 - r], fill=fill)
        draw.ellipse([x0, y0, x0 + 2 * r, y0 + 2 * r], fill=fill)
        draw.ellipse([x1 - 2 * r, y0, x1, y0 + 2 * r], fill=fill)
        draw.ellipse([x0, y1 - 2 * r, x0 + 2 * r, y1], fill=fill)
        draw.ellipse([x1 - 2 * r, y1 - 2 * r, x1, y1], fill=fill)
    if outline and outline_width > 0:
        for i in range(outline_width):
            o = i
            draw.line([x0 + r, y0 + o, x1 - r, y0 + o], fill=outline)
            draw.line([x0 + r, y1 - o, x1 - r, y1 - o], fill=outline)
            draw.line([x0 + o, y0 + r, x0 + o, y1 - r], fill=outline)
            draw.line([x1 - o, y0 + r, x1 - o, y1 - r], fill=outline)


def _build_teleprompter_frame(
    lines: List[tuple],    # [(text, line_height, phrase_idx), ...]
    active_line_idx: int,
    font_active,
    w: int,
    h: int,
) -> "Image.Image":
    """Build a single transparent RGBA frame with single-line caption.

    Design (v7 — single-line mode):
    - Only ONE line visible: the active (spoken) line.
    - Active line: white text, pill background, NO border/glow. Anchored at TARGET_Y.
    - No other lines visible — no next line preview.
    - Text is vertically centered inside the pill using font metrics.
    """
    from PIL import Image, ImageDraw

    target_y = int(h * TARGET_Y)
    max_width = w - 2 * MARGIN

    if not lines or active_line_idx >= len(lines):
        return Image.new("RGBA", (w, h), (0, 0, 0, 0))

    text, lh, pidx = lines[active_line_idx]
    font = font_active

    # Measure text with font metrics for proper vertical centering
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    pw = tw + 2 * PILL_PAD_X
    ph = th + 2 * PILL_PAD_Y
    px = (w - pw) // 2

    # Center the pill vertically around target_y
    py = target_y - ph // 2

    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw pill background
    _draw_rounded_rect(draw, [px, py, px + pw, py + ph], PILL_RADIUS,
                       fill=(*COLOR_PILL_BG, PILL_ALPHA_ACTIVE))

    # Center text horizontally
    tx = (w - tw) // 2
    # Center text vertically inside pill: account for font baseline offset
    ty = py + (ph - th) // 2 - bbox[1]

    # Subtle shadow for depth (no outline)
    draw.text((tx + 1, ty + 1), text, fill=COLOR_ACTIVE_SHADOW, font=font)
    draw.text((tx, ty), text, fill=COLOR_ACTIVE_TEXT, font=font)

    return img


def _run_silencedetect(audio_path: str, noise_db: float, min_duration: float) -> List[Tuple[float, float]]:
    """Single silencedetect pass; returns (start, end) pauses or [] on failure."""
    try:
        cmd = [
            "ffmpeg", "-i", audio_path,
            "-af", f"silencedetect=noise={noise_db}dB:d={min_duration}",
            "-f", "null", "-",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        starts: List[float] = []
        ends: List[float] = []
        for line in result.stderr.splitlines():
            if "silence_start" in line:
                starts.append(float(line.split("silence_start: ")[1].strip()))
            elif "silence_end" in line:
                ends.append(float(line.split("silence_end: ")[1].split("|")[0].strip()))
        pauses = []
        for i, s in enumerate(starts):
            e = ends[i] if i < len(ends) else s + min_duration
            pauses.append((s, e))
        # Merge pauses separated by only a sliver of speech (< 0.15s)
        merged = []
        for p in pauses:
            if merged and p[0] - merged[-1][1] < 0.15:
                merged[-1] = (merged[-1][0], max(merged[-1][1], p[1]))
            else:
                merged.append(p)
        return merged
    except Exception:
        return []


def _detect_pauses(audio_path: str, min_duration: float = 0.22) -> List[Tuple[float, float]]:
    """Detect real pauses (silences) in the TTS audio via ffmpeg silencedetect.

    The threshold is adaptive: TTS backends normalize to very different levels
    (Chatterbox ≈ −1 dB peak, edge-tts ≈ −4 dB peak), so a fixed absolute dB
    floor misses pauses on quieter output. Tries −32 → −42 → −50 dB and returns
    the first pass that finds pauses. Returns [] if the audio cannot be analyzed
    or contains no pauses >= min_duration.
    """
    for noise_db in (-32.0, -42.0, -50.0):
        pauses = _run_silencedetect(audio_path, noise_db, min_duration)
        if pauses:
            return pauses
    return []


def _is_phrase_end(word: str) -> bool:
    """True if the word terminates a display phrase (any of , ; : . ! ? …)."""
    stripped = word.strip('"\'”’)]}')
    if not stripped:
        return False
    return stripped[-1] in ',;:.!?…'


def _is_sentence_end(word: str) -> bool:
    """True if the word terminates a sentence ('.', '!', '?', '…')."""
    stripped = word.strip('"\'”’)]}')
    return stripped.endswith(('.', '!', '?', '…')) or stripped.endswith('."') or stripped.endswith('!"') or stripped.endswith('?"')



def _build_word_times(words: List[str], audio_duration: float,
                      pauses: List[Tuple[float, float]],
                      micro: Optional[List[Tuple[float, float]]] = None,
                      anchor_words: Optional[List[int]] = None) -> List[Tuple[float, float]]:
    """Word-level timing, anchored to real audio pauses.

    Baseline: each word gets a slot weighted by its LENGTH (long words take
    longer to speak than "and" — a plain equal-slot split drifts by >1s inside
    long speech blocks, measured 2026-09-15); punctuation pauses are absorbed
    into the last word of a phrase so ranges stay contiguous. The timeline is
    rescaled to audio_duration.

    Anchoring: every phrase-final word (`,` `;` `:` `.` `!` `?`) is pinned to a
    real pause in the audio. `micro` (pauses >= ~0.05s) is preferred when given:
    the Snoop clone marks phrase boundaries with 60-110ms micro-pauses, and the
    coarse 0.22s list misses ALL of them inside a long block — that was the
    "captions run ~1-1.8s ahead" bug (2026-09-15). Falls back to the coarse
    pause list, then to linear timing.

    ⚠️ Measured drift this fixes (2026-09-15 archaeology Short, 61 words):
    "across ancient Britain," was spoken at ~3.8s but captioned from ~2.0s.
    """
    n = len(words)
    if n == 0 or audio_duration <= 0:
        return []

    # ── Baseline slots: length-weighted (characters correlate with speech time) ──
    base = audio_duration / n
    raw_ends: List[float] = []
    cum = 0.0
    for w in words:
        # 3-char words ~1 unit, 8-char words ~1.6 units (sub-linear: long words
        # are not spoken proportionally slower, but noticeably slower than "a").
        weight = base * (max(len(w.strip('.,;:!?"\'')), 2) / 4.2) ** 0.7
        if _is_sentence_end(w):
            cum += weight + 0.35
        elif w.endswith((',', ';', ':', '—', '-')) or w.endswith((',"', ';"', ':"')):
            cum += weight + 0.20
        else:
            cum += weight
        raw_ends.append(cum)
    if raw_ends[-1] <= 0:
        return [(0.0, audio_duration)] * n
    scale = audio_duration / raw_ends[-1]
    lin_ends = [e * scale for e in raw_ends]

    # ── Anchor phrase-final words to real pauses ──
    # Anchor candidates = the words where the VISIBLE caption changes. That is
    # every sentence/comma end (`,` `;` `:` `.` `!` `?`) AND every display-chunk
    # boundary passed in via `anchor_words` (the renderer splits the script into
    # 3-4 word caption chunks; their boundaries need anchors too, otherwise the
    # captions inside a long speech block are only interpolated).
    # Prefer the fine-grained (micro) pause list when available.
    pool = micro if micro else pauses
    if anchor_words is not None:
        phrase_idxs = sorted(set(anchor_words) | {i for i, w in enumerate(words) if _is_phrase_end(w)})
    else:
        phrase_idxs = [i for i, w in enumerate(words) if _is_phrase_end(w)]
    anchor_idx: List[int] = []          # word indices pinned to a pause
    anchor_pause: List[Tuple[float, float]] = []  # matching pause (start, end)
    pi = 0
    prev_anchored_word = -1
    for si in phrase_idxs:
        # Linear estimate of where this phrase boundary lands
        est = lin_ends[si]
        tol = 1.0 if micro else 1.6
        if anchor_words is not None:
            tol = min(tol, 0.85)    # dense anchors: keep them tight & honest
        while pi < len(pool) and pool[pi][1] < est - tol:
            pi += 1
        if pi >= len(pool):
            break
        # Among the pauses inside the tolerance window pick the best one:
        # longer pauses win (they are real boundaries), with a mild preference
        # for the one closest to the estimate.
        best = None
        best_score = -1.0
        for k in range(pi, len(pool)):
            p_start, p_end = pool[k]
            if p_start - est > tol:
                break
            dur = p_end - p_start
            score = dur - 0.25 * abs(p_start - est)
            if p_end > audio_duration - 0.15:   # trailing pause: never an anchor
                continue
            if score > best_score:
                best_score = score
                best = k
        if best is None:
            continue
        p_start, p_end = pool[best]
        anchor_idx.append(si)
        anchor_pause.append((p_start, p_end))
        pi = best + 1

    # ── Plausibility filter ──
    # Drop anchors that would squeeze a chunk into less time than speech can
    # plausibly need (~0.11s per word). Without this, two micro-pauses lying
    # close together produce a 0.2s block for three words — the caption then
    # flickers through several chunks instantly (seen 2026-09-15).
    keep_idx: List[int] = []
    keep_pause: List[Tuple[float, float]] = []
    prev_w, prev_t = 0, 0.0
    for ai, (ps, pe) in zip(anchor_idx, anchor_pause):
        need = 0.11 * (ai + 1 - prev_w)
        if ps - prev_t < max(need, 0.18):
            continue
        keep_idx.append(ai)
        keep_pause.append((ps, pe))
        prev_w, prev_t = ai + 1, pe
    anchor_idx, anchor_pause = keep_idx, keep_pause

    # ── Distribute word slots per speech block (anchors = real pauses) ──
    # Each anchor pins a phrase-final word to the START of a real pause. Words
    # between two anchors live in the speech window [pause_end, next_pause_start]
    # — pauses become REAL gaps (no caption word ever covers silence) and each
    # block's words are scaled to that block's actual speech time, so fast or
    # slow sentences get proportional slots instead of a global average.
    if not anchor_idx:
        # No anchors (no pauses found or none matched): pure linear fallback
        word_times = [(0.0 if i == 0 else lin_ends[i - 1], lin_ends[i])
                      for i in range(n)]
        return word_times

    # Speech blocks: (first_word_idx, last_word_idx, window_start, window_end)
    blocks: List[Tuple[int, int, float, float]] = []
    prev_word = 0
    prev_t = 0.0
    for k, ai in enumerate(anchor_idx):
        blocks.append((prev_word, ai, prev_t, anchor_pause[k][0]))
        prev_word = ai + 1
        prev_t = anchor_pause[k][1]
    if prev_word < n:
        blocks.append((prev_word, n - 1, prev_t, audio_duration))

    word_times: List[Tuple[float, float]] = []
    for (w0, w1, t0, t1) in blocks:
        r0 = raw_ends[w0 - 1] if w0 > 0 else 0.0
        span = raw_ends[w1] - r0
        if span <= 0:
            span = 1.0
        for i in range(w0, w1 + 1):
            end = t0 + (raw_ends[i] - r0) / span * (t1 - t0)
            if i == 0:
                start = 0.0
            elif i == w0 and w0 > 0:
                # First word after an anchored pause: starts when speech resumes
                start = t0
            else:
                start = word_times[-1][1]
            word_times.append((start, max(end, start)))
    return word_times


def step_render_captions(
    script_text: str,
    audio_duration: float,
    resolution: Tuple[int, int],
    audio_path: Optional[str] = None,
) -> str:
    """Render caption overlay as transparent PNG sequence → qtrle video with alpha.

    v6 Two-Line Teleprompter:
    - Pre-computes ALL display lines from all phrases
    - Only renders 2 lines per frame: active (white) + next (gray)
    - All other lines (past + further future) are completely hidden
    - Active line stays at TARGET_Y with continuous scroll offset
    - Lines smoothly enter/exit the visible area with no discrete jumps

    Returns:
        Path to the caption video (qtrle with alpha channel).
    """
    from PIL import ImageFont

    w, h = resolution
    phrases = _split_phrases(script_text)
    n_phrases = len(phrases)
    words = script_text.split()
    n_words = len(words)

    print(f"  Phrases: {n_phrases}, Words: {n_words}")

    # ── Pre-compute ALL display lines (entire script, wrapped) ──
    font_active = ImageFont.truetype(FONT_FILE, FONT_SIZE_ACTIVE)
    max_width = w - 2 * MARGIN

    lines = []           # [(text, line_height, phrase_idx), ...]
    word_to_line = []    # word_idx → line_idx in `lines`

    for pi, phrase in enumerate(phrases):
        phrase_words = phrase.split()
        # Measure with active font (it's larger, so line heights are conservative)
        bbox = font_active.getbbox(phrase)
        th = bbox[3] - bbox[1]
        pill_h = th + 2 * PILL_PAD_Y
        lh = pill_h + 4
        wrapped = _wrap_text(phrase, font_active, max_width)
        for li, wline in enumerate(wrapped):
            if li > 0:
                wlh = max(th + PILL_PAD_Y + 2, pill_h)
            else:
                wlh = lh
            lines.append((wline, wlh, pi))
            nw_in_line = len(wline.split())
            word_to_line.extend([len(lines) - 1] * nw_in_line)

    if not lines:
        return _empty_caption_video(audio_duration, resolution)

    print(f"  Pre-computed {len(lines)} display lines, {len(word_to_line)} word mappings")

    # ── Word-level timing ──
    # Each word gets an equal slot. Punctuation pauses are absorbed into the
    # last word of a phrase so there are NO gaps between word ranges.
    # This prevents get_active_line from jumping back to word 0.
    # When the real TTS audio file is available, sentence boundaries are
    # additionally ANCHORED to the pauses detected in that audio (silencedetect),
    # so captions stay inside the actual speech spans instead of drifting.
    pauses = _detect_pauses(audio_path) if audio_path else []
    # Fine-grained pause list (2026-09-15): the Snoop clone separates phrases
    # with 60-110ms micro-pauses; the coarse 0.22s list saw none of them inside
    # a long speech block, so captions ran up to ~1.8s ahead of the voice.
    micro = _detect_pauses(audio_path, min_duration=0.05) if audio_path else []
    if micro and pauses and len(micro) <= len(pauses):
        micro = []
    # Words where the VISIBLE caption changes = last word of each display chunk.
    line_end_words = [i for i in range(len(word_to_line) - 1)
                      if word_to_line[i] != word_to_line[i + 1]]
    word_times = _build_word_times(words, audio_duration, pauses, micro, line_end_words)
    print(f"  Pauses detected: {len(pauses)}"
          + (f" (+{len(micro)} micro-pauses for anchoring)" if micro else "")
          + (" → word timing pause-anchored" if (pauses or micro) else " → word timing linear (no pauses found)"))

    def get_active_line(t: float) -> int:
        """Find which display line is active at time t (based on word timing)."""
        if not word_times:
            return 0
        # Find active word
        if t >= word_times[-1][1]:
            wi = len(word_times) - 1
        else:
            wi = 0
            for i, (ws, we) in enumerate(word_times):
                if ws <= t < we:
                    wi = i
                    break
        # Map word to line
        if wi < len(word_to_line):
            return word_to_line[wi]
        return len(lines) - 1

    # ── Render caption frames ──
    n_cap_frames = int(audio_duration * CAPTION_FPS) + 2
    cap_dir = tempfile.mkdtemp(prefix="shorts_caps_")
    cap_frame_paths = []

    print(f"  Rendering {n_cap_frames} caption frames at {CAPTION_FPS}fps...")
    t0 = time.time()

    # Track the furthest active line reached — never go back
    max_active_line = 0

    for fi in range(n_cap_frames):
        t = fi / CAPTION_FPS
        if t >= audio_duration:
            t = audio_duration - 0.01
        active_line = get_active_line(t)
        # Monotonic: active line never decreases
        if active_line < max_active_line:
            active_line = max_active_line
        max_active_line = max(max_active_line, active_line)
        cap_img = _build_teleprompter_frame(
            lines, active_line, font_active, w, h
        )
        fp = os.path.join(cap_dir, f"cap_{fi:05d}.png")
        cap_img.save(fp, "PNG")
        cap_frame_paths.append(fp)

    elapsed = time.time() - t0
    print(f"  Caption frames rendered: {len(cap_frame_paths)} in {elapsed:.1f}s")

    # Encode as qtrle with alpha (NOT prores_ks — timeout on RPi)
    cap_video_path = tempfile.mktemp(prefix="shorts_caps_", suffix=".mov")
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(CAPTION_FPS),
        "-i", os.path.join(cap_dir, "cap_%05d.png"),
        "-c:v", "qtrle",
        "-pix_fmt", "argb",
        "-shortest",
        cap_video_path,
    ]
    _run_ffmpeg(cmd, timeout=120, label="caption_qtrle_encode")

    # Cleanup PNG frames
    shutil.rmtree(cap_dir, ignore_errors=True)

    return cap_video_path


def _empty_caption_video(audio_duration: float, resolution: Tuple[int, int]) -> str:
    """Return a minimal placeholder caption video when there's nothing to render."""
    from PIL import Image
    w, h = resolution
    cap_dir = tempfile.mkdtemp(prefix="shorts_caps_")
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    fp = os.path.join(cap_dir, "cap_00000.png")
    img.save(fp, "PNG")
    cap_video_path = tempfile.mktemp(prefix="shorts_caps_", suffix=".mov")
    cmd = [
        "ffmpeg", "-y",
        "-framerate", "1",
        "-i", fp,
        "-c:v", "qtrle",
        "-pix_fmt", "argb",
        "-t", str(audio_duration),
        cap_video_path,
    ]
    _run_ffmpeg(cmd, timeout=30, label="empty_caption_qtrle")
    shutil.rmtree(cap_dir, ignore_errors=True)
    return cap_video_path


def step_final_compose(
    video_path: str,
    caption_video_path: str,
    audio_path: str,
    output_path: str,
    fps: int,
    timeout: int = 180,
) -> str:
    """Compose final video: overlay caption qtrle onto crossfaded video, add audio.

    Pipeline:
        [crossfaded_video] + [caption_qtrle] → overlay → [video_with_captions]
        [video_with_captions] + [tts_audio] → mux → final MP4
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", caption_video_path,
        "-i", audio_path,
        "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto[outv]",
        "-map", "[outv]",
        "-map", "2:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-r", str(fps),
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        "-movflags", "+faststart",
        output_path,
    ]

    print(f"  Composing final: video + captions + audio -> {output_path}")
    _run_ffmpeg(cmd, timeout=timeout, label="final_compose")

    final_dur = _probe_duration(output_path)
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"  Final video: {final_dur:.1f}s, {size_mb:.1f} MB")
    return output_path


def generate_shorts(
    query: str,
    output_path: str,
    script_text: Optional[str] = None,
    voice: str = DEFAULT_VOICE,
    tts: str = "edge",
    n_images: int = 6,
    n_videos: int = 0,
    segment_duration: float = DEFAULT_SEGMENT_DURATION,
    crossfade_duration: float = DEFAULT_CROSSFADE_DURATION,
    zoom_range: Tuple[float, float] = DEFAULT_KB_ZOOM,
    resolution: Tuple[int, int] = DEFAULT_RESOLUTION,
    fps: int = DEFAULT_FPS,
    cleanup: bool = True,
) -> str:
    """Full pipeline: Pexels -> Ken Burns -> Crossfade -> Final MP4.

    Args:
        query: Topic/keywords for Pexels search.
        output_path: Path for the final output MP4.
        script_text: Optional custom script. If None, uses a template.
        voice: edge-tts voice name.
        n_images: Number of images to fetch.
        n_videos: Number of videos to fetch (0 = images only).
        segment_duration: Duration per image segment in seconds.
        crossfade_duration: Crossfade duration between segments.
        zoom_range: (start_zoom, end_zoom) for Ken Burns.
        resolution: Target (width, height).
        fps: Target frames per second.
        cleanup: If True, remove temp files after completion.

    Returns:
        Path to the final output video.
    """
    timer = StepTimer()
    tmp_dirs = []

    try:
        # ── Generate or use provided script ──
        if not script_text:
            script_text = DEFAULT_SCRIPT_TEMPLATE.format(query=query)
        print(f"Script ({len(script_text.split())} words): {script_text[:100]}...")

        # ── Step 1: Fetch assets from Pexels ──
        assets = timer.run("Fetch Pexels assets", step_fetch_assets, query, n_images, n_videos)
        image_paths = assets["images"]
        if assets.get("_tmp_dir"):
            tmp_dirs.append(assets["_tmp_dir"])

        if len(image_paths) < 2:
            raise RuntimeError(
                f"Need at least 2 images, got {len(image_paths)}. "
                "Try a different query or check Pexels API key."
            )

        # ── Step 2: Generate TTS audio ──
        audio_path, audio_duration = timer.run(
            "Generate TTS audio", step_generate_tts, script_text, voice, tts
        )

        # Adjust segment duration to fit audio
        n_segments = len(image_paths)
        total_crossfade_time = (n_segments - 1) * crossfade_duration
        available_video_time = audio_duration + total_crossfade_time
        adjusted_seg_duration = available_video_time / n_segments

        # Clamp to reasonable range
        adjusted_seg_duration = max(2.0, min(8.0, adjusted_seg_duration))
        print(f"  Adjusted segment duration: {adjusted_seg_duration:.2f}s "
              f"(audio={audio_duration:.1f}s, {n_segments} segments)")

        # ── Step 3: Ken Burns + Crossfade ──
        kb_video = timer.run(
            "Ken Burns + Crossfade",
            step_ken_burns,
            image_paths,
            adjusted_seg_duration,
            zoom_range,
            resolution,
            fps,
            crossfade_duration,
            None,  # No audio yet — mux in final step
        )

        # ── Step 4: Render captions ──
        caption_video = timer.run(
            "Render captions",
            step_render_captions,
            script_text, audio_duration, resolution, audio_path,
        )

        # ── Step 5: Final compose (video + captions + audio) ──
        final_path = timer.run(
            "Final compose",
            step_final_compose,
            kb_video, caption_video, audio_path, output_path, fps,
        )

        # ── Verify output ──
        final_dur = _probe_duration(final_path)
        size_mb = os.path.getsize(final_path) / (1024 * 1024)

        print(f"\n{'='*60}")
        print(f"  DONE: {final_path}")
        print(f"  Duration: {final_dur:.1f}s | Size: {size_mb:.1f} MB")
        print(f"  Resolution: {resolution[0]}x{resolution[1]} | FPS: {fps}")
        print(f"{'='*60}")

        if final_dur > MAX_DURATION:
            print(f"  WARNING: Video is {final_dur:.1f}s (exceeds {MAX_DURATION}s YouTube Shorts limit)")

        timer.summary()
        return final_path

    finally:
        if cleanup:
            for d in tmp_dirs:
                shutil.rmtree(d, ignore_errors=True)
            # Clean up intermediate files
            for p in [kb_video, caption_video] if 'kb_video' in dir() and 'caption_video' in dir() else []:
                try:
                    os.remove(p)
                except OSError:
                    pass
            if 'audio_path' in dir():
                try:
                    os.remove(audio_path)
                except OSError:
                    pass


def main():
    parser = argparse.ArgumentParser(
        description="Generate a YouTube Short from a topic query",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 generate_shorts.py --query "nature" --output nature.mp4
  python3 generate_shorts.py --query "ocean waves" --duration 30 --voice en-US-BrianNeural
  python3 generate_shorts.py --query "space" --script "Did you know space is fascinating?" --images 8
        """,
    )
    parser.add_argument("--query", required=True, help="Topic/keywords for Pexels search")
    parser.add_argument("--output", "-o", default="short_output.mp4", help="Output MP4 path")
    parser.add_argument("--script", default=None, help="Custom TTS script text")
    parser.add_argument("--voice", default=DEFAULT_VOICE, help=f"TTS voice (default: {DEFAULT_VOICE}; chirp voices: Puck, Kore, Charon, ...; kokoro voices: af_heart, am_michael, ...; chatterbox: optional path to a reference WAV for voice cloning)")
    parser.add_argument("--tts", default="edge", choices=["edge", "chirp", "kokoro", "chatterbox"],
                        help="TTS backend: edge (Microsoft Neural), chirp (Gemini Chirp 3 HD, default voice Puck), kokoro (local, default voice af_heart) or chatterbox (local, GPU recommended)")
    parser.add_argument("--images", type=int, default=6, help="Number of images (default: 6)")
    parser.add_argument("--videos", type=int, default=0, help="Number of videos (default: 0)")
    parser.add_argument("--segment-duration", type=float, default=DEFAULT_SEGMENT_DURATION)
    parser.add_argument("--crossfade", type=float, default=DEFAULT_CROSSFADE_DURATION)
    parser.add_argument("--zoom-start", type=float, default=DEFAULT_KB_ZOOM[0])
    parser.add_argument("--zoom-end", type=float, default=DEFAULT_KB_ZOOM[1])
    parser.add_argument("--fps", type=int, default=DEFAULT_FPS)
    parser.add_argument("--width", type=int, default=DEFAULT_RESOLUTION[0])
    parser.add_argument("--height", type=int, default=DEFAULT_RESOLUTION[1])
    parser.add_argument("--no-cleanup", action="store_true", help="Keep temp files for debugging")

    args = parser.parse_args()

    resolution = (args.width, args.height)
    zoom_range = (args.zoom_start, args.zoom_end)
    if args.tts == "chirp" and args.voice == DEFAULT_VOICE:
        args.voice = "Puck"
    if args.tts == "kokoro" and args.voice == DEFAULT_VOICE:
        args.voice = "af_heart"

    print(f"generate_shorts.py — YouTube Shorts Pipeline")
    print(f"  Query: {args.query}")
    print(f"  Output: {args.output}")
    print(f"  Resolution: {resolution[0]}x{resolution[1]}@{args.fps}fps")
    print(f"  Images: {args.images}, Videos: {args.videos}")
    print(f"  Segment: {args.segment_duration}s, Crossfade: {args.crossfade}s")
    print(f"  Zoom: {zoom_range}, TTS: {args.tts}, Voice: {args.voice}")

    try:
        result = generate_shorts(
            query=args.query,
            output_path=args.output,
            script_text=args.script,
            voice=args.voice,
            tts=args.tts,
            n_images=args.images,
            n_videos=args.videos,
            segment_duration=args.segment_duration,
            crossfade_duration=args.crossfade,
            zoom_range=zoom_range,
            resolution=resolution,
            fps=args.fps,
            cleanup=not args.no_cleanup,
        )
        print(f"\nSuccess: {result}")
        sys.exit(0)
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
