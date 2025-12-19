#!/usr/bin/env python3
"""
MedAT Soziales Entscheiden Generator
Generiert automatisch Testsimulationen für den MedAT-Untertest "Soziales Entscheiden"
mit OpenAI API und erstellt PDF-Dokumente im MedAT-Format.
"""

import json
import random
import os
from datetime import datetime
from typing import Dict, List, Tuple
import openai
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, Rect
import logging
import re
from html import escape
import concurrent.futures

# Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MedATSEGenerator:
    """Generator für MedAT Soziales Entscheiden Aufgaben"""
    
    def __init__(self, api_key: str = None):
        """
        Initialisiert den MedAT SE Generator
        
        Args:
            api_key: OpenAI API Key. Wenn None, wird aus Umgebungsvariable gelesen.
        """
        # OpenAI API Setup
        if api_key:
            openai.api_key = api_key
        else:
            openai.api_key = os.getenv("OPENAI_API_KEY")
            if not openai.api_key:
                raise ValueError("OpenAI API Key nicht gefunden. Setze OPENAI_API_KEY Umgebungsvariable oder übergebe als Parameter.")
        
        # Create OpenAI client
        self.client = openai.OpenAI(api_key=openai.api_key)
        
        # Pfade
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.themes_file = os.path.join(self.base_dir, "themen.txt")
        self.output_dir = os.path.join(self.base_dir, "output")
        
        # Output-Verzeichnis erstellen falls nicht vorhanden
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Themes laden
        self.themes = self._load_themes()
        
        logger.info(f"MedAT SE Generator initialisiert. {len(self.themes)} Themen geladen.")
    
    def _clean_text_for_pdf(self, text: str) -> str:
        """Bereinigt Text für PDF-Generierung - ultra-sichere Version für ReportLab"""
        if not text:
            return ""
        
        # Entferne alle potentiell problematischen Zeichen für ReportLab
        # Erlaube nur Buchstaben, Zahlen, grundlegende Interpunktion und deutsche Umlaute
        text = re.sub(r'[^\w\säöüÄÖÜß.,!?\(\):;\-\s]', ' ', text)
        
        # Entferne mehrfache Leerzeichen
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    def _load_themes(self) -> List[str]:
        """Lädt Themen aus themen.txt"""
        try:
            with open(self.themes_file, 'r', encoding='utf-8') as f:
                themes = [line.strip() for line in f if line.strip()]
            logger.info(f"{len(themes)} Themen aus {self.themes_file} geladen")
            return themes
        except FileNotFoundError:
            logger.error(f"Themen-Datei nicht gefunden: {self.themes_file}")
            raise
        except Exception as e:
            logger.error(f"Fehler beim Laden der Themen: {e}")
            raise
    
    def _create_prompt(self, theme: str) -> str:
        """
        Erstellt einen strukturierten Prompt für die OpenAI API
        
        Args:
            theme: Das ethische Dilemma/Thema für die Aufgabe
        
        Returns:
            Formatierter Prompt-String
        """
        prompt = f"""
Du bist ein Experte für medizinische Ethik und erstellst Aufgaben für den MedAT-Untertest "Soziales Entscheiden". 

Erstelle eine Übungsaufgabe basierend auf folgendem ethischen Dilemma:

THEMA: {theme}

**WICHTIGE FORMATIERUNGSREGELN:**

1. **NAME AUS THEMA ÜBERNEHMEN:** Das Thema enthält bereits einen Namen. 
   Verwende EXAKT diesen Namen für das Szenario! Das Szenario MUSS mit diesem Namen beginnen.
   NIEMALS mit "Du", "Eine", "Ihr", "Ein/e" oder ähnlichem beginnen!

2. **SZENARIO-ENDE:** Das Szenario MUSS mit folgendem Satz enden (ersetze [Name] durch den Namen aus dem Thema):
   "Wie relevant sollten Ihrer Meinung nach die folgenden Überlegungen, die [Name] bei dieser Entscheidung angestellt haben könnte, sein?"

3. **ANTWORTMÖGLICHKEITEN:** Jede Antwortmöglichkeit MUSS als Frage formuliert sein und mit einem dieser Wörter beginnen:
   - "Würde..." / "Würden..."
   - "Hätte..."
   - "Sollte..." / "Sollten..."
   - "Müsste..." / "Müssten..."
   - "Wäre..." / "Wären..."
   - "Werde..."
   - "Bin..."
   - "Wenn..."
   - "Wie..."
   Die Antworten sollen maximal 25 Wörter haben.

4. **KOHLBERG-STUFEN:** Fünf Handlungsoptionen (A-E), die die 5 Kohlberg-Stufen repräsentieren:
   - Stufe 1: Anwendung eines allgemeinen Leitprinzips
   - Stufe 2: Bezug auf ein Leitprinzip/Norm
   - Stufe 3: Was würden andere tun/erwarten
   - Stufe 4: Vorteil für mich selbst
   - Stufe 5: Nachteil für mich selbst
   Die Begriffe "Leitprinzip", "Vorteil", "Nachteil" dürfen NICHT im Text vorkommen.
   WICHTIG: Im JSON muss "kohlberg" NUR Zahlen 1-5 enthalten (keine Strings wie "Stufe 1")!

5. **LÄNGE:** Der Aufgabentext (ohne die Abschlussfrage) soll ca. 60-80 Wörter lang sein.

6. **FORMAT:** Gib ausschließlich das JSON aus. Keine Einleitung, keine Zwischenüberschriften, keine Erklärungen.

**BEISPIELE für korrekte Aufgaben:**

Beispiel 1 (Thema: "Barbara beobachtet, wie ein Vorgesetzter..."):
"Barbara arbeitet in einem Büro und beobachtet, wie ein Vorgesetzter einer Arbeitskollegin auf den Hintern fasst, ohne dass diese sich wehrt. Barbara weiß nichts über eine etwaige gemeinsame Beziehung der beiden. Sie steht vor der Wahl, ihre Beobachtung der Kollegin mitzuteilen oder die Situation zu ignorieren.

Wie relevant sollten Ihrer Meinung nach die folgenden Überlegungen, die Barbara bei dieser Entscheidung angestellt haben könnte, sein?"

A: "Wäre es nicht meine Pflicht, Fehlverhalten und Machtmissbrauch aufzudecken?"
B: "Wie würde ich mich fühlen, wenn mich meine Kollegin auf einen solchen Vorfall ansprechen würde?"
C: "Würde ich den Vorgesetzten gegen mich aufbringen, wenn ich ihn durch das Aufdecken in eine unangenehme Situation bringe?"
D: "Würde sich das Arbeitsverhältnis zwischen mir und der Kollegin verbessern, wenn ich sie auf den Vorfall anspreche?"
E: "Sollte ich nicht meine Kollegin darauf ansprechen, weil es wichtig ist, dass sich Kollegen untereinander helfen?"

Beispiel 2 (Thema: "Philipp ist LKW-Fahrer und bemerkt..."):
"Philipp ist von Beruf LKW-Fahrer. Er hat heute eine lange Strecke vor sich und leider nicht viel Schlaf bekommen. Während der Fahrt bemerkt er, dass er immer müder wird und ihm fast die Augen zufallen. Er weiß um das Risiko, das Müdigkeit birgt. Wenn er nicht weiterfährt, wird er für die Strecke auch nicht bezahlt. Philipp ist nun unsicher, ob er versuchen soll weiterzufahren oder nicht.

Wie relevant sollten Ihrer Meinung nach die folgenden Überlegungen, die Philipp bei dieser Entscheidung angestellt haben könnte, sein?"

A: "Wäre es nicht besser weiterzufahren, weil ich dann die Bezahlung für diese Strecke auch bekomme?"
B: "Wäre mein Vorgesetzter wütend, wenn er einen Ersatz für mich suchen müsste?"
C: "Wäre es nicht generell richtig, auf meinen Körper zu hören?"
D: "Müsste ich mich nicht ausruhen, weil es wichtig ist, mich und meine Mitmenschen keinem Risiko auszusetzen?"
E: "Würde mein Vorgesetzter es verstehen, wenn ich stehen bleibe, um kurz zu regenerieren?"

Antworte ausschließlich im folgenden JSON-Format:

{{{{
    "aufgabenstellung": "Das komplette Szenario MIT der Abschlussfrage 'Wie relevant sollten Ihrer Meinung nach...'",
    "antwortmöglichkeiten": {{{{
        "A": "Erste Antwortmöglichkeit (Frage mit Würde/Hätte/Sollte/etc.)",
        "B": "Zweite Antwortmöglichkeit", 
        "C": "Dritte Antwortmöglichkeit",
        "D": "Vierte Antwortmöglichkeit",
        "E": "Fünfte Antwortmöglichkeit"
    }}}},
    "lösung": "A<B<C<D<E",
    "kohlberg": {{{{
      "A": 1,
      "B": 2,
      "C": 3,
      "D": 4,
      "E": 5
    }}}}
}}}}

WICHTIG für kohlberg: Nur Zahlen 1-5 verwenden, KEINE Strings wie "Stufe 1" oder "1"!

Stelle sicher, dass die Aufgabe anspruchsvoll aber lösbar ist und verschiedene ethische Perspektiven berücksichtigt.
"""
        return prompt.strip()
    
    def generate_task(self, theme: str = None) -> Dict:
        """
        Generiert eine einzelne SE-Aufgabe mit OpenAI API
        
        Args:
            theme: Spezifisches Thema. Wenn None, wird zufällig ausgewählt.
        
        Returns:
            Dictionary mit der generierten Aufgabe
        """
        if theme is None:
            theme = random.choice(self.themes)
        
        prompt = self._create_prompt(theme)
        
        try:
            logger.info(f"Generiere Aufgabe für Thema: {theme}")
            
            response = self.client.chat.completions.create(
                model="gpt-5-nano-2025-08-07",  # Hinweis: modell NIEMALS ändern ES EXISTIERT
                messages=[
                    {"role": "system", "content": "Du bist ein Experte für medizinische Ethik und MedAT-Aufgaben. Antworte ausschließlich im angeforderten JSON-Format."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            # Response parsen
            content = response.choices[0].message.content.strip()
            
            if not content:
                raise ValueError("OpenAI Response ist leer")
            
            # Versuche JSON zu extrahieren falls es von Text umgeben ist
            if not content.startswith('{'):
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    content = json_match.group()
            
            task_data = json.loads(content)

            
            # Kohlberg-Werte normalisieren (zu Integer)
            if 'kohlberg' in task_data:
                for key in task_data['kohlberg']:
                    val = task_data['kohlberg'][key]
                    if isinstance(val, str):
                        # Extrahiere Zahl aus Strings wie "Stufe 1", "1", etc.
                        import re as re_inner
                        match = re_inner.search(r'(\d+)', str(val))
                        if match:
                            task_data['kohlberg'][key] = int(match.group(1))
                        else:
                            task_data['kohlberg'][key] = val
                    elif isinstance(val, (int, float)):
                        task_data['kohlberg'][key] = int(val)
            
            # Validierung
            required_keys = ["aufgabenstellung", "antwortmöglichkeiten", "lösung", "kohlberg"]
            if not all(key in task_data for key in required_keys):
                raise ValueError(f"Unvollständige Antwort von OpenAI. Fehlende Keys: {set(required_keys) - set(task_data.keys())}")

            # Antworten zufällig anordnen und Lösung/Kohlberg remappen
            try:
                orig_letters = [k for k in task_data['antwortmöglichkeiten'].keys() if k in ['A', 'B', 'C', 'D', 'E']]
                items = [
                    {
                        'orig': L,
                        'text': task_data['antwortmöglichkeiten'][L],
                        'kohlberg': task_data['kohlberg'].get(L)
                    }
                    for L in orig_letters
                ]
                if len(items) == 5:
                    random.shuffle(items)
                    new_letters = ['A', 'B', 'C', 'D', 'E']
                    new_ans = {}
                    new_kohl = {}
                    orig_to_new = {}
                    for newL, item in zip(new_letters, items):
                        new_ans[newL] = item['text']
                        new_kohl[newL] = item['kohlberg']
                        orig_to_new[item['orig']] = newL
                    # Lösung remappen (z.B. "A<B<C<D<E")
                    sol = str(task_data.get('lösung', ''))
                    letters_in_sol = re.findall(r'[A-E]', sol)
                    if letters_in_sol:
                        mapped = [orig_to_new.get(s, s) for s in letters_in_sol]
                        new_solution = "<".join(mapped)
                    else:
                        new_solution = sol
                    task_data['antwortmöglichkeiten'] = new_ans
                    task_data['kohlberg'] = new_kohl
                    task_data['lösung'] = new_solution
            except Exception as mix_err:
                logger.warning(f"Antworten nicht gemischt (Fallback auf Originalreihenfolge): {mix_err}")
            
            # Zusätzliche Metadaten hinzufügen
            task_data["thema"] = theme
            task_data["generiert_am"] = datetime.now().isoformat()
            
            logger.info("Aufgabe erfolgreich generiert")
            return task_data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON Parse Fehler: {e}")
            logger.error(f"OpenAI Response: {content}")
            raise
        except Exception as e:
            logger.error(f"Fehler bei OpenAI API Aufruf: {e}")
            raise
    
    def generate_multiple_tasks(self, count: int) -> List[Dict]:
        """
        Generiert mehrere SE-Aufgaben
        
        Args:
            count: Anzahl der zu generierenden Aufgaben
        
        Returns:
            Liste mit generierten Aufgaben
        """
        # Themen vorbereiten, ohne Wiederholung (falls möglich)
        used_themes: List[str] = []
        themes_to_use: List[str] = []
        for _ in range(count):
            available = [t for t in self.themes if t not in used_themes] or self.themes
            t = random.choice(available)
            themes_to_use.append(t)
            used_themes.append(t)
            if len(used_themes) >= len(self.themes):
                used_themes = []

        # Parallel generieren mit stabiler Reihenfolge der Ergebnisse
        results: List[Dict] = [None] * len(themes_to_use)
        max_workers = min(8, max(1, count))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {executor.submit(self.generate_task, theme=t): idx for idx, t in enumerate(themes_to_use)}
            for future in concurrent.futures.as_completed(future_map):
                idx = future_map[future]
                try:
                    results[idx] = future.result()
                    logger.info(f"Aufgabe {idx+1}/{count} erfolgreich generiert")
                except Exception as e:
                    logger.warning(f"Fehler bei Generierung von Aufgabe {idx+1}: {e}")

        tasks = [r for r in results if r is not None]
        logger.info(f"{len(tasks)} von {count} Aufgaben erfolgreich generiert")
        return tasks
    
    def _get_pdf_styles(self):
        """Erstellt Styles für PDF-Generation im MedAT-Format"""
        styles = getSampleStyleSheet()
        
        # Title Style
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=16,
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        # Header Style
        header_style = ParagraphStyle(
            'CustomHeader',
            parent=styles['Heading2'],
            fontSize=12,
            # reduce vertical gap after header so the question sits closer to the heading
            spaceAfter=4,
            fontName='Helvetica-Bold'
        )
        
        # Question Style
        question_style = ParagraphStyle(
            'QuestionStyle',
            parent=styles['Normal'],
            fontSize=11,
            # tighten spacing after the question to conserve vertical space
            spaceAfter=8,
            alignment=TA_JUSTIFY,
            fontName='Helvetica'
        )
        
        # Answer Style (nur normaler Fließtext)
        answer_style = ParagraphStyle(
            'AnswerStyle',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            leftIndent=0,
            fontName='Helvetica'
        )
        
        # Solution Style
        solution_style = ParagraphStyle(
            'SolutionStyle',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=8,
            fontName='Helvetica-Bold'
        )
        
        return {
            'title': title_style,
            'header': header_style,
            'question': question_style,
            'answer': answer_style,
            'solution': solution_style,
            'normal': styles['Normal']
        }

    def _make_checkbox(self, size: int = 24) -> Drawing:
        """Erzeugt ein leeres Kästchen als Drawing-Objekt für Tabellennutzung."""
        d = Drawing(width=size, height=size)
        # Dünner Rahmen, leeres Rechteck
        d.add(Rect(0, 0, size, size, strokeColor=colors.black, fillColor=None, strokeWidth=1.5))
        return d
    
    def create_pdf(self, tasks: List[Dict], filename: str = None) -> str:
        """
        Erstellt PDF-Dokument mit den generierten Aufgaben
        
        Args:
            tasks: Liste der generierten Aufgaben
            filename: Optional - Dateiname. Wenn None, wird automatisch generiert.
        
        Returns:
            Pfad zur erstellten PDF-Datei
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"MedAT_SE_Simulation_{timestamp}_{len(tasks)}tasks.pdf"
        
        filepath = os.path.join(self.output_dir, filename)
        
        # PDF Document erstellen
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Styles laden
        styles = self._get_pdf_styles()
        
        # Story (Inhalt) aufbauen
        story = []
        
        # Title Page
        story.append(Paragraph("MedAT Testsimulation", styles['title']))
        story.append(Paragraph("Soziales Entscheiden", styles['title']))
        story.append(Spacer(1, 0.3*inch))
        
        # Hinweis / Einleitung
        story.append(Spacer(1, 0.2*inch))
        
        # Anweisungen
        instructions = """
    Anweisungen:
    Lesen Sie jede Aufgabe sorgfältig durch und reihen Sie die Antwortmöglichkeiten (A–E) gedanklich in der richtigen Reihenfolge.
    Berücksichtigen Sie ethische Prinzipien und die Kohlberg'sche Theorie der moralischen Entwicklung.
    Markieren Sie Ihre Auswahl pro Aufgabe in der Tabelle direkt neben den Antwortmöglichkeiten.
        """
        story.append(Paragraph(instructions, styles['normal']))
        story.append(PageBreak())
        
        # Aufgaben
        for i, task in enumerate(tasks, 1):
            # Aufgabennummer
            story.append(Paragraph(f"Aufgabe {i}", styles['header']))
            
            # Aufgabenstellung
            aufgabenstellung = self._clean_text_for_pdf(task['aufgabenstellung'])
            story.append(Paragraph(aufgabenstellung, styles['question']))
            
            # Antwortmöglichkeiten als Tabelle mit: [Kästchen] [Buchstabe] [Antworttext]
            table_rows = []
            box_size = 24
            for letter in ['A', 'B', 'C', 'D', 'E']:
                checkbox = self._make_checkbox(box_size)
                letter_text = self._clean_text_for_pdf(letter)
                answer_text = self._clean_text_for_pdf(task['antwortmöglichkeiten'][letter])
                table_rows.append([checkbox, letter_text, Paragraph(answer_text, styles['answer'])])

            # Spaltenbreiten: kleines Kästchen, Buchstabe, Rest Textbreite
            available_width = A4[0] - (doc.leftMargin + doc.rightMargin)
            col_widths = [box_size + 2, 18, max(100, available_width - (box_size + 2 + 18))]
            answers_table = Table(table_rows, colWidths=col_widths, hAlign='LEFT')
            answers_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 2),
                ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                # Etwas mehr Abstand rechts neben dem Kästchen
                ('RIGHTPADDING', (0, 0), (0, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
                ('LINEBELOW', (0, 0), (-1, 0), 0.25, colors.lightgrey),
                ('LINEBELOW', (0, 1), (-1, 1), 0.25, colors.lightgrey),
                ('LINEBELOW', (0, 2), (-1, 2), 0.25, colors.lightgrey),
                ('LINEBELOW', (0, 3), (-1, 3), 0.25, colors.lightgrey),
                ('LINEBELOW', (0, 4), (-1, 4), 0.25, colors.lightgrey),
            ]))
            story.append(answers_table)
            
            story.append(Spacer(1, 0.3*inch))
            
            # Seitenumbruch nach jeder 2. Aufgabe (außer bei der letzten)
            if i % 2 == 0 and i < len(tasks):
                story.append(PageBreak())
        
        # Lösungsseite
        story.append(PageBreak())
        story.append(Paragraph("Lösungen", styles['title']))
        story.append(Spacer(1, 0.3*inch))
        
        for i, task in enumerate(tasks, 1):
            clean_solution = self._clean_text_for_pdf(str(task['lösung']))
            solution_text = f"Aufgabe {i}: {clean_solution}"
            story.append(Paragraph(solution_text, styles['solution']))
            
            # Kohlberg-Einordnung
            clean_kohlberg = self._clean_text_for_pdf(str(task['kohlberg']))
            kohlberg_text = f"Kohlberg-Einordnung: {clean_kohlberg}"
            story.append(Paragraph(kohlberg_text, styles['normal']))
            story.append(Spacer(1, 0.1*inch))
        
        # PDF bauen
        try:
            doc.build(story)
            logger.info(f"PDF erfolgreich erstellt: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Fehler bei PDF-Erstellung: {e}")
            raise
    
    def save_tasks_json(self, tasks: List[Dict], filename: str = None) -> str:
        """
        Speichert Aufgaben als JSON-Datei
        
        Args:
            tasks: Liste der Aufgaben
            filename: Optional - Dateiname
            
        Returns:
            Pfad zur JSON-Datei
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"MedAT_SE_Tasks_{timestamp}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(tasks, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Tasks als JSON gespeichert: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Fehler beim Speichern der JSON-Datei: {e}")
            raise

        
def main():
    """Hauptfunktion für Kommandozeilen-Benutzung"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MedAT Soziales Entscheiden Generator")
    parser.add_argument("--count", "-c", type=int, default=14, help="Anzahl der zu generierenden Aufgaben (Standard: 5)")
    parser.add_argument("--api-key", help="OpenAI API Key (optional, falls nicht als Umgebungsvariable gesetzt)")
    parser.add_argument("--output", "-o", help="Output-Dateiname (ohne Erweiterung)")
    parser.add_argument("--json-only", action="store_true", help="Nur JSON speichern, kein PDF")
    parser.add_argument("--batch", type=int, default=1, help="Anzahl der unabhängigen Sets (Batches), Standard: 1")
    
    args = parser.parse_args()
    
    try:
        # Generator initialisieren
        generator = MedATSEGenerator(api_key=args.api_key)
        
        # Sets generieren (Batch)
        total_sets = max(1, int(args.batch))
        for set_idx in range(1, total_sets + 1):
            print(f"Generiere Set {set_idx}/{total_sets}: {args.count} Aufgaben...")
            tasks = generator.generate_multiple_tasks(args.count)

            # eindeutige Namen
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            if args.output:
                json_name = f"{args.output}_tasks_set{set_idx}_{ts}.json"
                pdf_name = f"{args.output}_set{set_idx}_{ts}.pdf"
            else:
                json_name = f"MedAT_SE_Tasks_{ts}_set{set_idx}.json"
                pdf_name = f"MedAT_SE_Simulation_{ts}_set{set_idx}_{len(tasks)}tasks.pdf"

            # JSON speichern
            json_file = generator.save_tasks_json(tasks, json_name)
            print(f"Tasks gespeichert: {json_file}")

            # PDF erstellen (falls nicht --json-only)
            if not args.json_only:
                pdf_file = generator.create_pdf(tasks, pdf_name)
                print(f"PDF erstellt: {pdf_file}")

        print("Fertig!")
        return 0
        
    except Exception as e:
        print(f"Fehler: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
