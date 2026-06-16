#!/usr/bin/env python3
"""Pexels API client module v2 — photos + videos with quality-aware selection.

Handles API key discovery (env var + .env files), pagination,
rate-limit awareness with retry/backoff, and returns structured results.

Usage:
    from pexels import search_photos, search_videos, download_photo, download_video

    photos = search_photos("nature", n=6)
    videos = search_videos("nature", n=3)
"""

import subprocess
import json
import os
import sys
import time
from typing import List, Dict, Optional
from urllib.parse import quote


def _find_api_key() -> str:
    """Locate Pexels API key from environment or .env files."""
    key = os.environ.get("PEXELS_API_KEY", "")
    if key and key != "{{PEXELS_API_KEY}}":
        return key

    for env_path in [
        os.path.join(os.path.expanduser("~"), ".env"),
        "/opt/data/.env",
    ]:
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("PEXELS_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val and val != "{{PEXELS_API_KEY}}":
                            return val
    return ""


API_KEY = _find_api_key()
BASE_URL = "https://api.pexels.com/v1"
VIDEO_BASE_URL = "https://api.pexels.com/videos"


def _api_request(url: str, max_retries: int = 3, timeout: int = 15) -> dict:
    """Make an authenticated request to the Pexels API with retry/backoff."""
    if not API_KEY:
        raise RuntimeError(
            "No Pexels API key found. Set PEXELS_API_KEY env var or add it to ~/.env"
        )

    for attempt in range(max_retries):
        result = subprocess.run(
            ["curl", "-s", "-H", f"Authorization: {API_KEY}", url],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"curl failed: {result.stderr}")

        try:
            data = json.loads(result.stdout)
            if "status" in data and data["status"] == 429:
                if attempt < max_retries - 1:
                    wait = 2 ** (attempt + 1)
                    print(f"  Pexels rate limited, waiting {wait}s...", file=sys.stderr)
                    time.sleep(wait)
                    continue
            return data
        except json.JSONDecodeError:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"Invalid JSON from Pexels: {result.stdout[:200]}")

    raise RuntimeError("Pexels API: max retries exhausted")


def search_photos(
    query: str,
    n: int = 6,
    orientation: str = "portrait",
    size: str = "medium",
) -> List[Dict]:
    """Search Pexels for photos.

    Returns:
        List of dicts with keys: url, photographer, photographer_url, id, avg_color.
    """
    url = (
        f"{BASE_URL}/search"
        f"?query={quote(query)}"
        f"&per_page={min(n + 4, 80)}"
        f"&orientation={orientation}"
    )
    data = _api_request(url)

    photos = []
    for p in data.get("photos", [])[:n]:
        src = p.get("src", {})
        photo_url = src.get("portrait") or src.get("large") or src.get("medium", "")
        if photo_url:
            photos.append({
                "url": photo_url,
                "photographer": p.get("photographer", ""),
                "photographer_url": p.get("photographer_url", ""),
                "id": p.get("id", 0),
                "avg_color": p.get("avg_color", "#000000"),
                "width": p.get("width", 0),
                "height": p.get("height", 0),
            })

    return photos


def _pick_best_video_file(video_files: List[Dict], orientation: str = "portrait") -> Optional[Dict]:
    """Pick the best video file from Pexels video_files list.

    Preference order:
      1. Portrait orientation (width < height)
      2. Higher quality: hd > sd > hls
      3. Larger pixel count as tiebreaker
    """
    quality_order = {"hd": 0, "sd": 1, "hls": 2}

    # Filter by orientation first
    portrait_files = [f for f in video_files if f.get("width", 0) < f.get("height", 0)]
    candidates = portrait_files if portrait_files else video_files

    if not candidates:
        return None

    # Sort by quality preference, then by pixel count (descending)
    def sort_key(f):
        q = quality_order.get(f.get("quality", "sd"), 1)
        pixels = f.get("width", 0) * f.get("height", 0)
        return (q, -pixels)

    candidates.sort(key=sort_key)
    return candidates[0]


def search_videos(
    query: str,
    n: int = 4,
    orientation: str = "portrait",
) -> List[Dict]:
    """Search Pexels for videos.

    Returns:
        List of dicts with keys: url, duration, photographer, id, thumbnail, width, height.
    """
    url = (
        f"{VIDEO_BASE_URL}/search"
        f"?query={quote(query)}"
        f"&per_page={min(n + 4, 80)}"
        f"&orientation={orientation}"
    )
    data = _api_request(url)

    videos = []
    for v in data.get("videos", [])[:n]:
        files = v.get("video_files", [])
        best = _pick_best_video_file(files, orientation)

        if best:
            videos.append({
                "url": best.get("link", ""),
                "duration": v.get("duration", 10),
                "photographer": v.get("user", {}).get("name", ""),
                "id": v.get("id", 0),
                "thumbnail": v.get("image", ""),
                "width": best.get("width", 0),
                "height": best.get("height", 0),
                "file_type": best.get("file_type", ""),
                "quality": best.get("quality", "sd"),
            })

    return videos


def download_photo(photo_url: str, output_path: str, timeout: int = 20) -> str:
    """Download a photo to a local file."""
    result = subprocess.run(
        ["curl", "-s", "-o", output_path, photo_url],
        capture_output=True, text=True, timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Download failed: {result.stderr}")
    if not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError(f"Downloaded file is empty: {output_path}")
    return output_path


def download_video(video_url: str, output_path: str, timeout: int = 120) -> str:
    """Download a video to a local file with progress-friendly settings.

    For Pexels videos which can be large, uses -L (follow redirects) and
    longer timeout.
    """
    result = subprocess.run(
        ["curl", "-L", "-s", "-o", output_path, video_url],
        capture_output=True, text=True, timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Video download failed: {result.stderr}")
    if not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError(f"Downloaded video is empty: {output_path}")
    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Pexels API client v2")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--type", choices=["photos", "videos", "both"], default="photos")
    parser.add_argument("--n", type=int, default=6)
    parser.add_argument("--orientation", default="portrait")
    parser.add_argument("--download", action="store_true", help="Download results to /tmp")
    args = parser.parse_args()

    if not API_KEY:
        print("ERROR: No Pexels API key found", file=sys.stderr)
        sys.exit(1)

    print(f"Searching Pexels for: '{args.query}' ({args.type})")

    if args.type in ("photos", "both"):
        photos = search_photos(args.query, args.n, args.orientation)
        print(f"\nPhotos ({len(photos)}):")
        for i, p in enumerate(photos):
            print(f"  [{i+1}] {p['url']} (by {p['photographer']})")
            if args.download:
                path = f"/tmp/pexels_photo_{i:03d}.jpg"
                download_photo(p["url"], path)
                print(f"       -> {path}")

    if args.type in ("videos", "both"):
        videos = search_videos(args.query, args.n, args.orientation)
        print(f"\nVideos ({len(videos)}):")
        for i, v in enumerate(videos):
            print(f"  [{i+1}] {v['url']} ({v['duration']}s, {v['quality']}, by {v['photographer']})")
            if args.download:
                path = f"/tmp/pexels_video_{i:03d}.mp4"
                download_video(v["url"], path)
                print(f"       -> {path}")
