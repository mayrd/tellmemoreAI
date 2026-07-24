# 🎧 Die letzte Schicht – Interaktiver Audio Escape Room

Ein interaktives Krimi-Hörspiel für YouTube.

## Konzept

Der Zuhörer schlüpft in die Rolle von Kommissarin Lena Voss, die eine verlassene Psychiatrie in den Alpen untersucht. Etwa alle 10 Minuten wird eine Entscheidung mit zwei Optionen gestellt. Der Hörer hat 30 Sekunden Zeit, über die YouTube-Kapitelmarken zur gewählten Option zu springen.

- **Genre:** Psychologischer Krimi / Thriller
- **Sprache:** Deutsch
- **Länge:** ~60-80 Minuten (alle Pfade)
- **Enden:** 4 (1 gutes Ende, 3 schlechte/bittersüße)
- **Format:** YouTube-Video mit Standbild + Kapitelmarken

## Projektstruktur

```
escape-room/
├── story_script.py            # Komplettes Skript mit allen Kapiteln
├── scripts/
│   └── generate_escape_room.py # Pipeline: TTS → Video → Kapitel
├── assets/
│   ├── audio/                  # TTS-Audiodateien (generiert)
│   └── images/
│       └── thumbnail.png       # YouTube-Thumbnail / Standbild
├── output/
│   ├── die_letzte_schicht.mp4  # Finales Video
│   ├── youtube_description.txt # YouTube-Beschreibung mit Kapiteln
│   └── chapters.json          # Kapitel-Timestamps
└── README.md                   # Diese Datei
```

## Stimmen

| Rolle | Stimme | Typ |
|-------|--------|-----|
| Erzählerin (Lena Voss) | KatjaNeural | Weiblich, warm |
| Fragen/Entscheidungen | ConradNeural | Männlich, autoritativ |
| Antagonist (Dr. Wagner) | KillianNeural | Männlich, tief |

## Entscheidungsbaum

```
Intro → Entscheidung 1
  ├── A: Direktorenbüro
  │   ├── A1: Elias Born → Entscheidung 3A1
  │   │   ├── A1a: Verstärkung → ENDE 1 (Gerechtigkeit)
  │   │   └── A1b: Allein → ENDE 2 (Die Wahrheit) ⭐
  │   └── A2: Safe → Entscheidung 3A2
  │       ├── A2a: Staatsanwaltschaft → ENDE 2 (Die Wahrheit) ⭐
  │       └── A2b: Konfrontation → ENDE 3 (Verspielt) 💀
  └── B: Patientenzelle 7
      ├── B1: Geheimgang → Entscheidung 3B1
      │   ├── B1a: Verstecken → ENDE 4 (Der Jäger) 💀
      │   └── B1b: Stellen → ENDE 2 (Die Wahrheit) ⭐
      └── B2: Pförtner → Entscheidung 3B2
          ├── B2a: Offiziell → ENDE 2 (Die Wahrheit) ⭐
          └── B2b: Konfrontation → ENDE 1 (Gerechtigkeit)
```

## Regenerieren

```bash
cd scripts
python3 generate_escape_room.py
```

Erfordert: `edge-tts`, `ffmpeg`, Python 3.10+

## YouTube-Upload

Das generierte Video in `output/die_letzte_schicht.mp4` enthält bereits Kapitelmarken.
Die YouTube-Beschreibung in `output/youtube_description.txt` enthält die Kapitel mit Zeitcodes.

1. Video auf YouTube hochladen
2. Beschreibung aus `youtube_description.txt` kopieren
3. Thumbnail aus `assets/images/thumbnail.png` verwenden
4. Info Cards für die ersten Entscheidungskapitel einrichten
