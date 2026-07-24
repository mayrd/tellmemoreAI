#!/usr/bin/env python3
"""
Die letzte Schicht — Interaktiver Audio-Escape-Room
===================================================
Ein Krimi-Hörspiel für YouTube mit Entscheidungsknoten.
Ca. 60-80 Minuten Gesamtlänge, 4 Enden, Kapitelmarken.

Stimmen:
  - Erzählerin (Kommissarin Lena Voss): de-DE-KatjaNeural (weiblich, warm)
  - Fragen/Entscheidungen: de-DE-ConradNeural (männlich, autoritativ)
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

Das Hauptgebäude ist verrammelt. Doch die Hintertür steht offen.

Sie betritt die Klinik. Der Geruch von Alter und Verfall liegt in der Luft. Ihre Schritte hallen durch den leeren Flur. Links ist das Büro des Direktors. Rechts führt ein Gang zu den Patientenzellen.

Sie muss eine Entscheidung treffen.""",

    # ── ENTSCHEIDUNG 1 ──
    "decision_1_title": "Entscheidung 1 – Der erste Schritt",
    "decision_1_question": "Wohin gehst du zuerst?",
    "decision_1_options": "A: Ich untersuche das Büro des Direktors. Springe zu Kapitel 'A: Das Büro des Direktors'. B: Ich gehe zu Patientenzelle 7, von der die Kollegen berichtet haben. Springe zu Kapitel 'B: Patientenzelle 7'.",
    "decision_1_repeat": "Noch einmal: Wohin gehst du zuerst? A: Das Büro des Direktors. B: Patientenzelle 7.",
    "decision_1_pause_s": 30,

    # ── PFAD A: DIREKTORSBÜRO ──
    "path_a_title": "A: Das Büro des Direktors",
    "path_a": """Lena öffnet die schwere Eichentür zum Direktorenbüro. Das Zimmer ist überraschend ordentlich. Ein massiver Schreibtisch aus dunklem Holz, lederne Sessel, ein alter Safe in der Ecke. An den Wänden hingen Zertifikate und Fotos – doch einige sind verschwunden, die hellen Rechtecke an der Tapete verraten es.

Sie setzt sich an den Schreibtisch und blättert durch die Papiere. Rechnungen, Korrespondenz, Forschungsnotizen. Nichts Ungewöhnliches. Bis sie auf das Tagebuch stößt.

Es ist in Leder gebunden, abgegriffen. Die letzte Seite ist frisch beschrieben. Lena liest:

"Es tut mir leid. Ich hätte es ihnen sagen sollen. Aber sie werden mich nicht verstehen. Die Stimmen in den Wänden... sie sind real."

Lena blättert zurück. Das Tagebuch berichtet von einem Patienten – Elias Born – der vor zwanzig Jahren in dieser Klinik verschwand. Dr. Richter habe versucht, ihm zu helfen. Aber etwas sei schiefgelaufen.

Ein Zettel fällt aus dem Tagebuch. Darauf steht eine Adresse in der Stadt. Und die Worte: "Der Schlüssel liegt in der Vergangenheit."

Dann bemerkt Lena den Safe. Ein massives Stahlschloss. Verschlossen natürlich. Aber auf dem Schreibtisch liegt ein Brieföffner mit einer seltsamen Gravur: "Patient 0 – der Anfang vom Ende."

Ihre Gedanken überschlagen sich. Der Safe. Die Adresse. Der verschwundene Patient. Was ist hier passiert?

Eine Entscheidung muss her.""",

    # ── ENTSCHEIDUNG 2A ──
    "decision_2a_title": "Entscheidung 2A – Der nächste Hinweis",
    "decision_2a_question": "Welche Spur verfolgst du?",
    "decision_2a_options": "A: Ich folge der Adresse von Elias Born. Springe zu Kapitel 'A1: Die Spur des Elias Born'. B: Ich versuche, den Safe zu öffnen. Springe zu Kapitel 'A2: Der Safe des Direktors'.",
    "decision_2a_repeat": "Noch einmal: Welche Spur verfolgst du? A: Die Adresse von Elias Born. B: Den Safe öffnen.",
    "decision_2a_pause_s": 30,

    # ── PFAD A1: ELIAS BORN ──
    "path_a1_title": "A1: Die Spur des Elias Born",
    "path_a1_voice": "KatjaNeural",
    "path_a1": """Lena entscheidet sich, der Adresse zu folgen. Sie verlässt die Klinik und fährt in die nahegelegene Stadt. Die Adresse führt sie zu einem alten Wohnhaus am Stadtrand. Die Fenster sind mit Brettern vernagelt. Aber die Tür steht einen Spalt offen.

Sie tritt ein. Die Wohnung ist durchwühlt. Möbel umgestoßen, Schubladen herausgerissen. Jemand war schneller.

Dann hört sie ein Geräusch. Aus dem Keller. Ein Wimmern.

Lena nimmt ihre Waffe und geht die Treppe hinunter. Der Keller ist feucht und dunkel. Der Geruch von Schimmel und etwas Metallischem liegt in der Luft.

In der Ecke hockt ein Mann. Verängstigt, abgemagert. Er trägt einen alten Klinikkittel.

"Ich bin's", flüstert er. "Elias. Sie sagten, ich wäre tot. Aber ich habe überlebt."

Lena kniet sich zu ihm. "Was ist hier passiert, Elias?"

Er sieht auf. In seinen Augen liegt etwas, das Lena nicht deuten kann – Angst oder Wahnsinn? Oder beides?

"Dr. Richter hat mich versteckt", sagt er leise. "Er wollte mich schützen. Aber jetzt ist er weg. Und die anderen... sie kommen zurück."

"Welche anderen?", fragt Lena.

Bevor er antworten kann, hören sie Schritte auf der Treppe. Schwere Schritte. Mehrere Personen.

Elias packt Lenas Arm. "Sie sind da. Du musst dich entscheiden. Zieh dich zurück und hol Verstärkung. Oder stell dich ihnen – allein.""",

    # ── ENTSCHEIDUNG 3A1 ──
    "decision_3a1_title": "Entscheidung 3A1 – Die Konfrontation",
    "decision_3a1_question": "Was tust du?",
    "decision_3a1_options": "A: Ich rufe Verstärkung und warte auf Unterstützung. Springe zu Kapitel 'Ende 1: Gerechtigkeit'. B: Ich stelle mich ihnen allein. Springe zu Kapitel 'Ende 2: Die Wahrheit'.",
    "decision_3a1_repeat": "Noch einmal: Was tust du? A: Verstärkung rufen. B: Allein stellen.",
    "decision_3a1_pause_s": 30,

    # ── PFAD A2: SAFE ──
    "path_a2_title": "A2: Der Safe des Direktors",
    "path_a2": """Lena entscheidet sich, den Safe zu öffnen. Der Brieföffner mit der Gravur "Patient 0" passt perfekt in ein verstecktes Schlüsselloch hinter einem losen Bücherregal. Mit einem Klicken entriegelt sich die Tür.

Im Safe findet sie keine Geld, keine Wertgegenstände. Stattdessen: Akten. Alte Krankenakten aus den Siebzigerjahren. Obenauf liegt eine mit der Aufschrift "Patient 0 – Versuchsreihe A".

Sie schlägt die Akte auf. Was sie liest, lässt ihr das Blut gefrieren.

Dr. Richter und ein Kollege hatten in den Siebzigern heimlich Experimente an Patienten durchgeführt. Elektroschocks, Psychopharmaka, Isolation. Offiziell sollten neue Behandlungsmethoden getestet werden. Inoffiziell ging es um etwas ganz anderes – Gedankenkontrolle. Der "Patient 0" war der erste, an dem sie es versuchten. Er überlebte nicht.

Aber die Experimente wurden nie gestoppt. Sie wurden nur besser versteckt.

Lena blättert weiter. Eine Liste mit Namen. Mindestens zwanzig Patienten über dreißig Jahre. Viele von ihnen gelten als "entwichen" oder "verstorben".

Ganz unten in der Akte findet sie ein Foto. Es zeigt Dr. Richter mit einem Mann – beide lächeln. Die Unterschrift: "Dr. Richter und Dr. Wagner, 1975."

Dr. Wagner. Der Name kommt Lena bekannt vor. Er ist der jetzige Leiter der Psychiatrie in der nahegelegenen Universitätsklinik.

Das Telefon klingelt. Lenas Diensthandy. Eine unbekannte Nummer.

Sie geht ran. Eine Stimme sagt: "Frau Kommissarin. Ich rate Ihnen, die Akte zurückzulegen und zu gehen. Nicht alles, was vergraben ist, muss ausgegraben werden."

Die Stimme kommt ihr bekannt vor. Es ist Dr. Wagner selbst.

Lena muss handeln.""",

    # ── ENTSCHEIDUNG 3A2 ──
    "decision_3a2_title": "Entscheidung 3A2 – Der Drahtzieher",
    "decision_3a2_question": "Wie reagierst du?",
    "decision_3a2_options": "A: Ich informiere die Staatsanwaltschaft und übergebe die Akten offiziell. Springe zu Kapitel 'Ende 2: Die Wahrheit'. B: Ich stelle Dr. Wagner persönlich zur Rede. Springe zu Kapitel 'Ende 3: Verspielt'.",
    "decision_3a2_repeat": "Noch einmal: Wie reagierst du? A: Staatsanwaltschaft informieren. B: Dr. Wagner persönlich stellen.",
    "decision_3a2_pause_s": 30,

    # ── PFAD B: PATIENTENZELLE ──
    "path_b_title": "B: Patientenzelle 7",
    "path_b": """Lena geht den düsteren Gang zu den Patientenzellen entlang. Die Luft wird kälter, der Geruch von Desinfektionsmittel stärker. Die Zellentüren sind massiv, mit kleinen Sichtfenstern. Nummer 1, 2, 3... bis 7.

Sie bleibt vor Zelle 7 stehen. Die Tür ist nicht verschlossen. Das ist ungewöhnlich.

Sie drückt die Klinke. Die Tür öffnet sich mit einem lang gezogenen Knarren.

Die Zelle ist leer. Aber nicht unberührt. Die Wände sind voller Kritzeleien. Zahlen, Daten, immer wieder dasselbe Wort: "ES-TUT-URS-LEID" – in Schleifen geschrieben, hundertfach.

In der Mitte des Raumes liegt ein einzelner Schuh. Abgenutzt, alt.

Lena bückt sich und hebt ihn auf. Unter dem Schuh liegt ein Zettel. Darauf steht in krakeliger Handschrift: "Frag den Pförtner, was er in der Nacht des 13. November 1998 gesehen hat."

Lena dreht sich um. Da ist etwas. Im Türrahmen. Eine kleine Gravur – fast unsichtbar – eingeritzt ins Holz. Eine Karte. Sie zeigt den Grundriss der Klinik. Und ein Raum, der auf keinem offiziellen Plan ist. Markiert mit einem roten "X".

Der Raum ist mit dem Keller verbunden.

Lena zögert. Der Pförtner wohnt im angrenzenden Haus. Aber die Karte... die Karte zeigt einen Geheimgang hinter der Zellenwand.

Was tut sie?""",

    # ── ENTSCHEIDUNG 2B ──
    "decision_2b_title": "Entscheidung 2B – Der Geheimgang",
    "decision_2b_question": "Was tust du?",
    "decision_2b_options": "A: Ich suche den Geheimgang hinter der Zellenwand. Springe zu Kapitel 'B1: Der Geheimgang'. B: Ich gehe zum Pförtnerhaus und befrage den Pförtner. Springe zu Kapitel 'B2: Der Pförtner'.",
    "decision_2b_repeat": "Noch einmal: Was tust du? A: Den Geheimgang suchen. B: Den Pförtner befragen.",
    "decision_2b_pause_s": 30,

    # ── PFAD B1: GEHEIMGANG ──
    "path_b1_title": "B1: Der Geheimgang",
    "path_b1": """Lena tastet die Wand ab. Die Karte hat nicht gelogen. Hinter einer losen Holzvertäfelung verbirgt sich ein Durchlass. Die Öffnung ist eng – kaum schulterbreit – aber sie führt in die Tiefe.

Sie klettert hindurch. Der Gang ist dunkel und niedrig. Ihre Taschenlampe beleuchtet Staub und Spinnweben. Die Wände sind aus rohem Beton, die Decke mit Kabeln und Rohren gespickt.

Nach etwa zwanzig Metern verbreitert sich der Gang zu einem Raum. Ein alter Behandlungsraum. Verlassen seit Jahrzehnten.

In der Mitte steht ein rostiger Operationstisch. Daneben ein Metallschrank. Lena öffnet ihn. Darin: Patientenakten, Dutzende. Alle mit demselben Vermerk: "Versuchsreihe A – abgeschlossen."

Sie nimmt eine Akte heraus. Liest. Was sie erfährt, ist unfassbar. Dr. Richter hat hier jahrelang verbotene Experimente durchgeführt. Elektrokrampftherapie, Isolation, Psychopharmaka ohne Einwilligung.

Eine der Akten trägt den Namen "Elias Born". Der Patient galt als verschollen. Aber laut dieser Akte wurde er in eine andere Einrichtung verlegt. Vor drei Tagen.

Da hört Lena Schritte. Von draußen. Sie sind nicht allein in der Klinik.""",

    # ── ENTSCHEIDUNG 3B1 ──
    "decision_3b1_title": "Entscheidung 3B1 – Die Schritte",
    "decision_3b1_question": "Was tust du?",
    "decision_3b1_options": "A: Ich verstecke mich und beobachte, wer kommt. Springe zu Kapitel 'Ende 4: Der Jäger'. B: Ich stelle mich offen – mit gezogener Waffe. Springe zu Kapitel 'Ende 2: Die Wahrheit'.",
    "decision_3b1_repeat": "Noch einmal: Was tust du? A: Verstecken. B: Stellen mit gezogener Waffe.",
    "decision_3b1_pause_s": 30,

    # ── PFAD B2: PFÖRTNER ──
    "path_b2_title": "B2: Der Pförtner",
    "path_b2": """Lena verlässt die Klinik und geht zum Pförtnerhaus. Ein kleiner, geduckter Bau aus den Zwanzigerjahren. Das Licht brennt. Sie klopft.

Es dauert. Dann öffnet ein älterer Mann die Tür. Er trägt eine abgewetzte Cordhose und ein kariertes Hemd. Seine Augen sind gerötet.

"Sie sind die Kommissarin", sagt er. Keine Frage. Er hat sie erwartet.

"Ja. Ich muss Ihnen ein paar Fragen stellen."

Der Pförtner – Herr Meier – nickt und lässt sie herein. Seine Wohnung ist vollgestopft mit Büchern und Zeitungsausschnitten. Alle handeln von der Klinik.

"Herr Meier, was ist in der Nacht des 13. November 1998 passiert?"

Der alte Mann zögert. Dann geht er zu einem Schrank und holt eine Schachtel heraus. Darin: Fotos. Unscharf, aber erkennbar. Sie zeigen Dr. Richter und einen anderen Mann – sie tragen etwas. Einen Körper, eingewickelt in Plastik.

"Ich habe sie gesehen", flüstert Meier. "Aber ich habe nie den Mut gehabt, etwas zu sagen. Richter war... gefährlich. Und sein Partner – Dr. Wagner – der hat noch mehr Macht."

"Dr. Wagner? Von der Universitätsklinik?"

Meier nickt. "Die Experimente. Sie wurden nie eingestellt. Nur verlagert. Wagner führt sie heute noch weiter."

Seine Hände zittern. "Sie müssen vorsichtig sein, Frau Kommissarin. Wagner weiß, dass Sie hier sind. Er hat überall Augen." """,

    # ── ENTSCHEIDUNG 3B2 ──
    "decision_3b2_title": "Entscheidung 3B2 – Der Drahtzieher",
    "decision_3b2_question": "Wie gehst du vor?",
    "decision_3b2_options": "A: Ich lasse die Beweise vom LKA sichern und leite ein offizielles Verfahren ein. Springe zu Kapitel 'Ende 2: Die Wahrheit'. B: Ich konfrontiere Dr. Wagner sofort – er ist noch heute in der Klinik. Springe zu Kapitel 'Ende 1: Gerechtigkeit'.",
    "decision_3b2_repeat": "Noch einmal: Wie gehst du vor? A: Beweise sichern lassen. B: Dr. Wagner sofort konfrontieren.",
    "decision_3b2_pause_s": 30,

    # ── ENDE 1: GERECHTIGKEIT (bittersüß) ──
    "ending_1_title": "Ende 1: Gerechtigkeit",
    "ending_1": """Lena zieht sich zurück und alarmiert Verstärkung. Die Kollegen treffen innerhalb weniger Minuten ein. Sie sichern das Gebäude.

In den folgenden Tagen wird die Klinik durchsucht. Die Beweise sind erdrückend: Die Akten, die Fotos, die Zeugenaussagen. Dr. Wagner wird festgenommen. Der Skandal fliegt auf.

Die Öffentlichkeit ist entsetzt. Die Politik verspricht Aufklärung. Ein Untersuchungsausschuss wird eingesetzt.

Dr. Richter wird nie gefunden. Ob er tot ist oder sich versteckt hat – niemand weiß es.

Lena erhält eine Belobigung. Aber etwas nagt an ihr. Die leeren Zellen. Die ungestellten Fragen. Die Opfer, die nie Gerechtigkeit erfahren haben.

"Vielleicht ist das manchmal alles, was wir tun können", denkt sie. "Nicht die perfekte Lösung finden. Sondern das System in Gang setzen, das sie finden kann."

Sie schließt die Akte. Ein kleiner Sieg. Aber ein wichtiger.

Ende 1 von 4 – Gerechtigkeit""",

    # ── ENDE 2: DIE WAHRHEIT (gutes Ende) ──
    "ending_2_title": "Ende 2: Die Wahrheit",
    "ending_2": """Lena stellt sich den Schritten entgegen. Ihre Waffe ist gezielt. Ihr Herz rast.

Die Tür fliegt auf. Drei Männer in dunklen Anzügen stehen davor. Einer davon ist Dr. Wagner.

"Frau Kommissarin", sagt er kalt. "Ich nehme an, Sie haben Dinge gefunden, die Sie nicht verstehen."

"Ich verstehe genug", erwidert Lena. "Sie und Richter haben jahrzehntelang Verbrechen begangen. Sie werden dafür bezahlen."

Wagner lächelt. "Wer sollte mich aufhalten? Sie? Eine einzelne Kommissarin?"

Da ertönt eine Sirene. Mehrere. Draußen. Lenas Kollegen.

"Ich habe keinen Alleingang gemacht", sagt Lena. "Die Beweise sind bereits auf dem Weg zur Staatsanwaltschaft."

Das Lächeln gefriert Wagner im Gesicht. Er dreht sich um. Aber es ist zu spät. Die ersten Beamten stürmen das Gebäude.

Monate später. Der Prozess ist der größte Medizinskandal seit Jahrzehnten. Wagner wird zu lebenslanger Haft verurteilt. Richter bleibt verschwunden – aber die Wahrheit über seine Taten ist ans Licht gekommen.

Lena sitzt in ihrem Büro. Auf ihrem Schreibtisch liegt ein Brief. Kein Absender. Nur eine Zeile:

"Danke. – E.B."

Elias Born hat überlebt.

Ende 2 von 4 – Die Wahrheit""",

    # ── ENDE 3: VERSPIELT (schlechtes Ende) ──
    "ending_3_title": "Ende 3: Verspielt",
    "ending_3": """Lena stellt Dr. Wagner persönlich. Ein Fehler.

Sie trifft ihn in seinem Büro in der Universitätsklinik. Er tut ahnungslos, bietet ihr Kaffee an, redet von Missverständnissen.

"Ich habe die Akten", sagt Lena direkt.

Wagner seufzt. "Das dachte ich mir."

Er öffnet eine Schublade. Lena greift nach ihrer Waffe. Aber sie ist zu langsam. Hinter ihr öffnet sich eine Tür. Zwei Männer packen sie.

Sie wird überwältigt. Die Akten werden ihr abgenommen. Als sie wieder zu sich kommt, ist sie in einem weißen Raum. Keine Fenster. Nur eine Tür aus Stahl.

"Sie werden hier bleiben", sagt eine Stimme aus dem Lautsprecher. "Bis wir entscheiden, was mit Ihnen geschieht."

Die Lichter gehen aus. Die Tür verriegelt sich.

Lena schreit. Aber niemand hört sie.

Ende 3 von 4 – Verspielt""",

    # ── ENDE 4: DER JÄGER (schlechtes Ende) ──
    "ending_4_title": "Ende 4: Der Jäger",
    "ending_4": """Lena versteckt sich. Ihr Herz pocht so laut, dass es in der Stille widerhallt. Die Schritte kommen näher. Sie presst sich in eine Nische.

Ein Schatten fällt über die Wand. Dann noch einer. Zwei Personen.

"Sie ist hier irgendwo", sagt eine Stimme.

"Findet sie."

Lena hält den Atem an. Aber es hilft nichts. Handschuhe packen sie von hinten. Sie wehrt sich. Tritt um sich. Aber die Übermacht ist zu groß.

Sie wird in einen Raum gezerrt. Die Tür fällt ins Schloss. Drinnen ist es stockfinster.

"Du wolltest die Wahrheit wissen, Kommissarin?" – eine Stimme aus dem Dunkel. "Jetzt wirst du sie am eigenen Leib erfahren."

Die Tür ist massiv. Die Wände sind dick. Kein Fenster. Kein Entkommen.

Die Experimente von Waldesruh haben eine neue Probandin.

Ende 4 von 4 – Der Jäger""",

    # ── OUTRO ──
    "outro_title": "Abspann & Danksagung",
    "outro": """Vielen Dank, dass du 'Die letzte Schicht' gespielt hast – einen interaktiven Audio-Escape-Room von Tell Me More AI!

Diese Geschichte hat vier mögliche Enden. Hast du alle gefunden?

Hier sind die Kapitel mit Zeitangaben in der Videobeschreibung. Du kannst jederzeit zurückspringen und eine andere Entscheidung treffen.

Wenn dir dieses Format gefällt, lass ein Like da und abonniere den Kanal. Sag uns in den Kommentaren: Welches Ende hattest du zuerst? Und welches war dein Lieblingsende?

Bis zum nächsten Fall!

– Tell Me More AI"""
}

# ─────────────────────────────────────────────────────────────
# 2. KAPITEL-STRUKTUR (Reihenfolge im Video)
# ─────────────────────────────────────────────────────────────
# Dies definiert die lineare Abspielreihenfolge aller Segmente.

VIDEO_SEGMENTS = [
    # (chapter_id, chapter_label)
    ("intro",               "Intro – Ankunft in der Klinik"),
    ("decision_1_question", "Entscheidung 1 – Wohin zuerst?"),
    ("decision_1_pause",    None),  # Pause ohne Kapitelmarke
    ("decision_1_repeat",   None),  # Wiederholung ohne Kapitelmarke
    
    ("path_a",              "A: Das Büro des Direktors"),
    ("decision_2a_question","Entscheidung 2A – Welche Spur?"),
    ("decision_2a_pause",   None),
    ("decision_2a_repeat",  None),
    
    ("path_a1",             "A1: Die Spur des Elias Born"),
    ("decision_3a1_question","Entscheidung 3A1 – Was tun?"),
    ("decision_3a1_pause",  None),
    ("decision_3a1_repeat", None),
    
    ("ending_1",            "Ende 1 – Gerechtigkeit"),
    ("ending_2",            "Ende 2 – Die Wahrheit"),
    
    ("path_a2",             "A2: Der Safe des Direktors"),
    ("decision_3a2_question","Entscheidung 3A2 – Wie reagieren?"),
    ("decision_3a2_pause",  None),
    ("decision_3a2_repeat", None),
    
    ("ending_3",            "Ende 3 – Verspielt"),
    
    ("path_b",              "B: Patientenzelle 7"),
    ("decision_2b_question","Entscheidung 2B – Geheimgang?"),
    ("decision_2b_pause",   None),
    ("decision_2b_repeat",  None),
    
    ("path_b1",             "B1: Der Geheimgang"),
    ("decision_3b1_question","Entscheidung 3B1 – Verstecken?"),
    ("decision_3b1_pause",  None),
    ("decision_3b1_repeat", None),
    
    ("ending_4",            "Ende 4 – Der Jäger"),
    
    ("path_b2",             "B2: Der Pförtner"),
    ("decision_3b2_question","Entscheidung 3B2 – Vorgehen?"),
    ("decision_3b2_pause",  None),
    ("decision_3b2_repeat", None),
    
    ("outro",               "Abspann"),
]
