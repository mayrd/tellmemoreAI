#!/usr/bin/env python3
"""NASA Image and Video Library client (public-domain imagery).

Why: stock-photo APIs have no usable images for space topics. Endless searching for
`saturn planet` returns neon signs, jewellery and generic illustrations, so the
pipeline used to fall back to *metaphors* (e.g. `geyser snow winter` for an ice-volcano
eruption). The result: pretty pictures that do not tell the story.

The NASA library is public domain (no attribution required), provides real mission
imagery (Cassini / MESSENGER / Hubble / JWST ...) and needs no API key:
https://images-api.nasa.gov

Usage:
    from nasa_images import search_images, download_image
    for cand in search_images("enceladus plume", n=4):
        download_image(cand, "/tmp/x.jpg")

CLI (test a query before production — prints titles so you can see the hits):
    python3 nasa_images.py "enceladus plume" 6
"""
import json
import os
import subprocess
import sys
from typing import Dict, List, Optional

SEARCH_URL = "https://images-api.nasa.gov/search"
ASSET_URL = "https://images-api.nasa.gov/asset/{}"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
# Preference order: big enough for 1080x1920 without pulling huge originals
SIZE_PREFERENCE = ("~large", "~medium", "~orig", "~small", "~thumb")
# Data plots and animations are useless as a video frame: searching "enceladus plume"
# returns e.g. the VIMS spectrum (false-colour map + curves) as the top hit. The FIRST
# image is the hook and must be an eye-catcher.
DATA_PLOT_WORDS = (
    "spectrum", "spectra", "spectral", "spectrometer", "graph", "chart", "diagram",
    "plot", "infographic", "animation", "movie", "timeline", "schematic", "cutaway",
    "cross-section", "cross section", "artist concept of the", "scale bar",
    "model", "montage", "measurement", "curves", "histogram",
)


def looks_like_data_plot(title: str, description: str = "") -> bool:
    """True for measurement plots/animations — unusable as a video frame."""
    blob = f"{title} {description}".lower()
    return any(w in blob for w in DATA_PLOT_WORDS)


def _curl(url: str, timeout: int = 45) -> Optional[bytes]:
    """Everything goes through curl — urllib gets 403 from image APIs."""
    r = subprocess.run(
        ["curl", "-sL", "--max-time", str(timeout), "-A", UA, url],
        capture_output=True,
    )
    if r.returncode != 0 or not r.stdout:
        return None
    return r.stdout


def search_images(query: str, n: int = 6, visuals_only: bool = True) -> List[Dict]:
    """Candidates for one query.

    visuals_only=True (default) filters out measurement plots, animations and schematics
    so the hook frame gets a real image.

    Returns a list of dicts: nasa_id, title, description, date_created, thumbnail
    (order = NASA relevance; the first hits are the iconic images)."""
    url = (f"{SEARCH_URL}?q={query.replace(' ', '%20')}"
           f"&media_type=image&page_size={max(1, min(n * 3 if visuals_only else n, 100))}")
    raw = _curl(url)
    if not raw:
        return []
    try:
        coll = json.loads(raw.decode("utf-8", "replace")).get("collection", {})
    except json.JSONDecodeError:
        return []
    out = []
    for item in coll.get("items", []):
        data = (item.get("data") or [{}])[0]
        links = item.get("links") or [{}]
        title = (data.get("title") or "").strip()
        desc = (data.get("description") or "").strip()[:400]
        if visuals_only and (looks_like_data_plot(title, desc) or not title):
            continue
        out.append({
            "nasa_id": data.get("nasa_id", ""),
            "title": title,
            "description": desc,
            "date_created": (data.get("date_created") or "")[:10],
            "thumbnail": links[0].get("href", ""),
        })
        if len(out) >= n:
            break
    return out


def asset_url(nasa_id: str) -> str:
    """Largest sensible image file for a nasa_id (prefers ~large)."""
    raw = _curl(ASSET_URL.format(nasa_id))
    if not raw:
        return ""
    try:
        items = json.loads(raw.decode("utf-8", "replace"))["collection"]["items"]
    except (json.JSONDecodeError, KeyError):
        return ""
    hrefs = [i.get("href", "") for i in items if i.get("href", "").lower().endswith((".jpg", ".jpeg", ".png"))]
    for size in SIZE_PREFERENCE:
        for h in hrefs:
            if size in h:
                return h
    return hrefs[0] if hrefs else ""


def download_image(candidate: Dict, output_path: str, timeout: int = 90) -> Optional[str]:
    """Download the best asset for a candidate. Falls back to the thumbnail.

    Returns the path, or None."""
    src = asset_url(candidate["nasa_id"]) if candidate.get("nasa_id") else ""
    if not src:
        src = candidate.get("thumbnail", "")
    if not src:
        return None
    data = _curl(src, timeout=timeout)
    if not data or len(data) < 2000:          # broken/empty response
        return None
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "wb") as fh:
        fh.write(data)
    return output_path


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    query = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    cands = search_images(query, n)
    if not cands:
        print(f"no hits for {query!r}")
        return 1
    print(f"{len(cands)} hits for {query!r}:")
    for c in cands:
        print(f"  - {c['title'][:80]}")
        print(f"      {c['date_created']} | {c['nasa_id']}")
        if c["description"]:
            print(f"      {c['description'][:160]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
