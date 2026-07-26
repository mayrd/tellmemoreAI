#!/usr/bin/env python3
"""
Generate interactive escape room video with multi-repeat decisions, SRT subtitles,
spoil-free chapters, and configurable voice speed.
"""

import asyncio, json, os, sys, subprocess, argparse, re
from pathlib import Path
import edge_tts

parser = argparse.ArgumentParser()
parser.add_argument("--language", "-l", default="de", choices=["de"])
args = parser.parse_args()
LANG = args.language

PROJECT = Path(__file__).parent.parent
AUDIO_DIR = PROJECT / "assets" / "audio" / LANG
OUTPUT = PROJECT / "output"
IMAGES = PROJECT / "assets" / "images"

# Voice config
VOICES = {
    "de": {"narrator": "de-DE-KatjaNeural", "decision": "de-DE-ConradNeural",
           "antagonist": "de-DE-KillianNeural", "decision_rate": "-30%"},
}

def get_voice(key):
    cfg = VOICES[LANG]
    if key.startswith("decision") or key.startswith("repeat"):
        return cfg["decision"], cfg["decision_rate"]
    if key in ("ending_3", "ending_4", "chapter_a2"):
        return cfg["antagonist"], "+0%"
    return cfg["narrator"], "+0%"

# ── HELPERS ──

async def tts(text, voice, rate, path):
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(path)
    r = subprocess.run(["ffprobe","-v","quiet","-show_entries","format=duration","-of","csv=p=0",path],
                       capture_output=True, text=True)
    return float(r.stdout.strip())

def silence(dur, path):
    import struct, wave
    with wave.open(path, 'w') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(44100)
        f.writeframes(struct.pack(f'<{int(44100*dur)}h', *[0]*int(44100*dur)))

def ffprobe_dur(path):
    r = subprocess.run(["ffprobe","-v","quiet","-show_entries","format=duration","-of","csv=p=0",str(path)],
                       capture_output=True, text=True)
    return float(r.stdout.strip()) if r.returncode == 0 else 0.0

# ── BUILD SEGMENT LIST ──
# Segments are built programmatically: narrative + decision blocks + endings + outro

def build_full_segments():
    import importlib.util
    sys.path.insert(0, str(PROJECT))
    spec = importlib.util.spec_from_file_location("story_data", str(PROJECT / "story_data.py"))
    sd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sd)
    STORY = sd.STORY
    DECISIONS = sd.DECISIONS
    CHAPTER_TITLES = sd.CHAPTER_TITLES
    
    segs = []  # (segment_key, chapter_label, text_or_special)
    all_texts = {}
    
    # Intro
    segs.append(("intro", CHAPTER_TITLES.get("intro",""), STORY["intro"]))
    
    # Build decision blocks + narrative chapters + endings dynamically
    # Structure:
    #   NARRATIVE → gap_5s → DECISION BLOCK (3 repeats) → gap_5s → NARRATIVE → ...
    
    decision_flow = [
        ("decision_1", "chapter_a", "chapter_b"),
        ("decision_2a", "chapter_a1", "chapter_a2"),
        ("decision_3a1", None, None),  # no more narrative after this, just endings
        ("decision_3a2", None, None),
        ("decision_2b", "chapter_b1", "chapter_b2"),
        ("decision_3b1", None, None),
        ("decision_3b2", None, None),
    ]
    
    endings = ["ending_1", "ending_2", "ending_3", "ending_4"]
    
    for dec_key, path_a, path_b in decision_flow:
        # Gap before decision
        segs.append(("gap_5s", None, ""))
        
        # Decision block with 3 repetitions
        d = DECISIONS.get(dec_key)
        if d:
            segs.append((f"{dec_key}_intro", None, "Jetzt musst du entscheiden wie es weitergeht."))
            segs.append((f"{dec_key}_q", None, d["question"]))
            for letter, option_text in d["options"]:
                segs.append((f"{dec_key}_opt_{letter}", None, f"{letter}: {option_text}"))
            
            # Pause 1: 10 seconds
            segs.append((f"{dec_key}_pause1", None, None))  # silence
            
            # Repeat 1
            segs.append((f"{dec_key}_r1_intro", None, "Jetzt musst du entscheiden wie es weitergeht."))
            segs.append((f"{dec_key}_r1_q", None, d["question"]))
            for letter, option_text in d["options"]:
                segs.append((f"{dec_key}_r1_opt_{letter}", None, f"{letter}: {option_text}"))
            
            # Pause 2: 30 seconds
            segs.append((f"{dec_key}_pause2", None, None))
            
            # Repeat 2
            segs.append((f"{dec_key}_r2_intro", None, "Jetzt musst du entscheiden wie es weitergeht."))
            segs.append((f"{dec_key}_r2_q", None, d["question"]))
            for letter, option_text in d["options"]:
                segs.append((f"{dec_key}_r2_opt_{letter}", None, f"{letter}: {option_text}"))
            
            # Pause 3: 15 seconds
            segs.append((f"{dec_key}_pause3", None, None))
        
        # Gap after decision
        segs.append(("gap_5s", None, ""))
        
        # Narrative chapters
        if path_a and path_a in STORY:
            segs.append((path_a, CHAPTER_TITLES.get(path_a, path_a), STORY[path_a]))
        if path_b and path_b in STORY:
            segs.append((path_b, CHAPTER_TITLES.get(path_b, path_b), STORY[path_b]))
    
    # Endings
    for ek in endings:
        if ek in STORY:
            segs.append((ek, CHAPTER_TITLES.get(ek, ek), STORY[ek]))
    
    # Outro
    segs.append(("outro", CHAPTER_TITLES.get("outro","Abspann"), STORY.get("outro","")))
    
    return segs, DECISIONS

# ── GENERATE ALL AUDIO ──

async def gen_all():
    segs, decisions = build_full_segments()
    assert segs, "No segments!"
    
    # Collect unique texts to generate
    text_segments = {}
    for key, label, text in segs:
        if text is not None and text:
            text_segments[key] = text
    
    generated = {}
    total_chars = 0
    for key, text in text_segments.items():
        path = AUDIO_DIR / f"{key}.mp3"
        voice, rate = get_voice(key)
        dur = await tts(text, voice, rate, str(path))
        generated[key] = [(str(path), dur)]
        total_chars += len(text)
        print(f"  [{key}] {dur:.1f}s ({voice}, {rate})")
    
    print(f"\n  Total chars: {total_chars}")
    return generated, segs, decisions

# ── BUILD SRT SUBTITLES ──

def build_subtitles(segs, decisions, audio_durations, file_list):
    """Create .srt entries for decision blocks showing question + options."""
    srt_entries = []
    idx = 1
    current_time = 0.0
    dur_pos = 0
    
    for key, label, text in segs:
        dur = audio_durations[dur_pos] if dur_pos < len(audio_durations) else 0
        dur_pos += 1
        
        # Check if this segment belongs to a decision block
        dec_key = None
        for dk in decisions:
            if key.startswith(dk):
                dec_key = dk
                break
        
        if dec_key and ("_q" in key or "_pause" in key or "_opt_" in key):
            d = decisions[dec_key]
            lines = []
            
            if "_q" in key:
                lines.append(f"❓ {d['question']}")
                for letter, opt_text in d["options"]:
                    lines.append(f"   {letter}: {opt_text}")
            elif "_opt_" in key:
                for letter, opt_text in d["options"]:
                    lines.append(f"{letter}: {opt_text}")
            elif "_pause" in key:
                lines.append(f"❓ {d['question']}")
                for letter, opt_text in d["options"]:
                    lines.append(f"   {letter}: {opt_text}")
            
            if lines:
                start = current_time
                end = current_time + dur
                srt_entries.append((start, end, "\n".join(lines), idx))
                idx += 1
        
        current_time += dur
    
    # Write SRT
    srt_path = OUTPUT / "subtitles.srt"
    with open(srt_path, "w", encoding="utf-8") as f:
        for start, end, text, idx in srt_entries:
            f.write(f"{idx}\n")
            f.write(f"{fmt_srt(start)} --> {fmt_srt(end)}\n")
            f.write(f"{text}\n\n")
    
    print(f"  SRT: {len(srt_entries)} subtitle entries")
    return str(srt_path)

def fmt_srt(sec):
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int((sec - int(sec)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

# ── ASSEMBLE VIDEO ──

async def main():
    print("=" * 60)
    print("  Die letzte Schicht - Escape Room Generator v3")
    print("=" * 60)
    
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    
    print("\n Generating audio...")
    generated, segs, decisions = await gen_all()
    
    print("\n Building file list...")
    
    # Build file list and get exact durations
    file_list = []
    for key, label, text in segs:
        if key.startswith("gap_5s"):
            gap = AUDIO_DIR / "gap_5s.wav"
            if not gap.exists():
                silence(5.0, str(gap))
            file_list.append(str(gap))
        elif key.endswith("_pause1"):
            p = AUDIO_DIR / f"{key}.wav"
            if not Path(p).exists():
                silence(10.0, p)
            file_list.append(p)
        elif key.endswith("_pause2"):
            p = AUDIO_DIR / f"{key}.wav"
            if not Path(p).exists():
                silence(30.0, p)
            file_list.append(p)
        elif key.endswith("_pause3"):
            p = AUDIO_DIR / f"{key}.wav"
            if not Path(p).exists():
                silence(15.0, p)
            file_list.append(p)
        elif key in generated:
            for path, _ in generated[key]:
                file_list.append(path)
        elif text is not None and text:
            # Generate TTS for any missing segments
            path = str(AUDIO_DIR / f"{key}.mp3")
            voice, rate = get_voice(key)
            dur = await tts(text, voice, rate, path)
            generated[key] = [(path, dur)]
            file_list.append(path)
    
    # Get exact durations
    exact_durs = [ffprobe_dur(f) for f in file_list]
    total_dur = sum(exact_durs)
    print(f"  Total: {total_dur:.0f}s = {total_dur/60:.1f} min")
    
    # Calculate chapter timestamps
    chapters = []
    current_time = 0.0
    for i, (key, label, text) in enumerate(segs):
        dur = exact_durs[i]
        if label:
            chapters.append((current_time, label))
        current_time += dur
    
    print(f"\n Chapters ({len(chapters)}):")
    for ts, lb in chapters:
        m, s = int(ts//60), int(ts%60)
        print(f"  {m:02d}:{s:02d} - {lb}")
    
    # Write concat file
    flist = OUTPUT / "file_list.txt"
    with open(flist, "w") as f:
        for fp in file_list:
            f.write(f"file '{fp}'\n")
    
    # Concat audio
    audio_out = str(OUTPUT / "full_audio.mp3")
    subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(flist),"-c","copy",audio_out],
                   check=True, capture_output=True, timeout=120)
    print(f"\n Audio concat: {os.path.getsize(audio_out)/1e6:.1f} MB")
    
    # Build SRT subtitles for decision blocks
    srt_path = build_subtitles(segs, decisions, exact_durs, file_list)
    
    # Create chapter metadata
    meta = OUTPUT / "chapter_meta.txt"
    with open(meta, "w") as f:
        f.write(";FFMETADATA1\n")
        for i, (ts, lb) in enumerate(chapters):
            end = chapters[i+1][0] if i+1 < len(chapters) else total_dur
            f.write(f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={int(ts*1000)}\nEND={int(end*1000)}\ntitle={lb}\n")
    
    # Create video with static image + SRT subtitles
    thumb = IMAGES / "thumbnail.png"
    video = str(OUTPUT / "die_letzte_schicht.mp4")
    
    if thumb.exists():
        subprocess.run([
            "ffmpeg", "-y",
            "-loop","1","-t",str(total_dur),"-i",str(thumb),
            "-i", audio_out,
            "-vf", f"subtitles={srt_path}:force_style='FontName=DejaVuSans-Bold,FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,MarginV=80'",
            "-c:v","libx264","-pix_fmt","yuv420p","-preset","ultrafast","-tune","stillimage",
            "-c:a","copy",
            "-shortest", video,
        ], check=True, capture_output=True, timeout=600)
        print(f" Video: {os.path.getsize(video)/1e6:.1f} MB")
    
    # Add chapters
    ch = OUTPUT / "ch_ready.mp4"
    subprocess.run(["ffmpeg","-y","-i",video,"-i",str(meta),"-map","0","-map_metadata","1","-c","copy",str(ch)],
                   check=True, capture_output=True, timeout=120)
    ch.replace(video)
    print(" Chapters added.")
    
    # Generate description
    desc = f"""# Die letzte Schicht - Interaktiver Audio Escape Room

**Ein Krimi-Horspiel von Tell Me More AI**

Du bist Kommissarin Lena Voss. Eine verlassene Psychiatrie in den Alpen. Ein verschwundener Direktor.

## Kapitel (zum Springen klicken)

"""
    for ts, lb in chapters:
        m, s = int(ts//60), int(ts%60)
        desc += f"{m:02d}:{s:02d} - {lb}\n"
    
    desc += """

## So funktioniert's
1. Hore das Intro und die erste Entscheidung
2. Wahle zwischen den Optionen
3. Springe zum entsprechenden Kapitel
4. Die Geschichte geht weiter

## Die 4 Enden
| Ende | Beschreibung |
|------|-------------|
| Ende 1 | Bittersuss |
| Ende 2 | Das beste Ende |
| Ende 3 | Schlecht |
| Ende 4 | Schlecht |

#Krimi #Horspiel #EscapeRoom #Interaktiv #TellMeMoreAI
"""
    (OUTPUT / "youtube_description.txt").write_text(desc, encoding="utf-8")
    
    print(f"\n Done! Video: {video}")
    print(f" Chapters: {len(chapters)}")
    print(f" Duration: {total_dur/60:.1f} min")

if __name__ == "__main__":
    asyncio.run(main())
