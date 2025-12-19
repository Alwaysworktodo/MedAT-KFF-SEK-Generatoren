# MedAT – Emotionen erkennen (EE) Generator

Dieses Modul generiert LLM-basierte Übungsaufgaben für den MedAT-Untertest "Emotionen erkennen" und exportiert die Ergebnisse als PDF und JSON.

## Funktionen im Überblick
- Liest Themen/Inspirationen aus `Szenario.txt` (eine Zeile pro Thema, `#`-Kommentare werden ignoriert; Anführungszeichen/Kommas am Zeilenende werden bereinigt).
- Erzeugt pro Aufgabe ein valides JSON mit:
  - `geschichte` (80–120 Wörter, realitätsnah, Hauptfigur mit Namen)
  - `frage` (z. B. "Wie fühlt sich [Name] in dieser Situation?")
  - `emotions_kandidaten` (Liste mit genau 5 Emotionen)
  - `loesungsweg` mit `eher_wahrscheinlich` und `eher_unwahrscheinlich` (jeweils Objekte mit `emotion` und `begruendung`)
- Parallelisierung: Aufgaben werden per ThreadPool (I/O-bound) parallel über die OpenAI API erzeugt.
- PDF-Erzeugung im ReportLab-Layout:
  - Aufgabenbereich (zwei Aufgaben pro Seite durch Seitenumbrüche)
  - pro Aufgabe eine Tabelle mit echten, anklickbaren Kästchen-Spalten: "Emotion", "Eher wahrscheinlich", "Eher unwahrscheinlich"
  - Lösungsbogen am Ende (Begründungen nach Kategorien)
- JSON-Export pro Set
- Batch-Unterstützung: mehrere Sets in einem Lauf

## Projektstruktur (relevant)
- `EE - Generator.py` – Hauptskript (CLI, OpenAI-Aufrufe, Parallelisierung, PDF/JSON-Export)
- `Szenario.txt` – Themenliste (eine Zeile pro Thema)
- `DejaVuSans.ttf` – Schriftdatei für bessere Unicode-Unterstützung (wird beim Start registriert)
- `PDF-Output/` – Zielordner für PDFs
- `Jsons-Output/` – Zielordner für JSON-Dateien
- `requirements.txt` – Python-Abhängigkeiten

## Voraussetzungen
- Python 3.10+
- OpenAI API Key in der Umgebungsvariable `OPENAI_API_KEY`
- Internetzugang

Abhängigkeiten installieren:
```powershell
# Im Ordner c:\Users\Norman\Desktop\experiments\EE ausführen
pip install -r requirements.txt
```

Hinweis: `EE - Generator.py` erwartet `DejaVuSans.ttf` im selben Ordner. Diese Datei ist im Repo vorhanden.

## Nutzung – Aufgaben erzeugen (CLI)
Grundaufrufe (PowerShell auf Windows):

- Ein Set mit 14 Aufgaben (Standard), 5 Worker, Temperatur 1.0:
```powershell
$env:OPENAI_API_KEY="<dein_api_key>"; python ".\EE - Generator.py" --tasks 14 --workers 5 --temp 1.0
```

- Zwei Batches à 10 Aufgaben:
```powershell
python ".\EE - Generator.py" --batches 2 --tasks 10
```

- Schnelltest mit 4 Aufgaben und 3 Workern:
```powershell
python ".\EE - Generator.py" --tasks 4 --workers 3 --temp 0.9
```

Parameter (Auszug):
- `--tasks` (int, Standard: 14) – Anzahl Aufgaben pro Set
- `--batches` (int, Standard: 1) – Anzahl der zu erzeugenden Sets
- `--workers` (int, Standard: 5) – parallele Threads (API-Aufrufe)
- `--temp` (float, Standard: 1.0) – Kreativität/Varianz der LLM-Antworten

## Output & Dateibenennung
Die Ausgabe landet automatisch in den Unterordnern des `EE`-Verzeichnisses.
- JSON: `Jsons-Output/EE_Set_Batch_<batch>_<YYYYMMDD_HHMMSS>_<n>tasks.json`
- PDF: `PDF-Output/EE_Set_Batch_<batch>_<YYYYMMDD_HHMMSS>_<n>tasks.pdf`

Inhalt der PDF:
- Titel mit Anzahl/Zeithinweis
- Aufgaben (mit Text, Frage und Tabelle zum Ankreuzen)
- Lösungsbogen (Begründungen je Kategorie „Eher wahrscheinlich“/„Eher unwahrscheinlich“)

## Themenliste anpassen (`Szenario.txt`)
- Eine Zeile pro Thema, z. B.:
```
Eine Geschichte über ein persönliches Scheitern bei einem wichtigen Projekt.
Die frustrierende Erfahrung im Umgang mit einer langsamen Bürokratie.
```
- Zeilen, die mit `#` beginnen, werden ignoriert.
- Führende/abschließende Anführungszeichen und ein endständiges Komma werden entfernt.
- Der Generator zieht zufällig Themen; wenn der Pool leer ist, wird er wieder aufgefüllt (möglichst ohne Wiederholung pro Set).

## Technische Details
- OpenAI-Aufruf über Chat Completions mit `response_format={"type":"json_object"}`
- Modell ist fest auf `gpt-5-nano-2025-08-07` konfiguriert (nicht ändern)
- PDF: ReportLab, Registrierung `DejaVuSans` (Unicode), Checkboxen als eigene Flowables

## Troubleshooting
- "OpenAI API-Schlüssel nicht gefunden": `OPENAI_API_KEY` in PowerShell setzen oder Shell neu starten.
- `Szenario.txt` leer/nicht gefunden: Das Skript bricht ab. Datei befüllen und erneut starten.
- JSON-Fehler: Falls das LLM einmal kein valides JSON liefert, wird die Aufgabe verworfen; erneut versuchen oder Temperatur/Worker leicht anpassen.
- PDF-Fehler/Font: Sicherstellen, dass `DejaVuSans.ttf` im `EE`-Ordner liegt und `reportlab` installiert ist.

## Entwicklung / Erweiterung
Wesentliche Funktionen/Komponenten in `EE - Generator.py`:
- `load_scenarios_from_file()` – lädt und bereinigt Themenzeilen aus `Szenario.txt`
- `generate_tasks_parallel()` – orchestriert parallele Aufgabenerzeugung (Threads)
- `generate_single_task()` – erzeugt eine Aufgabe (OpenAI-Aufruf + JSON-Parsing)
- `save_tasks_as_json()` – speichert die Aufgabenliste als JSON
- `speichere_aufgaben_als_pdf()` – baut das PDF (Aufgaben + Lösungsbogen)
- CLI-Entry `main()` – Batches steuern, Ordner anlegen, Dateinamen generieren

Bitte die Coding-Präferenzen beachten (keine Modelländerungen, saubere Struktur, keine doppelten Implementierungen).