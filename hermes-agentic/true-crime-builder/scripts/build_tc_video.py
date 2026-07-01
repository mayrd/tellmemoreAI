#!/usr/bin/env python3
"""Integrated true crime video builder: TTS → Pexels → Ken Burns → Captions → Thumbnail → Upload.
Landscape 1920×1080, 10-15 min, subtitle bar captions, thumbnail with title overlay.
"""
import subprocess, sys, os, tempfile, shutil, json, time, re
from PIL import Image, ImageFont, ImageDraw

SCRIPT_DIR = '/opt/data/skills/social-media/youtube-shorts-builder/scripts'
sys.path.insert(0, SCRIPT_DIR)
from pexels import search_photos, download_photo

# ── Config ──
W, H = 1920, 1080
FPS = 24; KB_FPS = 30
CROSSFADE = 0.5
ZOOM_START, ZOOM_END = 1.0, 1.08
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

def make_thumbnail(title, output_path):
    """Generate thumbnail: dark background + title + TRUE CRIME badge."""
    img = Image.new('RGB', (1280, 720), (15, 15, 25))
    draw = ImageDraw.Draw(img)
    
    # Title font
    try:
        title_font = ImageFont.truetype(FONT_FILE, 52)
        badge_font = ImageFont.truetype(FONT_FILE, 36)
    except:
        title_font = ImageFont.load_default()
        badge_font = title_font
    
    # Word-wrap title
    words = title.split()
    lines = []
    cur = []
    for w in words:
        test = ' '.join(cur + [w])
        if title_font.getbbox(test)[2] <= 1100:
            cur.append(w)
        else:
            if cur: lines.append(' '.join(cur))
            cur = [w]
    if cur: lines.append(' '.join(cur))
    
    # Draw title centered
    total_h = sum(title_font.getbbox(l)[3] for l in lines) + (len(lines)-1)*10
    y = (720 - total_h) // 2 - 30
    for line in lines:
        bbox = title_font.getbbox(line)
        tw = bbox[2] - bbox[0]
        tx = (1280 - tw) // 2
        draw.text((tx+2, y+2), line, fill=(0,0,0), font=title_font)
        draw.text((tx, y), line, fill=(255,255,255), font=title_font)
        y += bbox[3] + 10
    
    # TRUE CRIME badge
    badge_text = "TRUE CRIME"
    bbox = badge_font.getbbox(badge_text)
    bw, bh = bbox[2] - bbox[0] + 40, bbox[3] + 20
    bx, by = (1280 - bw) // 2, y + 20
    draw.rectangle([bx, by, bx+bw, by+bh], fill=(180, 30, 30))
    tx = bx + (bw - (bbox[2]-bbox[0])) // 2
    ty = by + (bh - bbox[3]) // 2 - bbox[1]
    draw.text((tx, ty), badge_text, fill=(255,255,255), font=badge_font)
    
    img.save(output_path, 'JPEG', quality=90)
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
    vf = f"zoompan=z='{z_expr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={nf}:s={W}x{H}:fps={KB_FPS}"
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
run(['ffmpeg', '-y', '-i', tmp_muxed, '-i', caps,
     '-filter_complex', '[0:v][1:v]overlay=0:0:format=auto[outv]',
     '-map', '[outv]', '-map', '0:a',
     '-c:v', 'libx264', '-preset', 'fast', '-crf', '23', '-pix_fmt', 'yuv420p',
     '-c:a', 'aac', '-b:a', '128k', '-shortest', '-movflags', '+faststart',
     '-r', str(FPS), OUTPUT], timeout=300, label='final compose')

# 8. Thumbnail
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
