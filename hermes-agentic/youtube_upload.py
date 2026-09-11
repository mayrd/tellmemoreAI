#!/opt/hermes/.venv/bin/python3
"""Upload a video to YouTube as a Short."""
import json, sys, os, urllib.parse, urllib.request, urllib.error

YOUTUBE_TOKEN = "/opt/data/youtube_token.json"
CLIENT_SECRET = "/opt/data/google_client_secret.json"
CHANNEL_ID = "UCLzNRDvPtqJkej4RnUp-6qQ"

# videos.update REPLACES the whole status object: any boolean left out is reset to
# false. Always send the full object (observed 2026-09-10: a minimal PUT flipped
# embeddable + publicStatsViewable back to false).
FULL_STATUS = {
    "privacyStatus": "public",
    "selfDeclaredMadeForKids": False,
    "containsSyntheticMedia": True,
    "embeddable": True,
    "publicStatsViewable": True,
}


def _load_token():
    """Load token from pipe-delimited ('1|{...}') or pure JSON format."""
    with open(YOUTUBE_TOKEN) as f:
        raw = f.read()
    return json.loads(raw.split('|', 1)[1] if '|' in raw else raw)


def refresh_token():
    token = _load_token()
    with open(CLIENT_SECRET) as f:
        secret = json.load(f)["installed"]

    import urllib.parse
    data = urllib.parse.urlencode({
        "client_id": secret["client_id"],
        "client_secret": secret["client_secret"],
        "refresh_token": token["refresh_token"],
        "grant_type": "refresh_token",
    }).encode()

    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data)
    with urllib.request.urlopen(req, timeout=15) as resp:
        new_token = json.loads(resp.read())

    token["access_token"] = new_token["access_token"]
    token["expires_in"] = new_token.get("expires_in", 3599)
    with open(YOUTUBE_TOKEN, "w") as f:
        json.dump(token, f)
    return token["access_token"]


def set_ai_disclosure(video_id, token):
    """Attempt to persist the AI/synthetic-media disclosure flag on a video.

    ⚠️ VERIFIED INEFFECTIVE (2026-09-11): videos.insert silently drops
    status.containsSyntheticMedia AND videos.update only *echoes* it — the PUT
    response contains "containsSyntheticMedia": true, but an independent
    videos.list?part=status read-back returns no such key, even minutes later
    (tested on all 4 Shorts of 2026-09-10: 5cQiqCLZbRY, GLJUEi6mKJ4,
    3h6F9w36Y1M, srqJ4mEnkWk). So there is currently NO API path for the
    disclosure — it must be set manually in YouTube Studio. This helper is kept
    so the behaviour can be re-tested (and a result claimed only after a
    separate read-back, never from the PUT response).

    videos.update REPLACES the whole status object, so every boolean is sent
    explicitly (a minimal PUT flipped embeddable/publicStatsViewable to false
    on 2026-09-10).
    """
    body = json.dumps({"id": video_id, "status": dict(FULL_STATUS)}).encode()
    req = urllib.request.Request(
        "https://www.googleapis.com/youtube/v3/videos?part=status",
        data=body, method="PUT",
    )
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            st = json.loads(resp.read()).get("status", {})
        return {
            "disclosure_set": st.get("containsSyntheticMedia") is True,
            "status": st,
        }
    except urllib.error.HTTPError as e:
        return {
            "disclosure_set": False,
            "code": e.code,
            "message": e.read().decode()[:300],
        }


def get_status(video_id, token):
    """Read back part=status for one video (verification helper)."""
    url = ("https://www.googleapis.com/youtube/v3/videos?part=status&id="
           + urllib.parse.quote(video_id))
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        items = json.loads(resp.read()).get("items", [])
    return items[0].get("status", {}) if items else {}


def upload_video(filepath, title, description, tags=None):
    token = refresh_token()

    # Read video file
    with open(filepath, "rb") as f:
        video_data = f.read()

    # Create metadata
    snippet = {
        "title": title,
        "description": description,
        "tags": tags or ["fun fact", "did you know", "shorts", "daily facts", "interesting facts"],
        "categoryId": "27",  # Education
    }
    status = {
        "privacyStatus": "public",
        "selfDeclaredMadeForKids": False,
        "containsSyntheticMedia": True,
    }

    # Multipart upload
    boundary = "YouTubeUploadBoundary42"
    body = b""

    # Metadata part
    body += f"--{boundary}\r\n".encode()
    body += b"Content-Type: application/json; charset=UTF-8\r\n\r\n"
    body += json.dumps({"snippet": snippet, "status": status}).encode()
    body += f"\r\n--{boundary}\r\n".encode()

    # Video part
    body += b"Content-Type: video/mp4\r\n\r\n"
    body += video_data
    body += f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        "https://www.googleapis.com/upload/youtube/v3/videos?part=snippet,status&uploadType=multipart"
    )
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", f"multipart/related; boundary={boundary}")
    req.add_header("Content-Length", str(len(body)))

    try:
        with urllib.request.urlopen(req, body, timeout=120) as resp:
            result = json.loads(resp.read())
        video_id = result["id"]
        video_url = f"https://www.youtube.com/shorts/{video_id}"
        # NOTE (verified 2026-09-11): neither videos.insert nor videos.update
        # persists status.containsSyntheticMedia — the PUT echoes the submitted
        # value but an independent videos.list?part=status read-back still returns
        # no containsSyntheticMedia key minutes later. There is currently NO API
        # path for the AI-content disclosure; it must be set in YouTube Studio.
        # The set_ai_disclosure() helper below is kept only so the behaviour can be
        # re-tested (--set-disclosure / --check-disclosure) if Google fixes it.
        return {"status": "ok", "video_id": video_id, "url": video_url}
    except urllib.error.HTTPError as e:
        return {"status": "error", "code": e.code, "message": e.read().decode()[:500]}


if __name__ == "__main__":
    args = [a for a in sys.argv[1:]]
    if not args:
        print("Usage: youtube_upload.py <video.mp4> [title]")
        print("       youtube_upload.py --set-disclosure <video_id> [<video_id> ...]")
        print("       youtube_upload.py --check-disclosure <video_id> [<video_id> ...]")
        sys.exit(1)

    if args[0] == "--set-disclosure":
        tok = refresh_token()
        for vid in args[1:]:
            res = set_ai_disclosure(vid, tok)
            st = res.get("status", {})
            print(json.dumps({
                "video_id": vid,
                "ok": res.get("disclosure_set"),
                "read_back": st.get("containsSyntheticMedia"),
                "privacy": st.get("privacyStatus"),
                "embeddable": st.get("embeddable"),
                "publicStatsViewable": st.get("publicStatsViewable"),
                "error": res.get("message"),
            }))
        sys.exit(0)

    if args[0] == "--check-disclosure":
        tok = refresh_token()
        for vid in args[1:]:
            st = get_status(vid, tok)
            print(json.dumps({
                "video_id": vid,
                "containsSyntheticMedia": st.get("containsSyntheticMedia", "MISSING"),
                "privacy": st.get("privacyStatus"),
            }))
        sys.exit(0)

    filepath = args[0]
    title = args[1] if len(args) > 1 else "Fun Fact of the Day 🧠"

    result = upload_video(filepath, title, f"Daily fun fact! #shorts #funfact #didyouknow")
    print(json.dumps(result, indent=2))
