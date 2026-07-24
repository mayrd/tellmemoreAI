#!/usr/bin/env python3
"""Generate decision overlay images with question + options."""
from PIL import Image, ImageDraw, ImageFont
import os, sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THUMB_PATH = os.path.join(PROJECT_DIR, "assets", "images", "thumbnail.png")
OUT_DIR = os.path.join(PROJECT_DIR, "assets", "images")

sys.path.insert(0, PROJECT_DIR)
from story_script import CHAPTERS

def create_overlay(question, options_a, options_b, letter_a, letter_b, output_path):
    """Create overlay image with question and two answer options on top of thumbnail."""
    thumb = Image.open(THUMB_PATH).convert("RGBA")
    thumb = thumb.resize((1920, 1080), Image.LANCZOS)
    
    # Semi-transparent dark overlay
    overlay = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Darken the background
    for y in range(1080):
        for x in range(1920):
            r, g, b, a = thumb.getpixel((x, y))
            thumb.putpixel((x, y), (r//3, g//3, b//3, 255))
    
    # Try to use a bold font, fall back to default
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Question at top
    if hasattr(draw, "textbbox"):
        bbox = draw.textbbox((0, 0), question, font=font_large)
        tw = bbox[2] - bbox[0]
    else:
        tw, _ = draw.textsize(question, font=font_large)
    draw.text(((1920 - tw) // 2, 80), question, fill=(255, 215, 0), font=font_large)
    
    # Option A box
    box_a = [(1920//2 - 440, 300), (1920//2 - 20, 520)]
    draw.rounded_rectangle(box_a, radius=16, fill=(50, 50, 70, 230), outline=(212, 175, 55), width=3)
    if hasattr(draw, "textbbox"):
        bbox = draw.textbbox((0, 0), f"{letter_a}. {options_a}", font=font_medium)
        tw = bbox[2] - bbox[0]
    else:
        tw, _ = draw.textsize(f"{letter_a}. {options_a}", font=font_medium)
    draw.text((box_a[0][0] + 20, box_a[0][1] + 15), f"{letter_a}", fill=(255, 215, 0), font=font_large)
    draw.text((box_a[0][0] + 60, box_a[0][1] + 25), options_a, fill=(255, 255, 255), font=font_medium)
    
    # Option B box
    box_b = [(1920//2 + 20, 300), (1920//2 + 440, 520)]
    draw.rounded_rectangle(box_b, radius=16, fill=(70, 50, 50, 230), outline=(180, 120, 120), width=3)
    draw.text((box_b[0][0] + 20, box_b[0][1] + 15), f"{letter_b}", fill=(255, 215, 0), font=font_large)
    draw.text((box_b[0][0] + 60, box_b[0][1] + 25), options_b, fill=(255, 255, 255), font=font_medium)
    
    # Hint at bottom
    hint = "📖 Wähle in der Videobeschreibung dein Kapitel"
    if hasattr(draw, "textbbox"):
        bbox = draw.textbbox((0, 0), hint, font=font_small)
        tw = bbox[2] - bbox[0]
    else:
        tw, _ = draw.textsize(hint, font=font_small)
    draw.text(((1920 - tw) // 2, 950), hint, fill=(180, 180, 180), font=font_small)
    
    # Composite
    result = Image.alpha_composite(thumb, overlay)
    result = result.convert("RGB")
    result.save(output_path, "JPEG", quality=92)
    print(f"  Saved: {output_path}")

# Define decision overlays
DECISIONS = [
    {
        "key": "decision_1",
        "question": "Wohin gehst du zuerst?",
        "options_a": "Das Büro des Direktors",
        "options_b": "Patientenzelle 7",
        "letter_a": "A", "letter_b": "B",
    },
    {
        "key": "decision_2a",
        "question": "Welche Spur verfolgst du?",
        "options_a": "Der Adresse von Elias Born folgen",
        "options_b": "Den Safe öffnen",
        "letter_a": "A1", "letter_b": "A2",
    },
    {
        "key": "decision_3a1",
        "question": "Was tust du?",
        "options_a": "Verstärkung rufen",
        "options_b": "Dich allein stellen",
        "letter_a": "A1a", "letter_b": "A1b",
    },
    {
        "key": "decision_3a2",
        "question": "Wie reagierst du?",
        "options_a": "Staatsanwaltschaft informieren",
        "options_b": "Dr. Wagner persönlich stellen",
        "letter_a": "A2a", "letter_b": "A2b",
    },
    {
        "key": "decision_2b",
        "question": "Was tust du?",
        "options_a": "Den Geheimgang suchen",
        "options_b": "Den Pförtner befragen",
        "letter_a": "B1", "letter_b": "B2",
    },
    {
        "key": "decision_3b1",
        "question": "Was tust du?",
        "options_a": "Verstecken und beobachten",
        "options_b": "Mit gezogener Waffe stellen",
        "letter_a": "B1a", "letter_b": "B1b",
    },
    {
        "key": "decision_3b2",
        "question": "Wie gehst du vor?",
        "options_a": "Beweise sichern lassen",
        "options_b": "Dr. Wagner sofort konfrontieren",
        "letter_a": "B2a", "letter_b": "B2b",
    },
]

if __name__ == "__main__":
    print("Generating decision overlay images...")
    for dec in DECISIONS:
        path = os.path.join(OUT_DIR, f"{dec['key']}_overlay.jpg")
        create_overlay(
            dec["question"], dec["options_a"], dec["options_b"],
            dec["letter_a"], dec["letter_b"], path,
        )
    print("\nDone!")
