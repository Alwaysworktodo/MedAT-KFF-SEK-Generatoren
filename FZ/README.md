# MedAT FZ Übungsset Generator

Dieses Skript erzeugt Übungsaufgaben für den MedAT-Untertest Figuren zusammensetzen (FZ). Aus einer zufällig gewählten Zielform
werden Teilstücke erzeugt (Fragmente), die als Bausteine gezeigt werden. Zusätzlich werden Antwortoptionen (A–E) dargestellt und ein
Antwortbogen sowie die grafischen Lösungen erzeugt.

## Funktionsumfang

- Schwierigkeitsgrade: `easy`, `easy-complex`, `medium`, `medium-complex`, `hard`, `hard-complex`, `mixed`, `mixed-complex`
  - `*-complex` erzeugt Splitterlinien mit Knicken (komplexere Schnitte).
  - Je nach Schwierigkeitsgrad variiert die Anzahl der Fragmente.
- Begrenzung der maximalen Fragmentgröße: `--max-piece-fraction`
  - Legt den maximalen Flächenanteil eines einzelnen Teilstücks an der Zielfigur fest (z. B. `0.4` = 40%).
  - Standard: `0.4`. Gültiger/empfohlener Bereich: 0.05–0.95.
- Batch-Erzeugung: Es können mehrere PDFs in einem Lauf erzeugt werden (`--batch-count`).
- Reproduzierbarkeit: Über `--seed` kann der Zufall gesteuert werden.
- Ausgabe:
  - Aufgabenblätter (2 Aufgaben pro Seite)
  - Antwortbogen
  - Lösungsseiten
  - Grafische Lösungen werden als exakte, vereinigte Form mit grauer Füllung und schwarzer Kontur gezeichnet (keine überstehenden Kanten/keine Löcher).

## Installation

Python 3.10+ wird empfohlen. Abhängigkeiten (z. B. `reportlab`, `shapely`, `numpy`) müssen installiert sein. In einer (virtuellen) Umgebung:

```powershell
pip install -r requirements.txt
```

(Die Datei `requirements.txt` liegt ggf. in einem übergeordneten Ordner/Projektteil; andernfalls diese Pakete manuell installieren.)

## Verwendung

Beispiel: Ein PDF mit 15 Aufgaben, Schwierigkeitsgrad "hard", Seed 1234, max. Teilstückgröße 40%:

```powershell
python "FZ.py" --n-items 15 --out-dir ".\output" --seed 1234 --difficulty hard --max-piece-fraction 0.4
```

Weitere Beispiele:

- Drei PDFs nacheinander mit steigendem Seed:

```powershell
python ".\# medat_fz_pdf_generator.py" --n-items 15 --batch-count 3 --out-dir ".\output" --difficulty mixed-comlex
```

- Weniger große Teilstücke (max. 25% Fläche pro Teil):

```powershell
python ".\# medat_fz_pdf_generator.py" --n-items 15 --difficulty medium-complex --max-piece-fraction 0.25
```

## Hinweise zur Ausgabe

- Aufgaben: Oben die Fragmente (Bausteine), darunter Antwortoptionen A–D sowie Option E ("Keine der Antwortmöglichkeiten ist richtig").
- Antwortbogen: Eine separate Seite zum Ankreuzen.
- Lösungen: Pro Aufgabe wird die korrekte Option als Text ("Aufgabe X:  <Buchstabe>") in Schwarz ausgewiesen und rechts die Zielkontur
  als durchgehende, vereinigte Form mit grauer Füllung und schwarzer Kontur gezeichnet. Dadurch werden kleinere Zeichenartefakte (z. B. überstehende Kanten, Löcher) vermieden, die Sichtbarkeit bleibt hoch.

## Tipps

- Mit dem Parameter `--seed` lassen sich identische Sätze erneut erzeugen (nützlich für Tests und Vergleiche).
- `*-complex` eignet sich für fortgeschrittene Nutzer, die unregelmäßigere Schnitte wünschen.
- Der Flächenanteil-Grenzwert `--max-piece-fraction` hilft, zu dominante Teilstücke zu vermeiden (z. B. max. 40% der Zielfläche).

## Lizenz

Interner Gebrauch. Bitte projektinterne Richtlinien beachten.
