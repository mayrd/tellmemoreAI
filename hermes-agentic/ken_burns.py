#!/usr/bin/env python3
"""Ken Burns Effect Module for YouTube Shorts Video Pipeline.

Applies panoramic zoom-and-pan effects to still images using FFmpeg's
zoompan filter. Supports zoom-in, zoom-out, and 5 pan directions.

Usage:
    from ken_burns import apply_ken_burns, images_to_video

    # Apply Ken Burns to a single image
    apply_ken_burns(
        image_path="photo.jpg",
        output_path="segment.mp4",
        duration=3.5,
        zoom_start=1.0,
        zoom_end=1.12,
        direction="zoom_in",
        resolution=(1080, 1920),
        fps=24,
    )

    # Convert multiple images into a Ken Burns video
    images_to_video(
        image_paths=["img1.jpg", "img2.jpg", "img3.jpg"],
        output_path="output.mp4",
        segment_duration=3.5,
        zoom_range=(1.0, 1.12),
    )
"""

import subprocess
import os
import sys
import tempfile
import shutil
from typing import List, Tuple, Optional


def _smooth_ease(t: float) -> float:
    """Smooth ease-in-out: 3t² - 2t³ (Hermite interpolation).
    
    t should be in [0, 1]. Returns eased value in [0, 1].
    This eliminates the mechanical linear stepping that causes
    visible jitter on large screens.
    """
    return t * t * (3.0 - 2.0 * t)


def apply_ken_burns(
    image_path: str,
    output_path: str,
    duration: float = 3.5,
    zoom_start: float = 1.0,
    zoom_end: float = 1.08,
    direction: str = "zoom_in",
    resolution: Tuple[int, int] = (1080, 1920),
    fps: int = 30,
    timeout: int = 60,
) -> str:
    """Apply Ken Burns pan-and-zoom effect to a single image.

    Converts a still image into a video clip with a slow zoom (and optional
    pan) using FFmpeg's zoompan filter.

    Uses smooth ease-in-out interpolation (Hermite) instead of linear
    to eliminate jitter on large screens. Renders at 30fps internally
    for smoother motion, output is set to target fps.

    Args:
        image_path: Path to the input image.
        output_path: Path for the output MP4 video.
        duration: Duration of the output clip in seconds.
        zoom_start: Starting zoom factor (1.0 = no zoom).
        zoom_end: Ending zoom factor (>1.0 = zoom in, <1.0 = zoom out).
        direction: "zoom_in", "zoom_out", or a pan direction
            ("left", "right", "up", "down").
        resolution: Target (width, height) for output.
        fps: Target frames per second (default 30 for smooth motion).
        timeout: Max seconds for FFmpeg encoding.

    Returns:
        Path to the output video file.

    Raises:
        FileNotFoundError: If image_path doesn't exist.
        RuntimeError: If FFmpeg encoding fails.
    """
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    w, h = resolution
    n_frames = int(duration * fps)
    z_diff = zoom_end - zoom_start

    # Build zoompan expressions based on direction
    # Use smoothstep easing: 3t²-2t³ for buttery smooth zoom
    # t = on/n_frames, eased = 3t²-2t³
    # Expanded: zoom_start + z_diff * 3*(on/n)² - z_diff * 2*(on/n)³
    # Simplified for ffmpeg expr: zoom_start + z_diff*(3*(on/n)^2 - 2*(on/n)^3)
    ease_expr = f"3*(on/{n_frames})^2-2*(on/{n_frames})^3"
    z_base = f"if(eq(on,0),{zoom_start},{zoom_start}+{z_diff}*({ease_expr}))"

    if direction == "zoom_in" or direction == "zoom_out":
        z_expr = z_base
        # Sub-pixel precision: use floating point for x/y to avoid integer rounding jitter
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
    elif direction == "left":
        z_expr = z_base
        x_expr = f"iw/2-(iw/zoom/2)-(on/{n_frames})*iw*0.06"
        y_expr = "ih/2-(ih/zoom/2)"
    elif direction == "right":
        z_expr = z_base
        x_expr = f"iw/2-(iw/zoom/2)+(on/{n_frames})*iw*0.06"
        y_expr = "ih/2-(ih/zoom/2)"
    elif direction == "up":
        z_expr = z_base
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = f"ih/2-(ih/zoom/2)-(on/{n_frames})*ih*0.06"
    elif direction == "down":
        z_expr = z_base
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = f"ih/2-(ih/zoom/2)+(on/{n_frames})*ih*0.06"
    else:
        raise ValueError(f"Unknown direction: {direction}. Use zoom_in/zoom_out/left/right/up/down")

    vf = (
        f"zoompan=z='{z_expr}':"
        f"x='{x_expr}':"
        f"y='{y_expr}':"
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

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(
            f"Ken Burns failed for {image_path}:\n{result.stderr[-500:]}"
        )

    return output_path


def images_to_video(
    image_paths: List[str],
    output_path: str,
    segment_duration: float = 3.5,
    zoom_range: Tuple[float, float] = (1.0, 1.08),
    directions: Optional[List[str]] = None,
    resolution: Tuple[int, int] = (1080, 1920),
    fps: int = 30,
    crossfade_duration: float = 0.0,
    audio_path: Optional[str] = None,
    timeout: int = 180,
) -> str:
    """Convert multiple images into a single Ken Burns video with optional crossfades.

    Each image is converted to a video segment with alternating zoom-in/zoom-out
    Ken Burns effect, then all segments are concatenated. Optionally uses
    crossfade_transitions module for smooth crossfades.

    Args:
        image_paths: List of paths to input images.
        output_path: Path for the output video.
        segment_duration: Duration of each image segment in seconds.
        zoom_range: (start_zoom, end_zoom) tuple.
        directions: Optional list of directions per image. If None, alternates
            zoom_in/zoom_out.
        resolution: Target (width, height).
        fps: Target frames per second.
        crossfade_duration: If > 0, apply crossfade between segments using
            crossfade_transitions module.
        audio_path: Optional audio file to mux with the output.
        timeout: Max seconds for the full pipeline.

    Returns:
        Path to the output video file.
    """
    if len(image_paths) < 1:
        raise ValueError("Need at least 1 image")

    if len(image_paths) == 1 and crossfade_duration == 0:
        # Single image, no crossfade — just apply Ken Burns
        zs, ze = zoom_range
        return apply_ken_burns(
            image_paths[0], output_path, segment_duration,
            zs, ze, "zoom_in", resolution, fps, timeout,
        )

    w, h = resolution
    tmp_dir = tempfile.mkdtemp(prefix="kb_")

    try:
        segment_paths = []
        zs, ze = zoom_range

        for i, img_path in enumerate(image_paths):
            seg_path = os.path.join(tmp_dir, f"s{i:03d}.mp4")

            if directions and i < len(directions):
                direction = directions[i]
                if direction == "zoom_in":
                    z_start, z_end = zs, ze
                else:
                    z_start, z_end = ze, zs
            else:
                # Alternate zoom_in / zoom_out for visual variety
                if i % 2 == 0:
                    direction = "zoom_in"
                    z_start, z_end = zs, ze
                else:
                    direction = "zoom_out"
                    z_start, z_end = ze, zs

            apply_ken_burns(
                img_path, seg_path, segment_duration,
                z_start, z_end, direction, resolution, fps,
            )
            segment_paths.append(seg_path)

        if crossfade_duration > 0 and len(segment_paths) >= 2:
            # Use crossfade_transitions module
            try:
                from crossfade_transitions import concatenate_clips_crossfade
                concatenate_clips_crossfade(
                    clip_paths=segment_paths,
                    output_path=output_path,
                    crossfade_duration=crossfade_duration,
                    transition_type="fade",
                    resolution=resolution,
                    fps=fps,
                    normalize=False,
                    audio_path=audio_path,
                    timeout=timeout,
                )
            except ImportError:
                # FFallback: simple concat without crossfade
                print(
                    "Warning: crossfade_transitions not available, "
                    "using simple concat",
                    file=sys.stderr,
                )
                _simple_concat(segment_paths, output_path, audio_path)
        elif len(segment_paths) == 1:
            shutil.move(segment_paths[0], output_path)
        else:
            _simple_concat(segment_paths, output_path, audio_path)

        return output_path
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _simple_concat(
    segment_paths: List[str],
    output_path: str,
    audio_path: Optional[str] = None,
    timeout: int = 60,
) -> str:
    """Simple concat demuxer fallback (no crossfade)."""
    tmp_dir = tempfile.mkdtemp(prefix="kbcat_")
    try:
        list_file = os.path.join(tmp_dir, "concat.txt")
        with open(list_file, "w") as f:
            for p in segment_paths:
                f.write(f"file '{p}'\n")

        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", list_file,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-pix_fmt", "yuv420p",
        ]
        if audio_path:
            cmd.extend(["-i", audio_path, "-c:a", "aac", "-b:a", "128k", "-shortest"])
        else:
            cmd.append("-an")
        cmd.extend(["-movflags", "+faststart", output_path])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            raise RuntimeError(f"Concat failed:\n{result.stderr[-500:]}")
        return output_path
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    import argparse
    import time

    parser = argparse.ArgumentParser(description="Ken Burns effect on images")
    parser.add_argument("images", nargs="+", help="Input image paths")
    parser.add_argument("-o", "--output", default="/tmp/ken_burns_out.mp4")
    parser.add_argument("--duration", type=float, default=3.5)
    parser.add_argument("--zoom-start", type=float, default=1.0)
    parser.add_argument("--zoom-end", type=float, default=1.08)
    parser.add_argument("--direction", default="zoom_in",
                        choices=["zoom_in", "zoom_out", "left", "right", "up", "down"])
    parser.add_argument("--resolution", default="1080x1920")
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--crossfade", type=float, default=0.0,
                        help="Crossfade duration (0=disabled)")
    args = parser.parse_args()

    w, h = map(int, args.resolution.split("x"))
    resolution = (w, h)

    t0 = time.time()
    if len(args.images) == 1:
        result = apply_ken_burns(
            args.images[0], args.output, args.duration,
            args.zoom_start, args.zoom_end, args.direction,
            resolution, args.fps,
        )
    else:
        result = images_to_video(
            args.images, args.output, args.duration,
            (args.zoom_start, args.zoom_end),
            resolution=resolution, fps=args.fps,
            crossfade_duration=args.crossfade,
        )

    # Get output duration
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", result],
        capture_output=True, text=True,
    )
    dur = float(probe.stdout.split('"duration"')[1].split(":")[1].split(",")[0].strip())
    size_mb = os.path.getsize(result) / (1024 * 1024)
    print(f"Output: {result} ({size_mb:.1f} MB, {dur:.1f}s, {time.time()-t0:.1f}s encode)")
