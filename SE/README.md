# MedAT – Soziales Entscheiden (SE) Generator

Dieser Ordner enthält ein Skript zur automatischen Generierung von Übungsaufgaben für den MedAT-Untertest "Soziales Entscheiden". Die Aufgaben werden per OpenAI-API erzeugt und als PDF im MedAT-ähnlichen Layout exportiert. Optional können die Aufgaben zusätzlich als JSON gespeichert werden.

## Hauptfunktionen
- Generiert einzelne oder mehrere SE-Aufgaben auf Basis von Themen aus `themen.txt`.
- Nutzt die OpenAI Chat Completions API, erzwingt JSON-Output und validiert die Struktur.
- Mischt die Antwortreihenfolge pro Aufgabe und mappt Lösung und Kohlberg-Zuordnung korrekt um.
- Erzeugt ein übersichtliches PDF im A4-Format mit Aufgaben und separater Lösungsseite.
- Speichert die generierten Aufgaben optional als JSON.
- Batch-Unterstützung: Mehrere unabhängige Sets in einem Lauf erzeugen.

## Projektstruktur (relevant)
- `SE.py` – Haupteinstiegspunkt und Generator-Klasse `MedATSEGenerator`.
- `themen.txt` – Themenliste; pro Zeile ein Thema (wird zufällig gezogen, sofern kein Thema angegeben wird).
- `requirements.txt` – Python-Abhängigkeiten für dieses Modul.
- `output/` – Zielordner für generierte PDFs und JSON-Dateien (wird automatisch erstellt).

## Voraussetzungen
- Python 3.10+ empfohlen.
- Ein gültiger OpenAI API Key in der Umgebungsvariable `OPENAI_API_KEY` oder via CLI-Parameter `--api-key`.
- Internetzugang, damit die API-Anfragen erfolgreich sind.

## Installation
1. (Empfohlen) Virtuelle Umgebung verwenden.
2. Abhängigkeiten installieren:

```powershell
# Im Ordner c:\Users\Norman\Desktop\experiments\SE ausführen
pip install -r requirements.txt
```

Hinweis: In diesem Ordner existiert ggf. bereits eine lokale `venv/`. Nutzen Sie wahlweise diese oder Ihre eigene Umgebung.

## Benutzung (Aufgaben erzeugen)
Das Skript kann direkt ausgeführt werden und bietet mehrere Optionen.

Grundaufruf:

```powershell
python .\SE.py
```

Wichtige Optionen:
- `--count`, `-c` – Anzahl der zu generierenden Aufgaben pro Set (Standard: 2). Beispiel: `--count 5`
- `--api-key` – OpenAI API Key (optional, wenn `OPENAI_API_KEY` nicht gesetzt ist)
- `--output`, `-o` – Basisname für Output-Dateien (ohne Erweiterung). Zeitstempel und Set-Index werden ergänzt.
- `--json-only` – Nur JSON speichern, kein PDF erzeugen.
- `--batch` – Anzahl unabhängiger Sets in einem Lauf, z.B. `--batch 3` erzeugt drei getrennte Dateien pro Typ.

Beispiele:

1) Ein Set mit 5 Aufgaben (PDF + JSON), API-Key aus Umgebungsvariable:
```powershell
$env:OPENAI_API_KEY="<dein_api_key>"; python .\SE.py --count 5
```

2) Nur JSON für 3 Aufgaben als Set, benannter Output:
```powershell
python .\SE.py --count 3 --json-only --output SE_Set
```

3) Drei unabhängige Sets mit je 2 Aufgaben (Standard):
```powershell
python .\SE.py --batch 3
```

4) API-Key direkt übergeben:
```powershell
python .\SE.py --count 4 --api-key "sk-..."
```

## Output
Alle Dateien werden im Ordner `output/` abgelegt.
- PDF: `MedAT_SE_Simulation_<timestamp>_set<idx>_<n>tasks.pdf` oder, falls `--output` gesetzt ist, `<output>_set<idx>_<timestamp>.pdf`
- JSON: `MedAT_SE_Tasks_<timestamp>_set<idx>.json` oder `<output>_tasks_set<idx>_<timestamp>.json`

Jedes PDF enthält:
- Titelseite und Hinweise
- Aufgaben mit Antworttabelle (A–E) und Ankreuz-Feldern
- Lösungsseite mit Reihenfolge (z. B. `A<B<C<D<E`) und der Kohlberg-Zuordnung

## Themen anpassen
Die Datei `themen.txt` enthält die potenziellen Dilemma-Themen (eine Zeile pro Thema). Beim Generieren zieht das Skript zufällig Themen aus dieser Liste und versucht Wiederholungen innerhalb eines Sets zu vermeiden. Passen Sie die Liste frei an und speichern Sie die Datei in UTF-8.

## Hinweise und Grenzen
- Das in `SE.py` konfigurierte Modell sowie das API-Verhalten sollten nicht verändert werden.
- Für die PDF-Erstellung wird die Schriftart Helvetica verwendet (ReportLab Standard). Sonderzeichen werden durch eine PDF-sichere Bereinigung minimiert. Achten Sie darauf, Themen und Texte in normaler deutscher Sprache zu halten.
- Bei API-Fehlern oder leeren Antworten erfolgt Logging auf der Konsole; JSON-Parsing-Fehler werden angezeigt.
- Die Antworten werden gemischt; Lösung und Kohlberg-Mapping werden automatisch an die neue Reihenfolge angepasst.

## Troubleshooting
- "OpenAI API Key nicht gefunden": Setzen Sie `OPENAI_API_KEY` oder übergeben Sie `--api-key`.
- PDF wird nicht erstellt: Prüfen Sie Schreibrechte im Ordner `output/` und ob `reportlab` korrekt installiert ist.
- JSON-Fehler: Die Antwort der API konnte nicht als gültiges JSON interpretiert werden. Erneut ausführen (Netzwerk/Rate-Limits) oder Thema-Liste anpassen.

## Entwicklung / Erweiterung
- Kernklasse: `MedATSEGenerator`
  - `generate_task(theme: str | None) -> dict`
  - `generate_multiple_tasks(count: int) -> list[dict]`
  - `create_pdf(tasks: list[dict], filename: str | None) -> str`
  - `save_tasks_json(tasks: list[dict], filename: str | None) -> str`
- CLI-Einstieg: `main()` in `SE.py`

Bitte die Coding-Präferenzen beachten (keine doppelten Implementierungen, keine Model-Änderungen, saubere Struktur).