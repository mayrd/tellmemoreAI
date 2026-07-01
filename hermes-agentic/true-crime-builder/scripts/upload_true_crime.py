#!/opt/hermes/.venv/bin/python3
"""Upload true crime video with custom description, tags, and thumbnail."""
import sys, os, json, urllib.request, urllib.error, urllib.parse

sys.path.insert(0, '/opt/data')
from youtube_upload import upload_video, refresh_token

VIDEO = sys.argv[1] if len(sys.argv) > 1 else '/tmp/true_crime_final.mp4'
TITLE = sys.argv[2] if len(sys.argv) > 2 else 'The Sodder Children: 5 Kids Vanished on Christmas Eve 1945'
THUMB = sys.argv[3] if len(sys.argv) > 3 else '/tmp/true_crime_thumb.jpg'
PLAYLIST_ID = 'PLbgCBs2RbYFQZ-vOZNdfYcsZqfCxKLONb'

with open('/opt/data/true_crime_description.txt') as f:
    DESCRIPTION = f.read()

TAGS = ['True Crime', 'Unsolved Mystery', 'Sodder Children', 'True Crime Story',
        'Cold Case', 'Missing Children', 'West Virginia', 'Documentary',
        'True Crime Documentary', 'Mystery', 'Unsolved', 'Crime Story']

# 1. Upload video
print(f'Uploading {VIDEO}...')
result = upload_video(VIDEO, TITLE, DESCRIPTION, tags=TAGS)
print(json.dumps(result, indent=2))
if result.get('status') != 'ok':
    print('Upload failed!')
    sys.exit(1)

video_id = result['video_id']
print(f'Video ID: {video_id}')

# 2. Set thumbnail
print(f'Setting thumbnail from {THUMB}...')
token = refresh_token()
with open(THUMB, 'rb') as f:
    thumb_data = f.read()
req = urllib.request.Request(
    f'https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={video_id}',
    data=thumb_data,
    headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'image/jpeg',
    },
    method='POST'
)
try:
    urllib.request.urlopen(req, timeout=30)
    print('Thumbnail set OK')
except Exception as e:
    print(f'Thumbnail error: {e}')

# 3. Add to playlist
print(f'Adding to playlist {PLAYLIST_ID}...')
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
    method='POST'
)
try:
    resp = urllib.request.urlopen(req, timeout=15)
    print(f'Added to playlist: {json.loads(resp.read())["id"][:40]}...')
except Exception as e:
    print(f'Playlist error: {e}')

print(f'\nDone! https://www.youtube.com/watch?v={video_id}')
