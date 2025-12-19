def find_common_words_from_structured_files(freq_file_path, new_list_file_path):
    """
    Liest zwei unterschiedlich formatierte Dateien, extrahiert und normalisiert die Wörter
    und gibt eine alphabetisch sortierte Liste der gemeinsamen Wörter zurück.

    Args:
        freq_file_path (str): Pfad zur Frequenzdatei (Format: ID\tWort\tAnzahl).
        new_list_file_path (str): Pfad zur neuen Wortliste (ein Wort pro Zeile, großgeschrieben).

    Returns:
        list or str: Eine Liste der gemeinsamen Wörter oder eine Fehlermeldung.
    """
    try:
        # --- Verarbeitung der Wortfrequenz-Datei ---
        freq_words = set()
        with open(freq_file_path, 'r', encoding='utf-8') as f1:
            for line in f1:
                # Zeile am Tabulator aufteilen
                parts = line.strip().split('\t')
                # Sicherstellen, dass die Zeile das erwartete Format hat (mindestens 2 Spalten)
                if len(parts) >= 2:
                    word = parts[1]
                    # Nur Wörter hinzufügen, die aus Buchstaben bestehen (filtert ".", "!", "123" etc. aus)
                    if word.isalpha():
                        # Wort in Kleinbuchstaben umwandeln und zum Set hinzufügen
                        freq_words.add(word.lower())

        # --- Verarbeitung der neuen Wortliste ---
        new_words = set()
        with open(new_list_file_path, 'r', encoding='utf-8') as f2:
            for line in f2:
                # Zeile von überflüssigen Leerzeichen befreien und in Kleinbuchstaben umwandeln
                word = line.strip().lower()
                # Nur hinzufügen, wenn die Zeile nicht leer ist
                if word:
                    new_words.add(word)

        # Die Schnittmenge der beiden Mengen finden, um die gemeinsamen Wörter zu erhalten. [9]
        common_words = list(freq_words.intersection(new_words))
        # Die Ergebnisliste alphabetisch sortieren für eine bessere Übersicht
        common_words.sort()
        return common_words

    except FileNotFoundError as e:
        return f"FEHLER: Datei nicht gefunden - {e.filename}. Bitte überprüfen Sie den Dateinamen und den Speicherort."
    except Exception as e:
        return f"Ein unerwarteter Fehler ist aufgetreten: {e}"

# --- Hauptprogramm ---
# Den Dateinamen hier anpassen:
file1 = "Wortfrequenz.txt"
file2 = "New_list.txt"

# Die Funktion aufrufen, um die gemeinsamen Wörter zu finden
common_words_list = find_common_words_from_structured_files(file1, file2)

# Überprüfen, ob das Ergebnis eine Liste (Erfolg) oder ein String (Fehler) ist
if isinstance(common_words_list, list):
    if common_words_list:
        print(f"Es wurden {len(common_words_list)} gemeinsame Wörter in beiden Listen gefunden:")
        # Nur die ersten 100 zur Vorschau ausgeben, falls die Liste sehr lang ist
        preview_count = 100
        for i, word in enumerate(common_words_list):
            if i < preview_count:
                print(word)
        if len(common_words_list) > preview_count:
            print(f"... und {len(common_words_list) - preview_count} weitere.")

        # Optional: Die komplette Liste in eine neue Datei schreiben
        with open("gemeinsame_woerter.txt", "w", encoding="utf-8") as f_out:
            for word in common_words_list:
                f_out.write(word + "\n")
        print("\nAlle gemeinsamen Wörter wurden in die Datei 'gemeinsame_woerter.txt' gespeichert.")

    else:
        print("Es wurden keine gemeinsamen Wörter in den beiden Listen gefunden.")
else:
    # Hier wird die Fehlermeldung aus dem 'except'-Block ausgegeben
    print(common_words_list)