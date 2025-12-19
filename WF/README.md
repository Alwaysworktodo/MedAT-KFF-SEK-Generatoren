# MedAT – Wortflüssigkeit (WF) Generator

Dieses Tool erzeugt Übungs-PDFs für den Untertest „Wortflüssigkeit“. Pro PDF werden mehrere Rätsel generiert, dazu ein Antwortbogen (A–E) und ein Lösungsbogen.

Die Implementierung befindet sich in `WF-Generator.py`.

## Funktionsumfang
- Auswahl geeigneter Wörter aus einer Wortliste (Standard: `finale_uebereinstimmungen30x40.txt`)
  - Nur Wörter mit ausreichend Länge je nach Schwierigkeitsgrad
  - Nur Wörter mit mindestens 4 unterschiedlichen Buchstaben (damit 1 richtige + 3 falsche Optionen möglich sind)
  - Jedes Wort wird pro Lauf nur einmal verwendet (keine Dopplungen)
- Generierung pro Aufgabe:
  - Anagramm des Lösungsworts (Buchstaben werden zufällig angeordnet)
  - Antwortoptionen a–d: einzelne Buchstaben aus dem Lösungswort (inkl. genau einem korrekten Anfangsbuchstaben)
  - Option e) „Keine Antwort ist richtig“ wird ergänzend aufgeführt
  - Lösungsspeicherung inkl. korrekter Auswahl und vollständigem Lösungswort
- PDF-Erstellung mit ReportLab:
  - Titelseite (z. B. „Wortflüssigkeit – Testzeit 20 min“ und Schwierigkeitsgrad)
  - Aufgabenseiten (mehrere Aufgaben pro Seite)
  - Antwortbogen (FZ-Style: Kästchen A–E je Aufgabe)
  - Lösungsbogen (Auflistung der richtigen Optionen und des Lösungsworts)
- Batch-Erzeugung mehrerer, eindeutiger PDFs in einem Lauf (`batch_create_pdfs`)
  - Ausgabe-Namen: `Wortflüssigkeit_<difficulty>_<laufindex>.pdf`
  - Ausgabeordner: standardmäßig `Batch_PDFs`

Hinweis: In dieser Implementierung ist die richtige Option stets eine der Buchstabenoptionen a–d. Die Option „e) Keine Antwort ist richtig“ dient als zusätzliche Antwortmöglichkeit.

## Schwierigkeitsgrade
Die Schwierigkeitsgrade bestimmen die Wortlängenbereiche:
- `easy`:   5–9 Zeichen
- `medium`: 7–12 Zeichen
- `hard`:   10–15 Zeichen
- `full`:   5–15 Zeichen (voller Bereich)

## Voraussetzungen
- Python 3.x
- Python-Paket `reportlab`

Installation (PowerShell):
```powershell
pip install reportlab
```

## Ordnerstruktur und Ressourcen
```
WF/
  WF-Generator.py
  finale_uebereinstimmungen30x40.txt   # Wortliste, ein Wort pro Zeile (UTF‑8)
  Batch_PDFs/                           # Ausgabeordner (wird automatisch erstellt)
```
Die Wortliste wird relativ zum Skriptpfad aufgelöst. Du kannst das Skript daher aus beliebigen Arbeitsverzeichnissen starten, solange sich die Wortliste im WF-Ordner befindet (bzw. der konfigurierte Pfad korrekt ist).

## Nutzung (PowerShell, Windows)
1) In den Ordner `WF` wechseln:
```powershell
cd "c:\Users\Norman\Desktop\experiments\WF"
```

2) Generator starten (verwendet die Konfiguration am Dateiende):
```powershell
python ".\WF-Generator.py"
```
Standardmäßig sind im Skript konfiguriert:
- `DIFFICULTY = "hard"`
- `PUZZLES_PER_PDF = 15`
- `NUMBER_OF_PDFS = 5`

Die PDFs werden in `WF/Batch_PDFs/` erzeugt, z. B. `Wortflüssigkeit_hard_001.pdf`, `Wortflüssigkeit_hard_002.pdf`, ...

## Konfiguration anpassen
Am Ende von `WF-Generator.py` findest du die zentrale Konfiguration:
- `DIFFICULTY` → `"easy" | "medium" | "hard" | "full"`
- `PUZZLES_PER_PDF` → Anzahl Aufgaben pro PDF (z. B. 10–20)
- `NUMBER_OF_PDFS` → Anzahl der zu erzeugenden PDFs im Batch

Wenn du den Ausgabeordner ändern möchtest, kannst du beim Aufruf der Methode `batch_create_pdfs` den Parameter `output_dir` anpassen, z. B.:
```python
generator.batch_create_pdfs(
    difficulty="medium",
    num_puzzles=12,
    num_batches=3,
    output_dir="Batch_PDFs"  # oder z. B. "output"
)
```

## Hinweise zur Wortliste
- Mindestens so viele eindeutige Wörter erforderlich wie `PUZZLES_PER_PDF * NUMBER_OF_PDFS`.
- Wenn die Wortliste nicht genügend geeignete Wörter enthält, wird der Batch vorzeitig beendet (mit Hinweis).

## Troubleshooting
- „FEHLER: Die Wortliste '…' wurde nicht gefunden.“
  - Stelle sicher, dass `finale_uebereinstimmungen30x40.txt` im WF-Ordner liegt oder passe den Pfad im Konstruktor `PuzzleGenerator(word_list_path=...)` an.
- „WARNUNG: Nicht genügend Wörter …“ / leere PDFs
  - Wortliste erweitern oder die Konfiguration (`PUZZLES_PER_PDF`, `NUMBER_OF_PDFS`) reduzieren.
- „ModuleNotFoundError: reportlab …“
  - Mit `pip install reportlab` installieren.

## Schnellstart (kompakt)
```powershell
cd "c:\Users\Norman\Desktop\experiments\WF"
pip install reportlab
python ".\WF-Generator.py"
```

Viel Erfolg beim Generieren der WF-Übungen!