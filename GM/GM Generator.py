# GM Generator.py

import os
import random
import argparse
from typing import List, Dict, Any
from collections import Counter

# Überprüfen, ob die benötigte Bibliothek 'reportlab' installiert ist
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle, KeepTogether
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.units import cm, mm
    from reportlab.lib import colors
except ImportError:
    print("FEHLER: Die Bibliothek 'reportlab' wurde nicht gefunden.")
    print("Bitte installieren Sie sie mit dem Befehl: pip install reportlab")
    exit()

# --------------------------------------------------------------------------
# --- TEIL 1: DATENMODELLE UND GENERIERUNGSLOGIK ---
# --------------------------------------------------------------------------

class AllergyCertificate:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.image_path = kwargs.get('image_path')
        self.name = kwargs.get('name')
        self.birthday = kwargs.get('birthday')
        self.medication = kwargs.get('medication')
        self.blood_group = kwargs.get('blood_group')
        self.allergies = kwargs.get('allergies', [])
        self.certificate_number = kwargs.get('certificate_number')
        self.country = kwargs.get('country')

def _load_resource(filename: str) -> List[str]:
    path = os.path.join('resources', filename)
    if not os.path.exists(path): raise FileNotFoundError(f"Datei nicht gefunden: {path}.")
    with open(path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
    if not lines: raise ValueError(f"Datei '{path}' ist leer.")
    return lines

def generate_single_certificate(id: int, difficulty: str, used_images: List[str], resources: Dict) -> AllergyCertificate:
    image_dir = os.path.join('resources', 'images')
    available_images = [img for img in os.listdir(image_dir) if img not in used_images and (img.lower().endswith((".png", ".jpg")))]
    if not available_images: raise ValueError("Nicht genügend Bilder im Ordner 'resources/images/'.")
    image_name = random.choice(available_images)
    difficulty_allergies = {'easy': [0, 1], 'medium': [1, 2], 'difficult': [2, 3]}
    num_allergies = random.choice(difficulty_allergies[difficulty])
    num_to_sample = min(num_allergies, len(resources['allergies']))
    allergies = random.sample(resources['allergies'], num_to_sample) if num_to_sample > 0 else []
    if difficulty == 'easy':
        base, digit = str(random.randint(100, 999)), str(random.randint(0, 9))
        pos = random.randint(0, 2)
        cert_number = base[:pos] + digit + digit + base[pos:]
    else:
        cert_number = str(random.randint(10000, 99999))
    return AllergyCertificate(id=id, image_path=os.path.join(image_dir, image_name), name=random.choice(resources['names']), birthday=f"{random.randint(1, 28):02d}. {random.choice(resources['months'])}", medication=random.choice(["Ja", "Nein"]), blood_group=random.choice(resources['blood_groups']), allergies=allergies, certificate_number=cert_number, country=random.choice(resources['countries']))

def generate_full_test_data(num_certificates: int, resources: Dict) -> List[AllergyCertificate]:
    certificates, used_images, used_names = [], [], []
    easy_count = num_certificates // 4
    difficult_count = num_certificates // 4
    medium_count = num_certificates - easy_count - difficult_count
    difficulty_list = (['easy'] * easy_count) + (['medium'] * medium_count) + (['difficult'] * difficult_count)
    while len(difficulty_list) < num_certificates: difficulty_list.append('medium')
    random.shuffle(difficulty_list)
    for i in range(num_certificates):
        name = random.choice([n for n in resources['names'] if n not in used_names])
        used_names.append(name)
        cert = generate_single_certificate(i + 1, difficulty_list[i], used_images, resources)
        cert.name = name
        certificates.append(cert)
        used_images.append(os.path.basename(cert.image_path))
    return certificates

# --------------------------------------------------------------------------
# --- FRAGENGENERATOREN ---
# --------------------------------------------------------------------------

GERMAN_MAP = {
    'name': ('der Name', 'Wie lautet der Name'), 'birthday': ('der Geburtstag', 'Wann'),
    'medication': ('der Medikamentenstatus', 'Welchen Medikamentenstatus'),
    'blood_group': ('die Blutgruppe', 'Welche Blutgruppe'),
    'allergies': ('die Allergien', 'Welche Allergien'),
    'certificate_number': ('die Ausweisnummer', 'Wie lautet die Ausweisnummer'),
    'country': ('das Ausstellungsland', 'Aus welchem Land')
}

def generate_questions(certificates: List[AllergyCertificate], num_questions: int) -> List[Dict[str, Any]]:
    questions, used_questions = [], set()
    question_pool = [gen_q_direct_person_data, gen_q_count, gen_q_identification, gen_q_cross_reference, gen_q_statement_validation, gen_q_country_cross_reference, gen_q_negation, gen_q_multi_conditional, gen_q_from_image]
    max_tries, try_count = 500, 0
    while len(questions) < num_questions and try_count < max_tries:
        try_count += 1; generator_func = random.choice(question_pool); q = generator_func(certificates)
        if not q: continue
        question_signature = q['text'] + q.get('image_path', '')
        if question_signature in used_questions: continue
        used_questions.add(question_signature); questions.append(q)
    return questions

def _create_mc_options(q, distractors, certificates):
    correct_answer = str(q['correct']); options = []
    unique_distractors = list(set([str(d) for d in distractors if str(d) != correct_answer]))
    if random.random() < 0.2 and len(unique_distractors) >= 4:
        q['correct'] = "Keine der Antwortmöglichkeiten ist richtig."; options = random.sample(unique_distractors, 4)
    else:
        options.append(correct_answer)
        num_to_add = min(3, len(unique_distractors)); options.extend(random.sample(unique_distractors, num_to_add))
        # Use actual certificate attribute values for fallback to avoid adding literal keys like 'country'
        fallback_pool = [c.name for c in certificates] + [c.country for c in certificates] + [c.birthday for c in certificates] + [c.certificate_number for c in certificates] + [c.blood_group for c in certificates]
        while len(options) < 4:
            potential_fill = random.choice(fallback_pool)
            if str(potential_fill) not in [str(o) for o in options]: options.append(potential_fill)
    random.shuffle(options); q['options'] = [str(o) for o in options] + ["Keine der Antwortmöglichkeiten ist richtig."]
    return q

def gen_q_direct_person_data(certificates):
    cert = random.choice(certificates); field = random.choice(['blood_group', 'country', 'birthday'])
    q_word = GERMAN_MAP[field][1]
    q_text = f"{q_word} hat die Person {cert.name} Geburtstag?" if field == 'birthday' else f"{q_word} kommt die Person {cert.name}?" if field == 'country' else f"{q_word} hat die Person {cert.name}?"
    q = {'text': q_text, 'correct': getattr(cert, field)}; all_possible = [getattr(c, field) for c in certificates]
    return _create_mc_options(q, all_possible, certificates)

def gen_q_count(certificates):
    field = random.choice(['medication', 'blood_group'])
    if field == 'medication':
        target = random.choice(['Ja', 'Nein'])
        q_text = "Wie viele Personen nehmen Medikamente ein?" if target == 'Ja' else "Wie viele Personen nehmen keine Medikamente ein?"
        q = {'text': q_text, 'correct': sum(1 for c in certificates if c.medication == target)}
    else:
        target = random.choice(['A', 'B', 'AB', '0'])
        q = {'text': f"Wie viele Personen haben die Blutgruppe {target}?", 'correct': sum(1 for c in certificates if c.blood_group == target)}
    return _create_mc_options(q, list(range(len(certificates) + 1)), certificates)

def gen_q_identification(certificates):
    all_allergies = Counter([a for c in certificates for a in c.allergies]); unique_allergies = [a for a, count in all_allergies.items() if count == 1]
    if not unique_allergies: return None
    target_allergy = random.choice(unique_allergies)
    cert = next(c for c in certificates if target_allergy in c.allergies)
    q = {'text': f"Welchen Namen hat die Person mit der Allergie gegen {target_allergy}?", 'correct': cert.name}
    return _create_mc_options(q, [c.name for c in certificates], certificates)

def gen_q_cross_reference(certificates):
    cert = random.choice(certificates); output_field = random.choice(['country', 'blood_group', 'birthday'])
    q_word = GERMAN_MAP[output_field][1]
    if output_field == 'birthday': q_text = f"Wann hat die Person mit der Ausweisnummer {cert.certificate_number} Geburtstag?"
    elif output_field == 'country': q_text = f"Aus welchem Land kommt die Person mit der Ausweisnummer {cert.certificate_number}?"
    else: q_text = f"{q_word} hat die Person mit der Ausweisnummer {cert.certificate_number}?"
    q = {'text': q_text, 'correct': getattr(cert, output_field)}
    return _create_mc_options(q, [getattr(c, output_field) for c in certificates], certificates)

def gen_q_country_cross_reference(certificates):
    country_counts = Counter(c.country for c in certificates); unique_countries = [country for country, count in country_counts.items() if count == 1]
    if not unique_countries: return None
    target_country = random.choice(unique_countries)
    cert = next(c for c in certificates if c.country == target_country)
    output_field = random.choice(['name', 'blood_group', 'birthday'])
    q_word = GERMAN_MAP[output_field][1]
    q_text = f"Wann hat die Person aus {target_country} Geburtstag?" if output_field == 'birthday' else f"{q_word} hat die Person aus {target_country}?"
    q = {'text': q_text, 'correct': getattr(cert, output_field)}
    return _create_mc_options(q, [getattr(c, output_field) for c in certificates], certificates)

def gen_q_multi_conditional(certificates):
    if len(certificates) < 2: return None
    fields = ['medication', 'blood_group', 'country']; field1, field2 = random.sample(fields, 2)
    target_cert = random.choice(certificates); value1, value2 = getattr(target_cert, field1), getattr(target_cert, field2)
    matches = [c for c in certificates if getattr(c, field1) == value1 and getattr(c, field2) == value2]
    if len(matches) != 1: return None
    cert = matches[0]
    output_field = random.choice(['name', 'certificate_number', 'birthday'])
    condition_text = {'medication': {'Ja': 'Medikamente nimmt', 'Nein': 'keine Medikamente nimmt'}, 'blood_group': {'A': 'Blutgruppe A hat', 'B': 'Blutgruppe B hat', 'AB': 'Blutgruppe AB hat', '0': 'Blutgruppe 0 hat'}, 'country': {'default': 'aus {} kommt'}}
    cond1_text = condition_text[field1]['default'].format(value1) if field1 == 'country' else condition_text[field1][value1]
    cond2_text = condition_text[field2]['default'].format(value2) if field2 == 'country' else condition_text[field2][value2]
    q_text = f"{GERMAN_MAP[output_field][1]} der Person, die {cond1_text} und {cond2_text}?"
    if output_field == 'birthday': q_text = f"Wann hat die Person Geburtstag, die {cond1_text} und {cond2_text}?"
    q = {'text': q_text, 'correct': getattr(cert, output_field)}
    return _create_mc_options(q, [getattr(c, output_field) for c in certificates], certificates)

def gen_q_from_image(certificates):
    cert = random.choice(certificates); output_field = random.choice(['name', 'certificate_number', 'birthday'])
    if output_field == 'name': q_text = "Wie lautet der Name der Person auf dem Bild?"
    elif output_field == 'certificate_number': q_text = "Wie lautet die Ausweisnummer der Person auf dem Bild?"
    else: q_text = "Wann hat die Person auf dem Bild Geburtstag?"
    q = {'text': q_text, 'image_path': cert.image_path, 'correct': getattr(cert, output_field)}
    return _create_mc_options(q, [getattr(c, output_field) for c in certificates], certificates)

def gen_q_statement_validation(certificates):
    if len(certificates) < 2: return None
    correct_cert, text_map = random.choice(certificates), {'country': 'kommt aus', 'blood_group': 'hat Blutgruppe'}
    field = random.choice(list(text_map.keys()))
    correct_statement = f"Die Person {correct_cert.name} {text_map[field]} {getattr(correct_cert, field)}"
    q = {'text': "Welche der folgenden Aussagen ist richtig?", 'correct': correct_statement}
    distractors = []
    while len(distractors) < 3:
        distractor_cert, distractor_field = random.choice(certificates), random.choice(list(text_map.keys()))
        true_val = getattr(distractor_cert, distractor_field)
        all_vals = list(set([getattr(c, distractor_field) for c in certificates]))
        if len(all_vals) < 2: continue
        wrong_val = random.choice([v for v in all_vals if v != true_val])
        false_statement = f"Die Person {distractor_cert.name} {text_map[distractor_field]} {wrong_val}"
        if false_statement != correct_statement and false_statement not in distractors: distractors.append(false_statement)
    return _create_mc_options(q, distractors, certificates)

def gen_q_negation(certificates):
    if len(certificates) < 2: return None
    cert = random.choice(certificates)
    true_statements_map = {'country': f"kommt aus {cert.country}", 'blood_group': f"hat Blutgruppe {cert.blood_group}", 'medication': f"nimmt Medikamente ({cert.medication})"}
    field_to_falsify = random.choice(list(true_statements_map.keys()))
    true_value = getattr(cert, field_to_falsify)
    all_possible_values = list(set(getattr(c, field_to_falsify) for c in certificates))
    if len(all_possible_values) < 2: return None
    wrong_value = random.choice([v for v in all_possible_values if v != true_value])
    text_map = {'country': 'kommt aus {}', 'blood_group': 'hat Blutgruppe {}', 'medication': "nimmt Medikamente ({})"}
    false_statement = text_map[field_to_falsify].format(wrong_value)
    q = {'text': f"Was trifft auf die Person {cert.name} NICHT zu?", 'correct': false_statement}
    distractors = [v for k, v in true_statements_map.items() if k != field_to_falsify]
    return _create_mc_options(q, distractors, certificates)
    
# --------------------------------------------------------------------------
# --- TEIL 2: PDF-ERSTELLUNGSLOGIK ---
# --------------------------------------------------------------------------

def create_pdf_report(certificates: List[AllergyCertificate], questions: List[Dict], num_questions: int, output_filename: str):
    full_path = os.path.join("output", output_filename)
    doc = SimpleDocTemplate(full_path, pagesize=A4, topMargin=1.5*cm, bottomMargin=1.5*cm, leftMargin=1.5*cm, rightMargin=1.5*cm)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("MedAT GM - Testsimulation", ParagraphStyle(name='Title', parent=styles['h1'], alignment=TA_CENTER)))
    story.append(Spacer(1, 1*cm)); story.append(Paragraph(f"{len(certificates)} Ausweise - {len(certificates)} Minuten Einprägungszeit", styles['h2']))
    story.append(Spacer(1, 0.5*cm)); story.append(Paragraph("40 Minuten Pause", styles['h2']))
    story.append(Spacer(1, 0.5*cm)); story.append(Paragraph("15 Minuten Wiedergabezeit", styles['h2']))
    story.append(PageBreak())
    
    page_capacity = 4 if len(certificates) > 2 else 2
    for i in range(0, len(certificates), page_capacity):
        for cert in certificates[i:i+page_capacity]:
            header = Paragraph("ALLERGIEAUSWEIS", ParagraphStyle(name='Header', textColor=colors.white, alignment=TA_CENTER))
            img = Image(cert.image_path, width=3.5*cm, height=4.5*cm)
            allergies_str = ', '.join(cert.allergies) if cert.allergies else 'Keine bekannt'
            label_style, value_style = ParagraphStyle(name='Label', fontName='Helvetica-Bold'), styles['Normal']
            text_data = [[Paragraph('Name:', label_style), Paragraph(cert.name, value_style)], [Paragraph('Geburtstag:', label_style), Paragraph(cert.birthday, value_style)], [Paragraph('Medikamente:', label_style), Paragraph(cert.medication, value_style)], [Paragraph('Blutgruppe:', label_style), Paragraph(cert.blood_group, value_style)], [Paragraph('Allergien:', label_style), Paragraph(allergies_str, value_style)], [Paragraph('Ausweis-Nr:', label_style), Paragraph(cert.certificate_number, value_style)], [Paragraph('Ausstellungsland:', label_style), Paragraph(cert.country, value_style)],]
            data_table = Table(text_data, colWidths=[3.8*cm, 7.7*cm]); data_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 0)]))
            content_table = Table([[img, data_table]], colWidths=[4*cm, 12.5*cm]); content_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 5)]))
            card_table = Table([[header], [content_table]], colWidths=[17*cm], rowHeights=[0.8*cm, 5.0*cm]); card_table.setStyle(TableStyle([('BOX', (0,0), (-1,-1), 1, colors.darkgrey), ('BACKGROUND', (0,0), (0,0), colors.HexColor("#6C8EBF")), ('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
            story.append(card_table); story.append(Spacer(1, 0.4*cm))
        story.append(PageBreak())

    story.append(Paragraph("Fragen", styles['h1'])); story.append(Spacer(1, 0.5*cm))
    option_labels = ['A', 'B', 'C', 'D', 'E']
    for i, q in enumerate(questions):
        question_block = []
        question_title = Paragraph(f"<b>{i+1}. {q['text']}</b>", ParagraphStyle(name='Q', spaceAfter=6))
        
        if 'image_path' in q:
            question_block.append(question_title)
            options_paragraphs = [Paragraph(f"{option_labels[j]}) {option}", ParagraphStyle(name='O', leftIndent=10, leading=14)) for j, option in enumerate(q.get('options', []))]
            
            # KORREKTUR: Bildgröße angepasst (10% kleiner als Ausweisbild)
            img_width = 3.5 * 0.9 * cm
            img_height = 4.5 * 0.9 * cm
            img = Image(q['image_path'], width=img_width, height=img_height)
            
            table_data = [[options_paragraphs, img]]
            question_table = Table(table_data, colWidths=[11*cm, img_width + 0.5*cm])
            question_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
            question_block.append(question_table)
        else:
            question_block.append(question_title)
            for j, option in enumerate(q.get('options', [])):
                question_block.append(Paragraph(f"{option_labels[j]}) {option}", ParagraphStyle(name='O', leftIndent=10)))
        
        story.append(KeepTogether(question_block + [Spacer(1, 0.5*cm)]))
    story.append(PageBreak())

    # --- Antwortbogen (einspaltig, identisch zum FZ-Generator) ---
    from reportlab.platypus import Flowable

    class AnswerSheet(Flowable):
        """Draw an answer sheet like the FZ generator: one column with each question and five small boxes A-E."""
        def __init__(self, num_questions, width=A4[0], height=A4[1], left_margin=1.5*cm):
            super().__init__()
            self.num_questions = num_questions
            self.width = width
            self.height = height
            self.left_margin = left_margin

        def wrap(self, availWidth, availHeight):
            return (availWidth, availHeight)

        def draw(self):
            c = self.canv
            mm_local = 1 * mm
            # Title
            c.setFont('Helvetica-Bold', 16)
            c.drawCentredString(self.width/2, self.height-40*mm, 'Antwortbogen')
            c.setFont('Helvetica', 12)
            start_y_ans = self.height-60*mm
            # Use left_margin for x-origin so the rows align to the document left margin
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

    # Only include the AnswerSheet itself (which already contains the 'Antwortbogen' title)
    story.append(AnswerSheet(num_questions))
    story.append(PageBreak())
    
    story.append(Paragraph("Lösungsbogen", styles['h1']))
    for i, q in enumerate(questions):
        try:
            correct_label = option_labels[q['options'].index(str(q['correct']))]
            story.append(Paragraph(f"<b>{i+1}.</b> {correct_label}", ParagraphStyle(name='S', leading=14)))
        except (ValueError, KeyError):
            story.append(Paragraph(f"<b>{i+1}.</b> FEHLER (Antwort: '{q.get('correct', 'N/A')}')", ParagraphStyle(name='S', leading=14)))
    doc.build(story)
    print(f"\nPDF '{output_filename}' erfolgreich im Ordner 'output' erstellt.")

# --------------------------------------------------------------------------
# --- TEIL 3: HAUPTSTEUERUNG ---
# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="MedAT GM PDF Testsimulations-Generator", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--difficulty', type=str, default='normal', choices=['sehr-leicht', 'leicht', 'mittel', 'normal'], help="""Wählt einen vordefinierten Schwierigkeitsgrad:\n  sehr-leicht: 2 Ausweise, 10 Fragen\n  leicht:       4 Ausweise, 15 Fragen\n  mittel:       6 Ausweise, 20 Fragen\n  normal:       8 Ausweise, 25 Fragen (Standard)\n""")
    parser.add_argument('--batch', type=int, default=1, help="Anzahl der Tests, die auf einmal generiert werden sollen. Standard: 1")
    parser.add_argument('--output', type=str, default='MedAT_GM_Simulation.pdf', help="Basis-Name der Ausgabe-PDF-Datei(en).")
    args = parser.parse_args()
    DIFFICULTY_SETTINGS = {'sehr-leicht': {'certs': 2, 'questions': 10}, 'leicht': {'certs': 4, 'questions': 15}, 'mittel': {'certs': 6, 'questions': 20}, 'normal': {'certs': 8, 'questions': 25},}
    settings = DIFFICULTY_SETTINGS[args.difficulty]
    num_certificates, num_questions = settings['certs'], settings['questions']
    try:
        if not os.path.exists('output'): os.makedirs('output')
        if not os.path.exists(os.path.join('resources', 'images')): raise FileNotFoundError("Der Ordner 'resources/images' wurde nicht gefunden.")
        resources = {'names': _load_resource('names.txt'), 'allergies': _load_resource('allergies.txt'), 'countries': _load_resource('countries.txt'), 'blood_groups': ['A', 'B', 'AB', '0'], 'months': ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']}
        for i in range(1, args.batch + 1):
            if args.batch > 1:
                print(f"\n--- Generiere Test {i} von {args.batch} ---")
                base, ext = os.path.splitext(args.output)
                output_filename = f"{base}_{i}{ext}"
            else:
                output_filename = args.output
            print(f"Schwierigkeit: '{args.difficulty}' ({num_certificates} Ausweise, {num_questions} Fragen)")
            print("Generiere Testdaten...")
            certificates = generate_full_test_data(num_certificates, resources)
            print("Generiere Fragen...")
            questions = generate_questions(certificates, num_questions)
            print("Erstelle PDF-Bericht...")
            create_pdf_report(certificates, questions, num_questions, output_filename)
    except (FileNotFoundError, ValueError, IndexError) as e:
        print(f"\nEin Fehler ist aufgetreten: {e}")
        print("Bitte stellen Sie sicher, dass alle Ordner und Ressourcendateien korrekt eingerichtet sind und genügend Daten enthalten.")

if __name__ == '__main__':
    main()