#!/opt/hermes/.venv/bin/python3
"""Upload a video to YouTube as a Short."""
import json, sys, os, urllib.request, urllib.error, urllib.parse

YOUTUBE_TOKEN = "/opt/data/youtube_token.json"
CLIENT_SECRET = "/opt/data/google_client_secret.json"

def _load_token():
    """Load token from pipe-delimited ('1|{...}') or pure JSON format."""
    with open(YOUTUBE_TOKEN) as f:
        raw = f.read()
    return json.loads(raw.split('|', 1)[1] if '|' in raw else raw)

def refresh_token():
    token = _load_token()
    with open(CLIENT_SECRET) as f:
        secret = json.load(f)["installed"]
    
    data = urllib.parse.urlencode({
        "client_id": secret["client_id"],
        "client_secret": secret["client_secret"],
        "refresh_token": token["refresh_token"],
        "grant_type": "refresh_token",
    }).encode()
    
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data)
    with urllib.request.urlopen(req, timeout=15) as resp:
        token["access_token"] = json.loads(resp.read())["access_token"]
    
    with open(YOUTUBE_TOKEN, "w") as f:
        json.dump(token, f)
    return token["access_token"]

def upload_video(filepath, title, description="", tags=None):
    token = refresh_token()
    
    with open(filepath, "rb") as f:
        video_data = f.read()
    
    snippet = {
        "title": title,
        "description": description or title,
        "tags": tags or ["shorts", "fun fact", "did you know", "daily facts"],
        "categoryId": "27",
    }
    status = {
        "privacyStatus": "public",
        "selfDeclaredMadeForKids": False,
        "containsSyntheticAudio": True,
        "containsSyntheticVideo": True,
    }
    
    boundary = "YouTubeUploadBoundary42"
    body = (
        f"--{boundary}\r\n"
        "Content-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{json.dumps({'snippet': snippet, 'status': status})}\r\n"
        f"--{boundary}\r\n"
        "Content-Type: video/mp4\r\n\r\n"
    ).encode() + video_data + f"\r\n--{boundary}--\r\n".encode()
    
    req = urllib.request.Request(
        "https://www.googleapis.com/upload/youtube/v3/videos?part=snippet,status&uploadType=multipart"
    )
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", f"multipart/related; boundary={boundary}")
    
    try:
        with urllib.request.urlopen(req, body, timeout=120) as resp:
            result = json.loads(resp.read())
        return {"status": "ok", "video_id": result["id"], "url": f"https://www.youtube.com/shorts/{result['id']}"}
    except urllib.error.HTTPError as e:
        return {"status": "error", "code": e.code, "message": e.read().decode()[:500]}

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("video", help="MP4 file to upload")
    ap.add_argument("title", nargs="?", default="Fun Fact of the Day")
    ap.add_argument("--description", default="")
    args = ap.parse_args()
    
    result = upload_video(args.video, args.title, args.description)
    print(json.dumps(result, indent=2))
