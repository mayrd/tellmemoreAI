#!/opt/hermes/.venv/bin/python3
"""Upload a video to YouTube as a Short."""
import json, sys, os, urllib.request, urllib.error

YOUTUBE_TOKEN = "/opt/data/youtube_token.json"
CLIENT_SECRET = "/opt/data/google_client_secret.json"
CHANNEL_ID = "UCLzNRDvPtqJkej4RnUp-6qQ"

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
        return {"status": "ok", "video_id": video_id, "url": video_url}
    except urllib.error.HTTPError as e:
        return {"status": "error", "code": e.code, "message": e.read().decode()[:500]}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: upload.py <video.mp4> [title]")
        sys.exit(1)

    filepath = sys.argv[1]
    title = sys.argv[2] if len(sys.argv) > 2 else "Fun Fact of the Day 🧠"

    result = upload_video(filepath, title, f"Daily fun fact! #shorts #funfact #didyouknow")
    print(json.dumps(result, indent=2))
