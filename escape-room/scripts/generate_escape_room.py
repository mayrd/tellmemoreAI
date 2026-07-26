#!/usr/bin/env python3
"""
Generic Audio Escape Room Video Generator
=========================================
Generates an interactive audio escape room YouTube video from story data.

Usage:
  python3 scripts/generate_escape_room.py --story de/letzte-schicht

The story file (e.g. stories/de/letzte-schicht.py) must define:
  STORY, VOICES, CHAPTERS, DECISIONS, SEGMENTS
"""

import asyncio, json, os, sys, subprocess, time, argparse, importlib.util
from pathlib import Path
import edge_tts

# ── Args ────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Generate Audio Escape Room Video")
parser.add_argument("--story", "-s", default="de/letzte-schicht",
                    help="Story path relative to stories/ dir (e.g. 'de/letzte-schicht')")
parser.add_argument("--generate", "-g", action="store_true",
                    help="Generate a new AI story via Gemini before building")
parser.add_argument("--skip-tts", action="store_true",
                    help="Skip TTS generation (use existing audio)")
parser.add_argument("--preset", default="ultrafast",
                    help="FFmpeg preset (default: ultrafast, good for RPi)")
args = parser.parse_args()

# ── Paths ────────────────────────────────────────────────────
PROJECT_DIR = Path(__file__).parent.parent
SCRIPTS_DIR = PROJECT_DIR / "scripts"
ASSETS_DIR = PROJECT_DIR / "assets"
STORIES_DIR = PROJECT_DIR / "stories"

# Load story
STORY_PATH = Path(args.story)
if not STORY_PATH.suffix:
    STORY_PATH = STORY_PATH.with_suffix(".py")
story_file = PROJECT_DIR / "stories" / STORY_PATH
if not story_file.exists():
    print(f"ERROR: Story file not found: {story_file}")
    print(f"Available stories:")
    for f in sorted((PROJECT_DIR / "stories").rglob("*.py")):
        rel = f.relative_to(PROJECT_DIR / "stories")
        print(f"  {rel}")
    sys.exit(1)

spec = importlib.util.spec_from_file_location("story_data", story_file)
story_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(story_mod)

STORY_META = story_mod.STORY
VOICES = story_mod.VOICES
CHAPTERS = story_mod.CHAPTERS
DECISIONS = story_mod.DECISIONS
SEGMENTS = story_mod.SEGMENTS

LANG = STORY_META["language"]
STORY_ID = STORY_META["id"]
STORY_TITLE = STORY_META["title"]

AUDIO_DIR = ASSETS_DIR / "audio" / LANG
OUTPUT_DIR = PROJECT_DIR / "output"

print(f"Story: {STORY_ID} ({LANG})")
print(f"Title: {STORY_TITLE}")
print(f"Target play: ~{STORY_META.get('target_play_minutes', '?')} min")

# ── Voice Resolution ────────────────────────────────────────
def resolve_voice(voice_key: str) -> tuple[str, str]:
    """Return (voice_name, rate) for a voice role key."""
    cfg = VOICES.get(voice_key, VOICES["narrator"])
    return cfg["voice"], cfg.get("rate", "+0%")

# ── TTS Generation ───────────────────────────────────────────
def chunk_text(text: str, max_chars: int = 3000) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    chunks, sentences = [], text.replace("! ", "!\n").replace("? ", "?\n").replace(". ", ".\n").split("\n")
    current = ""
    for sentence in sentences:
        s = sentence.strip()
        if not s: continue
        if len(current) + len(s) + 1 > max_chars and current:
            chunks.append(current.strip())
            current = s + " "
        else:
            current += s + " "
    if current.strip(): chunks.append(current.strip())
    return chunks

async def generate_tts(text: str, voice: str, output_path: str, rate: str = "+0%", pitch: str = "+0Hz") -> float:
    if not text: return 0.0
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save(output_path)
    result = subprocess.run(["ffprobe", "-v", "quiet", "-show_format", "-of", "json", output_path],
                            capture_output=True, text=True)
    return float(json.loads(result.stdout)["format"]["duration"]) if result.returncode == 0 else 0.0

def generate_silence(duration_sec: float, output_path: str, sample_rate: int = 44100):
    import struct, wave
    num_samples = int(sample_rate * duration_sec)
    with wave.open(output_path, 'w') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f'<{num_samples}h', *[0] * num_samples))

async def generate_all_audio():
    """Generate TTS for all CHAPTERS and DECISIONS."""
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    segments = {}
    total_chars = 0
    
    # Chapters
    for key, ch in CHAPTERS.items():
        text = ch.get("text", "")
        if not text: continue
        total_chars += len(text)
        voice_name, rate = resolve_voice(ch.get("voice", "narrator"))
        chunks_list = chunk_text(text)
        
        chunk_paths = []
        for i, chunk in enumerate(chunks_list):
            path = str(AUDIO_DIR / f"{key}_part{i:02d}.mp3")
            dur = await generate_tts(chunk, voice_name, path, rate=rate)
            chunk_paths.append((path, dur))
        segments[key] = chunk_paths
        print(f"  [{key}] {sum(d for _, d in chunk_paths):.1f}s ({voice_name})")
    
    # Decision sub-segments
    for dk, dc in DECISIONS.items():
        for part in ["question", "options", "question_repeat", "options_repeat"]:
            text = dc.get(part, "")
            if not text: continue
            total_chars += len(text)
            voice_name, rate = resolve_voice("decision")
            path = str(AUDIO_DIR / f"{dk}_{part}.mp3")
            dur = await generate_tts(text, voice_name, path, rate=rate)
            segments[f"{dk}_{part}"] = [(path, dur)]
            print(f"  [{dk}_{part}] {dur:.1f}s ({voice_name})")
    
    print(f"\nTotal text: {total_chars} chars")
    return segments

# ── Video Assembly ───────────────────────────────────────────
def assemble_video(segments):
    """Build the final video with audio concat, chapters, and thumbnail."""
    thumbnail_path = str(ASSETS_DIR / "images" / "thumbnail.png")
    
    # Build file list and get exact durations
    file_list = []
    gap_path = str(AUDIO_DIR.parent.parent / "audio" / "gap_200ms.mp3")
    
    for item in SEGMENTS:
        if isinstance(item, str):
            # Chapter or ending
            if item in segments:
                for chunk_path, _ in segments[item]:
                    file_list.append(chunk_path)
        elif isinstance(item, tuple):
            key, sub = item
            if sub == "gap":
                if os.path.exists(gap_path):
                    file_list.extend([gap_path] * 10)  # 2s gap
            if key in DECISIONS:
                for part in ["question", "options", "pause", "question_repeat", "options_repeat"]:
                    seg_key = f"{key}_{part}"
                    if part == "pause":
                        pause_path = str(AUDIO_DIR / f"{key}_pause.wav")
                        if not os.path.exists(pause_path):
                            generate_silence(DECISIONS[key].get("pause_s", 30), pause_path)
                        file_list.append(pause_path)
                    elif seg_key in segments:
                        fpath = segments[seg_key][0][0]
                        file_list.append(fpath)
    
    # Get exact durations
    exact_durations = []
    for fp in file_list:
        r = subprocess.run(["ffprobe", "-v", "quiet", "-show_format", "-of", "json", fp],
                           capture_output=True, text=True)
        dur = float(json.loads(r.stdout)["format"]["duration"]) if r.returncode == 0 else 0.0
        exact_durations.append(dur)
    
    # Calculate chapter timestamps
    chapters_out = []
    current_time = 0.0
    file_idx = 0
    
    for item in SEGMENTS:
        if isinstance(item, str):
            dur_sum = 0.0
            if item in segments:
                for _ in segments[item]:
                    dur_sum += exact_durations[file_idx] if file_idx < len(exact_durations) else 0
                    file_idx += 1
            
            ch_info = CHAPTERS.get(item, {})
            title = ch_info.get("title", "")
            if title:
                chapters_out.append({"start_sec": current_time, "label": title, "key": item})
            current_time += dur_sum
        
        elif isinstance(item, tuple):
            key, sub = item
            if sub == "gap":
                for _ in range(10):
                    current_time += exact_durations[file_idx] if file_idx < len(exact_durations) else 0
                    file_idx += 1
            if key in DECISIONS:
                total_dur = 0.0
                for part in ["question", "options", "pause", "question_repeat", "options_repeat"]:
                    seg_key = f"{key}_{part}"
                    if part == "pause":
                        total_dur += exact_durations[file_idx] if file_idx < len(exact_durations) else 0
                        file_idx += 1
                    elif seg_key in segments:
                        total_dur += exact_durations[file_idx] if file_idx < len(exact_durations) else 0
                        file_idx += 1
                current_time += total_dur
    
    total_dur = sum(exact_durations)
    
    print(f"\nChapter markers: {len(chapters_out)}")
    for i, ch in enumerate(chapters_out):
        m, s = int(ch["start_sec"]//60), int(ch["start_sec"]%60)
        print(f"  {i+1:2d}. {m:02d}:{s:02d} - {ch['label']}")
    print(f"\nTotal duration: {int(total_dur//60)}:{int(total_dur%60):02d}")
    
    # Write concat list
    file_list_path = str(OUTPUT_DIR / "file_list.txt")
    with open(file_list_path, "w") as f:
        for fp in file_list:
            f.write(f"file '{fp}'\n")
    
    # Concat audio
    audio_concat = str(OUTPUT_DIR / f"{STORY_ID}_audio.mp3")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", file_list_path, "-c", "copy", audio_concat],
                   check=True, capture_output=True, timeout=120)
    print(f"  Audio: {os.path.getsize(audio_concat)/1e6:.1f} MB")
    
    # Get actual audio duration
    dur_r = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", audio_concat],
                           capture_output=True, text=True)
    actual_dur = float(dur_r.stdout.strip()) if dur_r.returncode == 0 else total_dur
    
    # Scale chapter timestamps to actual duration
    scale = actual_dur / total_dur if total_dur > 0 else 1.0
    for ch in chapters_out:
        ch["start_sec"] *= scale
    total_dur = actual_dur
    
    # Write chapter metadata
    meta_path = str(OUTPUT_DIR / "chapter_meta.txt")
    with open(meta_path, "w") as f:
        f.write(";FFMETADATA1\n")
        for i, ch in enumerate(chapters_out):
            start_ms = int(ch["start_sec"] * 1000)
            end_ms = int(chapters_out[i+1]["start_sec"] * 1000) if i+1 < len(chapters_out) else int(total_dur * 1000)
            f.write(f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={start_ms}\nEND={end_ms}\ntitle={ch['label']}\n")
    
    # Create video
    output_video = str(OUTPUT_DIR / f"{STORY_ID}.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-loop", "1", "-t", str(actual_dur),
        "-i", thumbnail_path, "-i", audio_concat,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", args.preset, "-tune", "stillimage",
        "-c:a", "copy", "-shortest", output_video,
    ], check=True, capture_output=True, timeout=300)
    print(f"  Video: {os.path.getsize(output_video)/1e6:.1f} MB")
    
    # Add chapters
    chaptered = str(OUTPUT_DIR / f"{STORY_ID}_chapters.mp4")
    subprocess.run(["ffmpeg", "-y", "-i", output_video, "-i", meta_path,
                    "-map", "0", "-map_metadata", "1", "-c", "copy", chaptered],
                   check=True, capture_output=True, timeout=120)
    os.replace(chaptered, output_video)
    print(f"  Chapters added")
    
    return output_video, chapters_out

# ── Description ──────────────────────────────────────────────
def generate_description(chapters_out):
    """Generate YouTube description with chapter timestamps."""
    desc = f"# 🎧 {STORY_TITLE}\n\n"
    desc += STORY_META.get("description_intro", "") + "\n\n"
    desc += "Wähle deinen Weg. Jede Entscheidung zählt.\n\n---\n\n## 📖 Chapters\n\n"
    
    for i, ch in enumerate(chapters_out):
        m, s = int(ch["start_sec"]//60), int(ch["start_sec"]%60)
        desc += f"{m:02d}:{s:02d} – {ch['label']}\n"
    
    desc += "\n---\n\n## 🎮 How it works\n"
    desc += "1️⃣ Listen to the intro and first decision\n"
    desc += "2️⃣ Choose between option A or B\n"
    desc += "3️⃣ Click the corresponding chapter link above\n"
    desc += "4️⃣ The story continues to the next decision point\n\n"
    desc += f"At each decision you have 30 seconds to make your choice.\n\n"
    desc += "---\n\n**Production:** Tell Me More AI\n"
    desc += f"**Voices:** Edge TTS\n"
    desc += f"**Language:** {LANG}\n"
    
    tags = STORY_META.get("tags", [])
    if tags:
        desc += "\n" + " ".join(f"#{t}" for t in tags)
    
    desc_path = str(OUTPUT_DIR / f"{STORY_ID}_description.txt")
    with open(desc_path, "w", encoding="utf-8") as f:
        f.write(desc)
    print(f"\nDescription: {desc_path}")

# ── Main ─────────────────────────────────────────────────────
async def main():
    print("=" * 60)
    print(f"🎧 Audio Escape Room Generator — {STORY_ID}")
    print("=" * 60)
    
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # ── AI Story Generation ──────────────────────────────────
    if args.generate:
        print("\n🤖 Generating AI story via Gemini...")
        gen_result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "story_generator.py")],
            capture_output=True, text=True, timeout=600,
        )
        print(gen_result.stdout)
        if gen_result.returncode != 0:
            print(f"ERROR: Story generation failed: {gen_result.stderr[:500]}")
            return
        # Extract generated story filename from output
        import re as _re
        gen_match = _re.search(r"stories/(\w+/\w+)", gen_result.stdout)
        if gen_match:
            story_path = gen_match.group(1)
            print(f"  Using generated story: {story_path}")
            # Re-import with new story
            import importlib as _il
            spec = _il.util.spec_from_file_location("story_data", str(STORIES_DIR / f"{story_path}.py"))
            story_mod = _il.util.module_from_spec(spec)
            spec.loader.exec_module(story_mod)
            globals()["STORY"] = story_mod.STORY
            globals()["VOICES"] = story_mod.VOICES
            globals()["CHAPTERS"] = story_mod.CHAPTERS
            globals()["DECISIONS"] = story_mod.DECISIONS
            globals()["SEGMENTS"] = story_mod.SEGMENTS
            globals()["STORY_ID"] = story_path
            globals()["STORY_TITLE"] = story_mod.STORY.get("title", "AI-Generated Story")
    
    if not args.skip_tts:
        print("\n📢 Generating TTS audio...")
        segments = await generate_all_audio()
    else:
        print("\n📍 Skipping TTS (--skip-tts), loading existing audio...")
        segments = {}
        for key in CHAPTERS:
            mp3s = sorted(AUDIO_DIR.glob(f"{key}_part*.mp3")) or ([AUDIO_DIR / f"{key}.mp3"] if (AUDIO_DIR / f"{key}.mp3").exists() else [])
            if mp3s:
                paths = []
                for p in mp3s:
                    r = subprocess.run(["ffprobe", "-v", "quiet", "-show_format", "-of", "json", str(p)], capture_output=True, text=True)
                    dur = float(json.loads(r.stdout)["format"]["duration"]) if r.returncode == 0 else 0
                    paths.append((str(p), dur))
                segments[key] = paths
        for dk, dc in DECISIONS.items():
            for part in ["question", "options", "question_repeat", "options_repeat"]:
                p = AUDIO_DIR / f"{dk}_{part}.mp3"
                if p.exists():
                    r = subprocess.run(["ffprobe", "-v", "quiet", "-show_format", "-of", "json", str(p)], capture_output=True, text=True)
                    dur = float(json.loads(r.stdout)["format"]["duration"]) if r.returncode == 0 else 0
                    segments[f"{dk}_{part}"] = [(str(p), dur)]
    
    print("\n🎬 Assembling video...")
    video_path, chapters_out = assemble_video(segments)
    
    print("\n📝 Generating description...")
    generate_description(chapters_out)
    
    print(f"\n✅ Done!")
    print(f"   Video: {video_path}")
    print(f"   Size: {os.path.getsize(video_path)/1e6:.1f} MB" if os.path.exists(video_path) else "")

if __name__ == "__main__":
    asyncio.run(main())
