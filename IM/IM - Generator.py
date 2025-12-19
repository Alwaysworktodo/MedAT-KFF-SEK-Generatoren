import random
import json
import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def load_words_from_file(filename="words.txt"):
    """
    Liest Wörter aus einer Textdatei ein und gibt eine Liste zurück.
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            words = [line.strip() for line in f if line.strip()]
        if not words:
            print(f"FEHLER: Die Datei '{filename}' ist leer.")
            return []
        print(f"Erfolgreich {len(words)} Wörter aus '{filename}' geladen.")
        return words
    except FileNotFoundError:
        print(f"FEHLER: Die Datei '{filename}' wurde nicht gefunden.")
        return []
    except Exception as e:
        print(f"Ein unerwarteter Fehler ist beim Lesen der Datei aufgetreten: {e}")
        return []

class SyllogismGenerator:
    """
    Generiert Multiple-Choice-Fragen für den MedAT-Untertest "Implikationen erkennen".
    Die Logik dieser Klasse ist final und korrekt.
    """
    DEFAULT_NOUN_POOL = ["Theorien", "Algorithmen", "Kristalle", "Melodien", "Strukturen"]
    VALID_FORMS = {
        "AAA-1 (Barbara)": {"major": ('A', 'M', 'P'), "minor": ('A', 'S', 'M'), "conclusion": ('A', 'S', 'P')}, "EAE-1 (Celarent)": {"major": ('E', 'M', 'P'), "minor": ('A', 'S', 'M'), "conclusion": ('E', 'S', 'P')}, "AII-1 (Darii)": {"major": ('A', 'M', 'P'), "minor": ('I', 'S', 'M'), "conclusion": ('I', 'S', 'P')}, "EIO-1 (Ferio)": {"major": ('E', 'M', 'P'), "minor": ('I', 'S', 'M'), "conclusion": ('O', 'S', 'P')}, "EAE-2 (Cesare)": {"major": ('E', 'P', 'M'), "minor": ('A', 'S', 'M'), "conclusion": ('E', 'S', 'P')}, "AEE-2 (Camestres)": {"major": ('A', 'P', 'M'), "minor": ('E', 'S', 'M'), "conclusion": ('E', 'S', 'P')}, "EIO-2 (Festino)": {"major": ('E', 'P', 'M'), "minor": ('I', 'S', 'M'), "conclusion": ('O', 'S', 'P')}, "AOO-2 (Baroco)": {"major": ('A', 'P', 'M'), "minor": ('O', 'S', 'M'), "conclusion": ('O', 'S', 'P')}, "AAI-3 (Darapti)": {"major": ('A', 'M', 'P'), "minor": ('A', 'M', 'S'), "conclusion": ('I', 'S', 'P')}, "IAI-3 (Disamis)": {"major": ('I', 'M', 'P'), "minor": ('A', 'M', 'S'), "conclusion": ('I', 'S', 'P')}, "AII-3 (Datisi)": {"major": ('A', 'M', 'P'), "minor": ('I', 'M', 'S'), "conclusion": ('I', 'S', 'P')}, "EAO-3 (Felapton)": {"major": ('E', 'M', 'P'), "minor": ('A', 'M', 'S'), "conclusion": ('O', 'S', 'P')}, "OAO-3 (Bocardo)": {"major": ('O', 'M', 'P'), "minor": ('A', 'M', 'S'), "conclusion": ('O', 'S', 'P')}, "EIO-3 (Ferison)": {"major": ('E', 'M', 'P'), "minor": ('I', 'M', 'S'), "conclusion": ('O', 'S', 'P')}, "AAI-4 (Bamalip)": {"major": ('A', 'P', 'M'), "minor": ('A', 'M', 'S'), "conclusion": ('I', 'S', 'P')}, "AEE-4 (Calemes)": {"major": ('A', 'P', 'M'), "minor": ('E', 'M', 'S'), "conclusion": ('E', 'S', 'P')}, "IAI-4 (Dimatis)": {"major": ('I', 'P', 'M'), "minor": ('A', 'M', 'S'), "conclusion": ('I', 'S', 'P')}, "EAO-4 (Fesapo)": {"major": ('E', 'P', 'M'), "minor": ('A', 'M', 'S'), "conclusion": ('O', 'S', 'P')}, "EIO-4 (Fresison)": {"major": ('E', 'P', 'M'), "minor": ('I', 'M', 'S'), "conclusion": ('O', 'S', 'P')}, "AAI-1 (Barbari)": {"major": ('A', 'M', 'P'), "minor": ('A', 'S', 'M'), "conclusion": ('I', 'S', 'P')}, "EAO-1 (Celaront)": {"major": ('E', 'M', 'P'), "minor": ('A', 'S', 'M'), "conclusion": ('O', 'S', 'P')}, "AEO-2 (Cesaro)": {"major": ('E', 'P', 'M'), "minor": ('A', 'S', 'M'), "conclusion": ('O', 'S', 'P')}, "AEO-2 (Camestrop)": {"major": ('A', 'P', 'M'), "minor": ('E', 'S', 'M'), "conclusion": ('O', 'S', 'P')}, "EAO-4 (Calemop)": {"major": ('A', 'P', 'M'), "minor": ('E', 'M', 'S'), "conclusion": ('O', 'S', 'P')}
    }
    def __init__(self, noun_pool=None):
        self.noun_pool = noun_pool if noun_pool else self.DEFAULT_NOUN_POOL
        if len(self.noun_pool) < 3: raise ValueError("Wort-Pool muss mind. 3 Begriffe enthalten.")
    def _format_statement(self, s_type, subj, pred):
        return {'A': f"Alle {subj} sind {pred}.", 'E': f"Keine {subj} sind {pred}.", 'I': f"Einige {subj} sind {pred}.", 'O': f"Einige {subj} sind nicht {pred}."}[s_type]
    def _get_canonical_form(self, s_type, subj, pred):
        if s_type in ['E', 'I']: return (s_type, tuple(sorted((subj, pred))))
        return (s_type, (subj, pred))
    def _generate_distractors(self, form, terms):
        distractors, generated_forms, S, P, M = [], set(), terms['S'], terms['P'], terms['M']
        correct_conclusion = form['conclusion']
        generated_forms.add(self._get_canonical_form(correct_conclusion[0], terms[correct_conclusion[1]], terms[correct_conclusion[2]]))
        premise1_str = self._format_statement(form['major'][0], terms[form['major'][1]], terms[form['major'][2]])
        premise2_str = self._format_statement(form['minor'][0], terms[form['minor'][1]], terms[form['minor'][2]])
        potential_distractor_templates = []
        for s_type in ['A', 'E', 'I', 'O']:
            for t1 in [S, P, M]:
                for t2 in [S, P, M]:
                    if t1 != t2: potential_distractor_templates.append((s_type, t1, t2))
        random.shuffle(potential_distractor_templates)
        while len(distractors) < 3 and potential_distractor_templates:
            s_type, subj, pred = potential_distractor_templates.pop()
            distractor_str = self._format_statement(s_type, subj, pred)
            if distractor_str in [premise1_str, premise2_str]: continue
            if self._get_canonical_form(s_type, subj, pred) in generated_forms: continue
            distractors.append(distractor_str)
            generated_forms.add(self._get_canonical_form(s_type, subj, pred))
        return distractors
    def generate_question(self, question_id=1):
        form_name, form_structure = random.choice(list(self.VALID_FORMS.items()))
        s_term, p_term, m_term = random.sample(self.noun_pool, 3)
        term_map = {"S": s_term, "P": p_term, "M": m_term}
        major_premise = self._format_statement(form_structure['major'][0], term_map[form_structure['major'][1]], term_map[form_structure['major'][2]])
        minor_premise = self._format_statement(form_structure['minor'][0], term_map[form_structure['minor'][1]], term_map[form_structure['minor'][2]])
        correct_conclusion = self._format_statement(form_structure['conclusion'][0], term_map[form_structure['conclusion'][1]], term_map[form_structure['conclusion'][2]])
        distractors = self._generate_distractors(form_structure, term_map)
        options = [correct_conclusion] + distractors
        random.shuffle(options)
        answer_choices = {chr(65 + i): option for i, option in enumerate(options)}
        answer_choices['E'] = "Keine der Schlussfolgerungen ist richtig."
        correct_key = [key for key, value in answer_choices.items() if value == correct_conclusion][0]
        return {"frage_id": question_id, "praemissen": [major_premise, minor_premise], "antwortmoeglichkeiten": answer_choices, "korrekte_antwort": correct_key}

def generate_questions(num_questions=1, noun_pool=None):
    generator = SyllogismGenerator(noun_pool=noun_pool)
    return [generator.generate_question(i + 1) for i in range(num_questions)]

def create_pdf_from_questions(questions, filename="medat_aufgaben.pdf"):
    """
    Erstellt eine PDF-Datei und stellt sicher, dass eine moderne Schriftart
    verwendet wird, die alle Symbole (wie ☐) korrekt darstellt.
    """
    # Prefer DejaVuSans if available in repo (good unicode support), fallback to Verdana or Helvetica
    FONT_NAME = 'Helvetica'
    try:
        pdfmetrics.registerFont(TTFont('DejaVuSans', 'EE/DejaVuSans.ttf'))
        pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', 'EE/DejaVuSans.ttf'))
        pdfmetrics.registerFontFamily('DejaVuSans', normal='DejaVuSans', bold='DejaVuSans-Bold')
        FONT_NAME = 'DejaVuSans'
    except Exception:
        try:
            pdfmetrics.registerFont(TTFont('Verdana', 'Verdana.ttf'))
            pdfmetrics.registerFont(TTFont('Verdana-Bold', 'Verdanab.ttf'))
            pdfmetrics.registerFontFamily('Verdana', normal='Verdana', bold='Verdana-Bold')
            FONT_NAME = 'Verdana'
        except Exception:
            print("WARNUNG: Keine der bevorzugten Schriftarten gefunden. Verwende 'Helvetica' als Fallback.")
            FONT_NAME = 'Helvetica'
    
    # Reduce margins for a more compact layout
    doc = SimpleDocTemplate(filename, topMargin=1.2*cm, bottomMargin=1.2*cm, leftMargin=1.6*cm, rightMargin=1.6*cm)
    styles = getSampleStyleSheet()

    # Set consistent font and sizes/leading to better match the reference PDF
    for key in ['Normal', 'h1', 'h2', 'h3']:
        if key in styles:
            styles[key].fontName = FONT_NAME

    # Adjust sizes and leading (line spacing) to be slightly smaller for denser layout
    styles['h1'].fontSize = 16
    styles['h1'].leading = 20
    styles['h2'].fontSize = 13
    styles['h2'].leading = 16
    styles['h3'].fontSize = 12
    styles['h3'].leading = 14
    styles['Normal'].fontSize = 10
    styles['Normal'].leading = 12

    # Custom styles for questions/premises
    # Increase font size for examples and answer options a bit
    styles.add(styles['Normal'].clone('QuestionStyle', leftIndent=0.6*cm, spaceAfter=4, leading=13))
    # Premises will be placed inline (no bullet) to save vertical space
    styles.add(styles['Normal'].clone('PremiseStyle', leftIndent=0.6*cm, spaceBefore=2, spaceAfter=2, leading=13))
    
    story = []
    story.append(Paragraph("MedAT - KFF", styles['h1']))
    story.append(Paragraph("Untertest: Implikationen erkennen - 10 min", styles['h2']))
    story.append(Spacer(1, 0.8*cm))

    for q in questions:
        # Compact question block: title, premises each on their own line, then answer choices with reduced spacing
        question_block = [Paragraph(f"<b>Aufgabe {q['frage_id']}</b>", styles['h3'])]
        question_block.append(Spacer(1, 0.05*cm))
        for premise in q['praemissen']:
            question_block.append(Paragraph(premise, styles['PremiseStyle']))
        question_block.append(Spacer(1, 0.12*cm))
        for key in sorted(q['antwortmoeglichkeiten'].keys()):
            question_block.append(Paragraph(f"<b>{key})</b> {q['antwortmoeglichkeiten'][key]}", styles['QuestionStyle']))
        story.append(KeepTogether(question_block))
        story.append(Spacer(1, 0.4*cm))

    story.append(PageBreak())

    # Replace table-based Antwortbogen with a drawing-based AnswerSheet matching FZ layout
    from reportlab.platypus import Flowable

    class AnswerSheet(Flowable):
        """Draw an answer sheet like the FZ generator: centered title and one column with each question and five small boxes A-E."""
        def __init__(self, num_questions, left_margin=doc.leftMargin):
            super().__init__()
            self.num_questions = num_questions
            self.left_margin = left_margin

        def wrap(self, availWidth, availHeight):
            return (availWidth, availHeight)

        def draw(self):
            c = self.canv
            width, height = c._pagesize
            # Title (centered)
            c.setFont(FONT_NAME, 16)
            c.drawCentredString(width/2, height-40*mm, 'Antwortbogen')
            c.setFont(FONT_NAME, 12)
            start_y_ans = height-60*mm
            x_label = self.left_margin
            x_boxes_start = x_label + 30*mm
            box_spacing = 20*mm
            for i in range(self.num_questions):
                y = start_y_ans - (i*10*mm)
                c.drawString(x_label, y, f"Aufgabe {i + 1}:")
                for j, opt in enumerate(['A','B','C','D','E']):
                    bx = x_boxes_start + j*box_spacing
                    c.rect(bx, y-1, 4*mm, 4*mm, fill=0, stroke=1)
                    c.drawString(bx + 6*mm, y, opt)

    story.append(AnswerSheet(len(questions)))

    story.append(PageBreak())
    story.append(Paragraph("Lösungsschlüssel", styles['h1']))
    story.append(Spacer(1, 1*cm))
    # Larger font for solution key (we have space)
    solution_style = ParagraphStyle('SolutionStyle', parent=styles['Normal'], fontSize=12, leading=16)
    for q in questions:
        story.append(Paragraph(f"<b>Aufgabe {q['frage_id']}:</b> {q['korrekte_antwort']}", solution_style))

    doc.build(story)

# --- Hauptprogramm ---
if __name__ == "__main__":
    import argparse

    # Default configuration (can be overridden via CLI)
    DEFAULT_BATCH = 15
    DEFAULT_FRAGEN_PRO_PDF = 10
    DEFAULT_WORT_DATEI = "words.txt"
    DEFAULT_OUTPUT_DIR = "output"

    parser = argparse.ArgumentParser(description="IM (Implikationen erkennen) PDF Batch Generator")
    parser.add_argument("--batch", "-b", type=int, default=DEFAULT_BATCH, help="Anzahl der zu erstellenden PDFs (Standard: 15)")
    parser.add_argument("--questions", "-q", type=int, default=DEFAULT_FRAGEN_PRO_PDF, help="Anzahl Fragen pro PDF (Standard: 10)")
    parser.add_argument("--words", type=str, default=DEFAULT_WORT_DATEI, help="Wortdatei (Standard: words.txt)")
    parser.add_argument("--output-dir", type=str, default=DEFAULT_OUTPUT_DIR, help="Ausgabeverzeichnis (Standard: output)")

    args = parser.parse_args()

    BATCH_ANZAHL = max(1, int(args.batch))
    FRAGEN_PRO_PDF = max(1, int(args.questions))
    WORT_DATEI = args.words
    OUTPUT_DIR = args.output_dir

    print("--- Schritt 1: Lade Wörter ---")
    wortliste = load_words_from_file(filename=WORT_DATEI)

    if wortliste and len(wortliste) >= 3:
        print(f"\n--- Schritt 2: Starte Batch-Erstellung für {BATCH_ANZAHL} PDFs ---")
        # Sicherstellen, dass der Ausgabeordner existiert
        try:
            os.makedirs(OUTPUT_DIR, exist_ok=True)
        except Exception as e:
            print(f"FEHLER: Konnte Ausgabeverzeichnis '{OUTPUT_DIR}' nicht erstellen: {e}")
            raise
        for i in range(1, BATCH_ANZAHL + 1):
            pdf_name = f"IM_Simulation_{i}.pdf"
            output_path = os.path.join(OUTPUT_DIR, pdf_name)
            print(f"\nErstelle PDF {i}/{BATCH_ANZAHL}: '{output_path}'")
            questions = generate_questions(num_questions=FRAGEN_PRO_PDF, noun_pool=wortliste)
            try:
                create_pdf_from_questions(questions, filename=output_path)
                print(f"'{output_path}' wurde erfolgreich erstellt.")
            except Exception as e:
                print(f"FEHLER bei der Erstellung von '{output_path}': {e}")
        print(f"\nBatch-Prozess abgeschlossen. {BATCH_ANZAHL} Übungsblätter wurden in '{OUTPUT_DIR}' erstellt.")
    else:
        print("\nPROGRAMM BEENDET. Stelle sicher, dass 'words.txt' existiert und mind. 3 Wörter enthält.")