#!/usr/bin/env python3
"""
generate_shorts_v2.py — YouTube Shorts builder v2: Mixed media (videos + images).

Key new features vs v1:
  - Fetches BOTH Pexels videos AND images
  - Videos used as-is (normalized to target resolution/fps)
  - Images get Ken Burns pan-and-zoom treatment
  - Segments interleaved: video → image → video → image ...
  - Crossfade transitions between ALL segments
  - Fancy TikTok-style animated captions (pill backgrounds, glow, word-level timing)
  - TTS voiceover with edge-tts
  - Final compose → 1080x1920 MP4 ready for YouTube Shorts

Usage:
    python3 generate_shorts_v2.py --query "nature" --output nature_short.mp4
    python3 generate_shorts_v2.py --query "ocean waves" --images 4 --videos 2

Requirements:
    - FFmpeg + ffprobe (system)
    - Python 3.10+ with Pillow
    - edge-tts at /opt/data/home/.local/bin/edge-tts
    - Pexels API key (env var PEXELS_API_KEY or in ~/.env / /opt/data/.env)
"""

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── Script directory for local imports ──
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

# ── Defaults ──
DEFAULT_RESOLUTION = (1080, 1920)
DEFAULT_FPS = 24
DEFAULT_CROSSFADE_DURATION = 0.5
DEFAULT_KB_ZOOM = (1.0, 1.08)
DEFAULT_VOICE = "en-US-BrianNeural"
DEFAULT_N_IMAGES = 6
DEFAULT_N_VIDEOS = 2
EDGE_TTS_PATH = os.environ.get("EDGE_TTS_PATH", "/opt/data/home/.local/bin/edge-tts")
MAX_DURATION = 60  # YouTube Shorts limit

# ── Caption style constants (v5 Smooth Teleprompter) ──
FONT_FILE = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
CAPTION_FPS = 12

# Visible area: keep captions above YouTube's title bar (~bottom 12%)
VISIBLE_BOTTOM = 0.88    # bottom of caption area (88% from top = 12% from bottom)
TARGET_Y = 0.72          # active (focus) line stays at ~72% of frame height

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


# ══════════════════════════════════════════════════════════════
# Utility functions
# ══════════════════════════════════════════════════════════════

def _probe_duration(path: str) -> float:
    """Get video/audio duration via ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
        capture_output=True, text=True, timeout=15,
    )
    return float(json.loads(result.stdout)["format"]["duration"])


def _probe_video_info(path: str) -> dict:
    """Get full video stream info via ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_streams", "-show_format", path],
        capture_output=True, text=True, timeout=15,
    )
    return json.loads(result.stdout)


def _run_ffmpeg(cmd: List[str], timeout: int = 120, label: str = "") -> None:
    """Run ffmpeg and raise on failure."""
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg failed{f' ({label})' if label else ''}:\n{result.stderr[-800:]}"
        )


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


# ══════════════════════════════════════════════════════════════
# Step 1: Fetch mixed assets from Pexels (videos + images)
# ══════════════════════════════════════════════════════════════

def step_fetch_mixed_assets(query: str, n_images: int = 6, n_videos: int = 2) -> Dict:
    """Fetch both photos and videos from Pexels.

    Returns:
        Dict with keys:
            images: list of local image paths
            videos: list of local video paths (already .mp4)
            _tmp_dir: temp directory for downloaded assets
    """
    from pexels import search_photos, search_videos, download_photo, download_video

    result = {"images": [], "videos": [], "video_meta": []}

    tmp_dir = tempfile.mkdtemp(prefix="shorts_v2_assets_")
    result["_tmp_dir"] = tmp_dir

    # ── Fetch photos ──
    print(f"  Searching Pexels for '{query}' ({n_images} images)...")
    photos = search_photos(query, n=n_images + 4, orientation="portrait")
    photos = photos[:n_images]
    if not photos:
        raise RuntimeError(f"No Pexels photo results for '{query}'")
    print(f"  Found {len(photos)} photos")

    for i, photo in enumerate(photos):
        path = os.path.join(tmp_dir, f"img_{i:03d}.jpg")
        try:
            download_photo(photo["url"], path)
            result["images"].append(path)
        except Exception as e:
            print(f"  Warning: failed to download image {i}: {e}", file=sys.stderr)

    print(f"  Downloaded {len(result['images'])} images")

    # ── Fetch videos ──
    print(f"  Searching Pexels for '{query}' ({n_videos} videos)...")
    try:
        video_results = search_videos(query, n=n_videos + 3, orientation="portrait")
        video_results = video_results[:n_videos]
    except Exception as e:
        print(f"  Warning: video search failed: {e}", file=sys.stderr)
        video_results = []

    for i, video in enumerate(video_results):
        path = os.path.join(tmp_dir, f"vid_{i:03d}.mp4")
        try:
            download_video(video["url"], path, timeout=120)
            if os.path.getsize(path) < 1000:
                print(f"  Warning: video {i} too small, skipping", file=sys.stderr)
                os.remove(path)
                continue
            result["videos"].append(path)
            result["video_meta"].append(video)
        except Exception as e:
            print(f"  Warning: failed to download video {i}: {e}", file=sys.stderr)

    print(f"  Downloaded {len(result['videos'])} videos")
    print(f"  Total assets: {len(result['images'])} images + {len(result['videos'])} videos")

    return result


# ══════════════════════════════════════════════════════════════
# Step 2: Generate TTS audio
# ══════════════════════════════════════════════════════════════

def step_generate_tts(script_text: str, voice: str) -> Tuple[str, float]:
    """Generate TTS audio using edge-tts.

    Returns:
        Tuple of (audio_path, duration_seconds).
    """
    audio_path = tempfile.mktemp(prefix="shorts_v2_tts_", suffix=".mp3")
    print(f"  Generating TTS ({voice})...")
    print(f"  Script: {script_text[:100]}...")

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


# ══════════════════════════════════════════════════════════════
# Segment preparation: normalize videos + Ken Burns for images
# ══════════════════════════════════════════════════════════════

def _normalize_video_clip(
    input_path: str,
    output_path: str,
    resolution: Tuple[int, int],
    fps: int,
    target_duration: float,
    timeout: int = 60,
) -> str:
    """Re-encode a video clip to common format for xfade concatenation.

    Normalizes: resolution, fps, pixel_format, codec.
    Trims or loops the video to exactly match target_duration.
    Strips audio (TTS is the only audio track).
    """
    w, h = resolution
    # -t trims to target_duration; for short videos, use stream_loop to loop
    cmd = [
        "ffmpeg", "-y", "-stream_loop", "-1", "-i", input_path,
        "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
               f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,"
               f"setsar=1,fps={fps}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-an",
        "-t", str(target_duration),
        output_path,
    ]
    _run_ffmpeg(cmd, timeout=timeout, label=f"normalize {os.path.basename(input_path)}")
    return output_path


def _ken_burns_image(
    image_path: str,
    output_path: str,
    duration: float,
    zoom_start: float,
    zoom_end: float,
    resolution: Tuple[int, int],
    fps: int = 30,
    timeout: int = 60,
) -> str:
    """Apply Ken Burns zoom to a single image → video segment.

    Uses ffmpeg zoompan filter with smooth ease-in-out interpolation
    (Hermite: 3t²-2t³) to eliminate jitter on large screens.
    Renders at 30fps internally for smoother motion.
    """
    w, h = resolution
    n_frames = int(duration * fps)
    z_diff = zoom_end - zoom_start
    # Smoothstep easing: 3t²-2t³ for buttery smooth zoom
    ease_expr = f"3*(on/{n_frames})^2-2*(on/{n_frames})^3"
    z_expr = f"if(eq(on,0),{zoom_start},{zoom_start}+{z_diff}*({ease_expr}))"

    vf = (
        f"zoompan=z='{z_expr}':"
        f"x='iw/2-(iw/zoom/2)':"
        f"y='ih/2-(ih/zoom/2)':"
        f"d={n_frames}:"
        f"s={w}x{h}:"
        f"fps={fps}"
    )

    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", image_path,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-t", str(duration), "-an",
        output_path,
    ]
    _run_ffmpeg(cmd, timeout=timeout, label=f"ken_burns {os.path.basename(image_path)}")
    return output_path


def step_prepare_segments(
    image_paths: List[str],
    video_paths: List[str],
    segment_duration: float,
    zoom_range: Tuple[float, float],
    resolution: Tuple[int, int],
    fps: int,
) -> List[Dict]:
    """Prepare all segments: Ken Burns for images, normalize for videos.

    Interleaves: video, image, video, image... starting with video if available.
    Each segment has the same duration.

    Returns:
        List of dicts: [{type: 'video'|'image', path: str, duration: float}, ...]
    """
    tmp_dir = tempfile.mkdtemp(prefix="shorts_v2_segs_")
    segments = []

    # Build interleaved list of (type, source_path) tuples
    # Pattern: video first, then alternate
    n_vids = len(video_paths)
    n_imgs = len(image_paths)
    interleaved = []
    vi = ii = 0

    # Start with a video if available for immediate visual impact
    while vi < n_vids or ii < n_imgs:
        if vi < n_vids:
            interleaved.append(("video", video_paths[vi]))
            vi += 1
        if ii < n_imgs:
            interleaved.append(("image", image_paths[ii]))
            ii += 1

    print(f"  Preparing {len(interleaved)} segments ({n_vids} videos + {n_imgs} images)")
    print(f"  Segment duration: {segment_duration}s each")
    print(f"  Total video: {len(interleaved) * segment_duration:.1f}s "
          f"(crossfades will overlap)")

    zs, ze = zoom_range

    for i, (seg_type, src_path) in enumerate(interleaved):
        seg_path = os.path.join(tmp_dir, f"seg_{i:03d}.mp4")

        if seg_type == "video":
            # Normalize the Pexels video to our target format
            print(f"  Segment {i}: [VIDEO] normalize {os.path.basename(src_path)}")
            _normalize_video_clip(src_path, seg_path, resolution, fps, segment_duration)
        else:
            # Apply Ken Burns: alternate zoom in/out
            if i % 2 == 0:
                z_start, z_end = zs, ze
            else:
                z_start, z_end = ze, zs
            print(f"  Segment {i}: [IMAGE] Ken Burns {os.path.basename(src_path)} zoom={z_start}->{z_end}")
            _ken_burns_image(src_path, seg_path, segment_duration,
                             z_start, z_end, resolution, fps=30)

        segments.append({"type": seg_type, "path": seg_path, "duration": segment_duration})

    return segments, tmp_dir
# Step 3: Concatenate segments with crossfade transitions
# ══════════════════════════════════════════════════════════════

def step_crossfade_concat(
    segments: List[Dict],
    output_path: str,
    crossfade_duration: float,
    fps: int,
    resolution: Tuple[int, int],
    audio_path: Optional[str] = None,
    timeout: int = 180,
) -> str:
    """Concatenate prepared segments with xfade crossfade transitions.

    Uses ffmpeg xfade filter. Works on any mix of video/image segments.

    Args:
        segments: List of segment dicts from step_prepare_segments.
        output_path: Output video path.
        crossfade_duration: Crossfade duration in seconds.
        fps: Target fps.
        resolution: Target (width, height).
        audio_path: Optional audio to mux.
        timeout: Encoding timeout.

    Returns:
        Path to output video.
    """
    n = len(segments)
    if n == 0:
        raise ValueError("No segments to concatenate")
    if n == 1:
        shutil.copy2(segments[0]["path"], output_path)
        return output_path

    # All segments already normalized, no need to re-encode
    durations = [s["duration"] for s in segments]

    # Validate crossfade fits
    min_dur = min(durations)
    if crossfade_duration >= min_dur / 2:
        crossfade_duration = min_dur / 2 - 0.1
        print(f"  Adjusted crossfade to {crossfade_duration:.2f}s to fit shortest segment")

    # Build ffmpeg command
    inputs = []
    for seg in segments:
        inputs.extend(["-i", seg["path"]])

    if audio_path:
        inputs.extend(["-i", audio_path])

    # Build xfade filter chain
    filter_parts = []
    v_labels = ["0:v"]

    for i in range(1, n):
        prev_label = v_labels[i - 1]
        curr_label = f"{i}:v"
        out_label = f"vt{i}"
        offset = sum(durations[:i]) - i * crossfade_duration
        filter_parts.append(
            f"[{prev_label}][{curr_label}]"
            f"xfade=transition=fade"
            f":duration={crossfade_duration}"
            f":offset={offset:.4f}"
            f"[{out_label}]"
        )
        v_labels.append(out_label)

    final_v = v_labels[-1]
    filter_str = ";".join(filter_parts)

    cmd = ["ffmpeg", "-y"] + inputs + [
        "-filter_complex", filter_str,
        "-map", f"[{final_v}]",
    ]

    if audio_path:
        cmd.extend(["-map", f"{n}:a", "-c:a", "aac", "-b:a", "128k", "-shortest"])

    cmd.extend([
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-r", str(fps),
        "-movflags", "+faststart",
        output_path,
    ])

    print(f"  Crossfading {n} segments (transition={crossfade_duration}s)...")
    expected_dur = sum(durations) - (n - 1) * crossfade_duration
    print(f"  Expected output duration: ~{expected_dur:.1f}s")

    _run_ffmpeg(cmd, timeout=timeout, label="crossfade_concat")

    actual_dur = _probe_duration(output_path)
    print(f"  Crossfade video: {actual_dur:.1f}s")
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
    # Font ascent: distance from baseline to top of text
    ascent = font.getmetrics()[0]

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
    # The text bbox top (bbox[1]) is relative to baseline, so we offset by -bbox[1]
    # to align the visual center of the text with the visual center of the pill
    ty = py + (ph - th) // 2 - bbox[1]

    # Subtle shadow for depth (no outline)
    draw.text((tx + 1, ty + 1), text, fill=COLOR_ACTIVE_SHADOW, font=font)
    draw.text((tx, ty), text, fill=COLOR_ACTIVE_TEXT, font=font)

    return img


def step_render_captions(
    script_text: str,
    audio_duration: float,
    resolution: Tuple[int, int],
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
    word_times = []
    cum = 0.0
    base = audio_duration / n_words
    for i, word in enumerate(words):
        has_period = word.endswith('.') or word.endswith('!') or word.endswith('?')
        has_comma = word.endswith(',') or word.endswith(';') or word.endswith(':')
        if has_period or has_comma:
            # Last word in phrase: extend its slot to include the pause
            extra = 0.35 if has_period else 0.2
            word_times.append((cum, cum + base + extra))
            cum += base + extra
        else:
            word_times.append((cum, cum + base))
            cum += base

    # Scale to fit exact audio duration
    if cum > 0:
        scale = audio_duration / cum
        word_times = [(t[0] * scale, t[1] * scale) for t in word_times]

    def get_active_line(t: float) -> int:
        """Find which display line is active at time t (based on word timing)."""
        if not word_times:
            return 0
        # Find active word — use binary search for efficiency
        # Fall back to last word if t is beyond all ranges
        if t >= word_times[-1][1]:
            wi = len(word_times) - 1
        else:
            # Linear scan (word_times is sorted and mostly contiguous)
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
    cap_dir = tempfile.mkdtemp(prefix="shorts_v2_caps_")
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
    cap_video_path = tempfile.mktemp(prefix="shorts_v2_caps_", suffix=".mov")
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
    cap_dir = tempfile.mkdtemp(prefix="shorts_v2_caps_")
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    fp = os.path.join(cap_dir, "cap_00000.png")
    img.save(fp, "PNG")
    cap_video_path = tempfile.mktemp(prefix="shorts_v2_caps_", suffix=".mov")
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


# ══════════════════════════════════════════════════════════════
# Step 4: Final compose — overlay captions + audio onto crossfaded video
# ══════════════════════════════════════════════════════════════

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

    Args:
        video_path: Crossfaded video (no captions, no audio).
        caption_video_path: qtrle (argb) caption overlay.
        audio_path: TTS audio file.
        output_path: Final output path.
        fps: Target fps.
        timeout: Max encoding time.

    Returns:
        Path to final output video.
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


# ══════════════════════════════════════════════════════════════
# Main orchestration
# ══════════════════════════════════════════════════════════════

# Default script template (curiosity-gap format)
DEFAULT_SCRIPT_TEMPLATE = (
    "Did you know? Here are some fascinating facts about {query}. "
    "Nature never ceases to amaze us with its incredible diversity. "
    "From the smallest organisms to the largest creatures, "
    "every living thing plays a vital role in our ecosystem. "
    "Let's explore more about this amazing topic!"
)


def generate_shorts_v2(
    query: str,
    output_path: str,
    script_text: Optional[str] = None,
    voice: str = DEFAULT_VOICE,
    n_images: int = DEFAULT_N_IMAGES,
    n_videos: int = DEFAULT_N_VIDEOS,
    segment_duration: float = 3.5,
    crossfade_duration: float = DEFAULT_CROSSFADE_DURATION,
    zoom_range: Tuple[float, float] = DEFAULT_KB_ZOOM,
    resolution: Tuple[int, int] = DEFAULT_RESOLUTION,
    fps: int = DEFAULT_FPS,
    cleanup: bool = True,
) -> str:
    """Full v2 pipeline: Pexels videos+images → Ken Burns → Crossfade → Captions → MP4.

    Args:
        query: Topic/keywords for Pexels search.
        output_path: Path for the final output MP4.
        script_text: Optional custom script. If None, uses template.
        voice: edge-tts voice name.
        n_images: Number of images to fetch.
        n_videos: Number of videos to fetch.
        segment_duration: Target duration per segment (auto-adjusted to audio).
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
    tmp_files = []

    try:
        # ── Script ──
        if not script_text:
            script_text = DEFAULT_SCRIPT_TEMPLATE.format(query=query)
        w, h = resolution
        print(f"Script ({len(script_text.split())} words): {script_text[:100]}...")

        # ── Step 1: Fetch mixed assets ──
        assets = timer.run("Fetch Pexels assets", step_fetch_mixed_assets,
                           query, n_images, n_videos)
        image_paths = assets["images"]
        video_paths = assets["videos"]
        if assets.get("_tmp_dir"):
            tmp_dirs.append(assets["_tmp_dir"])

        if len(image_paths) + len(video_paths) < 2:
            raise RuntimeError(
                f"Need at least 2 assets total, got {len(image_paths)} images "
                f"+ {len(video_paths)} videos. Try a different query."
            )

        # ── Step 2: Generate TTS ──
        audio_path, audio_duration = timer.run(
            "Generate TTS", step_generate_tts, script_text, voice
        )
        tmp_files.append(audio_path)

        # Auto-adjust segment duration to match audio
        # Total segments = images + videos (interleaved)
        n_segments = len(image_paths) + len(video_paths)
        # With crossfades: total = n*seg_dur - (n-1)*crossfade
        # So: seg_dur = (audio_dur + (n-1)*crossfade) / n
        total_crossfade_time = (n_segments - 1) * crossfade_duration
        adjusted_seg_duration = (audio_duration + total_crossfade_time) / n_segments
        adjusted_seg_duration = max(2.0, min(8.0, adjusted_seg_duration))

        print(f"  Adjusted segment duration: {adjusted_seg_duration:.2f}s "
              f"(audio={audio_duration:.1f}s, {n_segments} segments)")
        print(f"  Estimated video: {n_segments * adjusted_seg_duration - total_crossfade_time:.1f}s")

        # ── Step 3: Prepare segments (videos normalized, images Ken Burns) ──
        segments, seg_tmp_dir = timer.run(
            "Prepare segments",
            step_prepare_segments,
            image_paths, video_paths,
            adjusted_seg_duration, zoom_range, resolution, fps,
        )
        tmp_dirs.append(seg_tmp_dir)

        # ── Step 4: Crossfade concatenation ──
        concat_video = tempfile.mktemp(prefix="shorts_v2_concat_", suffix=".mp4")
        tmp_files.append(concat_video)

        timer.run(
            "Crossfade concat",
            step_crossfade_concat,
            segments, concat_video, crossfade_duration, fps, resolution,
        )

        # ── Step 5: Render captions ──
        caption_video = timer.run(
            "Render captions",
            step_render_captions,
            script_text, audio_duration, resolution,
        )
        tmp_files.append(caption_video)

        # ── Step 6: Final compose ──
        final_path = timer.run(
            "Final compose",
            step_final_compose,
            concat_video, caption_video, audio_path, output_path, fps,
        )

        # ── Verify output ──
        final_dur = _probe_duration(final_path)
        size_mb = os.path.getsize(final_path) / (1024 * 1024)

        print(f"\n{'='*60}")
        print(f"  DONE: {final_path}")
        print(f"  Duration: {final_dur:.1f}s | Size: {size_mb:.1f} MB")
        print(f"  Resolution: {w}x{h} | FPS: {fps}")
        print(f"  Assets: {len(image_paths)} images + {len(video_paths)} videos")
        print(f"{'='*60}")

        if final_dur > MAX_DURATION:
            print(f"  WARNING: Video is {final_dur:.1f}s (exceeds {MAX_DURATION}s Shorts limit)")

        timer.summary()
        return final_path

    finally:
        if cleanup:
            for d in tmp_dirs:
                shutil.rmtree(d, ignore_errors=True)
            for f in tmp_files:
                try:
                    os.remove(f)
                except OSError:
                    pass


def main():
    parser = argparse.ArgumentParser(
        description="YouTube Shorts Builder v2 — Mixed media (videos + images)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 generate_shorts_v2.py --query "nature" --output nature.mp4
  python3 generate_shorts_v2.py --query "ocean waves" --images 4 --videos 2
  python3 generate_shorts_v2.py --query "space" --script "Space is vast and full of mysteries." --images 6 --videos 3 --crossfade 0.6
        """,
    )
    parser.add_argument("--query", required=True, help="Topic/keywords for Pexels search")
    parser.add_argument("--output", "-o", default="short_v2_output.mp4")
    parser.add_argument("--script", default=None, help="Custom TTS script text")
    parser.add_argument("--voice", default=DEFAULT_VOICE, help=f"TTS voice (default: {DEFAULT_VOICE})")
    parser.add_argument("--images", type=int, default=DEFAULT_N_IMAGES, help=f"Number of images (default: {DEFAULT_N_IMAGES})")
    parser.add_argument("--videos", type=int, default=DEFAULT_N_VIDEOS, help=f"Number of videos (default: {DEFAULT_N_VIDEOS})")
    parser.add_argument("--segment-duration", type=float, default=3.5)
    parser.add_argument("--crossfade", type=float, default=DEFAULT_CROSSFADE_DURATION)
    parser.add_argument("--zoom-start", type=float, default=DEFAULT_KB_ZOOM[0])
    parser.add_argument("--zoom-end", type=float, default=DEFAULT_KB_ZOOM[1])
    parser.add_argument("--fps", type=int, default=DEFAULT_FPS)
    parser.add_argument("--width", type=int, default=DEFAULT_RESOLUTION[0])
    parser.add_argument("--height", type=int, default=DEFAULT_RESOLUTION[1])
    parser.add_argument("--no-cleanup", action="store_true", help="Keep temp files")

    args = parser.parse_args()
    resolution = (args.width, args.height)
    zoom_range = (args.zoom_start, args.zoom_end)

    print(f"generate_shorts_v2.py — YouTube Shorts Builder v2")
    print(f"  Query: {args.query}")
    print(f"  Output: {args.output}")
    print(f"  Resolution: {resolution[0]}x{resolution[1]}@{args.fps}fps")
    print(f"  Images: {args.images}, Videos: {args.videos}")
    print(f"  Segment: {args.segment_duration}s, Crossfade: {args.crossfade}s")
    print(f"  Zoom: {zoom_range}, Voice: {args.voice}")

    try:
        result = generate_shorts_v2(
            query=args.query,
            output_path=args.output,
            script_text=args.script,
            voice=args.voice,
            n_images=args.images,
            n_videos=args.videos,
            segment_duration=args.segment_duration,
            crossfade_duration=args.crossfade,
            zoom_range=zoom_range,
            resolution=resolution,
            fps=args.fps,
            cleanup=not args.no_cleanup,
        )
        print(f"\nOutput: {result}")
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
