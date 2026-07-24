#!/usr/bin/env python3
"""
Generate the interactive escape room video.
Pipeline: TTS → silence → chapters → video → info cards.
"""

import asyncio
import json
import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path

# Edge TTS
import edge_tts

PROJECT_DIR = Path(__file__).parent.parent  # escape-room root
ASSETS_DIR = PROJECT_DIR / "assets"
AUDIO_DIR = ASSETS_DIR / "audio"
OUTPUT_DIR = PROJECT_DIR / "output"
SCRIPTS_DIR = PROJECT_DIR / "scripts"

# Voices
VOICE_NARRATOR = "de-DE-KatjaNeural"       # Lena Voss (female, warm)
VOICE_DECISION = "de-DE-ConradNeural"       # Question voice (male, authoritative)
VOICE_ANTAGONIST = "de-DE-KillianNeural"    # Antagonist (male, deep)

# ─────────────────────────────────────────────────────────────
# 1. VOICE MAPPING per Segment
# ─────────────────────────────────────────────────────────────
# Maps segment keys to voices based on content type

def get_voice_for_segment(segment_key: str) -> str:
    """Determine which voice to use for each segment."""
    if segment_key.startswith("decision_"):
        return VOICE_DECISION
    if segment_key in ("ending_3", "ending_4"):
        # Dark endings use antagonist voice
        return VOICE_ANTAGONIST  
    if segment_key == "path_a2":
        # Dr. Wagner's office scene
        return VOICE_ANTAGONIST
    return VOICE_NARRATOR

# ─────────────────────────────────────────────────────────────
# 2. CHUNK TEXT for TTS (handle long segments)
# ─────────────────────────────────────────────────────────────

def chunk_text(text: str, max_chars: int = 3000) -> list[str]:
    """Split long text into chunks at sentence boundaries."""
    if len(text) <= max_chars:
        return [text]
    
    chunks = []
    sentences = text.replace("! ", "!\n").replace("? ", "?\n").replace(". ", ".\n").split("\n")
    
    current = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(current) + len(sentence) + 1 > max_chars and current:
            chunks.append(current.strip())
            current = sentence + " "
        else:
            current += sentence + " "
    
    if current.strip():
        chunks.append(current.strip())
    
    return chunks

# ─────────────────────────────────────────────────────────────
# 3. GENERATE TTS AUDIO
# ─────────────────────────────────────────────────────────────

async def generate_tts(
    text: str,
    voice: str,
    output_path: str,
    rate: str = "+0%",
    pitch: str = "+0Hz",
) -> float:
    """Generate TTS audio file. Returns duration in seconds."""
    # Handle pauses in text (30s silence marker)
    if not text:
        return 0.0
    
    communicate = edge_tts.Communicate(
        text, 
        voice,
        rate=rate,
        pitch=pitch,
    )
    
    await communicate.save(output_path)
    
    # Get duration using ffprobe
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_format", "-of", "json", output_path],
        capture_output=True, text=True, check=True,
    )
    info = json.loads(result.stdout)
    duration = float(info["format"]["duration"])
    return duration

# ─────────────────────────────────────────────────────────────
# 4. SILENCE AUDIO
# ─────────────────────────────────────────────────────────────

def generate_silence(duration_sec: float, output_path: str, sample_rate: int = 44100):
    """Generate silence audio file using ffmpeg."""
    import struct
    import wave
    
    num_samples = int(sample_rate * duration_sec)
    
    with wave.open(output_path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f'<{num_samples}h', *[0] * num_samples))

# ─────────────────────────────────────────────────────────────
# 5. MAIN PIPELINE
# ─────────────────────────────────────────────────────────────

async def generate_all_audio():
    """Generate all TTS audio files for every segment."""
    # Import story script
    import importlib
    sys.path.insert(0, str(PROJECT_DIR.resolve()))
    spec = importlib.util.spec_from_file_location("story_script", str(PROJECT_DIR / "story_script.py"))
    story = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(story)
    CHAPTERS = story.CHAPTERS
    VIDEO_SEGMENTS = story.VIDEO_SEGMENTS
    
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    
    all_segments = {}
    total_chars = 0
    
    for segment_key, chapter_label in VIDEO_SEGMENTS:
        # Skip pause segments (generated separately)
        if segment_key.endswith("_pause"):
            continue
        if segment_key not in CHAPTERS:
            continue
        
        text = CHAPTERS[segment_key]
        if not text:
            continue
        
        total_chars += len(text)
        
        # Handle long text by chunking
        chunks = chunk_text(text)
        
        if len(chunks) > 1:
            # Generate multiple chunks
            chunk_paths = []
            for i, chunk in enumerate(chunks):
                path = str(AUDIO_DIR / f"{segment_key}_part{i:02d}.mp3")
                voice = get_voice_for_segment(segment_key)
                dur = await generate_tts(chunk, voice, path)
                chunk_paths.append((path, dur))
                print(f"  [{segment_key} part {i+1}/{len(chunks)}] {dur:.1f}s ({voice})")
            
            all_segments[segment_key] = chunk_paths
        else:
            path = str(AUDIO_DIR / f"{segment_key}.mp3")
            voice = get_voice_for_segment(segment_key)
            dur = await generate_tts(text, voice, path)
            all_segments[segment_key] = [(path, dur)]
            print(f"  [{segment_key}] {dur:.1f}s ({voice})")
        
        # Add a brief gap between segments
        gap_path = str(AUDIO_DIR / f"gap_200ms.mp3")
        if not os.path.exists(gap_path):
            generate_silence(0.2, gap_path)
    
    print(f"\nTotal text: {total_chars} chars")
    return all_segments, CHAPTERS, VIDEO_SEGMENTS

# ─────────────────────────────────────────────────────────────
# 6. ASSEMBLE VIDEO
# ─────────────────────────────────────────────────────────────

def assemble_video(segments, chapter_data, segment_order):
    """Combine all audio into one video with chapter markers."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Pre-generate any missing repeat audio
    for segment_key, _ in segment_order:
        if segment_key.endswith("_repeat"):
            repeat_path = str(AUDIO_DIR / f"{segment_key}.mp3")
            if not os.path.exists(repeat_path):
                text = chapter_data.get(segment_key, "")
                if text:
                    voice = get_voice_for_segment(segment_key)
                    # Generate TTS synchronously
                    subprocess.run([
                        "python3", "-m", "edge_tts",
                        "--voice", voice,
                        "--text", text,
                        "--write-media", repeat_path,
                    ], check=True, capture_output=True, timeout=120)
                    print(f"  Generated repeat: {segment_key}")
    
    # Create FFmpeg concat file
    concat_lines = []
    chapter_markers = []
    current_time = 0.0  # seconds
    chapter_index = 1
    
    # Temporary file list for concat
    file_list_path = str(OUTPUT_DIR / "file_list.txt")
    
    with open(file_list_path, "w") as f:
        for segment_key, _ in segment_order:
            if segment_key.endswith("_pause"):
                # Generate pause silence (30 seconds)
                pause_path = str(AUDIO_DIR / f"{segment_key}.wav")
                if not os.path.exists(pause_path):
                    generate_silence(30.0, pause_path)
                f.write(f"file '{pause_path}'\n")
                current_time += 30.0
                continue
            
            if segment_key.endswith("_repeat"):
                # Generate repeat text TTS if not done
                repeat_path = str(AUDIO_DIR / f"{segment_key}.mp3")
                if not os.path.exists(repeat_path):
                    # Use decision voice for repeats
                    text = chapter_data.get(segment_key, "")
                    if text:
                        voice = get_voice_for_segment(segment_key)
                        asyncio.run(generate_tts(text, voice, repeat_path))
                
                f.write(f"file '{repeat_path}'\n")
                result = subprocess.run(
                    ["ffprobe", "-v", "quiet", "-show_format", "-of", "json", repeat_path],
                    capture_output=True, text=True,
                )
                if result.returncode == 0:
                    dur = float(json.loads(result.stdout)["format"]["duration"])
                    current_time += dur
                continue
            
            if segment_key not in segments:
                continue
            
            file_label = chapter_data.get(f"{segment_key}_title", "")
            
            # Add chapter marker at start of this segment
            if file_label:
                chapter_markers.append({
                    "index": chapter_index,
                    "start_sec": current_time,
                    "label": file_label,
                })
                chapter_index += 1
            
            # Add all audio chunks for this segment
            for chunk_path, chunk_dur in segments[segment_key]:
                f.write(f"file '{chunk_path}'\n")
                current_time += chunk_dur
    
    total_duration = current_time
    
    # Build FFmpeg command
    output_video = str(OUTPUT_DIR / "die_letzte_schicht.mp4")
    
    # Create chapter metadata file for FFmpeg
    metadata_path = str(OUTPUT_DIR / "chapter_meta.txt")
    with open(metadata_path, "w") as f:
        f.write(";FFMETADATA1\n")
        for marker in chapter_markers:
            start_ms = int(marker["start_sec"] * 1000)
            # End time is the next chapter or total duration
            next_start = total_duration * 1000
            for m in chapter_markers:
                m_start = int(m["start_sec"] * 1000)
                if m_start > start_ms and m_start < next_start:
                    next_start = m_start
            f.write("[CHAPTER]\n")
            f.write("TIMEBASE=1/1000\n")
            f.write(f"START={start_ms}\n")
            f.write(f"END={next_start}\n")
            f.write(f"title={marker['label']}\n")
    
    print(f"\nChapter markers: {len(chapter_markers)}")
    for m in chapter_markers:
        m_min = int(m["start_sec"] // 60)
        m_sec = int(m["start_sec"] % 60)
        print(f"  {m['index']:2d}. {m_min:02d}:{m_sec:02d} - {m['label']}")
    
    print(f"\nTotal duration: {int(total_duration//60)}:{int(total_duration%60):02d}")
    
    # Generate video with static image + audio + chapters
    thumbnail_path = str(ASSETS_DIR / "images" / "thumbnail.png")
    
    # First create concat with ffmpeg
    audio_concat = str(OUTPUT_DIR / "full_audio.mp3")
    
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", file_list_path,
        "-c", "copy", audio_concat,
    ], check=True, capture_output=True)
    
    # Then create video with the static image
    if os.path.exists(thumbnail_path):
        subprocess.run([
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", thumbnail_path,
            "-i", audio_concat,
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            "-metadata", f"title=Die letzte Schicht - Interaktiver Audio Escape Room",
            "-metadata", "artist=Tell Me More AI",
            "-metadata", "genre=Crime, Thriller, Interactive",
            output_video,
        ], check=True, capture_output=True)
    else:
        # Generate a black placeholder
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=1920x1080:d=5",
            "-i", audio_concat,
            "-c:v", "libx264",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_video,
        ], check=True, capture_output=True)
    
    # Add chapters using ffmpeg metadata
    chaptered_video = str(OUTPUT_DIR / "die_letzte_schicht_final.mp4")
    subprocess.run([
        "ffmpeg", "-y",
        "-i", output_video,
        "-i", metadata_path,
        "-map_metadata", "1",
        "-codec", "copy",
        chaptered_video,
    ], check=True, capture_output=True)
    
    # Replace with chaptered version
    os.replace(chaptered_video, output_video)
    
    print(f"\n✅ Video saved: {output_video}")
    print(f"   File size: {os.path.getsize(output_video) / 1024 / 1024:.1f} MB")
    
    return output_video, chapter_markers

# ─────────────────────────────────────────────────────────────
# 7. GENERATE DESCRIPTION
# ─────────────────────────────────────────────────────────────

def generate_description(chapter_markers):
    """Generate YouTube description with chapter timestamps."""
    desc = """# 🎧 Die letzte Schicht – Interaktiver Audio Escape Room

**Ein Krimi-Hörspiel von Tell Me More AI**

Du bist Kommissarin Lena Voss. Eine verlassene Psychiatrie in den Alpen. Ein verschwundener Direktor. Und eine Wahrheit, die seit Jahrzehnten vergraben liegt.

Wähle deinen Weg. Jede Entscheidung zählt. Vier mögliche Enden.

---

## 📖 Kapitel (zum Springen klicken)

"""
    
    for m in chapter_markers:
        m_min = int(m["start_sec"] // 60)
        m_sec = int(m["start_sec"] % 60)
        desc += f"{m_min:02d}:{m_sec:02d} – {m['label']}\n"
    
    desc += """
---

## 🎮 So funktioniert's

1️⃣ Höre das Intro und die erste Entscheidung  
2️⃣ Wähle zwischen Option A und B  
3️⃣ Springe zum entsprechenden Kapitel (Link oben)  
4️⃣ Die Geschichte geht weiter – bis zum nächsten Entscheidungspunkt  

Bei jeder Entscheidung hast du **30 Sekunden Zeit**, um zu klicken.  
Danach wird die Frage wiederholt.

---

## 🏁 Die 4 Enden

| Ende | Beschreibung |
|------|-------------|
| **Ende 1 – Gerechtigkeit** | 🤝 Der offizielle Weg – nicht perfekt, aber richtig |
| **Ende 2 – Die Wahrheit** | ⭐ Die Wahrheit kommt ans Licht – das beste Ende |
| **Ende 3 – Verspielt** | 💀 Zu viel Risiko – die falsche Entscheidung |
| **Ende 4 – Der Jäger** | 🕳️ Im Dunkel gefangen – kein Entkommen |

---

## 📝 Credits

**Produktion:** Tell Me More AI  
**Stimmen:** Edge TTS (KatjaNeural, ConradNeural, KillianNeural)  
**Geschichte & Konzept:** Tell Me More AI  
**Kanal:** @TellMeMoreAI  

---

**Hast du alle 4 Enden gefunden?** Schreib's in die Kommentare!

#Krimi #Hörspiel #EscapeRoom #Interaktiv #AudioDrama #TrueCrime #TellMeMoreAI
"""
    
    desc_path = str(OUTPUT_DIR / "youtube_description.txt")
    with open(desc_path, "w", encoding="utf-8") as f:
        f.write(desc)
    print(f"\n📝 Description saved: {desc_path}")
    return desc

# ─────────────────────────────────────────────────────────────
# 8. RUN
# ─────────────────────────────────────────────────────────────

async def main():
    print("=" * 60)
    print("🎧 Die letzte Schicht – Audio Escape Room Generator")
    print("=" * 60)
    
    out_dir = OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    
    # Step 1: Generate all audio
    print("\n📢 Step 1: Generating TTS audio...")
    segments, chapter_data, segment_order = await generate_all_audio()
    
    # Step 2: Assemble video
    print("\n🎬 Step 2: Assembling video...")
    video_path, chapter_markers = assemble_video(segments, chapter_data, segment_order)
    
    # Step 3: Generate description
    print("\n📝 Step 3: Generating YouTube description...")
    generate_description(chapter_markers)
    
    print("\n✅ Done!")
    print(f"   Video: {video_path}")
    print(f"   Chapters: {len(chapter_markers)}")
    
    # Save chapter timestamps for later reference
    chapters_json = []
    for m in chapter_markers:
        m_min = int(m["start_sec"] // 60)
        m_sec = int(m["start_sec"] % 60)
        chapters_json.append({
            "index": m["index"],
            "time": f"{m_min:02d}:{m_sec:02d}",
            "seconds": m["start_sec"],
            "title": m["label"],
        })
    
    with open(str(out_dir / "chapters.json"), "w", encoding="utf-8") as f:
        json.dump(chapters_json, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    asyncio.run(main())
