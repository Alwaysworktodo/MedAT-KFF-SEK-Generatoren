import re

def parse_word_token(token):
    """
    Analysiert ein Wort-Token und extrahiert alle möglichen Wortformen.
    Beispiele:
    - "der,die,das" -> ['der', 'die', 'das']
    - "ein(e)" -> ['ein', 'eine']
    - "jed(e,r,s)" -> ['jed', 'jede', 'jeder', 'jedes']
    - "und" -> ['und']
    """
    words = set()

    # Prüft auf das Format "stamm(endung1,endung2,...)"
    match = re.match(r"(\w+)\((.+)\)", token)
    if match:
        base = match.group(1)
        endings_str = match.group(2)
        
        # Füge den Wortstamm als eigenes Wort hinzu (z.B. "ein" aus "ein(e)")
        words.add(base)
        
        # Kombiniere den Stamm mit jeder Endung
        for ending in endings_str.split(','):
            words.add(base + ending)
        return list(words)

    # Prüft auf kommaseparierte Wörter
    if ',' in token:
        return token.split(',')

    # Ansonsten ist es ein einzelnes Wort
    return [token]


def compare_final_lists(base_list_path, pos_list_path):
    """
    Vergleicht eine einfache Wortliste mit einer formatierten Wortart-Liste
    und findet die gemeinsamen Wörter.

    Args:
        base_list_path (str): Pfad zur sauberen Wortliste (ein Wort pro Zeile).
        pos_list_path (str): Pfad zur formatierten Wortart-Liste.

    Returns:
        list or str: Eine alphabetisch sortierte Liste der gemeinsamen Wörter oder eine Fehlermeldung.
    """
    try:
        # --- 1. Die bereits bereinigte Wortliste laden ---
        with open(base_list_path, 'r', encoding='latin-1') as f1:
            # Annahme: Diese Liste ist bereits sauber und in Kleinbuchstaben
            base_words = set(f1.read().splitlines())

        # --- 2. Die neue, komplex formatierte Liste verarbeiten ---
        pos_words = set()
        with open(pos_list_path, 'r', encoding='latin-1') as f2:
            for line in f2:
                if not line.strip():  # Leere Zeilen überspringen
                    continue
                
                # Den ersten Teil der Zeile (das Wort-Token) extrahieren
                word_token = line.split()[0]
                
                # Das Token in einzelne Wörter aufschlüsseln
                extracted_words = parse_word_token(word_token)
                
                # Jedes extrahierte Wort in Kleinbuchstaben zum Set hinzufügen
                for word in extracted_words:
                    pos_words.add(word.lower())

        # --- 3. Die Schnittmenge der beiden Wort-Sets finden ---
        final_common_words = list(base_words.intersection(pos_words))
        final_common_words.sort()  # Ergebnis alphabetisch sortieren
        
        return final_common_words

    except FileNotFoundError as e:
        return f"FEHLER: Datei nicht gefunden - {e.filename}. Bitte überprüfen Sie den Dateinamen und den Speicherort."
    except Exception as e:
        return f"Ein unerwarteter Fehler ist aufgetreten: {e}"

# --- Hauptprogramm ---

# Annahme: Die erste Liste ist das Ergebnis aus dem vorherigen Schritt.
# Die zweite Liste ist die neu von Ihnen bereitgestellte Datei.
file_base_list = "gemeinsame_woerter30k.txt" 
file_pos_list = "Base40.1" # Speichern Sie die neue Liste unter diesem Namen

# Erstellen Sie eine Dummy-Datei 'Wortart.txt' mit dem von Ihnen bereitgestellten Inhalt,
# damit das Skript ausgeführt werden kann.

final_list = compare_final_lists(file_base_list, file_pos_list)

if isinstance(final_list, list):
    if final_list:
        print(f"Abgleich erfolgreich! Es wurden {len(final_list)} übereinstimmende Wörter gefunden:")
        
        # Vorschau der ersten 100 Wörter
        for i, word in enumerate(final_list[:100]):
            print(word)
        if len(final_list) > 100:
            print(f"... und {len(final_list) - 100} weitere.")

        # Optional: Das Endergebnis in einer neuen Datei speichern
        output_filename = "finale_uebereinstimmungen.txt"
        with open(output_filename, "w", encoding="utf-8") as f_out:
            for word in final_list:
                f_out.write(word + "\n")
        print(f"\nAlle übereinstimmenden Wörter wurden in '{output_filename}' gespeichert.")

    else:
        print("Es wurden keine übereinstimmenden Wörter in den beiden Listen gefunden.")
else:
    # Fehlermeldung ausgeben
    print(final_list)