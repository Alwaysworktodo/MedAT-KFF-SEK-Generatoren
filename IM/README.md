# MedAT – KFF (Implikationen erkennen) Generator

Dieses Tool generiert Übungs-PDFs für den Untertest „Implikationen erkennen“ (Syllogismen). Es erzeugt pro PDF mehrere Aufgaben mit:
- Zwei Prämissen pro Aufgabe
- Antwortmöglichkeiten A–D (Schlussfolgerungen) und E = „Keine der Schlussfolgerungen ist richtig.“
- Antwortbogen (A–E je Aufgabe)
- Lösungsschlüssel (A–E pro Aufgabe)

Die Logik und PDF-Erstellung sind in `IM - Generator.py` implementiert.

## Funktionsumfang
- Vollständig implementierte, gültige Syllogismenformen (z. B. Barbara, Celarent, Darii, Ferio, …)
- Automatische Generierung plausibler Distraktoren (keine Duplikate, keine Prämissen als Optionen)
- Zufällige Wahl der Terme aus einer Wortliste (`words.txt`)
- Mehrere PDFs in einem Lauf (Batch), nummeriert: `KFF_Simulation_1.pdf`, `KFF_Simulation_2.pdf`, …
- Ausgabe in `IM/output/`

## Voraussetzungen
- Python 3.x
- Datei `words.txt` im Ordner `IM/` mit mindestens 3 Begriffen (ein Begriff pro Zeile)

Beispiel für `words.txt`:
```
Theorien
Algorithmen
Kristalle
Melodien
Strukturen
```

## Ordnerstruktur
```
IM/
  IM - Generator.py
  words.txt
  output/                 # wird automatisch erstellt
```

## Nutzung (PowerShell auf Windows)
1) In den IM-Ordner wechseln:
```powershell
cd "c:\Users\Norman\Desktop\experiments\IM"
```

2) Generator starten (Standardwerte im Skript):
```powershell
python ".\IM - Generator.py"
```

Standardkonfiguration im Skript:
- `BATCH_ANZAHL = 5`  → erzeugt 5 PDFs
- `FRAGEN_PRO_PDF = 10` → 10 Aufgaben je PDF
- Ausgabe in `IM/output/`

Die erstellten PDFs heißen dann z. B. `output/KFF_Simulation_1.pdf`, `output/KFF_Simulation_2.pdf`, …

## Parameter anpassen
Die Konfiguration befindet sich am Ende von `IM - Generator.py`:
- `BATCH_ANZAHL` → Anzahl PDFs pro Lauf
- `FRAGEN_PRO_PDF` → Anzahl Aufgaben pro PDF
- `WORT_DATEI` → Pfad zur Wortliste (Standard: `words.txt` im IM-Ordner)

## Fehlerbehandlung & Tipps
- „Die Datei 'words.txt' wurde nicht gefunden.“
  - Lege eine `words.txt` neben das Skript. Mindestens 3 Zeilen.
- „Die Datei 'words.txt' ist leer.“
  - Fülle die Wortliste (ein Begriff pro Zeile).
- PDF wird nicht erstellt / Ordner fehlt
  - Der Ordner `output/` wird automatisch angelegt. Bei Problemen erneut starten und ggf. Schreibrechte prüfen.

## Hinweis zur Zufälligkeit
- Jede Ausführung erzeugt neue, zufällige Aufgaben. Für Reproduzierbarkeit könntest du im Code `random.seed(<zahl>)` setzen (optional).
