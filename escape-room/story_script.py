#!/usr/bin/env python3
"""
Die letzte Schicht — Interaktiver Audio-Escape-Room
===================================================
Ein Krimi-Hörspiel für YouTube mit Entscheidungsknoten.

Stimmen:
  - Erzählerin: de-DE-KatjaNeural (weiblich, warm)
  - Entscheidungen: de-DE-ConradNeural (männlich, -15% langsamer)
  - Antagonist: de-DE-KillianNeural (männlich, tief)

YouTube: @TellMeMoreAI
"""

# ─────────────────────────────────────────────────────────────
# 1. STORY-SKRIPT — Alle Kapitel mit Dialog
# ─────────────────────────────────────────────────────────────

CHAPTERS = {
    # ── INTRO ──
    "intro_title": "Intro – Ankunft in der Klinik",
    "intro": """Es ist ein kalter Herbstabend, als Kommissarin Lena Voss ihren Dienstwagen am Fuß der Alpen parkt. Vor ihr liegt die ehemalige geschlossene Psychiatrie "Waldesruh" – ein düsteres Gebäude aus grauem Stein, das sich bedrohlich gegen den Nebel abzeichnet.

Der Anruf kam vor zwei Stunden. Dr. Johannes Richter, der ehemalige ärztliche Direktor, ist spurlos verschwunden. Seit drei Tagen. Die Kollegen vor Ort haben nichts gefunden – keine Spur, kein Motiv, keine Leiche.

Lena schaltet ihre Taschenlampe ein und geht den Kiesweg entlang. Die Stille ist bedrückend. Nur ihr eigener Atem und das Knirschen der Steine unter ihren Füßen sind zu hören.

Das Hauptgebäude ist verrammelt. Doch die Hintertür steht offen. Sie betritt die Klinik. Der Geruch von Alter und Verfall liegt in der Luft. Ihre Schritte hallen durch den leeren Flur.

Links ist das Büro des Direktors. Rechts führt ein Gang zu den Patientenzellen. Sie muss eine Entscheidung treffen.""",

    # ── ENTSCHEIDUNG 1 ──
    "decision_1_title": "Entscheidung 1 – Wohin zuerst?",
    "decision_1_question": "Du musst jetzt entscheiden.",
    "decision_1_options": "Wohin gehst du zuerst? A: Ich untersuche das Büro des Direktors. B: Ich gehe zu Patientenzelle 7.",
    "decision_1_question_repeat": "Noch einmal die Frage: Wohin gehst du zuerst?",
    "decision_1_options_repeat": "A: Das Büro des Direktors, springe zu Kapitel A. B: Patientenzelle 7, springe zu Kapitel B.",
    "decision_1_pause_s": 30,

    # ── PFAD A: DIREKTORSBÜRO ──
    "chapter_a_title": "A: Das Büro des Direktors",
    "chapter_a": """Lena öffnet die schwere Eichentür zum Direktorenbüro. Das Zimmer ist überraschend ordentlich. Ein massiver Schreibtisch aus dunklem Holz, lederne Sessel, ein alter Safe in der Ecke.

Sie setzt sich an den Schreibtisch und blättert durch die Papiere. Rechnungen, Korrespondenz, Forschungsnotizen. Bis sie auf das Tagebuch stößt.

Es ist in Leder gebunden, abgegriffen. Die letzte Seite ist frisch beschrieben: "Es tut mir leid. Ich hätte es ihnen sagen sollen. Aber sie werden mich nicht verstehen. Die Stimmen in den Wänden... sie sind real."

Lena blättert zurück. Das Tagebuch berichtet von einem Patienten – Elias Born – der vor zwanzig Jahren in dieser Klinik verschwand. Dr. Richter habe versucht, ihm zu helfen. Aber etwas sei schiefgelaufen.

Ein Zettel fällt aus dem Tagebuch. Darauf steht eine Adresse in der Stadt. Und die Worte: "Der Schlüssel liegt in der Vergangenheit."

Dann bemerkt Lena den Safe. Ein massives Stahlschloss. Verschlossen. Auf dem Schreibtisch liegt ein Brieföffner mit einer Gravur: "Patient 0".

Ihre Gedanken überschlagen sich. Der Safe. Die Adresse. Der verschwundene Patient.""",

    # ── ENTSCHEIDUNG 2A ──
    "decision_2a_title": "Entscheidung 2A – A1 oder A2?",
    "decision_2a_question": "Du musst jetzt entscheiden.",
    "decision_2a_options": "Welche Spur verfolgst du zuerst? A1: Ich folge der Adresse von Elias Born. A2: Ich versuche, den Safe zu öffnen.",
    "decision_2a_question_repeat": "Noch einmal: Welche Spur verfolgst du zuerst?",
    "decision_2a_options_repeat": "A1: Der Adresse von Elias Born folgen. A2: Den Safe öffnen.",
    "decision_2a_pause_s": 30,

    # ── PFAD A1: ELIAS BORN ──
    "chapter_a1_title": "A1: Die Spur des Elias Born",
    "chapter_a1": """Lena folgt der Adresse. Sie verlässt die Klinik und fährt in die Stadt. Die Adresse führt zu einem alten Wohnhaus am Stadtrand. Die Fenster sind vernagelt. Aber die Tür steht offen.

Sie tritt ein. Die Wohnung ist durchwühlt. Möbel umgestoßen, Schubladen herausgerissen. Jemand war schneller.

Dann hört sie ein Geräusch. Aus dem Keller. Ein Wimmern.

Lena geht die Treppe hinunter. Der Keller ist feucht und dunkel. In der Ecke hockt ein Mann. Verängstigt, abgemagert. Er trägt einen alten Klinikkittel.

"Ich bin's", flüstert er. "Elias. Sie sagten, ich wäre tot. Aber ich habe überlebt."

"Was ist hier passiert, Elias?"

Er sieht auf. "Dr. Richter hat mich versteckt. Er wollte mich schützen. Aber jetzt ist er weg. Und die anderen... sie kommen zurück."

Bevor er antworten kann, hören sie schwere Schritte auf der Treppe. Mehrere Personen.

Elias packt Lenas Arm. "Sie sind da. Du musst dich entscheiden." """,

    # ── ENTSCHEIDUNG 3A1 ──
    "decision_3a1_title": "Entscheidung 3A1 – A1a oder A1b?",
    "decision_3a1_question": "Du musst jetzt entscheiden.",
    "decision_3a1_options": "Was tust du? A1a: Ich rufe Verstärkung und warte auf Unterstützung. A1b: Ich stelle mich ihnen allein.",
    "decision_3a1_question_repeat": "Noch einmal: Was tust du?",
    "decision_3a1_options_repeat": "A1a: Verstärkung rufen. A1b: Dich allein stellen.",
    "decision_3a1_pause_s": 30,

    # ── PFAD A2: SAFE ──
    "chapter_a2_title": "A2: Der Safe des Direktors",
    "chapter_a2": """Lena öffnet den Safe. Der Brieföffner mit der Gravur "Patient 0" passt perfekt in ein verstecktes Schlüsselloch. Mit einem Klicken entriegelt sich die Tür.

Im Safe findet sie keine Geld, keine Wertgegenstände. Stattdessen: Akten. Alte Krankenakten aus den Siebzigerjahren. Obenauf liegt eine mit der Aufschrift "Patient 0 – Versuchsreihe A".

Was sie liest, lässt ihr das Blut gefrieren. Dr. Richter und ein Kollege hatten heimlich Experimente an Patienten durchgeführt. Elektroschocks, Psychopharmaka, Isolation. Offiziell sollten neue Behandlungsmethoden getestet werden. Inoffiziell ging es um Gedankenkontrolle.

Ganz unten in der Akte findet sie ein Foto. Es zeigt Dr. Richter mit einem Mann. Die Unterschrift: "Dr. Richter und Dr. Wagner, 1975."

Dr. Wagner. Der jetzige Leiter der Psychiatrie in der Universitätsklinik.

Das Telefon klingelt. Eine unbekannte Nummer. Eine Stimme sagt: "Frau Kommissarin. Ich rate Ihnen, die Akte zurückzulegen und zu gehen."

Es ist Dr. Wagner selbst.""",

    # ── ENTSCHEIDUNG 3A2 ──
    "decision_3a2_title": "Entscheidung 3A2 – A2a oder A2b?",
    "decision_3a2_question": "Du musst jetzt entscheiden.",
    "decision_3a2_options": "Wie reagierst du? A2a: Ich informiere die Staatsanwaltschaft und übergebe die Akten offiziell. A2b: Ich stelle Dr. Wagner persönlich zur Rede.",
    "decision_3a2_question_repeat": "Noch einmal: Wie reagierst du?",
    "decision_3a2_options_repeat": "A2a: Staatsanwaltschaft informieren. A2b: Dr. Wagner persönlich stellen.",
    "decision_3a2_pause_s": 30,

    # ── PFAD B: PATIENTENZELLE ──
    "chapter_b_title": "B: Patientenzelle 7",
    "chapter_b": """Lena geht den düsteren Gang zu den Patientenzellen entlang. Die Luft wird kälter. Die Zellentüren sind massiv mit kleinen Sichtfenstern. Nummer 1, 2, 3... bis 7.

Zelle 7 ist nicht verschlossen. Seltsam.

Sie drückt die Klinke. Die Tür öffnet sich mit einem Knarren. Die Zelle ist leer. Aber die Wände sind voller Kritzeleien. Zahlen, Daten, immer wieder dasselbe Wort: "ES-TUT-URS-LEID" – in Schleifen geschrieben, hundertfach.

In der Mitte liegt ein einzelner Schuh. Darunter ein Zettel: "Frag den Pförtner, was er in der Nacht des 13. November 1998 gesehen hat."

Im Türrahmen entdeckt Lena eine Gravur. Eine Karte. Der Grundriss der Klinik. Und ein Raum, der auf keinem offiziellen Plan ist. Markiert mit einem roten "X".

Der Pförtner wohnt im angrenzenden Haus. Aber die Karte zeigt einen Geheimgang hinter der Zellenwand.""",

    # ── ENTSCHEIDUNG 2B ──
    "decision_2b_title": "Entscheidung 2B – B1 oder B2?",
    "decision_2b_question": "Du musst jetzt entscheiden.",
    "decision_2b_options": "Was tust du? B1: Ich suche den Geheimgang hinter der Zellenwand. B2: Ich gehe zum Pförtnerhaus und befrage den Pförtner.",
    "decision_2b_question_repeat": "Noch einmal: Was tust du?",
    "decision_2b_options_repeat": "B1: Den Geheimgang suchen. B2: Den Pförtner befragen.",
    "decision_2b_pause_s": 30,

    # ── PFAD B1: GEHEIMGANG ──
    "chapter_b1_title": "B1: Der Geheimgang",
    "chapter_b1": """Lena tastet die Wand ab. Hinter einer losen Holzvertäfelung verbirgt sich ein Durchlass. Die Öffnung ist eng, aber sie führt in die Tiefe.

Sie klettert hindurch. Der Gang ist dunkel und niedrig. Ihre Taschenlampe beleuchtet Staub und Spinnweben.

Nach etwa zwanzig Metern verbreitert sich der Gang zu einem Raum. Ein alter Behandlungsraum. In der Mitte steht ein rostiger Operationstisch. Daneben ein Metallschrank. Lena öffnet ihn. Darin: Patientenakten, Dutzende.

Sie nimmt eine Akte heraus. Dr. Richter hat hier jahrelang verbotene Experimente durchgeführt. Eine der Akten trägt den Namen "Elias Born". Der Patient galt als verschollen. Aber laut dieser Akte wurde er in eine andere Einrichtung verlegt. Vor drei Tagen.

Da hört Lena Schritte. Von draußen. Sie ist nicht allein.""",

    # ── ENTSCHEIDUNG 3B1 ──
    "decision_3b1_title": "Entscheidung 3B1 – B1a oder B1b?",
    "decision_3b1_question": "Du musst jetzt entscheiden.",
    "decision_3b1_options": "Was tust du? B1a: Ich verstecke mich und beobachte. B1b: Ich stelle mich mit gezogener Waffe.",
    "decision_3b1_question_repeat": "Noch einmal: Was tust du?",
    "decision_3b1_options_repeat": "B1a: Verstecken und beobachten. B1b: Stellen mit gezogener Waffe.",
    "decision_3b1_pause_s": 30,

    # ── PFAD B2: PFÖRTNER ──
    "chapter_b2_title": "B2: Der Pförtner",
    "chapter_b2": """Lena geht zum Pförtnerhaus. Ein kleiner, geduckter Bau. Das Licht brennt. Sie klopft.

Ein älterer Mann öffnet. Abgewetzte Cordhose, kariertes Hemd. Gerötete Augen. "Sie sind die Kommissarin", sagt er.

"Was ist in der Nacht des 13. November 1998 passiert?"

Der alte Mann zögert. Dann holt er eine Schachtel mit Fotos. Unscharf, aber erkennbar. Sie zeigen Dr. Richter und einen anderen Mann – sie tragen einen Körper, eingewickelt in Plastik.

"Ich habe sie gesehen", flüstert er. "Aber ich hatte nie den Mut, etwas zu sagen. Richter war gefährlich. Und sein Partner – Dr. Wagner – der hat noch mehr Macht."

"Dr. Wagner von der Universitätsklinik?"

Er nickt. "Die Experimente wurden nie eingestellt. Nur verlagert. Wagner führt sie heute noch weiter. Sie müssen vorsichtig sein, Frau Kommissarin. Er hat überall Augen."  """,

    # ── ENTSCHEIDUNG 3B2 ──
    "decision_3b2_title": "Entscheidung 3B2 – B2a oder B2b?",
    "decision_3b2_question": "Du musst jetzt entscheiden.",
    "decision_3b2_options": "Wie gehst du vor? B2a: Ich lasse die Beweise vom LKA sichern und leite ein offizielles Verfahren ein. B2b: Ich konfrontiere Dr. Wagner sofort – er ist heute noch in der Klinik.",
    "decision_3b2_question_repeat": "Noch einmal: Wie gehst du vor?",
    "decision_3b2_options_repeat": "B2a: Beweise sichern lassen. B2b: Dr. Wagner sofort konfrontieren.",
    "decision_3b2_pause_s": 30,

    # ── ENDE 1: GERECHTIGKEIT ──
    "ending_1_title": "Ende 1: Gerechtigkeit (bittersüß)",
    "ending_1": """Lena zieht sich zurück und alarmiert Verstärkung. Die Kollegen treffen ein und sichern das Gebäude. In den folgenden Tagen wird die Klinik durchsucht. Die Beweise sind erdrückend.

Dr. Wagner wird festgenommen. Der Skandal fliegt auf. Ein Untersuchungsausschuss wird eingesetzt. Dr. Richter wird nie gefunden.

Lena erhält eine Belobigung. Aber etwas nagt an ihr. Die leeren Zellen. Die Opfer, die nie Gerechtigkeit erfahren haben.

"Vielleicht ist das manchmal alles, was wir tun können", denkt sie. "Nicht die perfekte Lösung finden. Sondern das System in Gang setzen."

Ende 1 von 4 – Gerechtigkeit""",

    # ── ENDE 2: DIE WAHRHEIT ──
    "ending_2_title": "Ende 2: Die Wahrheit (gutes Ende)",
    "ending_2": """Lena stellt sich den Schritten entgegen. Ihre Waffe ist gezielt.

Die Tür fliegt auf. Drei Männer in dunklen Anzügen stehen davor. Dr. Wagner.

"Sie haben Dinge gefunden, die Sie nicht verstehen", sagt er kalt.

"Ich verstehe genug."

Da ertönen Sirenen. Mehrere. Draußen. Lenas Kollegen.

"Ich habe keinen Alleingang gemacht. Die Beweise sind bereits auf dem Weg zur Staatsanwaltschaft."

Monate später. Der größte Medizinskandal seit Jahrzehnten. Wagner wird zu lebenslanger Haft verurteilt. Die Wahrheit ist ans Licht gekommen.

Auf Lenas Schreibtisch liegt ein Brief. Kein Absender. Nur: "Danke. – E.B."

Elias Born hat überlebt.

Ende 2 von 4 – Die Wahrheit""",

    # ── ENDE 3: VERSPIELT ──
    "ending_3_title": "Ende 3: Verspielt (schlechtes Ende)",
    "ending_3": """Lena stellt Dr. Wagner persönlich. Ein Fehler.

Sie trifft ihn in seinem Büro. Er tut ahnungslos, bietet Kaffee an.

"Ich habe die Akten", sagt Lena direkt.

Wagner seufzt. Er öffnet eine Schublade. Hinter ihr geht eine Tür auf. Zwei Männer packen Lena von hinten.

Sie wird überwältigt. Die Akten werden ihr abgenommen. Als sie zu sich kommt, ist sie in einem weißen Raum. Keine Fenster. Eine Stahltür.

"Sie werden hier bleiben", sagt eine Stimme aus dem Lautsprecher. "Bis wir entscheiden, was mit Ihnen geschieht."

Die Lichter gehen aus. Die Tür verriegelt sich.

Ende 3 von 4 – Verspielt""",

    # ── ENDE 4: DER JÄGER ──
    "ending_4_title": "Ende 4: Der Jäger (schlechtes Ende)",
    "ending_4": """Lena versteckt sich. Die Schritte kommen näher. Zwei Personen.

"Sie ist hier irgendwo", sagt eine Stimme. "Findet sie."

Handschuhe packen Lena von hinten. Sie wehrt sich, tritt um sich. Aber die Übermacht ist zu groß.

Sie wird in einen Raum gezerrt. Die Tür fällt ins Schloss. Stockfinster.

"Du wolltest die Wahrheit wissen, Kommissarin?" – eine Stimme aus dem Dunkel. "Jetzt wirst du sie am eigenen Leib erfahren."

Die Experimente von Waldesruh haben eine neue Probandin.

Ende 4 von 4 – Der Jäger""",

    # ── OUTRO ──
    "outro_title": "Abspann & Danksagung",
    "outro": """Vielen Dank, dass du 'Die letzte Schicht' gespielt hast!

Diese Geschichte hat vier mögliche Enden. Hast du alle gefunden?

Hier sind die Kapitel mit Zeitangaben in der Videobeschreibung. Du kannst jederzeit zurückspringen und eine andere Entscheidung treffen.

Wenn dir dieses Format gefällt, lass ein Like da und abonniere den Kanal.

Bis zum nächsten Fall! – Tell Me More AI"""
}

# ─────────────────────────────────────────────────────────────
# 2. KAPITEL-STRUKTUR
# ─────────────────────────────────────────────────────────────

VIDEO_SEGMENTS = [
    # INTRO
    ("intro",               "Intro – Ankunft in der Klinik"),
    ("gap_2s",              None),
    # DECISION 1
    ("decision_1_question", None),
    ("decision_1_options",  None),
    ("decision_1_pause",    None),
    ("decision_1_question_repeat", None),
    ("decision_1_options_repeat", None),
    ("gap_2s",              None),
    # PATH A
    ("chapter_a",           "A: Das Büro des Direktors"),
    ("gap_2s",              None),
    # DECISION 2A
    ("decision_2a_question", None),
    ("decision_2a_options",  None),
    ("decision_2a_pause",    None),
    ("decision_2a_question_repeat", None),
    ("decision_2a_options_repeat", None),
    ("gap_2s",              None),
    # PATH A1
    ("chapter_a1",          "A1: Die Spur des Elias Born"),
    ("gap_2s",              None),
    # DECISION 3A1
    ("decision_3a1_question", None),
    ("decision_3a1_options",  None),
    ("decision_3a1_pause",    None),
    ("decision_3a1_question_repeat", None),
    ("decision_3a1_options_repeat", None),
    ("gap_2s",              None),
    # ENDINGS
    ("ending_1",            "Ende 1: Gerechtigkeit"),
    ("ending_2",            "Ende 2: Die Wahrheit"),
    ("gap_2s",              None),
    # PATH A2
    ("chapter_a2",          "A2: Der Safe des Direktors"),
    ("gap_2s",              None),
    # DECISION 3A2
    ("decision_3a2_question", None),
    ("decision_3a2_options",  None),
    ("decision_3a2_pause",    None),
    ("decision_3a2_question_repeat", None),
    ("decision_3a2_options_repeat", None),
    ("gap_2s",              None),
    ("ending_3",            "Ende 3: Verspielt"),
    ("gap_2s",              None),
    # PATH B
    ("chapter_b",           "B: Patientenzelle 7"),
    ("gap_2s",              None),
    # DECISION 2B
    ("decision_2b_question", None),
    ("decision_2b_options",  None),
    ("decision_2b_pause",    None),
    ("decision_2b_question_repeat", None),
    ("decision_2b_options_repeat", None),
    ("gap_2s",              None),
    # PATH B1
    ("chapter_b1",          "B1: Der Geheimgang"),
    ("gap_2s",              None),
    # DECISION 3B1
    ("decision_3b1_question", None),
    ("decision_3b1_options",  None),
    ("decision_3b1_pause",    None),
    ("decision_3b1_question_repeat", None),
    ("decision_3b1_options_repeat", None),
    ("gap_2s",              None),
    ("ending_4",            "Ende 4: Der Jäger"),
    ("gap_2s",              None),
    # PATH B2
    ("chapter_b2",          "B2: Der Pförtner"),
    ("gap_2s",              None),
    # DECISION 3B2
    ("decision_3b2_question", None),
    ("decision_3b2_options",  None),
    ("decision_3b2_pause",    None),
    ("decision_3b2_question_repeat", None),
    ("decision_3b2_options_repeat", None),
    ("gap_2s",              None),
    # OUTRO
    ("outro",               "Abspann & Danksagung"),
]
