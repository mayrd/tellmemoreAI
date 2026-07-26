#!/usr/bin/env python3
"""
AI Story Generator for Audio Escape Room Pipeline.
Generates a complete branching crime/thriller story with 4 endings
using the Gemini API, directly compatible with generate_escape_room.py.
"""

import json, urllib.request, base64, re, os, sys, time
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
LANGUAGES_DIR = PROJECT_DIR / "stories"

def load_gemini_key():
    with open('/opt/data/.env', 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('GEMINI_API_KEY=') and not line.startswith('#'):
                return line.split('=', 1)[1].strip().split()[0]
    return None

API_KEY = load_gemini_key()
if not API_KEY:
    print("ERROR: No GEMINI_API_KEY found")
    sys.exit(1)

MODEL = "gemini-3.1-flash-image-preview"

def call_gemini(prompt, max_retries=3):
    """Call Gemini API with a prompt and return text response."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.85,
            "maxOutputTokens": 8192,
        }
    }
    
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'),
                                         headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=300) as resp:
                result = json.load(resp)
            
            for candidate in result.get('candidates', []):
                for part in candidate.get('content', {}).get('parts', []):
                    if 'text' in part:
                        return part['text']
            print(f"  No text response (attempt {attempt+1})")
            time.sleep(3)
        except Exception as e:
            print(f"  API error (attempt {attempt+1}): {e}")
            time.sleep(5)
    return None

# ─────────────────────────────────────────────────────────────
# 1. STORY OUTLINE GENERATOR
# ─────────────────────────────────────────────────────────────

def generate_story_outline():
    """Generate full story outline with all branches."""
    prompt = """Generate a complete interactive crime/thriller audio drama story in German.
The story must follow this EXACT structure:

CHARACTERS:
- Kommissar/in (main character, detective)
- 1-2 supporting characters (suspect, witness, colleague)
- 1 antagonist

SETTING:
A German location (city, building, landscape) - atmospheric and slightly eerie.

STORY STRUCTURE:
1. INTRO (~4-5 min narrated): Hook, setting, first clues
2. DECISION 1: Two options (Path A / Path B)
3. PATH A (~4 min): Narrative following choice A
4. DECISION 2A: Two options (A1 / A2)  
5. OPTION A1 (~3 min): Leads to ENDING 1 or 2
6. DECISION 3A1: Two paths
7. OPTION A2 (~3 min): Leads to ENDING 2 or 3
8. DECISION 3A2: Two paths
9. PATH B (~4 min): Narrative following choice B
10. DECISION 2B: Two options (B1 / B2)
11. OPTION B1 (~3 min): Leads to ENDING 2 or 4
12. DECISION 3B1: Two paths
13. OPTION B2 (~3 min): Leads to ENDING 1 or 2
14. DECISION 3B2: Two paths

4 ENDINGS:
- ENDING 1 (bittersweet/cautionary): "Gerechtigkeit" - justice served but not perfect
- ENDING 2 (good): "Die Wahrheit" - hero succeeds, case solved ⭐
- ENDING 3 (bad): "Verspielt" - hero makes fatal mistake
- ENDING 4 (bad): "Der Jäger" - hero becomes victim

Now generate the story. Output as JSON with EXACTLY this structure:

{
  "title": "Geschichtentitel",
  "setting": "Setting description",
  "intro": "Full intro narrative text (ca. 500 words, suspenseful, immersive, in German. Write as a thrilling audio drama monologue.)",
  "decision_1_question": "Du musst jetzt entscheiden. [The question]",
  "decision_1_options": "[Option label]: [Full option description including chapter reference] OR [Option label]: [Full option description including chapter reference]",
  "decision_1_repeat": "Noch einmal: [brief question repeat with option labels and chapter references]",
  
  "path_a": "Full narrative for Path A (ca. 400 words, immersive)",
  "decision_2a_question": "Du musst jetzt entscheiden. [The question]",
  "decision_2a_options": "[Option]: [description] OR [Option]: [description]",
  "decision_2a_repeat": "Noch einmal: [brief repeat]",
  
  "path_a1": "Full narrative for Path A1 (ca. 300 words)",
  "decision_3a1_question": "...",
  "decision_3a1_options": "...",
  "decision_3a1_repeat": "...",
  
  "path_a2": "Full narrative for Path A2 (ca. 300 words)",
  "decision_3a2_question": "...",
  "decision_3a2_options": "...",
  "decision_3a2_repeat": "...",
  
  "path_b": "Full narrative for Path B (ca. 400 words)",
  "decision_2b_question": "...",
  "decision_2b_options": "...",
  "decision_2b_repeat": "...",
  
  "path_b1": "Full narrative for Path B1 (ca. 300 words)",
  "decision_3b1_question": "...",
  "decision_3b1_options": "...",
  "decision_3b1_repeat": "...",
  
  "path_b2": "Full narrative for Path B2 (ca. 300 words)",
  "decision_3b2_question": "...",
  "decision_3b2_options": "...",
  "decision_3b2_repeat": "...",
  
  "ending_1": "Full ending 1 text (ca. 200 words, emotional closure)",
  "ending_2": "Full ending 2 text (ca. 200 words, triumphant closure)",
  "ending_3": "Full ending 3 text (ca. 200 words, dark closure)",
  "ending_4": "Full ending 4 text (ca. 200 words, terrifying closure)",
  "outro": "Outro text thanking listener, mentioning 4 endings"
}

IMPORTANT: Write ALL narrative text as spoken German audio drama style - descriptive, atmospheric, with suspense. Each "path" segment must be a complete narrative scene with dialogue. Do NOT use placeholders or "..." - write the FULL text. Each decision question starts with "Du musst jetzt entscheiden." and includes option labels like A, A1, A2, B, B1, B2.

Output ONLY valid JSON. No markdown. No comments."""
    
    print(f"  Generating story with Gemini...")
    result = call_gemini(prompt)
    if not result:
        print("  ERROR: Failed to generate story")
        return None
    
    # Extract JSON from response
    json_match = re.search(r'\{.*\}', result, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError as e:
            print(f"  JSON parse error: {e}")
            print(f"  Raw output (first 500): {result[:500]}")
            return None
    else:
        print(f"  No JSON found in response")
        print(f"  Raw output (first 500): {result[:500]}")
        return None

# ─────────────────────────────────────────────────────────────
# 2. GENERATE STORY SCRIPT FILE
# ─────────────────────────────────────────────────────────────

def generate_story_script(story_data, lang="de", name="ai-generated"):
    """Convert story JSON into a Python story script file."""
    if not story_data:
        return None
    
    out_dir = LANGUAGES_DIR / lang
    out_dir.mkdir(parents=True, exist_ok=True)
    
    title = story_data.get("title", "Unbekannter Fall")
    safe_title = re.sub(r'[^a-zA-Z0-9_-]', '', title.lower().replace(' ', '-'))
    filename = f"{safe_title}.py"
    
    content = f'''"""
{title} — AI-Generated Interactive Audio Escape Room Story
Language: {lang}
Generated: {time.strftime('%Y-%m-%d %H:%M')}
"""

STORY = {json.dumps(story_data, ensure_ascii=False, indent=2)}

VOICES = {{
    "narrator": "de-DE-KatjaNeural",
    "decision": "de-DE-ConradNeural",
    "antagonist": "de-DE-KillianNeural",
    "decision_rate": "-15%",
}}

CHAPTERS = {{
    "intro_title": "Intro – {story_data.get("setting", "Start")}",
    "intro": STORY["intro"],
    "path_a_title": "A: {story_data.get("path_a", "")[:50]}",
    "path_a": STORY["path_a"],
    "path_a1_title": "A1: {story_data.get("path_a1", "")[:50]}",
    "path_a1": STORY["path_a1"],
    "path_a2_title": "A2: {story_data.get("path_a2", "")[:50]}",
    "path_a2": STORY["path_a2"],
    "path_b_title": "B: {story_data.get("path_b", "")[:50]}",
    "path_b": STORY["path_b"],
    "path_b1_title": "B1: {story_data.get("path_b1", "")[:50]}",
    "path_b1": STORY["path_b1"],
    "path_b2_title": "B2: {story_data.get("path_b2", "")[:50]}",
    "path_b2": STORY["path_b2"],
    "ending_1_title": "Ende 1: Gerechtigkeit",
    "ending_1": STORY["ending_1"],
    "ending_2_title": "Ende 2: Die Wahrheit",
    "ending_2": STORY["ending_2"],
    "ending_3_title": "Ende 3: Verspielt",
    "ending_3": STORY["ending_3"],
    "ending_4_title": "Ende 4: Der Jäger",
    "ending_4": STORY["ending_4"],
    "outro_title": "Abspann",
    "outro": STORY["outro"],
}}

# Decision texts
DECISIONS = {{
    "decision_1_question": STORY.get("decision_1_question", "Du musst jetzt entscheiden."),
    "decision_1_options": STORY.get("decision_1_options", ""),
    "decision_1_question_repeat": "Noch einmal: " + STORY.get("decision_1_options", ""),
    "decision_1_options_repeat": "Springe zu Kapitel A für Option 1 oder Kapitel B für Option 2.",
    
    "decision_2a_question": STORY.get("decision_2a_question", "Du musst jetzt entscheiden."),
    "decision_2a_options": STORY.get("decision_2a_options", ""),
    "decision_2a_question_repeat": "Noch einmal: " + STORY.get("decision_2a_options", ""),
    "decision_2a_options_repeat": "Springe zu Kapitel A1 oder A2.",
    
    "decision_3a1_question": STORY.get("decision_3a1_question", "Du musst jetzt entscheiden."),
    "decision_3a1_options": STORY.get("decision_3a1_options", ""),
    "decision_3a1_question_repeat": "Noch einmal: " + STORY.get("decision_3a1_options", ""),
    "decision_3a1_options_repeat": "Springe zum entsprechenden Kapitel.",
    
    "decision_3a2_question": STORY.get("decision_3a2_question", "Du musst jetzt entscheiden."),
    "decision_3a2_options": STORY.get("decision_3a2_options", ""),
    "decision_3a2_question_repeat": "Noch einmal: " + STORY.get("decision_3a2_options", ""),
    "decision_3a2_options_repeat": "Springe zum entsprechenden Kapitel.",
    
    "decision_2b_question": STORY.get("decision_2b_question", "Du musst jetzt entscheiden."),
    "decision_2b_options": STORY.get("decision_2b_options", ""),
    "decision_2b_question_repeat": "Noch einmal: " + STORY.get("decision_2b_options", ""),
    "decision_2b_options_repeat": "Springe zu Kapitel B1 oder B2.",
    
    "decision_3b1_question": STORY.get("decision_3b1_question", "Du musst jetzt entscheiden."),
    "decision_3b1_options": STORY.get("decision_3b1_options", ""),
    "decision_3b1_question_repeat": "Noch einmal: " + STORY.get("decision_3b1_options", ""),
    "decision_3b1_options_repeat": "Springe zum entsprechenden Kapitel.",
    
    "decision_3b2_question": STORY.get("decision_3b2_question", "Du musst jetzt entscheiden."),
    "decision_3b2_options": STORY.get("decision_3b2_options", ""),
    "decision_3b2_question_repeat": "Noch einmal: " + STORY.get("decision_3b2_options", ""),
    "decision_3b2_options_repeat": "Springe zum entsprechenden Kapitel.",
}}

SEGMENTS = [
    ("intro", "Intro – {story_data.get("setting", "Start")}"),
    ("gap_2s", None),
    ("decision_1_question", None), ("decision_1_options", None),
    ("decision_1_pause", None),
    ("decision_1_question_repeat", None), ("decision_1_options_repeat", None),
    ("gap_2s", None),
    ("path_a", "A: Erste Wahl"),
    ("gap_2s", None),
    ("decision_2a_question", None), ("decision_2a_options", None),
    ("decision_2a_pause", None),
    ("decision_2a_question_repeat", None), ("decision_2a_options_repeat", None),
    ("gap_2s", None),
    ("path_a1", "A1: Zweite Wahl"),
    ("gap_2s", None),
    ("decision_3a1_question", None), ("decision_3a1_options", None),
    ("decision_3a1_pause", None),
    ("decision_3a1_question_repeat", None), ("decision_3a1_options_repeat", None),
    ("gap_2s", None),
    ("ending_1", "Ende 1: Gerechtigkeit"),
    ("ending_2", "Ende 2: Die Wahrheit"),
    ("gap_2s", None),
    ("path_a2", "A2: Alternative"),
    ("gap_2s", None),
    ("decision_3a2_question", None), ("decision_3a2_options", None),
    ("decision_3a2_pause", None),
    ("decision_3a2_question_repeat", None), ("decision_3a2_options_repeat", None),
    ("gap_2s", None),
    ("ending_3", "Ende 3: Verspielt"),
    ("gap_2s", None),
    ("path_b", "B: Erste Wahl"),
    ("gap_2s", None),
    ("decision_2b_question", None), ("decision_2b_options", None),
    ("decision_2b_pause", None),
    ("decision_2b_question_repeat", None), ("decision_2b_options_repeat", None),
    ("gap_2s", None),
    ("path_b1", "B1: Zweite Wahl"),
    ("gap_2s", None),
    ("decision_3b1_question", None), ("decision_3b1_options", None),
    ("decision_3b1_pause", None),
    ("decision_3b1_question_repeat", None), ("decision_3b1_options_repeat", None),
    ("gap_2s", None),
    ("ending_4", "Ende 4: Der Jäger"),
    ("gap_2s", None),
    ("path_b2", "B2: Alternative"),
    ("gap_2s", None),
    ("decision_3b2_question", None), ("decision_3b2_options", None),
    ("decision_3b2_pause", None),
    ("decision_3b2_question_repeat", None), ("decision_3b2_options_repeat", None),
    ("gap_2s", None),
    ("outro", "Abspann"),
]
'''
    
    path = out_dir / filename
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"  ✅ Story saved: {path}")
    return filename

# ─────────────────────────────────────────────────────────────
# 3. MAIN
# ─────────────────────────────────────────────────────────────

def generate(lang="de", name=None):
    """Generate a complete story and save it."""
    print(f"\n🎭 Generating AI story (lang={lang})...")
    story_data = generate_story_outline()
    if not story_data:
        print("  ❌ Failed to generate story")
        return None
    
    filename = generate_story_script(story_data, lang, name)
    if filename:
        print(f"\n✅ Story '{story_data.get('title', 'Unknown')}' generated!")
        print(f"   Run with: python3 scripts/generate_escape_room.py --story {lang}/{filename.replace('.py','')}")
        return filename
    return None

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate AI story for audio escape room")
    parser.add_argument("--language", "-l", default="de", help="Language code")
    parser.add_argument("--name", "-n", default=None, help="Custom story name (optional)")
    args = parser.parse_args()
    
    generate(args.language, args.name)
