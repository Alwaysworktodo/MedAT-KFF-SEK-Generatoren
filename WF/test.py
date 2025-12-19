import random
import csv
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from collections import defaultdict
import string # Importiert für Buchstaben-Generierung

# --------------------------
# Wortflüssigkeit Exercise Generator - Überarbeitet
# --------------------------

# --- Konfiguration ---
DEFAULT_WORD_FILE = 'input.txt' # Deine große Wortliste hier eintragen
NUM_EXERCISES_PER_SIM = 15 # Sicherstellen, dass es 15 ist
MAX_EXERCISES_PER_PAGE = 6 # Neu: Maximal 6 Übungen pro Seite
FORBIDDEN_CHARS = 'ÄÖÜäöüß' # Zeichen, die komplett ausgeschlossen werden

# Schwierigkeitsgrade definieren die Wortlängen (nach Normalisierung)
DIFFICULTY_SETTINGS = {
    "easy":   {"min_len": 5, "max_len": 9},
    "medium": {"min_len": 7, "max_len": 12},
    "hard":   {"min_len": 10, "max_len": 15},
    "full":   {"min_len": 5, "max_len": 15}, # Gesamter erlaubter Bereich
}
# --- Ende Konfiguration ---


def normalize_word(word: str) -> str:
    """
    Convert a word to the normalized form used in the puzzle:
    - Uppercase. (Assumes forbidden chars like ÄÖÜß were already filtered out)
    """
    return word.strip().upper()


def load_word_list(source_file: str) -> list:
    """
    Load words from a source file (one word per line).
    Returns a list of raw words.
    """
    words = []
    print(f"Lade Wortliste aus '{source_file}'...")
    try:
        with open(source_file, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.split()
                if parts:
                    words.append(parts[0])
    except FileNotFoundError:
        print(f"FEHLER: Wortlistendatei '{source_file}' nicht gefunden.")
        return []
    except Exception as e:
        print(f"FEHLER beim Lesen der Datei '{source_file}': {e}")
        return []
    print(f"{len(words)} Wörter geladen.")
    return words


def filter_words(raw_word_list: list, min_len: int = 5, max_len: int = 15) -> list:
    """
    Filter the raw word list based on multiple criteria:
    1. Initial filter on raw words: No spaces, no forbidden chars (ÄÖÜß), must be alphabetic.
    2. Normalize passing words (uppercase).
    3. Filter normalized words by length (min_len, max_len).
    4. Filter out potential plural forms heuristically.
    5. Filter out *all* words that are part of an anagram group.
    """
    print("Filtere Wörter...")
    # 1. Initial filter on raw words
    initially_filtered = []
    for word in raw_word_list:
        w = word.strip()
        if not w: continue
        if ' ' in w: continue
        if any(c in w for c in FORBIDDEN_CHARS): continue
        if not w.isalpha(): continue
        initially_filtered.append(w)

    print(f"{len(initially_filtered)} Wörter nach initialem Roh-Filter.")

    # 2. Normalize & 3. Filter by length
    normalized_candidates = []
    for word in initially_filtered:
        norm = normalize_word(word)
        if min_len <= len(norm) <= max_len:
            normalized_candidates.append(norm)

    print(f"{len(normalized_candidates)} Wörter nach Normalisierung und Längenfilter ({min_len}-{max_len}).")

    # 4. Exclude potential plural forms (heuristic)
    singles = set(normalized_candidates)
    no_plurals = []
    plural_suffixes = ['ER', 'EN', 'E', 'N', 'S']
    for w in normalized_candidates:
        is_plural = False
        for suf in plural_suffixes:
            if w.endswith(suf) and len(w) > len(suf) and w[:-len(suf)] in singles:
                is_plural = True
                break
        if not is_plural:
            no_plurals.append(w)

    print(f"{len(no_plurals)} Wörter nach Plural-Filter.")

    # 5. Exclude *all* anagrams
    anagram_map = defaultdict(list)
    for w in no_plurals:
        key = ''.join(sorted(w))
        anagram_map[key].append(w)

    words_to_remove = set()
    for key, group in anagram_map.items():
        if len(group) > 1:
            words_to_remove.update(group)

    final_list = [w for w in no_plurals if w not in words_to_remove]

    print(f"{len(words_to_remove)} Wörter wegen Anagrammen entfernt.")
    print(f"{len(final_list)} Wörter final für die Übungsgenerierung verfügbar.")
    return final_list


def generate_exercises(word_list: list, count: int = 15) -> list:
    """
    Generate Wortflüssigkeit exercises:
    - Scramble letters, pick options A–E.
    - Aim for ~20% chance for Option E to be correct.
    - Ensure no repeat of words in one session.
    """
    if not word_list:
        print("WARNUNG: Keine Wörter zum Generieren von Übungen verfügbar.")
        return []
    if len(word_list) < count:
        print(f"WARNUNG: Nur {len(word_list)} Wörter verfügbar, benötige {count}. Generiere mit weniger Übungen.")
        count = len(word_list)

    exercises = []
    selected_words = random.sample(word_list, count)

    for word in selected_words:
        letters = list(word)
        random.shuffle(letters)
        scrambled = "   ".join(letters)
        correct_first_letter = word[0]
        unique_letters_in_word = set(word)

        is_option_e_correct = random.random() < 0.20

        options = {}
        opt_letters = []

        if is_option_e_correct:
            possible_distractors = list(unique_letters_in_word - {correct_first_letter})
            needed = 4
            alphabet = string.ascii_uppercase
            if len(possible_distractors) < needed:
                 num_extras_needed = needed - len(possible_distractors)
                 available_extras = [L for L in alphabet if L not in unique_letters_in_word]
                 num_to_add = min(num_extras_needed, len(available_extras))
                 if num_to_add > 0:
                      possible_distractors.extend(random.sample(available_extras, num_to_add))

            if len(possible_distractors) >= 4:
                opt_letters = random.sample(possible_distractors, 4)
            else:
                opt_letters = possible_distractors
                additional_needed = 4 - len(opt_letters)
                if additional_needed > 0:
                    forbidden_options = unique_letters_in_word.union(set(opt_letters))
                    available_final_fill = [L for L in alphabet if L not in forbidden_options]
                    num_final_fill = min(additional_needed, len(available_final_fill))
                    if num_final_fill > 0:
                        opt_letters.extend(random.sample(available_final_fill, num_final_fill))

            if correct_first_letter in opt_letters:
                 replacement_found = False
                 forbidden_options = unique_letters_in_word.union(set(opt_letters))
                 available_replacements = [L for L in alphabet if L not in forbidden_options]
                 if available_replacements:
                     replacement = random.choice(available_replacements)
                     opt_letters[opt_letters.index(correct_first_letter)] = replacement
                     replacement_found = True

            correct_label = 'E'

        else: # Option A, B, C oder D ist richtig
            possible_distractors = list(unique_letters_in_word - {correct_first_letter})
            needed = 3
            alphabet = string.ascii_uppercase
            if len(possible_distractors) < needed:
                 num_extras_needed = needed - len(possible_distractors)
                 available_extras = [L for L in alphabet if L not in unique_letters_in_word]
                 num_to_add = min(num_extras_needed, len(available_extras))
                 if num_to_add > 0:
                      possible_distractors.extend(random.sample(available_extras, num_to_add))

            if len(possible_distractors) >= 3:
                distractors = random.sample(possible_distractors, 3)
            else:
                distractors = possible_distractors
                additional_needed = 3 - len(distractors)
                if additional_needed > 0:
                    forbidden_options = unique_letters_in_word.union(set(distractors))
                    available_final_fill = [L for L in alphabet if L not in forbidden_options]
                    num_final_fill = min(additional_needed, len(available_final_fill))
                    if num_final_fill > 0:
                        distractors.extend(random.sample(available_final_fill, num_final_fill))

            opt_letters = distractors + [correct_first_letter]
            while len(opt_letters) < 4:
                 forbidden_options = unique_letters_in_word.union(set(opt_letters))
                 available_fill = [L for L in alphabet if L not in forbidden_options]
                 if not available_fill: break
                 opt_letters.append(random.choice(available_fill))

            random.shuffle(opt_letters)

            try:
                 correct_index = opt_letters.index(correct_first_letter)
                 correct_label = chr(ord('A') + correct_index)
            except ValueError:
                 print(f"FEHLER: Korrekter Buchstabe {correct_first_letter} nicht in Optionen {opt_letters} für Wort {word} gefunden, obwohl E falsch sein sollte.")
                 correct_label = '?'

        for i, letter in enumerate(opt_letters):
             # Stelle sicher, dass wir nicht mehr als 4 Buchstabenoptionen (A-D) erstellen
             if i < 4:
                options[chr(ord('A') + i)] = f"Anfangsbuchstabe: {letter}"
        # Füge Option E hinzu
        options['E'] = "Keine der Antwortmöglichkeiten ist richtig."
        # Überprüfe, ob alle 4 Optionen A-D erstellt wurden
        if len(options) < 5:
             print(f"WARNUNG: Konnte nicht genügend Optionsbuchstaben (A-D) für Wort {word} generieren. Optionen: {options}")


        exercises.append({
            'scrambled': scrambled,
            'options': options,
            'correct_option': correct_label,
            'source_word': word
        })

    return exercises


def save_exercises_to_csv(exercises: list, filename: str):
    """Speichert Übungen und Lösungen in einer CSV-Datei."""
    headers = ['Nr', 'Buchstaben', 'OptionA', 'OptionB',
               'OptionC', 'OptionD', 'OptionE', 'KorrekteOptionLabel',
               'Loesungswort']
    print(f"Speichere Übungen nach '{filename}'...")
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for i, ex in enumerate(exercises, 1):
            opts = ex['options']
            opt_a = opts.get('A', 'Anfangsbuchstabe: ?').split(': ')[-1]
            opt_b = opts.get('B', 'Anfangsbuchstabe: ?').split(': ')[-1]
            opt_c = opts.get('C', 'Anfangsbuchstabe: ?').split(': ')[-1]
            opt_d = opts.get('D', 'Anfangsbuchstabe: ?').split(': ')[-1]
            opt_e_text = opts.get('E', 'Keine der Antwortmöglichkeiten ist richtig.')

            row = [
                i,
                ex['scrambled'].replace('   ', ''),
                opt_a, opt_b, opt_c, opt_d,
                opt_e_text,
                ex['correct_option'],
                ex['source_word']
            ]
            writer.writerow(row)


def save_exercises_to_pdf(exercises: list, filename: str, title_suffix: str = ""):
    """Erstellt eine PDF-Datei mit Übungen (max 6 pro Seite) und Lösungsseite."""
    print(f"Generiere PDF '{filename}'...")
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4
    margin_top = 25 * mm
    margin_bottom = 20 * mm
    margin_left = 20 * mm
    line_height_exercise = 6 * mm # Höhe einer Zeile innerhalb einer Übung
    line_height_solution = 5 * mm
    content_width = width - 2 * margin_left

    def draw_header(page_num, title):
        c.setFont('Helvetica-Bold', 14)
        c.drawCentredString(width / 2, height - 15 * mm, title)
        c.setFont('Helvetica', 9)
        # Seitenanzahl unten zeichnen für Konsistenz
        # c.drawString(margin_left, margin_bottom - 10*mm, f"Seite {page_num}")

    def draw_footer(page_num):
         c.setFont('Helvetica', 9)
         c.drawRightString(width - margin_left, margin_bottom - 10*mm, f"Seite {page_num}")


    # --- Übungsseiten ---
    page_num = 1
    title = f'Wortflüssigkeit Testsimulation {title_suffix}'.strip()
    draw_header(page_num, title)
    c.setFont('Helvetica', 11)
    c.drawCentredString(width / 2, height - 22 * mm, 'Bearbeitungszeit: 20 Minuten')

    y = height - margin_top - 15 * mm # Startposition etwas tiefer für mehr Platz oben
    item_spacing = 8 * mm # Größerer Abstand zwischen Aufgaben
    exercises_on_page = 0 # Zähler für Übungen auf der aktuellen Seite

    for i, ex in enumerate(exercises, 1):
        # Berechne benötigte Höhe für diese eine Übung (1 Zeile für Buchstaben + Anzahl Optionen + Abstand)
        # Annahme: 5 Optionen (A-E) + 1 Zeile für verwürfelte Buchstaben
        num_option_lines = len(ex.get('options', {}))
        # Mindesthöhe für eine Aufgabe inkl. Abstand
        required_height = (1 + num_option_lines) * line_height_exercise + item_spacing

        # Seitenumbruch prüfen: Entweder Zähler erreicht oder nicht genug Platz
        # WICHTIG: Prüfung *bevor* die Übung gezeichnet wird
        if exercises_on_page >= MAX_EXERCISES_PER_PAGE or y < margin_bottom + required_height:
            draw_footer(page_num) # Fußzeile auf alter Seite
            c.showPage()
            page_num += 1
            draw_header(page_num, title) # Kopfzeile auf neuer Seite
            y = height - margin_top # Y-Position zurücksetzen
            exercises_on_page = 0 # Zähler für neue Seite zurücksetzen

        # --- Zeichne die Übung ---
        c.setFont('Helvetica-Bold', 11)
        num_str = f"{i}."
        c.drawString(margin_left, y, num_str)

        c.setFont('Courier', 11) # Courier für feste Breite der Buchstaben
        c.drawString(margin_left + 12*mm, y, ex['scrambled']) # Etwas mehr Platz für Nummer

        y -= line_height_exercise * 1.5 # Mehr Abstand zur ersten Option

        c.setFont('Helvetica', 10)
        option_labels = sorted(ex['options'].keys()) # A, B, C, D, E

        for lbl in option_labels:
             if lbl in ex['options']: # Nur zeichnen, wenn Option existiert
                 c.drawString(margin_left + 7*mm, y, f"({lbl}) {ex['options'][lbl]}") # Optionen einrücken
                 y -= line_height_exercise

        # Nach dem Zeichnen der Übung
        exercises_on_page += 1
        y -= item_spacing # Abstand zur nächsten Aufgabe

    draw_footer(page_num) # Fußzeile auf letzter Übungsseite

    # --- Lösungsseite ---
    c.showPage()
    page_num += 1
    solution_title = f'Lösungen - Simulation {title_suffix}'.strip()
    draw_header(page_num, solution_title)
    y = height - margin_top

    # Layout für Lösungen (z.B. 2 Spalten, wenn viele Lösungen)
    col_width = (width - 2 * margin_left - 10*mm) / 2 # Breite einer Spalte
    col1_x = margin_left
    col2_x = margin_left + col_width + 10*mm
    mid_point = (len(exercises) + 1) // 2 # Ungefähre Mitte für Spaltenumbruch

    c.setFont('Helvetica', 10)
    current_col_x = col1_x
    solutions_in_col = 0
    max_solutions_per_col = int((height - margin_top - margin_bottom) / line_height_solution) -1 # Geschätzte max Zeilen

    for i, ex in enumerate(exercises, 1):
        # Spalten- oder Seitenumbruch prüfen
        # if solutions_in_col >= max_solutions_per_col: # Wenn Spalte voll ist
        if i == mid_point + 1 and len(exercises) > 10: # Wenn mehr als 10 Übungen, wechsle zur 2. Spalte nach der Hälfte
             current_col_x = col2_x # Wechsle zur zweiten Spalte
             y = height - margin_top # Setze Y zurück für neue Spalte
             solutions_in_col = 0

        # Wenn Y zu niedrig wird (unabhängig von Spalte) -> neue Seite
        if y < margin_bottom + line_height_solution:
            draw_footer(page_num)
            c.showPage()
            page_num += 1
            draw_header(page_num, solution_title)
            y = height - margin_top
            current_col_x = col1_x # Starte wieder in Spalte 1 auf neuer Seite
            solutions_in_col = 0
            # Neuberechnung Mittelpunkt für Rest? Vorerst nicht.

        solution_text = f"{i}. ({ex['correct_option']}) {ex['source_word']}"
        c.drawString(current_col_x, y, solution_text)
        y -= line_height_solution
        solutions_in_col += 1


    draw_footer(page_num) # Fußzeile auf letzter Lösungsseite

    c.save()


# --- Hauptausführung ---
if __name__ == '__main__':
    # Wähle den Schwierigkeitsgrad: "easy", "medium", "hard", "full"
    difficulty_level = "medium"

    if difficulty_level not in DIFFICULTY_SETTINGS:
        print(f"FEHLER: Unbekannter Schwierigkeitsgrad '{difficulty_level}'. Verfügbar: {list(DIFFICULTY_SETTINGS.keys())}")
        exit(1)

    settings = DIFFICULTY_SETTINGS[difficulty_level]
    min_word_len = settings["min_len"]
    max_word_len = settings["max_len"]
    print(f"--- Generiere Simulation: Schwierigkeit '{difficulty_level}' (Wortlänge {min_word_len}-{max_word_len}) ---")

    raw_words = load_word_list(DEFAULT_WORD_FILE)

    if not raw_words:
        print("Keine Wörter geladen. Skript wird beendet.")
        exit(1)

    valid_words = filter_words(raw_words, min_word_len, max_word_len)

    if not valid_words:
        print("Nach dem Filtern sind keine gültigen Wörter übrig. Skript wird beendet.")
        exit(1)
    elif len(valid_words) < NUM_EXERCISES_PER_SIM:
         print(f"WARNUNG: Es gibt nur {len(valid_words)} gültige Wörter, aber {NUM_EXERCISES_PER_SIM} Übungen pro Simulation sind gewünscht.")

    print(f"Generiere {NUM_EXERCISES_PER_SIM} Übungen...")
    exercises = generate_exercises(valid_words, NUM_EXERCISES_PER_SIM)

    if not exercises:
        print("Konnte keine Übungen generieren. Skript wird beendet.")
        exit(1)

    pdf_filename = f'Wortfluessigkeit_{difficulty_level}_sim_001.pdf'
    csv_filename = f'Wortfluessigkeit_{difficulty_level}_sim_001.csv'
    title_suffix = f"({difficulty_level.capitalize()})"

    # Übergebe MAX_EXERCISES_PER_PAGE nicht direkt, es wird jetzt intern verwendet
    save_exercises_to_pdf(exercises, pdf_filename, title_suffix)
    save_exercises_to_csv(exercises, csv_filename)

    print("-" * 30)
    print(f"Erfolgreich {len(exercises)} Übungen generiert und gespeichert:")
    print(f"  PDF: {pdf_filename}")
    print(f"  CSV: {csv_filename}")
    print("-" * 30)