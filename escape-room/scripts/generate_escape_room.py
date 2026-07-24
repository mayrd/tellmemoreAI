#!/usr/bin/env python3
"""
Generate the interactive escape room video.
Pipeline: TTS -> silence -> chapters -> video -> info cards.
Supports multiple languages via --language flag.
"""

import asyncio
import json
import os
import sys
import subprocess
import tempfile
import shutil
import argparse
from pathlib import Path

# Edge TTS
import edge_tts

# Parse arguments
parser = argparse.ArgumentParser(description="Generate Audio Escape Room Video")
parser.add_argument("--language", "-l", default="de", choices=["de"],
                    help="Language code (default: de)")
args = parser.parse_args()
LANGUAGE = args.language

PROJECT_DIR = Path(__file__).parent.parent  # escape-room root
ASSETS_DIR = PROJECT_DIR / "assets"
AUDIO_DIR = ASSETS_DIR / "audio" / LANGUAGE
OUTPUT_DIR = PROJECT_DIR / "output"
SCRIPTS_DIR = PROJECT_DIR / "scripts"

# ─────────────────────────────────────────────────────────────
# LANGUAGE CONFIGURATION
# ─────────────────────────────────────────────────────────────
# Add new languages here. Voices must exist in edge-tts.
# List all voices: python3 -m edge_tts --list-voices | grep <lang>

LANGUAGE_CONFIG = {
    "de": {
        "narrator": "de-DE-KatjaNeural",       # Female, warm – narrator
        "decision": "de-DE-ConradNeural",       # Male, authoritative – questions
        "antagonist": "de-DE-KillianNeural",    # Male, deep – antagonist scenes
        "decision_rate": "-15%",                # Slower for clarity
    },
    # Future languages — uncomment and add voice names when ready:
    # "en": {
    #     "narrator": "en-US-JennyNeural",
    #     "decision": "en-US-GuyNeural",
    #     "antagonist": "en-US-DavisNeural",
    #     "decision_rate": "-15%",
    # },
    # "fr": {
    #     "narrator": "fr-FR-DeniseNeural",
    #     "decision": "fr-FR-HenriNeural",
    #     "antagonist": "fr-FR-ClaudeNeural",
    #     "decision_rate": "-15%",
    # },
    # "es": {
    #     "narrator": "es-ES-ElviraNeural",
    #     "decision": "es-ES-AlvaroNeural",
    #     "antagonist": "es-ES-TeoNeural",
    #     "decision_rate": "-15%",
    # },
}

def get_voice_for_segment(segment_key: str) -> tuple[str, str]:
    """Determine (voice, rate) for each segment based on language config."""
    cfg = LANGUAGE_CONFIG.get(LANGUAGE, LANGUAGE_CONFIG["de"])
    narrator, decision, antagonist = cfg["narrator"], cfg["decision"], cfg["antagonist"]
    rate = cfg["decision_rate"]
    
    if segment_key.startswith("decision_"):
        return (decision, rate)
    if segment_key in ("ending_3", "ending_4"):
        return (antagonist, "+0%")
    if segment_key == "chapter_a2":
        return (antagonist, "+0%")
    return (narrator, "+0%")

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
                voice, rate = get_voice_for_segment(segment_key)
                dur = await generate_tts(chunk, voice, path, rate=rate)
                chunk_paths.append((path, dur))
                print(f"  [{segment_key} part {i+1}/{len(chunks)}] {dur:.1f}s ({voice})")
            
            all_segments[segment_key] = chunk_paths
        else:
            path = str(AUDIO_DIR / f"{segment_key}.mp3")
            voice, rate = get_voice_for_segment(segment_key)
            dur = await generate_tts(text, voice, path, rate=rate)
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
    print(f"\n🎬 Step 2: Assembling video...")
    
    # Calculate exact timestamps from audio files
    file_list = []
    for segment_key, _ in segment_order:
        if segment_key.endswith("_pause"):
            pause_path = str(AUDIO_DIR / f"{segment_key}.wav")
            if not os.path.exists(pause_path):
                generate_silence(30.0, pause_path)
            file_list.append(pause_path)
        elif segment_key == "gap_2s":
            gap_path = str(AUDIO_DIR / "gap_200ms.mp3")
            file_list.extend([gap_path] * 10)
        elif segment_key.endswith("_repeat") or segment_key.endswith("_options") or segment_key.endswith("_options_repeat") or segment_key.endswith("_question_repeat"):
            repeat_path = str(AUDIO_DIR / f"{segment_key}.mp3")
            if not os.path.exists(repeat_path):
                text = chapter_data.get(segment_key, "")
                if text:
                    voice, rate = get_voice_for_segment(segment_key)
                    subprocess.run([
                        "python3", "-m", "edge_tts",
                        "--voice", voice, "--rate", rate,
                        "--text", text, "--write-media", repeat_path,
                    ], check=True, capture_output=True, timeout=120)
            file_list.append(repeat_path)
        elif segment_key in segments:
            for chunk_path, _ in segments[segment_key]:
                file_list.append(chunk_path)
    
    # Get exact durations of all files using ffprobe
    exact_durations = []
    for fp in file_list:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_format", "-of", "json", fp],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            duration = float(json.loads(result.stdout)["format"]["duration"])
        else:
            duration = 0.0
        exact_durations.append(duration)
    
    # Calculate chapter timestamps from exact durations
    chapter_markers = []
    chapter_index = 1
    current_time = 0.0
    file_idx = 0
    
    for segment_key, _ in segment_order:
        if segment_key.endswith("_pause"):
            current_time += exact_durations[file_idx] if file_idx < len(exact_durations) else 0
            file_idx += 1
        elif segment_key == "gap_2s":
            for _ in range(10):
                current_time += exact_durations[file_idx] if file_idx < len(exact_durations) else 0
                file_idx += 1
        elif segment_key.endswith("_repeat") or segment_key.endswith("_options") or segment_key.endswith("_options_repeat") or segment_key.endswith("_question_repeat"):
            current_time += exact_durations[file_idx] if file_idx < len(exact_durations) else 0
            file_idx += 1
        elif segment_key in segments:
            file_label = chapter_data.get(f"{segment_key}_title", "")
            if file_label:
                chapter_markers.append({
                    "index": chapter_index,
                    "start_sec": current_time,
                    "label": file_label,
                })
                chapter_index += 1
            for _ in segments[segment_key]:
                current_time += exact_durations[file_idx] if file_idx < len(exact_durations) else 0
                file_idx += 1
    
    total_duration = sum(exact_durations)
    
    print(f"\nChapter markers: {len(chapter_markers)}")
    for m in chapter_markers:
        m_min = int(m["start_sec"] // 60)
        m_sec = int(m["start_sec"] % 60)
        print(f"  {m['index']:2d}. {m_min:02d}:{m_sec:02d} - {m['label']}")
    
    print(f"\nTotal duration: {int(total_duration//60)}:{int(total_duration%60):02d}")
    
    # Write concat file for audio
    file_list_path = str(OUTPUT_DIR / "file_list.txt")
    with open(file_list_path, "w") as f:
        for fp in file_list:
            f.write(f"file '{fp}'\n")
    
    # Concatenate audio
    audio_concat = str(OUTPUT_DIR / "full_audio.mp3")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", file_list_path, "-c", "copy", audio_concat,
    ], check=True, capture_output=True, timeout=120)
    print(f"  Audio concat: OK ({os.path.getsize(audio_concat)/1e6:.1f} MB)")
    
    # Build FFmpeg with image switching at exact timestamps
    # Determine which image to use for each segment
    thumbnail_path = str(ASSETS_DIR / "images" / "thumbnail.png")
    segment_images = {}
    for segment_key, _ in segment_order:
        for prefix in ["decision_1", "decision_2a", "decision_3a1", "decision_3a2", 
                       "decision_2b", "decision_3b1", "decision_3b2"]:
            if segment_key.startswith(prefix):
                overlay = str(ASSETS_DIR / "images" / f"{prefix}_overlay.jpg")
                if os.path.exists(overlay):
                    segment_images[segment_key] = overlay
                    break
    
    # Build video segment list with images and durations, consolidating consecutive same-image segments
    video_segments = []
    exact_pos = 0
    prev_img = None
    current_dur = 0.0
    
    for i, (segment_key, _) in enumerate(segment_order):
        dur = 0.0
        if segment_key.endswith("_pause"):
            dur = exact_durations[exact_pos] if exact_pos < len(exact_durations) else 0
            exact_pos += 1
        elif segment_key == "gap_2s":
            for _ in range(10):
                dur += exact_durations[exact_pos] if exact_pos < len(exact_durations) else 0
                exact_pos += 1
        elif segment_key.endswith("_repeat") or segment_key.endswith("_options") or segment_key.endswith("_options_repeat") or segment_key.endswith("_question_repeat"):
            dur = exact_durations[exact_pos] if exact_pos < len(exact_durations) else 0
            exact_pos += 1
        elif segment_key in segments:
            for _ in segments[segment_key]:
                dur += exact_durations[exact_pos] if exact_pos < len(exact_durations) else 0
                exact_pos += 1
        
        if dur <= 0:
            continue
        
        img = segment_images.get(segment_key, str(thumbnail_path) if os.path.exists(thumbnail_path) else "color=c=black:s=1920x1080")
        
        # Consolidate consecutive same-image segments
        if img == prev_img:
            video_segments[-1] = (img, video_segments[-1][1] + dur)
        else:
            video_segments.append((img, dur))
            prev_img = img
    
    # Get actual concat duration from output audio
    audio_dur_result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", audio_concat],
        capture_output=True, text=True,
    )
    total_audio_dur = float(audio_dur_result.stdout.strip()) if audio_dur_result.returncode == 0 else sum(exact_durations)
    print(f"  Total audio: {total_audio_dur:.0f}s = {total_audio_dur/60:.1f} min")
    
    # Recalculate chapter timestamps from actual concat duration
    # Scale exact_durations proportionally to match actual concat duration
    summed_durs = sum(exact_durations)
    scale = total_audio_dur / summed_durs if summed_durs > 0 else 1.0
    scaled_durations = [d * scale for d in exact_durations]
    
    chapter_markers = []
    chapter_index = 1
    current_time = 0.0
    file_idx = 0
    
    for segment_key, _ in segment_order:
        if segment_key.endswith("_pause"):
            current_time += scaled_durations[file_idx] if file_idx < len(scaled_durations) else 0
            file_idx += 1
        elif segment_key == "gap_2s":
            for _ in range(10):
                current_time += scaled_durations[file_idx] if file_idx < len(scaled_durations) else 0
                file_idx += 1
        elif segment_key.endswith("_repeat") or segment_key.endswith("_options") or segment_key.endswith("_options_repeat") or segment_key.endswith("_question_repeat"):
            current_time += scaled_durations[file_idx] if file_idx < len(scaled_durations) else 0
            file_idx += 1
        elif segment_key in segments:
            file_label = chapter_data.get(f"{segment_key}_title", "")
            if file_label:
                chapter_markers.append({
                    "index": chapter_index,
                    "start_sec": current_time,
                    "label": file_label,
                })
                chapter_index += 1
            for _ in segments[segment_key]:
                current_time += scaled_durations[file_idx] if file_idx < len(scaled_durations) else 0
                file_idx += 1
    
    total_duration = total_audio_dur
    
    print(f"\nChapter markers: {len(chapter_markers)}")
    for m in chapter_markers:
        m_min = int(m["start_sec"] // 60)
        m_sec = int(m["start_sec"] % 60)
        print(f"  {m['index']:2d}. {m_min:02d}:{m_sec:02d} - {m['label']}")
    
    print(f"\nTotal duration: {int(total_duration//60)}:{int(total_duration%60):02d}")
    
    # Create video from static thumbnail + audio
    output_video = str(OUTPUT_DIR / "die_letzte_schicht.mp4")
    thumbnail_path = str(ASSETS_DIR / "images" / "thumbnail.png")
    
    if os.path.exists(thumbnail_path):
        subprocess.run([
            "ffmpeg", "-y",
            "-loop", "1", "-t", str(total_audio_dur), "-i", thumbnail_path,
            "-i", audio_concat,
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-preset", "ultrafast", "-tune", "stillimage",
            "-c:a", "copy",
            "-shortest", output_video,
        ], check=True, capture_output=True, timeout=300)
        print(f"  Video created: {os.path.getsize(output_video)/1e6:.1f} MB")
    
    # Create chapter metadata file
    metadata_path = str(OUTPUT_DIR / "chapter_meta.txt")
    with open(metadata_path, "w") as f:
        f.write(";FFMETADATA1\n")
        for i, marker in enumerate(chapter_markers):
            start_ms = int(marker["start_sec"] * 1000)
            end_ms = int(chapter_markers[i+1]["start_sec"] * 1000) if i+1 < len(chapter_markers) else int(total_duration * 1000)
            f.write("[CHAPTER]\n")
            f.write("TIMEBASE=1/1000\n")
            f.write(f"START={start_ms}\n")
            f.write(f"END={end_ms}\n")
            f.write(f"title={marker['label']}\n")
    
    # Add chapters
    chaptered = str(OUTPUT_DIR / "chapters_output.mp4")
    subprocess.run([
        "ffmpeg", "-y",
        "-i", output_video,
        "-i", metadata_path,
        "-map", "0", "-map_metadata", "1",
        "-c", "copy", chaptered,
    ], check=True, capture_output=True, timeout=120)
    os.replace(chaptered, output_video)
    print(f"  Chapters added: OK")
    
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
