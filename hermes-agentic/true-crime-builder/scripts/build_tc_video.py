#!/usr/bin/env python3
"""Integrated true crime video builder: TTS → Pexels → Ken Burns → Captions → Thumbnail → Upload.
Landscape 1920×1080, 10-15 min, subtitle bar captions, thumbnail with title overlay.
"""
import subprocess, sys, os, tempfile, shutil, json, time, re, urllib.request
from PIL import Image, ImageFont, ImageDraw

SCRIPT_DIR = '/opt/data/skills/social-media/youtube-shorts-builder/scripts'
sys.path.insert(0, SCRIPT_DIR)
from pexels import search_photos, download_photo

# ── Config ──
W, H = 1920, 1080
FPS = 24; KB_FPS = 24    # match output FPS — no judder
CROSSFADE = 0.5
ZOOM_START, ZOOM_END = 1.0, 1.04   # gentler 4% zoom for big screen
BATCH_SIZE = 10
EDGE_TTS = '/opt/data/home/.local/bin/edge-tts'
VOICE = 'en-US-BrianNeural'
FONT_FILE = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

# Caption style (subtitle bar for landscape)
CAP_FPS = 12
CAP_FONT_SIZE = 32
CAP_BAR_ALPHA = 180
CAP_MARGIN_X = 80
CAP_MARGIN_BOTTOM = 60
CAP_BAR_HEIGHT = 70

def run(cmd, timeout=120, label=''):
    print(f'  [{label}]...', flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        err = r.stderr[-500:]
        print(f'  ERROR: {err}')
        raise RuntimeError(f'{label}: {err}')
    return r

def probe_dur(path):
    r = subprocess.run(['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', path],
                       capture_output=True, text=True, timeout=10)
    return float(json.loads(r.stdout)['format']['duration'])

def render_captions(script_text, audio_dur):
    """Render subtitle-bar captions for landscape video. Returns path to qtrle mov."""
    words = script_text.split()
    n_words = len(words)
    
    # Split into display phrases
    raw = re.split(r'(?<=[,;:.!?])\s+', script_text)
    phrases = [c.strip() for c in raw if c.strip()]
    
    # Pre-compute display lines
    font = ImageFont.truetype(FONT_FILE, CAP_FONT_SIZE)
    max_width = W - 2 * CAP_MARGIN_X
    
    def wrap(text):
        ws = text.split()
        lines = []
        cur = []
        for w in ws:
            test = ' '.join(cur + [w])
            if font.getbbox(test)[2] <= max_width:
                cur.append(w)
            else:
                if cur: lines.append(' '.join(cur))
                cur = [w]
        if cur: lines.append(' '.join(cur))
        return lines
    
    display_lines = []
    word_to_line = []
    for phrase in phrases:
        wrapped = wrap(phrase)
        for wl in wrapped:
            display_lines.append(wl)
            word_to_line.extend([len(display_lines)-1] * len(wl.split()))
    
    if not display_lines:
        cap_dir = tempfile.mkdtemp(prefix='tc_caps_')
        img = Image.new('RGBA', (W, H), (0,0,0,0))
        img.save(os.path.join(cap_dir, 'cap_00000.png'))
        out = tempfile.mktemp(prefix='tc_caps_', suffix='.mov')
        run(['ffmpeg', '-y', '-framerate', '1', '-i', os.path.join(cap_dir, 'cap_00000.png'),
             '-c:v', 'qtrle', '-pix_fmt', 'argb', '-t', str(audio_dur), out], timeout=30, label='empty caps')
        return out
    
    # Word-level timing
    word_times = []
    cum = 0.0
    base = audio_dur / n_words
    for w in words:
        extra = 0.35 if w.endswith(('.','!','?')) else (0.2 if w.endswith((',',';',':')) else 0)
        word_times.append((cum, cum + base + extra))
        cum += base + extra
    if cum > 0:
        scale = audio_dur / cum
        word_times = [(t[0]*scale, t[1]*scale) for t in word_times]
    
    def active_line(t):
        if t >= word_times[-1][1]: wi = len(word_times)-1
        else:
            wi = 0
            for i, (ws, we) in enumerate(word_times):
                if ws <= t < we: wi = i; break
        return word_to_line[min(wi, len(word_to_line)-1)]
    
    # Render frames
    n_frames = int(audio_dur * CAP_FPS) + 2
    cap_dir = tempfile.mkdtemp(prefix='tc_caps_')
    bar_y = H - CAP_MARGIN_BOTTOM - CAP_BAR_HEIGHT
    max_al = 0
    t0 = time.time()
    
    for fi in range(n_frames):
        t = fi / CAP_FPS
        if t >= audio_dur: t = audio_dur - 0.01
        al = active_line(t)
        al = max(al, max_al)
        max_al = al
        if al >= len(display_lines): al = len(display_lines)-1
        
        img = Image.new('RGBA', (W, H), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        
        text = display_lines[al]
        # Semi-transparent bar
        draw.rectangle([0, bar_y, W, bar_y + CAP_BAR_HEIGHT], fill=(0,0,0, CAP_BAR_ALPHA))
        # Center text
        bbox = font.getbbox(text)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = (W - tw) // 2
        ty = bar_y + (CAP_BAR_HEIGHT - th) // 2 - bbox[1]
        draw.text((tx, ty), text, fill=(255,255,255), font=font)
        
        img.save(os.path.join(cap_dir, f'cap_{fi:05d}.png'))
    
    print(f'  Captions: {n_frames} frames in {time.time()-t0:.1f}s', flush=True)
    
    out = tempfile.mktemp(prefix='tc_caps_', suffix='.mov')
    run(['ffmpeg', '-y', '-framerate', str(CAP_FPS),
         '-i', os.path.join(cap_dir, 'cap_%05d.png'),
         '-c:v', 'qtrle', '-pix_fmt', 'argb', '-shortest', out],
        timeout=300, label='caption encode')
    shutil.rmtree(cap_dir, ignore_errors=True)
    return out

def download_crime_scene_bg():
    """Download a crime scene background image from Pexels for thumbnails.
    Uses the Pexels API key from /opt/data/.env. Falls back gracefully."""
    try:
        # Load API key
        key = None
        env_path = '/opt/data/.env'
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('PEXELS_API_KEY='):
                        key = line.split('=', 1)[1].strip().strip('"').strip("'")
                        break
        
        if not key:
            print('  Thumbnail bg: no Pexels API key, using dark background')
            return None
        
        # Search for crime scene
        url = "https://api.pexels.com/v1/search?query=crime+scene+tape+dark&orientation=landscape&size=large&per_page=3"
        req = urllib.request.Request(url, headers={"Authorization": key})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        
        photos = data.get('photos', [])
        if not photos:
            print('  Thumbnail bg: no crime scene photos found')
            return None
        
        # Download best match
        photo_url = photos[0]['src']['landscape']
        bg_path = '/tmp/crime_scene_bg.jpg'
        urllib.request.urlretrieve(photo_url, bg_path)
        print(f'  Thumbnail bg: downloaded crime scene ({photos[0]["photographer"]})')
        return bg_path
    except Exception as e:
        print(f'  Thumbnail bg: download failed ({e}), using dark background')
        return None

def make_thumbnail(title, output_path):
    """Generate thumbnail: crime scene background + dark overlay + large title + TRUE CRIME badge."""
    W, H = 1280, 720
    
    # Load crime scene background (with fallback to solid dark)
    bg_path = '/tmp/crime_scene_bg.jpg'
    try:
        bg = Image.open(bg_path).convert('RGB').resize((W, H), Image.LANCZOS)
    except Exception:
        bg = Image.new('RGB', (W, H), (10, 10, 20))
    
    img = bg.copy()
    draw = ImageDraw.Draw(img)
    
    # Dark gradient overlay for text readability
    overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    # Full dark overlay at 50% opacity
    for y in range(H):
        alpha = int(140 + 40 * (y / H))  # 140-180 alpha gradient
        odraw.line([(0, y), (W, y)], fill=(0, 0, 0, alpha))
    img.paste(overlay, (0, 0), overlay)
    draw = ImageDraw.Draw(img)
    
    # Larger fonts
    try:
        title_font = ImageFont.truetype(FONT_FILE, 72)   # was 52
        subtitle_font = ImageFont.truetype(FONT_FILE, 48)
        badge_font = ImageFont.truetype(FONT_FILE, 80)    # was 56 — bigger, bolder
    except:
        title_font = ImageFont.load_default()
        subtitle_font = title_font
        badge_font = title_font
    
    # Word-wrap title (wider: 1150px for 72pt font)
    words = title.split()
    lines = []
    cur = []
    max_w = 1150
    for w in words:
        test = ' '.join(cur + [w])
        if title_font.getbbox(test)[2] <= max_w:
            cur.append(w)
        else:
            if cur: lines.append(' '.join(cur))
            cur = [w]
    if cur: lines.append(' '.join(cur))
    
    # If too many lines, shrink font
    if len(lines) > 4:
        try:
            title_font = ImageFont.truetype(FONT_FILE, 56)
        except:
            pass
        lines = []
        cur = []
        for w in words:
            test = ' '.join(cur + [w])
            if title_font.getbbox(test)[2] <= max_w:
                cur.append(w)
            else:
                if cur: lines.append(' '.join(cur))
                cur = [w]
        if cur: lines.append(' '.join(cur))
    
    # Draw title with stronger shadow
    total_h = sum(title_font.getbbox(l)[3] for l in lines) + (len(lines)-1)*14
    y = (H - total_h) // 2 - 50
    for line in lines:
        bbox = title_font.getbbox(line)
        tw = bbox[2] - bbox[0]
        tx = (W - tw) // 2
        # Thicker shadow (4px offset)
        for dx, dy in [(4,4), (-2,-2), (2,-2), (-2,2)]:
            draw.text((tx+dx, y+dy), line, fill=(0,0,0), font=title_font)
        draw.text((tx, y), line, fill=(255,255,255), font=title_font)
        y += bbox[3] + 14
    
    # TRUE CRIME badge — larger, suspense-red with yellow police-tape accent
    badge_text = "TRUE CRIME"
    bbox = badge_font.getbbox(badge_text)
    bw, bh = bbox[2] - bbox[0] + 80, bbox[3] + 40  # more padding for bigger font
    bx, by = (W - bw) // 2, y + 30
    
    # Dark shadow backdrop behind badge for extra pop
    draw.rectangle([bx-8, by-8, bx+bw+8, by+bh+8], fill=(5, 2, 2))
    # Police tape yellow border (thicker)
    draw.rectangle([bx-5, by-5, bx+bw+5, by+bh+5], fill=(220, 180, 20))
    # Suspense blood-red badge background
    draw.rectangle([bx, by, bx+bw, by+bh], fill=(130, 8, 8))
    # Dark diagonal tape stripes inside badge
    for sx in range(bx, bx+bw, 22):
        draw.line([(sx, by), (sx-bh, by+bh)], fill=(150, 12, 12), width=3)
    
    tx = bx + (bw - (bbox[2]-bbox[0])) // 2
    ty = by + (bh - bbox[3]) // 2 - bbox[1]
    # Badge text shadow — deeper for bigger font
    draw.text((tx+4, ty+4), badge_text, fill=(0,0,0), font=badge_font)
    draw.text((tx+2, ty+2), badge_text, fill=(20, 0, 0), font=badge_font)
    draw.text((tx, ty), badge_text, fill=(255,255,255), font=badge_font)
    
    img.save(output_path, 'JPEG', quality=92)
    print(f'  Thumbnail: {output_path}')

# ════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════
SCRIPT_TXT = sys.argv[1] if len(sys.argv) > 1 else '/opt/data/true_crime_script.txt'
TITLE = sys.argv[2] if len(sys.argv) > 2 else 'The Sodder Children: 5 Kids Vanished on Christmas Eve 1945'
OUTPUT = sys.argv[3] if len(sys.argv) > 3 else '/tmp/true_crime_final.mp4'
AUDIO = '/tmp/true_crime_audio.mp3'
THUMB = '/tmp/true_crime_thumb.jpg'

t_total = time.time()

# Load script
with open(SCRIPT_TXT) as f:
    script = f.read().strip()
n_words = len(script.split())
print(f'Script: {n_words} words')

# 1. TTS
if not os.path.exists(AUDIO):
    print('Generating TTS...', flush=True)
    r = subprocess.run([EDGE_TTS, '--voice', VOICE, '--rate', '+10%', '-f', SCRIPT_TXT, '--write-media', AUDIO],
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        raise RuntimeError(f'TTS: {r.stderr}')
audio_dur = probe_dur(AUDIO)
print(f'Audio: {audio_dur:.1f}s = {audio_dur/60:.1f} min')

# 2. Images (need ~audio_dur/4.5 segments)
n_imgs = min(130, max(60, int(audio_dur / 4.5)))
queries = [
    'dark night house fire burning', 'police investigation crime scene',
    'mystery fog abandoned building', 'vintage 1940s family portrait',
    'west virginia mountains forest', 'old billboard highway',
    'burned ruins house debris', 'detective evidence board',
    'small town main street 1940s', 'letters mailbox old photograph',
    'newspaper headline crime', 'courtroom judge gavel',
    'missing person poster', 'flames fire dark',
    'empty road night fog', 'typewriter old document',
    'telephone vintage 1940s', 'cemetery fog grave',
]
per_q = max(6, n_imgs // len(queries) + 2)
print(f'Fetching {n_imgs} images from {len(queries)} queries...')
all_photos = []
for q in queries:
    try:
        photos = search_photos(q, n=per_q, orientation='landscape')
        all_photos.extend(photos)
    except Exception as e:
        print(f'  {q}: SKIP ({e})')
all_photos = all_photos[:n_imgs]

tmp_dir = tempfile.mkdtemp(prefix='tc_')
img_paths = []
for i, photo in enumerate(all_photos):
    path = os.path.join(tmp_dir, f'img_{i:03d}.jpg')
    try:
        download_photo(photo['url'], path, timeout=20)
        img_paths.append(path)
    except:
        pass
n_segs = len(img_paths)
seg_dur = (audio_dur + (n_segs - 1) * CROSSFADE) / n_segs
seg_dur = max(2.0, min(8.0, seg_dur))
print(f'Downloaded {n_segs} images, segment: {seg_dur:.1f}s')

# 3. Ken Burns
t0 = time.time()
seg_dir = tempfile.mkdtemp(prefix='tc_segs_')
for i, img in enumerate(img_paths):
    out = os.path.join(seg_dir, f'seg_{i:03d}.mp4')
    nf = int(seg_dur * KB_FPS)
    zs, ze = (ZOOM_START, ZOOM_END) if i % 2 == 0 else (ZOOM_END, ZOOM_START)
    zd = ze - zs
    ease = f'3*(on/{nf})^2-2*(on/{nf})^3'
    z_expr = f'if(eq(on,0),{zs},{zs}+{zd}*({ease}))'
    vf = (
        f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"   # normalize to 16:9
        f"zoompan=z='{z_expr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={nf}:s={W}x{H}:fps={KB_FPS}"
    )
    run(['ffmpeg', '-y', '-loop', '1', '-i', img, '-vf', vf,
         '-c:v', 'libx264', '-preset', 'fast', '-crf', '23', '-pix_fmt', 'yuv420p',
         '-t', str(seg_dur), '-an', out], timeout=60, label=f'KB {i}')
seg_paths = sorted([os.path.join(seg_dir, f) for f in os.listdir(seg_dir) if f.endswith('.mp4')])
print(f'Ken Burns: {len(seg_paths)} segs in {time.time()-t0:.1f}s')

# 4. Cascaded xfade
t0 = time.time()
batch_outs = []
for bi in range(0, len(seg_paths), BATCH_SIZE):
    batch = seg_paths[bi:bi+BATCH_SIZE]
    if len(batch) == 1:
        batch_outs.append(batch[0])
        continue
    bout = os.path.join(tmp_dir, f'batch_{bi:03d}.mp4')
    inputs = [x for s in batch for x in ('-i', s)]
    fps_parts = []
    vl = ['0:v']
    for j in range(1, len(batch)):
        off = j * seg_dur - j * CROSSFADE
        ol = f'vb{bi}_{j}'
        fps_parts.append(f'[{vl[-1]}][{j}:v]xfade=transition=fade:duration={CROSSFADE}:offset={off:.4f}[{ol}]')
        vl.append(ol)
    run(['ffmpeg', '-y'] + inputs + ['-filter_complex', ';'.join(fps_parts),
         '-map', f'[{vl[-1]}]', '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
         '-pix_fmt', 'yuv420p', '-an', bout], timeout=300, label=f'xfade batch {bi}')
    batch_outs.append(bout)
print(f'{len(batch_outs)} batches in {time.time()-t0:.1f}s')

# 5. Merge batches
if len(batch_outs) == 1:
    video = batch_outs[0]
else:
    bd = tempfile.mkdtemp(prefix='tc_merge_')
    for bi, bp in enumerate(batch_outs):
        shutil.copy2(bp, os.path.join(bd, f'b{bi:03d}.mp4'))
    cl = os.path.join(tmp_dir, 'merge.txt')
    with open(cl, 'w') as f:
        for fn in sorted(os.listdir(bd)):
            f.write(f"file '{os.path.join(bd, fn)}'\n")
    video = os.path.join(tmp_dir, 'merged.mp4')
    run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', cl, '-c', 'copy', '-an', video],
        timeout=120, label='merge')

# 6. Captions
caps = render_captions(script, audio_dur)

# 7. Final compose (video + captions + audio)
# First mux video+audio, then overlay captions
tmp_muxed = os.path.join(tmp_dir, 'muxed.mp4')
run(['ffmpeg', '-y', '-i', video, '-i', AUDIO, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k',
     '-shortest', tmp_muxed], timeout=120, label='mux audio')

# Detect best encoder: hw V4L2 or software fallback
# NOTE: h264_v4l2m2m unreliable with overlay filters on RPi — force SW
hw_enc = None
# Use ultrafast for speed on RPi; HW encoder uses -b:v, SW uses -crf
if hw_enc:
    vcodec_opts = ['-c:v', hw_enc, '-b:v', '4M', '-pix_fmt', 'yuv420p']
else:
    vcodec_opts = ['-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23', '-pix_fmt', 'yuv420p']

compose_timeout = 900  # 15 min for long videos
run(['ffmpeg', '-y', '-i', tmp_muxed, '-i', caps,
     '-filter_complex', '[0:v][1:v]overlay=0:0:format=auto[outv]',
     '-map', '[outv]', '-map', '0:a'] + vcodec_opts +
     ['-c:a', 'copy', '-shortest', '-movflags', '+faststart',
      '-r', str(FPS), OUTPUT], timeout=compose_timeout, label='final compose')

# 8. Thumbnail
download_crime_scene_bg()
make_thumbnail(TITLE, THUMB)

final_dur = probe_dur(OUTPUT)
size_mb = os.path.getsize(OUTPUT) / 1e6
total_t = time.time() - t_total
print(f'\n{"="*60}')
print(f'DONE: {OUTPUT}')
print(f'Duration: {final_dur:.1f}s ({final_dur/60:.1f} min) | Size: {size_mb:.1f} MB')
print(f'Thumbnail: {THUMB}')
print(f'Total: {total_t:.0f}s ({total_t/60:.1f} min)')
print(f'{"="*60}')
