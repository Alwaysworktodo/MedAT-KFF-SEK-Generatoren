# MedAT – Zahlenfolgen (ZF) Generator

Dieses Tool erzeugt Übungs-PDFs für den Untertest „Zahlenfolgen“. Es generiert pro PDF Aufgabenblätter, einen Antwortbogen (A–E) und einen Lösungsbogen.

Implementierung: `ZF-generator.py`

## Funktionsumfang
- Verschiedene Folgentypen:
  - Arithmetisch (konstante Differenz)
  - Multiplikativ (konstantes Verhältnis)
  - Fibonacci (Summe der zwei vorhergehenden Werte)
  - Mehrstufig (Rechenschritte bilden selbst eine arithmetische Folge)
  - Wechselnde Operationen (z. B. ×a, −b im Wechsel)
  - Verschachtelte Folgen (3er- oder 4er-Sprünge, inkl. A‑B‑A‑B‑Muster)
- Automatische Distraktoren und optionale „E ist richtig“‑Fälle (standardmäßig 20% Wahrscheinlichkeit)
- PDF mit:
  - Titel/Meta (Zeit, Schwierigkeit)
  - Aufgaben (5 pro Seite)
  - Antwortbogen (FZ‑Style: Kästchen A–E)
  - Lösungsbogen (korrekter Buchstabe, letzte Zahlen und Regelbeschreibung)
- Deduplizierung: Identische Aufgaben werden in einem Lauf vermieden

## Voraussetzungen
- Python 3.x
- Paket `reportlab`

Installation (PowerShell):
```powershell
pip install reportlab
```

## Ordnerstruktur
```
ZF/
  ZF-generator.py
  output/                # wird automatisch erstellt; PDFs landen hier
```

## Nutzung (PowerShell, Windows)
1) In den ZF‑Ordner wechseln:
```powershell
cd "c:\Users\Norman\Desktop\experiments\ZF"
```

2) Generator starten (Standard: alle Schwierigkeitsgrade, 1 PDF je Grad, 10 Aufgaben):
```powershell
python ".\ZF-generator.py"
```
Die Dateien werden in `ZF/output/` erzeugt, z. B.:
- `MedAT_Uebung_Einfach_1.pdf`
- `MedAT_Uebung_Mittel_1.pdf`
- `MedAT_Uebung_Schwer_1.pdf`

## CLI-Optionen und Beispiele
- `--difficulty {Einfach|Mittel|Schwer|all}`
  - Welcher Schwierigkeitsgrad generiert werden soll (Standard: `all` generiert alle drei).
- `--num-sequences, -n <int>`
  - Anzahl Aufgaben pro PDF (Standard: 10).
- `--batch <int>`
  - Anzahl der PDFs je Schwierigkeitsgrad (Standard: 1). Bei Werten > 1 wird eine Laufnummer angehängt.
- `--output-dir <pfad>`
  - Ausgabeordner relativ zum Skript (Standard: `output`).
- `--base-name <name>`
  - Basisname der PDFs (Standard: `MedAT_Uebung`).

Beispiele (PowerShell):
- Nur „Mittel“, 10 Aufgaben, eine PDF:
```powershell
python ".\ZF-generator.py" --difficulty Mittel
```

- „Schwer“, 12 Aufgaben, 3 PDFs:
```powershell
python ".\ZF-generator.py" --difficulty Schwer -n 12 --batch 3
```

- Alle Schwierigkeitsgrade, 2 PDFs pro Grad, Ausgabe nach `out/` mit Basisname `ZF_Set`:
```powershell
python ".\ZF-generator.py" --difficulty all --batch 2 --output-dir out --base-name ZF_Set
```

## Konfiguration im Code
- Wahrscheinlichkeit, dass „E“ korrekt ist (`E_IS_CORRECT_PROBABILITY`) steht am Anfang der Datei (Standard: 0.20).

## Troubleshooting
- „ModuleNotFoundError: reportlab …“ → `pip install reportlab`
- PDF wird nicht erzeugt / Ordner fehlt → `ZF/output/` wird automatisch angelegt; bei Fehlern erneut starten und Schreibrechte prüfen.
- Zu „wilde“ Zahlen → Parameterbereiche in den Sequenzklassen anpassen (Startwerte, Differenzen, Verhältnisse), falls nötig.

## Schnellstart
```powershell
cd "c:\Users\Norman\Desktop\experiments\ZF"
pip install reportlab
python ".\ZF-generator.py" --difficulty all --batch 1 -n 10
```

Viel Erfolg beim Trainieren der Zahlenfolgen!