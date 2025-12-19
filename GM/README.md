# MedAT GM – Testsimulations‑Generator

Dieses Tool generiert eine komplette PDF‑Simulation der Untergruppe Gedächtnis & Merkfähigkeit (GM) mit:
- Ausweisen (Allergieausweise) inklusive Foto und Datenfeldern
- Multiple‑Choice‑Fragen (A–E, inkl. „Keine der Antwortmöglichkeiten ist richtig.“)
- Antwortbogen (ankreuzbare Kästchen A–E)
- Lösungsbogen (richtige Buchstaben je Aufgabe)

Die Logik und PDF‑Erstellung steckt in `GM Generator.py`.

## Funktionsumfang im Überblick
- Realistische Testdaten pro Ausweis:
  - Name, Geburtstag (Format: `TT. Monat`), Medikamentenstatus (`Ja/Nein`), Blutgruppe (`A/B/AB/0`), Allergien (0–3 je nach Schwierigkeitsgrad), Ausweis‑Nr., Ausstellungsland
  - Pro Ausweis ein einzigartiges Foto aus `resources/images` (`.png` oder `.jpg`)
- Fragenpool (wird zufällig gezogen, Duplikate werden vermieden):
  - Direktes Abrufen von Personendaten (z. B. Blutgruppe, Land, Geburtstag)
  - Zählfragen (z. B. „Wie viele Personen nehmen Medikamente ein?“)
  - Identifikation über einzigartige Allergie (Person finden, die nur einmal vorkommende Allergie hat)
  - Querverweise über Ausweis‑Nr. oder Land (z. B. „Wer kommt aus …?“ bzw. „Wann hat die Person mit Ausweis‑Nr. … Geburtstag?“)
  - Mehrfachbedingungen (z. B. Person, die Kriterien X und Y erfüllt → gesuchte Information Z)
  - Negationsfragen (Aussage, die NICHT zutrifft)
  - Aussagevalidierung (nur eine der Aussagen ist korrekt)
  - Bildbasierte Fragen (Foto wird neben Antwortoptionen angezeigt)
- Antwortoptionen werden automatisch generiert (inkl. plausibler Ablenker); Option E enthält stets „Keine der Antwortmöglichkeiten ist richtig.“ (diese kann korrekt sein)
- PDF‑Ausgabe mit Titel‑/Zeitvorgaben, Ausweis‑Seiten, Fragen‑Teil, Antwortbogen und Lösungen

## Voraussetzungen
- Python 3.x (empfohlen: aktuelle 3.x‑Version)
- Paket `reportlab`

Installation von `reportlab` (PowerShell):
```powershell
pip install reportlab
```

## Ordnerstruktur und Ressourcen
Bitte aus dem Ordner `GM/` heraus ausführen, da das Skript relative Pfade erwartet.

```
GM/
  GM Generator.py
  resources/
    names.txt        # ein Name pro Zeile, keine Leerzeilen
    allergies.txt    # eine Allergie pro Zeile
    countries.txt    # ein Land pro Zeile
    images/          # Portrait‑Bilder (.png/.jpg), je Ausweis ein Bild
  output/            # wird automatisch erstellt; hier landen die PDFs
```
Hinweise:
- `resources/*.txt` dürfen nicht leer sein. Das Skript bricht sonst mit Fehlermeldung ab.
- In `resources/images` müssen genügend Bilder liegen (mindestens so viele wie Ausweise pro Test), Dateiendung `.png` oder `.jpg`.
- Bildformat: Hochformat ist ideal (im PDF ca. 3,5 × 4,5 cm; in bildbasierten Fragen leicht verkleinert).

## Schwierigkeitsgrade
Das Skript bietet vordefinierte Profile, die Anzahl Ausweise und Fragen steuern:

- `sehr-leicht`: 2 Ausweise, 10 Fragen
- `leicht`: 4 Ausweise, 15 Fragen
- `mittel`: 6 Ausweise, 20 Fragen
- `normal` (Standard): 8 Ausweise, 25 Fragen

Die Anzahl Allergien pro Ausweis wird zudem abhängig von der internen Schwierigkeitsverteilung gewählt:
- easy: 0–1 Allergien
- medium: 1–2 Allergien
- difficult: 2–3 Allergien

## Nutzung (PowerShell, Windows)
1) In den `GM`‑Ordner wechseln:
```powershell
cd "c:\Users\Norman\Desktop\experiments\GM"
```

2) Skript ausführen (Standard: `normal`, 1 PDF, Dateiname `MedAT_GM_Simulation.pdf`):
```powershell
python ".\GM Generator.py"
```

### CLI‑Parameter
- `--difficulty {sehr-leicht|leicht|mittel|normal}`
  - Wählt das Profil (siehe oben). Standard: `normal`.
- `--batch <int>`
  - Anzahl der zu erzeugenden unabhängigen Tests in einem Lauf. Bei `> 1` wird `_<laufindex>` an den Dateinamen angehängt.
- `--output <dateiname.pdf>`
  - Basis‑Name der Ausgabedatei(en). Die PDFs werden in `output/` abgelegt.

### Beispielaufrufe
- Leichter Test, Standarddateiname:
```powershell
python ".\GM Generator.py" --difficulty leicht
```

- Mittlerer Test, benannter Output:
```powershell
python ".\GM Generator.py" --difficulty mittel --output "MedAT_GM_Simulation_Mittel.pdf"
```

- Drei Tests am Stück, durchnummeriert:
```powershell
python ".\GM Generator.py" --difficulty normal --batch 3 --output "MedAT_GM_Simulation.pdf"
# erzeugt: output/MedAT_GM_Simulation_1.pdf, _2.pdf, _3.pdf
```

## PDF‑Aufbau
1) Titelseite mit Zeiten (Einprägungs‑/Pause‑/Wiedergabezeit)
2) Ausweise (mehrere pro Seite, mit Rahmen und Daten‑Tabelle)
3) Fragen (je 5 Antwortoptionen A–E; E ist immer „Keine der …“; bei bildbasierten Fragen wird das Porträt eingeblendet)
4) Antwortbogen (einspaltig, Kästchen A–E je Aufgabe)
5) Lösungsbogen (nur Buchstaben A–E je Frage)

## Fehlerbehandlung & Troubleshooting
- „Die Bibliothek 'reportlab' wurde nicht gefunden.“
  - `pip install reportlab` ausführen und erneut starten.
- „Der Ordner 'resources/images' wurde nicht gefunden.“
  - Aus `GM/` starten oder Ordner anlegen und Bilder hinzufügen.
- „Datei nicht gefunden: resources/<datei>.“ oder „Datei … ist leer.“
  - Sicherstellen, dass `names.txt`, `allergies.txt`, `countries.txt` vorhanden und nicht leer sind; je Zeile ein Eintrag.
- „Nicht genügend Bilder …“
  - Genug Bilder in `resources/images` bereitstellen (mindestens so viele wie Ausweise im gewählten Profil).
- Falscher Arbeitsordner
  - Immer zunächst in `GM/` wechseln, da das Skript relative Pfade nutzt.

## Hinweise zur Zufälligkeit
- Jede Ausführung erzeugt neue, zufällige Testdaten und Fragen. Eine Reproduzierbarkeit über mehrere Läufe hinweg ist ohne Anpassung des Codes (z. B. `random.seed(...)`) nicht garantiert.

## Lizenz & Beiträge
- Interne Nutzung. Passen Sie bei Bedarf Ressourcen (Namen, Länder, Allergien, Bilder) an, um Varianten zu erstellen.
