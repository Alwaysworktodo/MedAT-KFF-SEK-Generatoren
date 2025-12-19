import os
import json
import random
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.platypus import Flowable

pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))

class CheckBox(Flowable):
    """Eine anpassbare Checkbox für ReportLab"""
    def __init__(self, size=12):
        self.size = size
        self.width = size
        self.height = size
    
    def draw(self):
        # Zeichne ein leeres Rechteck
        self.canv.rect(0, 0, self.size, self.size, stroke=1, fill=0)

def create_checkbox():
    """Erstellt eine schöne leere Checkbox"""
    return CheckBox(12)

# --- SICHERHEIT: API-Schlüssel laden ---
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OpenAI API-Schlüssel nicht gefunden. Bitte setzen Sie die Umgebungsvariable OPENAI_API_KEY.")

client = OpenAI(api_key=api_key)

# --- MODELL-DEFINITION (Wie von Ihnen gewünscht) ---
MODELL_AUFGABENSTELLER = "gpt-5-nano-2025-08-07"

# --- EMOTIONS-BLACKLIST (Wörter die NICHT in der Geschichte vorkommen dürfen) ---
# Der Test-Taker soll die Emotionen selbst erkennen!
# HINWEIS: Reduzierte Liste - erlaubt etwas mehr Ausdruck für natürlichere Geschichten
EMOTIONS_BLACKLIST = [
    # Grundemotionen (direkte Benennung)
    "freude", "freudig", "glücklich", "glück", "fröhlich", 
    "trauer", "traurig", "traurigkeit", "betrübt",
    "angst", "verängstigt", "panisch",
    "wut", "wütend", "zornig", "zorn", "verärgert",
    "ekel", "ekelt", "angewidert",
    "überraschung", "verblüfft",
    # Komplexere Emotionen (nur direkte Benennung)
    "stolz", "stolze", "stolzen",
    "scham", "schämt", "beschämt",
    "schuldgefühl", "schuldgefühle",
    "neid", "neidisch", "eifersüchtig", "eifersucht",
    "frustration", "frustriert",
    "enttäuschung", "enttäuscht",
    "erleichterung", "erleichtert",
    "dankbarkeit", "dankbar",
    "zufriedenheit", "zufrieden",
    "nervosität", "nervös",
    "verzweiflung", "verzweifelt",
    "begeisterung", "begeistert",
    "euphorie", "euphorisch",
    "melancholie", "melancholisch",
    "resignation", "resigniert",
    "reue", "bereut",
    "einsamkeit", "einsam",
    "verlegenheit", "verlegen",
    "mitleid", "bemitleidet",
    # Verben die Emotionen direkt beschreiben
    "fühlt sich", "fühlte sich", "empfindet", "empfand",
    # Zusätzliche emotionale Ausdrücke
    "glücksgefühl", "freudenschrei", "tränen der freude",
]

def contains_emotion_words(text):
    """Prüft ob der Text verbotene Emotionswörter enthält."""
    text_lower = text.lower()
    found_emotions = []
    for emotion in EMOTIONS_BLACKLIST:
        if emotion in text_lower:
            found_emotions.append(emotion)
    return found_emotions

# Fallback Szenarien für den Fall, dass die Datei nicht geladen werden kann
FALLBACK_SCENARIOS = [
]

def load_scenarios_from_file(filename="Szenario.txt"):
    """Lädt Szenario-Kategorien aus einer Datei"""
    scenarios = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):  # Ignoriere leere Zeilen und Kommentare
                    # Entferne führende/endende Anführungszeichen, Leerzeichen und Kommas
                    # Zuerst alle führenden Leerzeichen/Tabs entfernen
                    clean_line = line.lstrip(' \t')
                    # Dann Anführungszeichen und Kommas am Anfang und Ende entfernen
                    if clean_line.startswith('"'):
                        clean_line = clean_line[1:]
                    if clean_line.endswith('",') or clean_line.endswith('"'):
                        clean_line = clean_line.rstrip('",')
                    
                    if clean_line:
                        scenarios.append(clean_line)
                        
        print(f"✓ {len(scenarios)} Szenarien aus {filename} geladen")
        if scenarios:
            print(f"   Erstes Szenario: {scenarios[0][:50]}...")
        return scenarios
    except FileNotFoundError:
        print(f"❌ Warnung: {filename} nicht gefunden. Verwende Fallback-Szenarien.")
        return FALLBACK_SCENARIOS
    except Exception as e:
        print(f"❌ Fehler beim Laden von {filename}: {e}")
        return FALLBACK_SCENARIOS

def ensure_output_folders():
    """Stellt sicher, dass die Output-Ordner existieren"""
    folders = ['PDF-Output', 'Jsons-Output']
    for folder in folders:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"✓ Ordner '{folder}' erstellt")
        else:
            print(f"✓ Ordner '{folder}' existiert bereits")


# --- DER DYNAMISCHE MASTER-PROMPT ---
PROMPT_AUFGABENSTELLER = """
Rolle und Ziel:
Du bist ein Autor für psychometrische Testaufgaben zum Thema "Emotionen erkennen".

**Szenario für diese Aufgabe:**
Die Geschichte MUSS auf folgendem Szenario basieren: **"{szenario}"**

Das Szenario enthält bereits den Namen der Hauptfigur - verwende diesen Namen auch in der Frage!

---
**STILREGELN (UNBEDINGT EINHALTEN):**

1. **Sachlicher, aber lebendiger Stil:** Schreibe klar und verständlich. Leichte Beschreibungen von Reaktionen sind erlaubt.
2. **Keine übertriebenen Metaphern:** Keine poetischen Vergleiche, aber natürliche Alltagssprache ist OK.
3. **Konkrete Alltagssituation:** Beruf, Familie, Studium, Freizeit - realistische Szenarien.
4. **Klare Handlung:** Was passiert? Wer tut was? Was ist das Ergebnis?
5. **60-75 Wörter:** Ausreichend Kontext für die Situation.
6. **Frage am Ende:** Die Frage MUSS lauten: "Wie fühlt sich [Name der Hauptfigur aus dem Szenario]?"

**⚠️ WICHTIGSTE REGEL - KEINE EMOTIONEN IM TEXT NENNEN:**
Die Geschichte darf NIEMALS explizit Emotionen, Gefühle oder emotionale Zustände benennen!
Der Leser (Test-Taker) soll die Emotion SELBST erkennen - das ist der Sinn des Tests!

STRENG VERBOTEN in der Geschichte:
- "Er fühlte Freude/Stolz/Angst/Frustration..."
- "Sie spürte Erleichterung/Nervosität/Trauer..."
- "Glücklich/traurig/wütend/erleichtert sein..."
- "Schuldgefühle/Hoffnung/Enttäuschung machten sich breit..."

ERLAUBT: Beschreibe NUR Handlungen, Situationen, Ereignisse und beobachtbare Reaktionen!

---
**SO SOLL ES AUSSEHEN (Positivbeispiele - KEINE Emotionen genannt!):**

Beispiel 1:
"Maria arbeitet neben ihrem Jusstudium in einer Kanzlei. Sie ist eine sehr eifrige Person und freut sich auf jeden neuen, schwierigen Arbeitsauftrag. Bei der Weihnachtsfeier lobt sie ihr Chef mehrmals für ihre tolle Mitarbeit und bietet ihr eine Fixanstellung nach dem Studium an."
Frage: "Wie fühlt sich Maria?"

Beispiel 2:
"Karl hat bereits mehrmals versucht, seinen geliebten Oldtimer zu reparieren, doch jedes Mal ohne Erfolg. Bei offenem Garagentor startet Karl heute seinen letzten Versuch. Sein Nachbar, mit dem er nicht viel zu tun hat, spaziert gerade an der Garage vorbei. Da er ein begeisterter Hobbymechaniker ist, bietet er Karl spontan seine Hilfe an."
Frage: "Wie fühlt sich Karl?"

Beispiel 3:
"Lucia hat sich im Skiurlaub mit ihrer Familie das Bein gebrochen. Für die vollständige Genesung ist ein Liegegips für 6 Wochen und ein anschließender Gehgips für weitere 3 Wochen vorgesehen. Bei ihrer letzten Kontrolle erfährt Lucia, sie könne den Gehgips bereits früher und eventuell kürzer tragen."
Frage: "Wie fühlt sich Lucia?"

---
**SO SOLL ES NICHT AUSSEHEN (Negativbeispiele - VERMEIDE DIESEN STIL):**

STILISTISCH FALSCH (zu poetisch):
- "Vor der Leinwand sitzt Max, Maler, der versucht, die letzte Linie zu setzen. Der Moment der Blockade..."
- "Die Zeit zog sich wie klebriger Honig..."

INHALTLICH FALSCH (Emotionen werden genannt - DAS IST VERBOTEN!):
- "Max fühlt Frustration und Selbstzweifel..." ❌
- "Sie spürte Ärger, spürte Frustration..." ❌
- "Erleichterung mischte sich mit Müdigkeit." ❌
- "Er war glücklich über das Ergebnis." ❌
- "Schuldgefühle überkamen sie." ❌

Diese Fehler zerstören den Test - der Leser soll die Emotion SELBST erkennen!

---
**AUSGABEFORMAT (JSON):**

Generiere eine einzelne Aufgabe als valides JSON:

{{
{{"geschichte": "Der sachliche Text der Geschichte (55-70 Wörter) basierend auf dem Szenario.",
  "frage": "Wie fühlt sich [Name aus Szenario]?",
  "emotions_kandidaten": [
    "Emotion 1",
    "Emotion 2", 
    "Emotion 3",
    "Emotion 4",
    "Emotion 5"
  ],
  "loesungsweg": {{
    "eher_wahrscheinlich": [
      {{
        "emotion": "Wahrscheinliche Emotion",
        "begruendung": "Kurze psychologische Begründung."
      }}
    ],
    "eher_unwahrscheinlich": [
      {{
        "emotion": "Unwahrscheinliche Emotion",
        "begruendung": "Kurze Begründung warum unwahrscheinlich."
      }}
    ]
  }}
}}

WICHTIG: 
- Alle 5 Emotionen aus emotions_kandidaten müssen in loesungsweg erscheinen (entweder wahrscheinlich oder unwahrscheinlich).
- Die Verteilung muss zur Geschichte passen.
- Verwende KEINE Platzhalter wie [Name] - nutze den konkreten Namen aus dem Szenario.
"""

def call_openai_api(prompt, model, temperature=1):
    """Ruft die OpenAI Chat API auf, mit höherer Temperatur für mehr Kreativität."""
    try:
        response = client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Ein Fehler ist bei der API-Anfrage aufgetreten: {e}")
        return None

def generate_single_task(szenario, task_number, total_tasks, max_retries=3):
    """Generiert eine einzelne Aufgabe - für parallele Verarbeitung, mit Validierung und Retry.
    Verwendet das Szenario direkt (inkl. der darin enthaltenen Namen)."""
    
    for attempt in range(max_retries):
        print(f"-> Generiere Aufgabe {task_number}/{total_tasks} (Versuch {attempt+1})...")
        print(f"   Szenario: '{szenario[:55]}...'")
        
        dynamischer_prompt = PROMPT_AUFGABENSTELLER.format(szenario=szenario)
        aufgabe_json_str = call_openai_api(dynamischer_prompt, MODELL_AUFGABENSTELLER)
        
        if not aufgabe_json_str:
            print(f"   ❌ FEHLER: API-Aufruf fehlgeschlagen. Retry...")
            continue
        
        try:
            aufgabe_dict = json.loads(aufgabe_json_str)
            
            # --- VALIDIERUNG ---
            geschichte = aufgabe_dict.get('geschichte', '')
            frage = aufgabe_dict.get('frage', '')
            
            # Prüfe auf Platzhalter wie [Name], [Hauptfigur], etc.
            if '[' in geschichte or '[' in frage:
                print(f"   ⚠️  Platzhalter gefunden in Text. Retry...")
                continue
            
            # Prüfe ob die Frage "Wie fühlt sich" enthält
            if "Wie fühlt sich" not in frage:
                print(f"   ⚠️  Frage hat falsches Format. Retry...")
                continue
            
            # Prüfe ob verbotene Emotionswörter in der Geschichte vorkommen
            found_emotions = contains_emotion_words(geschichte)
            if found_emotions:
                print(f"   ⚠️  Emotionswörter in Geschichte gefunden: {found_emotions[:3]}... Retry...")
                continue
            
            print(f"   ✓ Aufgabe {task_number} erfolgreich generiert und validiert.")
            return aufgabe_dict
            
        except json.JSONDecodeError:
            print(f"   ❌ FEHLER: Kein valides JSON. Retry...")
            continue
    
    print(f"   ❌ FEHLER: Aufgabe {task_number} nach {max_retries} Versuchen fehlgeschlagen. Überspringe.")
    return None

def generate_tasks_parallel(scenarios, num_tasks, max_workers=5):
    """Generiert Aufgaben parallel mit ThreadPoolExecutor.
    Stellt sicher, dass exakt num_tasks Aufgaben generiert werden,
    indem bei Fehlschlägen weitere Versuche gemacht werden."""
    print(f"🚀 Starte parallele Generierung von {num_tasks} Aufgaben mit {max_workers} Workers...")
    
    finale_aufgaben = []
    max_total_attempts = num_tasks * 3  # Maximal 3x so viele Versuche wie benötigte Aufgaben
    total_attempts = 0
    task_counter = 0  # Zähler für Aufgabennummern
    
    while len(finale_aufgaben) < num_tasks and total_attempts < max_total_attempts:
        # Wie viele Aufgaben fehlen noch?
        noch_benoetigt = num_tasks - len(finale_aufgaben)
        
        # Bereite die Szenarien vor
        szenario_pool = scenarios[:]
        selected_scenarios = []
        
        for i in range(noch_benoetigt):
            if not szenario_pool:
                szenario_pool = scenarios[:]
            
            gewaehltes_szenario = random.choice(szenario_pool)
            szenario_pool.remove(gewaehltes_szenario)
            task_counter += 1
            selected_scenarios.append((gewaehltes_szenario, task_counter, num_tasks))
        
        # Parallele Verarbeitung
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {
                executor.submit(generate_single_task, szenario, task_num, num_tasks): task_num 
                for szenario, task_num, num_tasks in selected_scenarios
            }
            
            for future in as_completed(future_to_task):
                result = future.result()
                if result:
                    finale_aufgaben.append(result)
                total_attempts += 1
        
        if len(finale_aufgaben) < num_tasks:
            print(f"   ⚠ {len(finale_aufgaben)}/{num_tasks} Aufgaben erfolgreich. Generiere {num_tasks - len(finale_aufgaben)} weitere...")
    
    if len(finale_aufgaben) < num_tasks:
        print(f"   ❌ WARNUNG: Nur {len(finale_aufgaben)} von {num_tasks} Aufgaben nach {total_attempts} Versuchen generiert!")
    else:
        print(f"✓ Exakt {len(finale_aufgaben)} von {num_tasks} Aufgaben erfolgreich generiert!")
    
    return finale_aufgaben

def save_tasks_as_json(aufgaben, filename_base):
    """Speichert Aufgaben als JSON-Datei"""
    json_filename = os.path.join("Jsons-Output", f"{filename_base}.json")
    try:
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(aufgaben, f, ensure_ascii=False, indent=2)
        print(f"✓ JSON '{json_filename}' wurde erfolgreich erstellt.")
        return json_filename
    except Exception as e:
        print(f"❌ Fehler beim Speichern der JSON-Datei: {e}")
        return None

def speichere_aufgaben_als_pdf(aufgaben, filename_base):
    """Speichert Aufgaben und Lösungen getrennt, mit ankreuzbarer Antwort-Tabelle."""
    pdf_filename = os.path.join("PDF-Output", f"{filename_base}.pdf")
    
    doc = SimpleDocTemplate(pdf_filename,
                          rightMargin=2*cm, leftMargin=2*cm,
                          topMargin=2*cm, bottomMargin=2*cm)
    
    styles = getSampleStyleSheet()
    style_title = ParagraphStyle(name='Title', parent=styles['h1'], alignment=TA_CENTER, spaceAfter=1*cm)
    style_h1 = ParagraphStyle(name='H1', parent=styles['h2'], spaceBefore=0.5*cm, spaceAfter=0.5*cm)
    style_h2 = ParagraphStyle(name='H2', parent=styles['h3'], spaceBefore=0.4*cm, spaceAfter=0.2*cm)
    style_body = ParagraphStyle(name='Body', parent=styles['Normal'], alignment=TA_LEFT, spaceAfter=0.4*cm)
    story = []

    # --- TEIL 1: Alle Aufgaben generieren ---
    story.append(Paragraph("14 Aufgaben Emotionen Erkennen - 21Min", style_title))
    
    for i, aufgabe_daten in enumerate(aufgaben):
        # Seitenumbruch nach jeder 2. Aufgabe (außer vor der ersten)
        if i > 0 and i % 2 == 0:
            story.append(PageBreak())
        
        story.append(Paragraph(f"Aufgabe {i+1}", style_h1))
        
        story.append(Paragraph(aufgabe_daten.get('geschichte', 'N/A'), style_body))
        story.append(Paragraph(f"<b>{aufgabe_daten.get('frage', 'N/A')}</b>", style_body))

        # --- SCHRITT 2: Tabelle mit echten leeren Checkbox-Feldern ---
        tabellen_daten = [['Emotion', 'Eher wahrscheinlich', 'Eher unwahrscheinlich']]
        for emotion in aufgabe_daten.get('emotions_kandidaten', []):
            # Verwende echte gezeichnete Checkboxen
            tabellen_daten.append([emotion, create_checkbox(), create_checkbox()])
        
        antwort_tabelle = Table(tabellen_daten, colWidths=[6*cm, 4*cm, 4*cm])
        antwort_tabelle.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.black),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        story.append(antwort_tabelle)
        story.append(Spacer(1, 1*cm))

    # --- TEIL 2: Der Lösungsbogen am Ende ---
    story.append(PageBreak())
    story.append(Paragraph("Lösungsbogen", style_title))

    for i, aufgabe_daten in enumerate(aufgaben):
        story.append(Paragraph(f"Lösung zu Aufgabe {i+1}", style_h1))
        loesungsweg = aufgabe_daten.get('loesungsweg', {})
        
        story.append(Paragraph("<u>Eher wahrscheinlich</u>", style_h2))
        for loesung in loesungsweg.get('eher_wahrscheinlich', []):
            story.append(Paragraph(f"<b>{loesung.get('emotion', 'N/A')}:</b> {loesung.get('begruendung', 'N/A')}", style_body))

        story.append(Paragraph("<u>Eher unwahrscheinlich</u>", style_h2))
        for loesung in loesungsweg.get('eher_unwahrscheinlich', []):
            story.append(Paragraph(f"<b>{loesung.get('emotion', 'N/A')}:</b> {loesung.get('begruendung', 'N/A')}", style_body))
        story.append(Spacer(1, 0.5*cm))

    try:
        doc.build(story)
        print(f"✓ PDF '{pdf_filename}' wurde erfolgreich erstellt.")
        return pdf_filename
    except Exception as e:
        print(f"❌ Fehler beim Erstellen der PDF-Datei: {e}")
        return None


def generate_batch_filename(batch_num=None, num_tasks=None):
    """Generiert einen Dateinamen für Batch-Verarbeitung"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if batch_num is not None:
        return f"EE_Set_Batch_{batch_num}_{timestamp}_{num_tasks}tasks"
    else:
        return f"EE_Set_{timestamp}_{num_tasks}tasks"

def main():
    """Hauptfunktion mit Batch-Unterstützung und Command-Line-Argumenten."""
    parser = argparse.ArgumentParser(description='EE (Emotionserkennung) Generator mit Batch-Funktionalität')
    parser.add_argument('--tasks', type=int, default=14, help='Anzahl der Aufgaben pro Set (Standard: 14)')
    parser.add_argument('--batches', type=int, default=1, help='Anzahl der Batches zu generieren (Standard: 1)')
    parser.add_argument('--workers', type=int, default=5, help='Anzahl der parallelen Workers (Standard: 5)')
    parser.add_argument('--temp', type=float, default=1.0, help='Temperatur für API-Aufrufe (Standard: 1.0)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🎯 EE GENERATOR - ERWEITERTE BATCH-VERSION")
    print("=" * 60)
    print(f"📋 Konfiguration:")
    print(f"   • Aufgaben pro Set: {args.tasks}")
    print(f"   • Anzahl Batches: {args.batches}")
    print(f"   • Parallele Workers: {args.workers}")
    print(f"   • Temperatur: {args.temp}")
    print("=" * 60)
    
    # Stelle sicher, dass Output-Ordner existieren
    ensure_output_folders()
    
    # Lade Szenarien aus der Datei
    scenarios = load_scenarios_from_file()
    if not scenarios:
        print("❌ Keine Szenarien gefunden. Beende Programm.")
        return
    
    print(f"📚 {len(scenarios)} Szenarien verfügbar für Generierung\n")
    
    # Generiere Batches
    for batch_num in range(1, args.batches + 1):
        print(f"🚀 STARTE BATCH {batch_num}/{args.batches}")
        print("-" * 50)
        
        # Generiere Aufgaben parallel
        finale_aufgaben = generate_tasks_parallel(scenarios, args.tasks, args.workers)
        
        if not finale_aufgaben:
            print(f"❌ Keine Aufgaben für Batch {batch_num} generiert. Überspringe.")
            continue
        
        # Prüfe ob exakt die gewünschte Anzahl erreicht wurde
        if len(finale_aufgaben) < args.tasks:
            print(f"❌ Nur {len(finale_aufgaben)} von {args.tasks} Aufgaben generiert. Batch {batch_num} wird übersprungen.")
            print(f"   (PDF wird nur bei exakt {args.tasks} Aufgaben erstellt)")
            continue
        
        # Erstelle Dateiname
        filename_base = generate_batch_filename(batch_num, len(finale_aufgaben))
        
        # Speichere als JSON und PDF
        print(f"\n💾 Speichere Batch {batch_num}...")
        json_file = save_tasks_as_json(finale_aufgaben, filename_base)
        pdf_file = speichere_aufgaben_als_pdf(finale_aufgaben, filename_base)
        
        if json_file and pdf_file:
            print(f"✅ Batch {batch_num} erfolgreich erstellt!")
        else:
            print(f"⚠️  Batch {batch_num} teilweise erstellt.")
        
        print("-" * 50)
        print()
    
    print("🎉 ALLE BATCHES ABGESCHLOSSEN!")
    print("=" * 60)

if __name__ == "__main__":
    main()