#!/opt/hermes/.venv/bin/python3
"""Resumable YouTube upload using existing OAuth token + direct HTTP."""
import sys, os, json, urllib.request, urllib.error, time

sys.path.insert(0, '/opt/data')
from youtube_upload import refresh_token

VIDEO = sys.argv[1] if len(sys.argv) > 1 else '/tmp/true_crime_final.mp4'
TITLE = sys.argv[2] if len(sys.argv) > 2 else 'Video Title'
THUMB = sys.argv[3] if len(sys.argv) > 3 else '/tmp/true_crime_thumb.jpg'
PLAYLIST_ID = 'PLbgCBs2RbYFQZ-vOZNdfYcsZqfCxKLONb'

with open('/opt/data/true_crime_description.txt') as f:
    DESCRIPTION = f.read()

TAGS = ['True Crime', 'Unsolved Mystery', 'True Crime Story',
        'Cold Case', 'Documentary', 'Mystery', 'Crime Story']

video_size = os.path.getsize(VIDEO)
print(f'Uploading {VIDEO} ({video_size/1e6:.1f} MB)...')

snippet = {
    'title': TITLE,
    'description': DESCRIPTION,
    'tags': TAGS,
    'categoryId': '27',
}
status = {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}

# Step 1: Initiate resumable upload
token = refresh_token()
metadata = json.dumps({'snippet': snippet, 'status': status}).encode()

req = urllib.request.Request(
    'https://www.googleapis.com/upload/youtube/v3/videos?part=snippet,status&uploadType=resumable')
req.add_header('Authorization', f'Bearer {token}')
req.add_header('Content-Type', 'application/json; charset=UTF-8')
req.add_header('X-Upload-Content-Type', 'video/mp4')
req.add_header('X-Upload-Content-Length', str(video_size))

try:
    with urllib.request.urlopen(req, metadata, timeout=30) as resp:
        upload_url = resp.headers['Location']
    print(f'Resumable session started')
except urllib.error.HTTPError as e:
    print(f'Init failed: {e.code} {e.read().decode()[:500]}')
    sys.exit(1)

# Step 2: Upload in chunks
CHUNK = 10 * 1024 * 1024  # 10 MB
uploaded = 0
t0 = time.time()

with open(VIDEO, 'rb') as f:
    while uploaded < video_size:
        chunk_end = min(uploaded + CHUNK, video_size)
        f.seek(uploaded)
        data = f.read(chunk_end - uploaded)
        content_range = f'bytes {uploaded}-{chunk_end-1}/{video_size}'
        
        req = urllib.request.Request(upload_url, data=data, method='PUT')
        req.add_header('Content-Range', content_range)
        req.add_header('Content-Length', str(len(data)))
        
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read())
                video_id = result['id']
                print(f'  Complete! Video ID: {video_id}')
                break
        except urllib.error.HTTPError as e:
            if e.code == 308:
                # Resume incomplete — get new range from Range header
                uploaded = int(e.headers.get('Range', 'bytes=0-0').split('-')[1]) + 1
                pct = uploaded / video_size * 100
                elapsed = time.time() - t0
                speed = uploaded / elapsed / 1e6 if elapsed > 0 else 0
                eta = (video_size - uploaded) / (speed * 1e6) if speed > 0 else 0
                print(f'  {pct:.0f}% ({uploaded/1e6:.0f}/{video_size/1e6:.0f} MB) {speed:.1f} MB/s ETA {eta:.0f}s', flush=True)
            else:
                print(f'Upload error {e.code}: {e.read().decode()[:500]}')
                sys.exit(1)

print(f'URL: https://www.youtube.com/watch?v={video_id}')

# Set thumbnail
if os.path.exists(THUMB):
    token = refresh_token()
    with open(THUMB, 'rb') as f:
        thumb_data = f.read()
    req = urllib.request.Request(
        f'https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={video_id}',
        data=thumb_data,
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'image/jpeg'},
        method='POST')
    try:
        urllib.request.urlopen(req, timeout=30)
        print('Thumbnail set OK')
    except Exception as e:
        print(f'Thumbnail error: {e}')

# Add to playlist
token = refresh_token()
body = json.dumps({
    'snippet': {
        'playlistId': PLAYLIST_ID,
        'resourceId': {'kind': 'youtube#video', 'videoId': video_id}
    }
}).encode()
req = urllib.request.Request(
    'https://www.googleapis.com/youtube/v3/playlistItems?part=snippet',
    data=body,
    headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
    method='POST')
try:
    resp = urllib.request.urlopen(req, timeout=15)
    print('Added to playlist OK')
except Exception as e:
    print(f'Playlist error: {e}')

print(f'\nDone! https://www.youtube.com/watch?v={video_id}')
