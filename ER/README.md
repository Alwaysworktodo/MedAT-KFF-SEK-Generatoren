# MedAT – Emotionen Regulieren (ER) Generator

Dieses Modul erzeugt LLM-basierte Übungsaufgaben für den MedAT-Untertest "Emotionen Regulieren" und exportiert sie als PDF und JSON.

## Hauptfunktionen
- Liest kurze Szenario-Snippets aus `Szenario.txt` und nutzt sie als Inspiration für realitätsnahe Aufgaben.
- Erzeugt pro Aufgabe:
  - Aufgabenstellung (80–120 Wörter)
  - fünf Antwortmöglichkeiten (A–E)
  - korrekte Antwort (Buchstabe)
  - Lösungsweg mit Begründungen (warum richtig/falsch)
- Robuste JSON-Extraktion und -Normalisierung trotz unterschiedlicher LLM-Ausgabe-Formate.
- Parallele Generierung mehrerer Aufgaben (Threads, I/O-lastig).
- Erstellung eines kompakten PDFs mit 2 Aufgaben pro Seite, Antwortbogen und Lösungssektion.
- Speicherung der Aufgaben als JSON inklusive aller Felder.

## Projektstruktur (relevant)
- `ER.py` – Hauptskript mit:
  - `LLMClient` (dünne Abstraktion für OpenAI-Aufrufe, Responses API bevorzugt, Fallback Chat Completions)
  - Prompt-Rendering, JSON-Parsing/Normalisierung
  - PDF-Renderer (ReportLab)
  - CLI (Argumente, Batch-Mode)
- `Szenario.txt` – Inspirations-Snippets (eine Zeile pro Fall)
- `PDF-Output/` – erzeugte PDFs
- `Json-Output/` – erzeugte JSON-Dateien (inkl. Debug-Dumps bei Parsingfehlern)
- `requirements.txt` – Abhängigkeiten

## Voraussetzungen
- Python 3.10+
- OpenAI API Key in `OPENAI_API_KEY`
- Internetzugang

Abhängigkeiten installieren:
```powershell
# Im Ordner c:\Users\Norman\Desktop\experiments\ER ausführen
pip install -r requirements.txt
```

## Nutzung – Aufgaben erzeugen (CLI)
Standard: 12 Aufgaben, 1 Set, Temperature 0.7.

- Ein Set mit 12 Aufgaben (nutzt `ER/PDF-Output` und `ER/Json-Output`):
```powershell
$env:OPENAI_API_KEY="<dein_api_key>"; python .\ER.py --tasks 12 --temp 0.7
```

- Szenario-Datei wechseln und 6 Aufgaben erzeugen:
```powershell
python .\ER.py --tasks 6 --scenario .\Szenario.txt
```

- Mehrere Sets (Batch): 3 Sets à 8 Aufgaben:
```powershell
python .\ER.py --batches 3 --tasks 8
```

- Ausgabepfade anpassen:
```powershell
python .\ER.py --tasks 10 --pdf-out .\PDF-Output --json-out .\Json-Output
```

## Nutzung – VS Code Tasks
Es sind Aufgaben hinterlegt, die `ER.py` mit sinnvollen Defaults starten. Du findest sie im VS Code Run and Debug/Tasks Panel, z. B.:
- `Run ER generator (1 task quick)`
- `Run ER generator (1 task) no temp`

Diese Tasks setzen voraus, dass `OPENAI_API_KEY` verfügbar ist.

## Output & Dateinamen
- JSON: `ER/Json-Output/ER_Set_<YYYYMMDD_HHMMSS>.json`
- PDF: `ER/PDF-Output/ER_Set_<YYYYMMDD_HHMMSS>.pdf`

Die PDF-Datei enthält:
- Titelseite
- Aufgaben (2 pro Seite, A–E)
- Antwortbogen-Seite
- Lösungssektion mit "Warum richtig" und kompaktem "Warum falsch" je Option

## Wichtige Details & Verhalten
- Modell: Das festgelegte Modell wird nicht geändert (siehe `MODEL` in `ER.py`).
- Robustheit: JSON-Ausgabe wird aus dem LLM-Text extrahiert (inkl. Codefences) und ins gewünschte Schema normalisiert.
- Schriftarten: Versucht, `DejaVuSans` aus `EE/DejaVuSans.ttf` zu registrieren (bessere Unicode-Unterstützung); fällt auf `Verdana`/`Helvetica` zurück.
- Parallelisierung: Thread-basiert, bis zu 8 Worker (I/O-bound).
- Fehlerfälle: Bei Parsingfehlern werden Rohantwort und JSON-Kandidaten in `Json-Output` als Debug-Dateien abgelegt.

## Troubleshooting
- "Fehlende Umgebungsvariable OPENAI_API_KEY": API-Key setzen oder in die Shell exportieren.
- `openai` nicht gefunden: `pip install -r requirements.txt` erneut ausführen.
- Leeres/ungültiges JSON: Skript erzeugt Debug-Dumps; erneuter Versuch oder `Szenario.txt` prüfen.
- PDF-Fehler: Sicherstellen, dass `reportlab` installiert und die Output-Ordner schreibbar sind.

## Entwicklung / Erweiterung
Wichtige Funktionen/Klassen in `ER.py`:
- `LLMClient.generate(prompt, temperature)` – LLM-Aufruf (Responses API bevorzugt)
- `generate_task_from_scenario(client, snippet, temperature)` – Prompting, Parsing und Normalisierung
- `run_generation(num_tasks, scenario_file, out_pdf_dir, out_json_dir, temperature)` – Ein Set erzeugen und speichern
- `run_batch_generation(batch_count, ...)` – Mehrere Sets sequenziell erstellen
- `create_pdf(tasks, filename)` – PDF-Erstellung (2 Aufgaben pro Seite, Antwortbogen, Lösungen)

Bitte beachte die Coding-Präferenzen im Projekt (keine Modelländerungen, keine doppelten Implementierungen, saubere Struktur).