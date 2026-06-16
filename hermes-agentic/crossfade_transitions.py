#!/usr/bin/env python3
"""Crossfade Transitions Module for YouTube Shorts Video Pipeline.

Provides functions to concatenate multiple video clips (from Pexels videos
and Ken Burns-processed images) with smooth crossfade transitions.

Uses FFmpeg's xfade filter for hardware-efficient compositing.
Supports configurable crossfade duration, multiple transition types,
and automatic re-encoding to a common format before crossfading.

Usage:
    from crossfade_transitions import concatenate_clips_crossfade, crossfade_from_images

    # Concatenate pre-existing video clips with crossfade
    concatenate_clips_crossfade(
        clip_paths=["seg1.mp4", "seg2.mp4", "seg3.mp4"],
        output_path="/tmp/output.mp4",
        crossfade_duration=0.5,
        transition_type="fade",
    )

    # Create crossfade video from images with Ken Burns
    crossfade_from_images(
        image_paths=["img1.jpg", "img2.jpg", "img3.jpg"],
        output_path="/tmp/output.mp4",
        segment_duration=5.0,
        crossfade_duration=0.5,
        ken_burns=True,
    )
"""

import subprocess
import os
import sys
import json
import tempfile
import shutil
from typing import List, Optional, Tuple


def probe_video(path: str) -> dict:
    """Probe a video file with ffprobe and return stream info."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_streams", "-show_format", path],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {path}: {result.stderr}")
    return json.loads(result.stdout)


def get_video_duration(path: str) -> float:
    """Get the duration of a video file in seconds."""
    info = probe_video(path)
    dur = info.get("format", {}).get("duration")
    if dur:
        return float(dur)
    for stream in info.get("streams", []):
        if stream.get("codec_type") == "video":
            dur = stream.get("duration")
            if dur:
                return float(dur)
    raise RuntimeError(f"Cannot determine duration of {path}")


def normalize_clip(
    input_path: str,
    output_path: str,
    resolution: Tuple[int, int] = (1080, 1920),
    fps: int = 24,
    timeout: int = 60,
) -> str:
    """Re-encode a clip to a common format suitable for xfade concatenation.

    All clips must have identical resolution, fps, pixel format, and codec
    for xfade to work. This function normalizes any input clip.
    """
    w, h = resolution
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
               f"pad={w}:{h}:(ow-iw)/2:(oh-iw)/2:color=black,"
               f"setsar=1,fps={fps}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-an",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"normalize_clip failed for {input_path}:\n{result.stderr[-500:]}")
    return output_path


def concatenate_clips_crossfade(
    clip_paths: List[str],
    output_path: str,
    crossfade_duration: float = 0.5,
    transition_type: str = "fade",
    resolution: Tuple[int, int] = (1080, 1920),
    fps: int = 24,
    normalize: bool = True,
    audio_path: Optional[str] = None,
    timeout: int = 120,
) -> str:
    """Concatenate multiple video clips with smooth crossfade transitions.

    Uses FFmpeg's xfade filter to blend between consecutive clips.
    Each crossfade overlaps the end of clip N with the start of clip N+1
    by crossfade_duration seconds.

    Total output duration = sum(clip_durations) - (n_clips - 1) * crossfade_duration

    Args:
        clip_paths: List of paths to input video clips (min 2).
        output_path: Path for the output video file.
        crossfade_duration: Duration of each crossfade in seconds (default 0.5).
            Must be shorter than half the shortest clip duration.
        transition_type: xfade transition type. Common options:
            "fade" — smooth opacity crossfade (default, most versatile)
            "wipeleft", "wiperight", "wipeup", "wipedown" — directional wipes
            "dissolve" — similar to fade with different curve
            "slideright", "slideleft" — sliding transitions
            "circlecrop" — circular reveal
            "fadeblack" — fade through black
            "fadewhite" — fade through white
            "radial" — radial wipe
        resolution: Target (width, height) for output.
        fps: Target frames per second.
        normalize: If True, re-encode all clips to common format first.
        audio_path: Optional audio file to mux with the output.
        timeout: Max seconds for the final encoding step.

    Returns:
        Path to the output video file.

    Raises:
        ValueError: If fewer than 2 clips, or crossfade too long.
        RuntimeError: If FFmpeg encoding fails.
    """
    if len(clip_paths) < 2:
        raise ValueError(f"Need at least 2 clips, got {len(clip_paths)}")

    for p in clip_paths:
        if not os.path.isfile(p):
            raise FileNotFoundError(f"Clip not found: {p}")

    durations = [get_video_duration(p) for p in clip_paths]
    min_duration = min(durations)
    if crossfade_duration >= min_duration / 2:
        raise ValueError(
            f"crossfade_duration ({crossfade_duration}s) must be less than "
            f"half the shortest clip ({min_duration}s)"
        )

    if normalize:
        tmp_dir = tempfile.mkdtemp(prefix="xfn_")
        try:
            normalized = []
            for i, path in enumerate(clip_paths):
                np = os.path.join(tmp_dir, f"n{i:03d}.mp4")
                normalize_clip(path, np, resolution, fps)
                normalized.append(np)
            return _xfade_concat(normalized, output_path, crossfade_duration,
                                 transition_type, fps, audio_path, timeout)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
    else:
        return _xfade_concat(clip_paths, output_path, crossfade_duration,
                             transition_type, fps, audio_path, timeout)


def _xfade_concat(
    clip_paths: List[str],
    output_path: str,
    crossfade_duration: float,
    transition_type: str,
    fps: int,
    audio_path: Optional[str],
    timeout: int,
) -> str:
    """Build and run the xfade filter_complex chain.

    Creates a chain like:
        [0:v][1:v]xfade=transition=fade:duration=0.5:offset=4.5[vt1];
        [vt1][2:v]xfade=transition=fade:duration=0.5:offset=9.0[vt2]
    """
    n = len(clip_paths)
    durations = [get_video_duration(p) for p in clip_paths]

    inputs = []
    for path in clip_paths:
        inputs.extend(["-i", path])

    if audio_path:
        inputs.extend(["-i", audio_path])

    filter_parts = []
    v_labels = ["0:v"]

    for i in range(1, n):
        prev_label = v_labels[i - 1]
        curr_label = f"{i}:v"
        out_label = f"vt{i}"
        offset = sum(durations[:i]) - i * crossfade_duration
        filter_parts.append(
            f"[{prev_label}][{curr_label}]"
            f"xfade=transition={transition_type}"
            f":duration={crossfade_duration}"
            f":offset={offset}"
            f"[{out_label}]"
        )
        v_labels.append(out_label)

    final_v = v_labels[-1]
    filter_str = ";".join(filter_parts)

    cmd = ["ffmpeg", "-y"] + inputs + ["-filter_complex", filter_str]
    cmd.extend(["-map", f"[{final_v}]"])

    if audio_path:
        cmd.extend(["-map", f"{n}:a"])

    cmd.extend([
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-r", str(fps),
    ])

    if audio_path:
        cmd.extend(["-c:a", "aac", "-b:a", "128k", "-shortest"])

    cmd.extend(["-movflags", "+faststart", output_path])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"xfade concatenation failed:\n{result.stderr[-1000:]}")
    return output_path


def crossfade_from_images(
    image_paths: List[str],
    output_path: str,
    segment_duration: float = 3.5,
    crossfade_duration: float = 0.5,
    transition_type: str = "fade",
    resolution: Tuple[int, int] = (1080, 1920),
    fps: int = 24,
    ken_burns: bool = True,
    zoom_range: Tuple[float, float] = (1.0, 1.12),
    audio_path: Optional[str] = None,
    timeout: int = 180,
) -> str:
    """Create a crossfade video from a list of still images.

    Each image is converted to a video segment (optionally with Ken Burns
    zoom effect), then all segments are concatenated with crossfade transitions.

    This is the high-level function for the YouTube Shorts pipeline:
    Pexels images -> Ken Burns segments -> crossfade concat -> final video.

    Args:
        image_paths: List of paths to input images (min 2).
        output_path: Path for the output video.
        segment_duration: Duration of each image segment in seconds.
        crossfade_duration: Duration of crossfade between segments.
        transition_type: xfade transition type.
        resolution: Target (width, height).
        fps: Target frames per second.
        ken_burns: If True, apply slow zoom to each image.
        zoom_range: (start_zoom, end_zoom) for Ken Burns effect.
        audio_path: Optional audio file to mux.
        timeout: Max seconds for the full pipeline.

    Returns:
        Path to the output video file.
    """
    if len(image_paths) < 2:
        raise ValueError(f"Need at least 2 images, got {len(image_paths)}")

    w, h = resolution
    tmp_dir = tempfile.mkdtemp(prefix="xfi_")

    try:
        segment_paths = []
        for i, img_path in enumerate(image_paths):
            seg_path = os.path.join(tmp_dir, f"s{i:03d}.mp4")

            if ken_burns:
                zs, ze = zoom_range
                z_start, z_end = (zs, ze) if i % 2 == 0 else (ze, zs)
                n_frames = int(segment_duration * fps)
                z_diff = z_end - z_start
                z_expr = f"if(eq(on,0),{z_start},{z_start}+{z_diff}*on/{n_frames})"
                vf = (f"zoompan=z='{z_expr}':x='iw/2-(iw/zoom/2)'"
                      f":y='ih/2-(ih/zoom/2)':d={n_frames}:s={w}x{h}:fps={fps}")
            else:
                vf = (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                      f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1")

            cmd = [
                "ffmpeg", "-y", "-loop", "1", "-i", img_path,
                "-vf", vf, "-c:v", "libx264", "-preset", "fast",
                "-crf", "23", "-pix_fmt", "yuv420p",
                "-t", str(segment_duration), "-an", seg_path,
            ]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if r.returncode != 0:
                raise RuntimeError(f"Segment failed for {img_path}:\n{r.stderr[-500:]}")
            segment_paths.append(seg_path)

        return concatenate_clips_crossfade(
            clip_paths=segment_paths, output_path=output_path,
            crossfade_duration=crossfade_duration, transition_type=transition_type,
            resolution=resolution, fps=fps, normalize=False,
            audio_path=audio_path, timeout=timeout,
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def get_available_transitions() -> List[str]:
    """Return a list of available xfade transition types."""
    return [
        "fade", "wipeleft", "wiperight", "wipeup", "wipedown",
        "dissolve", "slideright", "slideleft", "slideup", "slidedown",
        "circlecrop", "rectcrop", "distance", "fadeblack", "fadewhite",
        "radial", "smoothleft", "smoothright", "smoothup", "smoothdown",
        "diagtl", "diagtr", "diagbl", "diagbr",
    ]


if __name__ == "__main__":
    import time

    resolution = (1080, 1920)
    fps = 24
    seg_dur = 5.0
    cf_dur = 0.5
    colors = ["red", "green", "blue"]
    expected = 3 * seg_dur - 2 * cf_dur

    tmp = tempfile.mkdtemp(prefix="xftest_")
    try:
        print(f"Self-test: crossfade_transitions.py")
        print(f"  {resolution[0]}x{resolution[1]}@{fps}fps, {len(colors)} clips x {seg_dur}s, crossfade={cf_dur}s")
        print(f"  Expected output: ~{expected:.1f}s")

        clips = []
        for i, c in enumerate(colors):
            p = os.path.join(tmp, f"t_{c}.mp4")
            subprocess.run([
                "ffmpeg", "-y", "-f", "lavfi",
                "-i", f"color=c={c}:s=1080x1920:d={seg_dur}:r={fps}",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-pix_fmt", "yuv420p", "-an", p,
            ], capture_output=True, check=True, timeout=30)
            clips.append(p)
            print(f"  Clip {i}: {c} ({get_video_duration(p):.2f}s)")

        # Test 1: fade
        t0 = time.time()
        o1 = os.path.join(tmp, "out_fade.mp4")
        concatenate_clips_crossfade(clips, o1, cf_dur, "fade", resolution, fps, normalize=False)
        d1 = get_video_duration(o1)
        print(f"  Test 1 (fade): {d1:.2f}s, {os.path.getsize(o1):,}B, {time.time()-t0:.1f}s")
        assert abs(d1 - expected) < 1.0

        # Test 2: wipeleft
        t0 = time.time()
        o2 = os.path.join(tmp, "out_wipe.mp4")
        concatenate_clips_crossfade(clips, o2, cf_dur, "wipeleft", resolution, fps, normalize=False)
        d2 = get_video_duration(o2)
        print(f"  Test 2 (wipeleft): {d2:.2f}s, {time.time()-t0:.1f}s")
        assert abs(d2 - expected) < 1.0

        # Test 3: crossfade_from_images
        imgs = []
        for c in colors:
            ip = os.path.join(tmp, f"img_{c}.png")
            subprocess.run([
                "ffmpeg", "-y", "-f", "lavfi",
                "-i", f"color=c={c}:s=1080x1920:d=1:r=1",
                "-frames:v", "1", ip,
            ], capture_output=True, check=True, timeout=10)
            imgs.append(ip)

        t0 = time.time()
        o3 = os.path.join(tmp, "out_imgs.mp4")
        crossfade_from_images(imgs, o3, seg_dur, cf_dur, "fade", resolution, fps, ken_burns=True)
        d3 = get_video_duration(o3)
        print(f"  Test 3 (images+KB): {d3:.2f}s, {os.path.getsize(o3):,}B, {time.time()-t0:.1f}s")
        assert abs(d3 - expected) < 1.5

        # Test 4: with audio
        ap = os.path.join(tmp, "audio.wav")
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"aevalsrc=0.1*sin(2*PI*440*t):c=mono:s=24000:d={expected}",
            ap,
        ], capture_output=True, check=True, timeout=10)
        o4 = os.path.join(tmp, "out_audio.mp4")
        concatenate_clips_crossfade(clips, o4, cf_dur, "fade", resolution, fps, normalize=False, audio_path=ap)
        d4 = get_video_duration(o4)
        print(f"  Test 4 (audio): {d4:.2f}s")
        assert abs(d4 - expected) < 1.0

        # Test 5: different crossfade durations
        for cfd in [0.3, 0.8]:
            exp = 3 * seg_dur - 2 * cfd
            op = os.path.join(tmp, f"out_cf{cfd}.mp4")
            concatenate_clips_crossfade(clips, op, cfd, "fade", resolution, fps, normalize=False)
            od = get_video_duration(op)
            print(f"  Test cfd={cfd}s: {od:.2f}s (exp ~{exp:.2f}s)")
            assert abs(od - exp) < 1.0

        print(f"\n  All tests PASSED!")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
