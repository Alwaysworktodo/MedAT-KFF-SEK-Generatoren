import random
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm

class PuzzleGenerator:
    """
    Erstellt Wortflüssigkeits-Rätsel als PDF, jetzt mit Titelseite und Batch-Funktion.
    """
    DIFFICULTY_LEVELS = {
        "easy":   {"min_len": 5, "max_len": 9},
        "medium": {"min_len": 7, "max_len": 12},
        "hard":   {"min_len": 10, "max_len": 15},
        "full":   {"min_len": 5, "max_len": 15},
    }
    ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    def __init__(self, word_list_path="finale_uebereinstimmungen30x40.txt"):
        """
        Initialisiert den Generator und lädt die Wortliste.
        """
        # Stelle sicher, dass relative Pfade relativ zur Skriptdatei aufgelöst werden,
        # damit das Skript unabhängig vom aktuellen Arbeitsverzeichnis funktioniert.
        if not os.path.isabs(word_list_path):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            word_list_path = os.path.join(base_dir, word_list_path)
        try:
            with open(word_list_path, 'r', encoding='utf-8') as f:
                self.master_word_list = [word.strip() for word in f if word.strip()]
            print(f"{len(self.master_word_list)} Wörter erfolgreich aus '{word_list_path}' geladen.")
        except FileNotFoundError:
            print(f"FEHLER: Die Wortliste '{word_list_path}' wurde nicht gefunden.")
            self.master_word_list = []
        
        self.used_words = set()

    def _select_word(self, min_len, max_len):
        """Wählt ein passendes, unbenutztes Wort aus."""
        # Nur Wörter mit ausreichend vielen unterschiedlichen Buchstaben zulassen,
        # damit wir 4 Antwortoptionen (eine richtige + drei falsche) aus dem Wort bilden können.
        candidate_words = [
            word for word in self.master_word_list
            if (
                min_len <= len(word) <= max_len
                and word not in self.used_words
                and len(set(word.upper())) >= 4
            )
        ]
        if not candidate_words: return None
        chosen_word = random.choice(candidate_words)
        self.used_words.add(chosen_word)
        return chosen_word

    def _create_single_puzzle(self, word):
        """Erstellt ein einzelnes Rätsel basierend auf dem Anfangsbuchstaben."""
        word_upper = word.upper()
        correct_answer = word_upper[0]
        
        word_list = list(word_upper)
        random.shuffle(word_list)
        anagram = "".join(word_list)

        # Falsche Antworten ausschließlich aus Buchstaben des Lösungsworts wählen (ohne den korrekten Anfangsbuchstaben).
        # Durch die Filterung in _select_word haben wir garantiert mindestens 3 andere Buchstaben zur Auswahl.
        unique_letters = set(word_upper)
        wrong_pool = list(unique_letters - {correct_answer})
        wrong_answers = random.sample(wrong_pool, 3)

        options = [correct_answer] + wrong_answers
        random.shuffle(options)
        
        correct_option_index = options.index(correct_answer)
        
        return {
            "anagram": anagram,
            "options": options,
            "solution_word": word,
            "correct_answer_char": correct_answer,
            "correct_option_index": correct_option_index,
        }

    def generate_puzzle_data(self, difficulty, num_puzzles=15):
        """Generiert die Daten für eine komplette Serie von Rätseln."""
        if difficulty not in self.DIFFICULTY_LEVELS:
            print(f"FEHLER: Schwierigkeitsgrad '{difficulty}' ist ungültig.")
            return [], []

        level = self.DIFFICULTY_LEVELS[difficulty]
        puzzles_data = []
        solutions_data = []

        for i in range(num_puzzles):
            word = self._select_word(level["min_len"], level["max_len"])
            if word is None:
                print(f"WARNUNG: Nicht genügend Wörter für {num_puzzles} Aufgaben. Es wurden nur {i} erstellt.")
                break
            
            puzzle = self._create_single_puzzle(word)
            puzzles_data.append(puzzle)
            
            option_letter = chr(97 + puzzle['correct_option_index'])
            solution_text = f"{i+1}. {option_letter}) {puzzle['correct_answer_char']} (Lösungswort: {puzzle['solution_word']})"
            solutions_data.append(solution_text)
            
        return puzzles_data, solutions_data

    def create_pdf(self, puzzles_data, solutions_data, filename, difficulty_str):
        """Erstellt die PDF-Datei mit Titelseite, Aufgaben, Antwort- und Lösungsbogen."""
        c = canvas.Canvas(filename, pagesize=A4)
        width, height = A4
        margin_x, margin_y = 2*cm, 2*cm
        
        # --- SEITE 1: TITELSEITE ---
        c.setFont("Helvetica-Bold", 24)
        c.drawCentredString(width / 2, height / 2 + 2*cm, "Wortflüssigkeit - Testzeit 20 min")
        c.setFont("Helvetica", 18)
        c.drawCentredString(width / 2, height / 2, f"Schwierigkeitsgrad: {difficulty_str.title()}")
        c.showPage()

        # --- SEITEN 2 (ff): AUFGABEN ---
        y_pos = height - margin_y
        for i, puzzle in enumerate(puzzles_data):
            if i > 0 and i % 4 == 0:
                c.showPage()
                y_pos = height - margin_y

            c.setFont("Helvetica-Bold", 12)
            c.drawString(margin_x, y_pos, f"Übungsaufgabe {i + 1}")
            y_pos -= 1.2 * cm
            
            c.setFont("Helvetica-Bold", 16)
            # Passen Sie diesen Wert an, um den Buchstabenabstand zu ändern
            letter_spacing = 3 * cm / 4 # Entspricht ca. 3 Leerzeichen
            x_pos = margin_x + 1*cm
            for char in puzzle['anagram']:
                c.drawString(x_pos, y_pos, char)
                x_pos += letter_spacing
            y_pos -= 1.2 * cm
            
            c.setFont("Helvetica", 11)
            options_list = [f"{chr(97+j)}) {opt}" for j, opt in enumerate(puzzle['options'])]
            options_list.append("e) Keine Antwort ist richtig")
            
            for line in options_list:
                c.drawString(margin_x + 1*cm, y_pos, line)
                y_pos -= 0.7 * cm
            y_pos -= 1 * cm

        # --- ANTWORTBOGEN (FZ-style) ---
        c.showPage()
        c.setFont("Helvetica-Bold", 16); c.drawCentredString(width/2, height-40*mm, "Antwortbogen")
        c.setFont("Helvetica", 12); start_y_ans = height-60*mm
        for i in range(len(puzzles_data)):
            y = start_y_ans - (i*10*mm)
            c.drawString(40*mm, y, f"Aufgabe {i + 1}:")
            for j, opt in enumerate(["A","B","C","D","E"]):
                c.rect(80*mm+j*20*mm, y-1, 4*mm, 4*mm, fill=0, stroke=1)
                c.drawString(80*mm+j*20*mm+6*mm, y, opt)
        c.showPage()
        y_pos = height - margin_y
        c.setFont("Helvetica-Bold", 16)
        c.drawString(margin_x, y_pos, "Lösungsbogen")
        y_pos -= 1.5 * cm
        
        c.setFont("Helvetica", 12)
        for solution in solutions_data:
            c.drawString(margin_x, y_pos, solution)
            y_pos -= 0.8 * cm

        c.save()

    def batch_create_pdfs(self, difficulty, num_puzzles, num_batches, output_dir="Batch_PDFs"):
        """Erstellt eine große Anzahl einzigartiger PDF-Tests auf einmal."""
        
        required_words = num_puzzles * num_batches
        if required_words > len(self.master_word_list):
            print(f"WARNUNG: Sie möchten {required_words} einzigartige Wörter verwenden, aber die Liste enthält nur {len(self.master_word_list)}.")
            print("Der Prozess wird gestoppt, wenn keine Wörter mehr verfügbar sind.")
        
        os.makedirs(output_dir, exist_ok=True)
        print(f"\nBeginne Batch-Erstellung von {num_batches} PDFs im Ordner '{output_dir}'...")

        for i in range(num_batches):
            print(f"--- Erstelle PDF {i+1}/{num_batches} ---")
            
            puzzles, solutions = self.generate_puzzle_data(difficulty, num_puzzles)
            
            if not puzzles:
                print("Keine weiteren Wörter verfügbar. Batch-Prozess wird vorzeitig beendet.")
                break
            
            filename = os.path.join(output_dir, f"Wortflüssigkeit_{difficulty}_{i+1:03d}.pdf")
            
            self.create_pdf(puzzles, solutions, filename, difficulty)
        
        print("\nBatch-Erstellung abgeschlossen.")

# --- HAUPTPROGRAMM (Hier konfigurieren Sie alles) ---
if __name__ == "__main__":
    
    # 1. Den Generator instanziieren
    generator = PuzzleGenerator(word_list_path="finale_uebereinstimmungen30x40.txt")

    if generator.master_word_list:
        
        # 2. Konfiguration für die Batch-Erstellung
        DIFFICULTY = "hard"       # Wählen Sie: "easy", "medium", "hard", "full"
        PUZZLES_PER_PDF = 15      # Anzahl der Aufgaben pro einzelner PDF
        NUMBER_OF_PDFS = 15       # Wie viele einzigartige PDFs sollen erstellt werden? (erhöht auf 15 auf Benutzeranforderung)
        
        # 3. Batch-Prozess starten
        generator.batch_create_pdfs(
            difficulty=DIFFICULTY,
            num_puzzles=PUZZLES_PER_PDF,
            num_batches=NUMBER_OF_PDFS
        )