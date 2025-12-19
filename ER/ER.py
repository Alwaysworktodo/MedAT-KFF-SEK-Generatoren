import os
import re
import json
import time
import random
from datetime import datetime
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse

# PDF generation
from reportlab.platypus import (
	BaseDocTemplate,
	PageTemplate,
	Frame,
	Paragraph,
	Spacer,
	PageBreak,
	KeepTogether,
	Flowable,
	FrameBreak,
	Table,
	TableStyle,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ------------------------------
# Prompt-Vorlage (nicht verändern)
# ------------------------------
LLM_PROMPT_TEMPLATE = """
Du bist ein Experte für die Erstellung von Testaufgaben für den österreichischen Medizin-Aufnahmetest (MedAT), spezialisiert auf den Untertest "Emotionen Regulieren". Deine Aufgabe ist es, eine vollständige und realitätsnahe Testaufgabe zu generieren.
So könnte eine Beispiel situation zb ausschauen: Paul hat vor ein paar Monaten sein Medizinstudium beendet. Schon im Studium hat er begonnen an einigen Forschungsprojekten mitzuarbeiten und hat sich auch seit seinem Abschluss auf die Forschung konzentriert. Als er zufällig von einem neuen Forschungsprojekt liest, für das noch jemand gesucht wird, beschließt er direkt anzurufen. Er ist sehr positiv gestimmt, da er schon viel Erfahrung in dem Bereich hat. Der Herr am Telefon lässt ihn nicht mal ausreden und sagt „Sie glauben doch nicht wirklich, ohne Ph.D. in diesem Bereich arbeiten zu können.“ Paul ist enttäuscht und wütend, aber möchte das Gespräch nicht zu nahe an sich heranlassen."
Nutze das folgende Szenario als kreative Inspiration, um eine einzigartige Situation zu entwerfen. Übernimm das Szenario nicht wörtlich, sondern entwickle daraus eine detaillierte, alltagsnahe Geschichte.
Verwende nicht den Begriff "emotionen Regulieren" in der Aufgabenstellung oder den Antwortmöglichkeiten.
---
**INSPIRATIONS-SZENARIO:**
{scenario_snippet}
---

Erstelle basierend auf dieser Inspiration eine Aufgabe, die folgende Kriterien erfüllt:

1.  **Aufgabenstellung:** Formuliere einen detaillierten Beschreibungstext von 80 bis 120 Wörtern. Die Situation sollte eine Person in einer herausfordernden emotionalen Lage beschreiben und mit "Was soll deiner Meinung nach in dieser Situation gemacht werden?". Der Stil soll dem des MedAT entsprechen.
2.  **Antwortmöglichkeiten:** Erstelle exakt fünf realistische Handlungsoptionen (Option A bis E). Nur eine dieser Optionen darf die beste Strategie zur Emotionsregulation darstellen (konstruktiv, deeskalierend, zielorientiert). Die anderen vier (Distraktoren) müssen plausibel, aber weniger effektiv oder kontraproduktiv sein.
3.  **Richtige Antwort:** Gib den Buchstaben der korrekten Antwort an.
4.  **Lösungsweg:**
	* **warum_richtig:** Erkläre psychologisch fundiert, warum die gewählte Antwort die beste Strategie ist.
	* **warum_falsch:** Erkläre für jede der vier falschen Antworten kurz, warum sie nicht optimal ist.

Stelle das gesamte Ergebnis ausnahmslos als valides JSON-Objekt dar, das exakt der folgenden Struktur entspricht. Füge keine zusätzlichen Texte oder Erklärungen außerhalb des JSON-Formats hinzu.

{
  "aufgabenstellung": "Hier steht der von dir generierte Beschreibungstext (80-120 Wörter)...",
  "antwortmoeglichkeiten": {
	"A": "Antwortmöglichkeit A",
	"B": "Antwortmöglichkeit B",
	"C": "Antwortmöglichkeit C",
	"D": "Antwortmöglichkeit D",
	"E": "Antwortmöglichkeit E"
  },
  "richtige_antwort": "Buchstabe der richtigen Antwort",
  "loesungsweg": {
	"warum_richtig": "Erklärung, warum die richtige Antwort die beste Strategie ist.",
	"warum_falsch": {
	  "A": "Erklärung, warum A falsch ist.",
	  "B": "Erklärung, warum B falsch ist.",
	  "C": "Erklärung, warum C falsch ist.",
	  "D": "Erklärung, warum D falsch ist.",
	  "E": "Erklärung, warum E falsch ist."
	}
  }
}
"""

def render_prompt_with_scenario(scenario_snippet: str) -> str:
	"""Render the prompt by a simple placeholder replacement to avoid format() brace issues."""
	return LLM_PROMPT_TEMPLATE.replace("{scenario_snippet}", scenario_snippet)

# Feste Modellvorgabe (wie gewünscht)
MODEL = "gpt-5-nano-2025-08-07"
VERSION = "ER-Generator 1.1.0"


# ------------------------------
# Einfache LLM-Client-Schicht
# ------------------------------
class LLMClient:
	"""
	Dünne Abstraktionsschicht für LLM-Aufrufe.

	Standard: OpenAI (via Umgebungsvariablen OPENAI_API_KEY, OPENAI_MODEL).
	Austauschbar erweiterbar, ohne den restlichen Code anzupassen.
	"""

	def __init__(self, provider: str = "openai", model: Optional[str] = None):
		self.provider = (provider or os.getenv("LLM_PROVIDER") or "openai").lower()
		# Default-Modell auf vom Nutzer gewünschtes setzen; Umgebungsvariable kann überschreiben
		self.model = model or os.getenv("OPENAI_MODEL") or MODEL
		self._setup()

	def _setup(self):
		if self.provider == "openai":
			try:
				import openai  # type: ignore
			except Exception as e:
				raise RuntimeError(
					"Das Paket 'openai' ist nicht installiert. Bitte mit 'pip install openai' nachrüsten."
				) from e
			self._openai = openai
			api_key = os.getenv("OPENAI_API_KEY")
			if not api_key:
				raise RuntimeError(
					"Fehlende Umgebungsvariable OPENAI_API_KEY. Bitte setzen, um API-Aufrufe zu ermöglichen."
				)
			# Newer OpenAI SDKs use OpenAI() client; keep compatibility with legacy
			try:
				from openai import OpenAI  # type: ignore
				self._client = OpenAI(api_key=api_key)
				# Prefer Responses API
				self._use_responses_api = True
			except Exception:
				# Legacy ChatCompletion API fallback
				self._openai.api_key = api_key
				self._client = None
				self._use_responses_api = False
		else:
			raise NotImplementedError(f"LLM-Provider '{self.provider}' wird aktuell nicht unterstützt.")

	def generate(self, prompt: str, temperature: float = 0.7, max_retries: int = 2, timeout_s: int = 120) -> str:
		last_err = None
		for attempt in range(max_retries + 1):
			try:
				if self.provider == "openai":
					if self._use_responses_api:
						# Responses API
						resp = self._client.responses.create(
							model=self.model,
							input=prompt,
						)
						# Extract text
						text_parts: List[str] = []
						# SDK variants differ; try multiple shapes
						output = getattr(resp, "output", None)
						if output:
							for item in output or []:
								if getattr(item, "type", None) == "message":
									msg = getattr(item, "message", None)
									if msg is not None:
										for c in getattr(msg, "content", []) or []:
											if getattr(c, "type", None) == "text":
												text_parts.append(getattr(c, "text", ""))
						# Newer SDKs expose a flat output_text string
						if not text_parts:
							flat = getattr(resp, "output_text", None)
							if isinstance(flat, str) and flat.strip():
								return flat.strip()
						if not text_parts:
							# Fallback: some SDK variants store in choices
							content = getattr(getattr(resp, "choices", [{}])[0], "message", {}).get("content", "")
							if content:
								return content
						return "\n".join(text_parts).strip()
					else:
						# Legacy Chat Completions
						completion = self._openai.ChatCompletion.create(
							model=self.model,
							messages=[{"role": "user", "content": prompt}],
						)
						return completion["choices"][0]["message"]["content"].strip()
				else:
					raise NotImplementedError
			except Exception as e:
				last_err = e
				# Kurze Backoff-Pause
				time.sleep(1.5 * (attempt + 1))
		raise RuntimeError(f"LLM-Aufruf fehlgeschlagen: {last_err}")


# ------------------------------
# Hilfsfunktionen
# ------------------------------
def read_scenarios(file_path: str) -> List[str]:
	"""Liest Szenario-Snippets (eine Zeile je Fall) und filtert leere Zeilen."""
	with open(file_path, "r", encoding="utf-8") as f:
		lines = [ln.strip() for ln in f.readlines()]
	return [ln for ln in lines if ln]


def _strip_code_fences(s: str) -> str:
	s = s.strip()
	if s.startswith("```"):
		# remove leading fence line
		first_nl = s.find("\n")
		if first_nl != -1:
			s = s[first_nl + 1 :]
	if s.endswith("```"):
		s = s[: -3]
	return s.strip()


def extract_json_candidates(text: str) -> List[str]:
	"""Extract all top-level JSON object substrings by brace matching, after stripping code fences."""
	text = _strip_code_fences(text)
	# Common fenced variants like ```json
	if text.lower().startswith("json\n"):
		text = text[5:]
	buf = []
	stack = []
	starts: List[int] = []
	candidates: List[str] = []
	for i, ch in enumerate(text):
		if ch == '{':
			if not stack:
				starts.append(i)
			stack.append('{')
		elif ch == '}':
			if stack:
				stack.pop()
				if not stack and starts:
					start = starts.pop(0)
					candidates.append(text[start : i + 1].strip())
	# Also consider the greedy slice as fallback
	start = text.find('{')
	end = text.rfind('}')
	if start != -1 and end != -1 and end > start:
		greedy = text[start : end + 1].strip()
		if greedy not in candidates:
			candidates.append(greedy)
	return candidates


def parse_first_valid_json(text: str) -> Dict[str, Any]:
	"""Try parsing from likely candidates; prefer those containing expected keys, try from rightmost to leftmost."""
	cands = extract_json_candidates(text)
	# Prefer candidates that look like our schema
	expected_keys = ["aufgabenstellung", "antwortmoeglichkeiten", "richtige_antwort", "loesungsweg"]
	def score(s: str) -> int:
		sc = 0
		low = s.lower()
		for k in expected_keys:
			if k in low:
				sc += 1
		return sc
	cands.sort(key=lambda s: (score(s), len(s)), reverse=True)
	last_err = None
	for c in cands:
		try:
			return json.loads(c)
		except Exception as e:
			# Try trailing-comma cleanup once
			cleaned = re.sub(r",\s*([}\]])", r"\1", c)
			try:
				return json.loads(cleaned)
			except Exception as e2:
				last_err = e2
				continue
	# If no candidates found, try whole text
	try:
		return json.loads(text)
	except Exception as e3:
		cleaned = re.sub(r",\s*([}\]])", r"\1", text)
		return json.loads(cleaned)


def _sanitize_keys(obj: Any) -> Any:
	"""Recursively sanitize dict keys: trim whitespace/newlines and remove wrapping quotes."""
	if isinstance(obj, dict):
		out: Dict[Any, Any] = {}
		for k, v in obj.items():
			nk = k
			if isinstance(nk, str):
				nk = nk.strip()
				if len(nk) >= 2 and (
					(nk.startswith('"') and nk.endswith('"')) or (nk.startswith("'") and nk.endswith("'"))
				):
					nk = nk[1:-1].strip()
			out[nk] = _sanitize_keys(v)
		return out
	if isinstance(obj, list):
		return [_sanitize_keys(i) for i in obj]
	return obj

def _coerce_to_object(x: Any) -> Any:
	"""Coerce list-of-pairs to dict if needed; otherwise return input unchanged."""
	if isinstance(x, dict):
		return x
	if isinstance(x, list) and all(isinstance(i, (list, tuple)) and len(i) == 2 for i in x):
		out: Dict[str, Any] = {}
		for k, v in x:
			sk = k
			if isinstance(sk, str):
				sk = sk.strip()
				if len(sk) >= 2 and ((sk.startswith('"') and sk.endswith('"')) or (sk.startswith("'") and sk.endswith("'"))):
					sk = sk[1:-1].strip()
			out[str(sk)] = v
		return out
	return x


def normalize_task_schema(obj: Dict[str, Any]) -> Dict[str, Any]:
	"""
	Bringt geringfügig abweichende Antworten in das gewünschte Schema.
	- Sorgt dafür, dass 'antwortmoeglichkeiten' ein Dict mit Schlüsseln A..E ist.
	- Schneidet Whitespace.
	- Validiert erforderliche Felder minimal.
	"""
	required_top = ["aufgabenstellung", "antwortmoeglichkeiten", "richtige_antwort", "loesungsweg"]

	def _canon_map(d: Dict[str, Any]) -> Dict[str, str]:
		m: Dict[str, str] = {}
		for k in d.keys():
			kk = k
			if isinstance(kk, str):
				kk = kk.strip()
				if len(kk) >= 2 and ((kk.startswith('"') and kk.endswith('"')) or (kk.startswith("'") and kk.endswith("'"))):
					kk = kk[1:-1].strip()
				kk = kk.lower()
			m[kk] = k
		return m

	if not isinstance(obj, dict):
		raise ValueError("Antwort ist kein JSON-Objekt.")

	top_map = _canon_map(obj)
	for k in required_top:
		if k not in top_map:
			raise ValueError(f"Fehlendes Feld im JSON: {k}")

	# Normalize answer options
	am = obj[top_map["antwortmoeglichkeiten"]]
	if isinstance(am, list):
		if len(am) != 5:
			raise ValueError("'antwortmoeglichkeiten' Liste hat nicht exakt 5 Elemente.")
		obj["antwortmoeglichkeiten"] = {chr(65 + i): str(v).strip() for i, v in enumerate(am)}
	elif isinstance(am, dict):
		# Ensure keys A..E in order
		keys = ["A", "B", "C", "D", "E"]
		obj["antwortmoeglichkeiten"] = {k: str(am.get(k, "")).strip() for k in keys}
	else:
		raise ValueError("'antwortmoeglichkeiten' muss Liste oder Dict sein.")

	# Clean strings
	obj["aufgabenstellung"] = str(obj[top_map["aufgabenstellung"]]).strip()
	obj["richtige_antwort"] = str(obj[top_map["richtige_antwort"]]).strip().upper()

	# loesungsweg
	lw = obj[top_map["loesungsweg"]]
	if not isinstance(lw, dict):
		raise ValueError("'loesungsweg' muss ein Objekt sein.")
	lw_map = _canon_map(lw)
	if "warum_richtig" not in lw_map or "warum_falsch" not in lw_map:
		raise ValueError("'loesungsweg' muss 'warum_richtig' und 'warum_falsch' enthalten.")
	wf = lw[lw_map["warum_falsch"]]
	if isinstance(wf, dict):
		obj["loesungsweg"]["warum_falsch"] = {k: str(wf.get(k, "")).strip() for k in ["A", "B", "C", "D", "E"]}
	else:
		# Falls als Liste geliefert, kurz transformieren
		if isinstance(wf, list) and len(wf) == 5:
			obj["loesungsweg"]["warum_falsch"] = {chr(65 + i): str(v).strip() for i, v in enumerate(wf)}
		else:
			raise ValueError("'warum_falsch' muss ein Objekt mit Schlüsseln A..E oder eine Liste mit 5 Einträgen sein.")
	obj["loesungsweg"]["warum_richtig"] = str(lw.get(lw_map["warum_richtig"], "")).strip()

	# Basic validations
	if obj["richtige_antwort"] not in ["A", "B", "C", "D", "E"]:
		raise ValueError("'richtige_antwort' muss A..E sein.")
	for k, v in obj["antwortmoeglichkeiten"].items():
		if not v:
			raise ValueError(f"Antwortmöglichkeit {k} ist leer.")

	return obj


def generate_task_from_scenario(client: LLMClient, snippet: str, temperature: float = 0.7) -> Dict[str, Any]:
	prompt = render_prompt_with_scenario(snippet)
	raw = client.generate(prompt, temperature=temperature)
	try:
		obj = parse_first_valid_json(raw)
		obj = _sanitize_keys(_coerce_to_object(obj))
		return normalize_task_schema(obj)
	except Exception as e:
		# Dump raw and candidates for debugging
		try:
			base_dir = os.path.dirname(__file__)
			dbg_dir = os.path.join(base_dir, "Json-Output")
			os.makedirs(dbg_dir, exist_ok=True)
			ts = datetime.now().strftime("%Y%m%d_%H%M%S")
			raw_path = os.path.join(dbg_dir, f"ER_debug_raw_{ts}.txt")
			cand_path = os.path.join(dbg_dir, f"ER_debug_candidates_{ts}.txt")
			with open(raw_path, "w", encoding="utf-8") as f:
				f.write(raw)
			try:
				cands = extract_json_candidates(raw)
			except Exception:
				cands = []
			with open(cand_path, "w", encoding="utf-8") as f:
				for i, c in enumerate(cands, start=1):
					f.write(f"--- CANDIDATE {i} ---\n{c}\n\n")
			raise RuntimeError(f"Parsing der JSON-Antwort fehlgeschlagen. Debug gespeichert unter: {raw_path} und {cand_path}. Ursprünglicher Fehler: {e}")
		except Exception:
			raise


# ------------------------------
# PDF-Erstellung
# ------------------------------
def register_fonts() -> str:
	"""Registriert bevorzugte Schriftarten. Rückgabe: gewählter Fontname."""
	font_name = "Helvetica"
	# Prefer DejaVuSans from repo for unicode support
	try:
		base_dir = os.path.dirname(__file__)
		dejavu_path = os.path.join(base_dir, "..", "EE", "DejaVuSans.ttf")
		dejavu_path = os.path.abspath(dejavu_path)
		pdfmetrics.registerFont(TTFont("DejaVuSans", dejavu_path))
		pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", dejavu_path))
		pdfmetrics.registerFontFamily("DejaVuSans", normal="DejaVuSans", bold="DejaVuSans-Bold")
		font_name = "DejaVuSans"
	except Exception:
		try:
			pdfmetrics.registerFont(TTFont("Verdana", "Verdana.ttf"))
			pdfmetrics.registerFont(TTFont("Verdana-Bold", "Verdanab.ttf"))
			pdfmetrics.registerFontFamily("Verdana", normal="Verdana", bold="Verdana-Bold")
			font_name = "Verdana"
		except Exception:
			font_name = "Helvetica"
	return font_name


def build_styles(font_name: str):
	styles = getSampleStyleSheet()
	for key in ["Normal", "Title", "Heading1", "Heading2", "Heading3"]:
		if key in styles:
			styles[key].fontName = font_name

	# Tuning sizes
	styles["Title"].fontSize = 20
	styles["Title"].leading = 24
	styles["Heading1"].fontSize = 16
	styles["Heading1"].leading = 20
	styles["Heading2"].fontSize = 14
	styles["Heading2"].leading = 18
	styles["Heading3"].fontSize = 12
	styles["Heading3"].leading = 14
	styles["Normal"].fontSize = 10
	styles["Normal"].leading = 13

	styles.add(ParagraphStyle("TaskBody", parent=styles["Normal"], spaceAfter=6))
	styles.add(ParagraphStyle("Option", parent=styles["Normal"], leftIndent=0.6 * cm, spaceBefore=1, spaceAfter=1))
	styles.add(ParagraphStyle("Solution", parent=styles["Normal"], spaceBefore=2, spaceAfter=4))
	return styles


def create_pdf(tasks: List[Dict[str, Any]], filename: str):
	font_name = register_fonts()
	styles = build_styles(font_name)

	class TwoPerPageDoc(BaseDocTemplate):
		def __init__(self, filename, **kw):
			super().__init__(filename, **kw)
			frame_margin_h = 1.6 * cm
			frame_margin_v = 1.2 * cm
			frame_gap = 1.0 * cm
			page_w, page_h = self.pagesize
			frame_height = (page_h - 2 * frame_margin_v - frame_gap)
			frame_height /= 2.0
			frame_width = page_w - 2 * frame_margin_h

			top_frame = Frame(
				frame_margin_h,
				page_h - frame_margin_v - frame_height,
				frame_width,
				frame_height,
				id="top",
				showBoundary=0,
			)
			bottom_frame = Frame(
				frame_margin_h,
				frame_margin_v,
				frame_width,
				frame_height,
				id="bottom",
				showBoundary=0,
			)

			self.addPageTemplates(
				[PageTemplate(id="TwoPerPage", frames=[top_frame, bottom_frame])]
			)

	doc = TwoPerPageDoc(
		filename,
		topMargin=1.2 * cm,
		bottomMargin=1.2 * cm,
		leftMargin=1.6 * cm,
		rightMargin=1.6 * cm,
	)

	story: List[Any] = []

	# Titelblatt als eigene Seite
	story.append(Paragraph("MedAT - Emotionen Regulieren", styles["Title"]))
	story.append(Spacer(1, 0.5 * cm))
	story.append(Paragraph("12 Aufgaben", styles["Heading2"]))
	story.append(Spacer(1, 1.2 * cm))
	today = datetime.now().strftime("%d.%m.%Y %H:%M")
	story.append(PageBreak())

	# Aufgaben: exakt 2 pro Seite mithilfe zweier Frames und FrameBreak
	for idx, t in enumerate(tasks, start=1):
		block: List[Any] = []
		block.append(Paragraph(f"Aufgabe {idx}", styles["Heading3"]))
		block.append(Spacer(1, 0.1 * cm))
		block.append(Paragraph(t["aufgabenstellung"], styles["TaskBody"]))
		block.append(Spacer(1, 0.15 * cm))
		for key in ["A", "B", "C", "D", "E"]:
			block.append(Paragraph(f"<b>{key})</b> {t['antwortmoeglichkeiten'][key]}", styles["Option"]))

		story.append(KeepTogether(block))

		# FrameBreak nur zwischen Aufgaben, nicht nach der letzten
		if idx < len(tasks):
			story.append(FrameBreak())

	# Antwortbogen auf separater Seite (außerhalb des Frame-Systems)
	story.append(PageBreak())
	# Einfacher Antwortbogen als Paragraphs statt Flowable
	story.append(Paragraph("Antwortbogen", styles["Title"]))
	story.append(Spacer(1, 1 * cm))
	
	# Erstelle Antwortbogen als Tabelle für bessere Kontrolle
	answer_data = []
	for i in range(len(tasks)):
		row = [f"Aufgabe {i+1}:"] + ["☐ A", "☐ B", "☐ C", "☐ D", "☐ E"]
		answer_data.append(row)
	
	answer_table = Table(answer_data, colWidths=[3*cm, 1.5*cm, 1.5*cm, 1.5*cm, 1.5*cm, 1.5*cm])
	answer_table.setStyle(TableStyle([
		('FONTNAME', (0, 0), (-1, -1), font_name),
		('FONTSIZE', (0, 0), (-1, -1), 12),
		('LEFTPADDING', (0, 0), (-1, -1), 6),
		('RIGHTPADDING', (0, 0), (-1, -1), 6),
		('TOPPADDING', (0, 0), (-1, -1), 4),
		('BOTTOMPADDING', (0, 0), (-1, -1), 4),
		('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
	]))
	story.append(answer_table)

	# Lösungen mit Begründungen
	story.append(PageBreak())
	story.append(Paragraph("Lösungen", styles["Heading1"]))
	story.append(Spacer(1, 0.3 * cm))  # Kompakter Header-Abstand
	
	for idx, t in enumerate(tasks, start=1):
		sol_block: List[Any] = []
		sol_block.append(Paragraph(f"<b>Aufgabe {idx}: Richtige Antwort: {t['richtige_antwort']}</b>", styles["Solution"]))
		sol_block.append(Paragraph(f"<b>Warum richtig:</b> {t['loesungsweg']['warum_richtig']}", styles["Solution"]))
		sol_block.append(Spacer(1, 0.05 * cm))  # Kompakter Abstand
		wrong = t["loesungsweg"]["warum_falsch"]
		sol_block.append(Paragraph("<b>Warum die anderen Antworten falsch sind:</b>", styles["Solution"]))
		for key in ["A", "B", "C", "D", "E"]:
			if key != t['richtige_antwort'] and key in wrong and wrong[key].strip():
				sol_block.append(Paragraph(f"<b>{key}:</b> {wrong[key]}", styles["Solution"]))
		
		story.append(KeepTogether(sol_block))
		
		# Kompakter, einheitlicher Abstand zwischen Lösungen (nur wenn nicht letzte Lösung)
		if idx < len(tasks):
			story.append(Spacer(1, 0.2 * cm))

	doc.build(story)


# ------------------------------
# Hauptlogik
# ------------------------------
def run_generation(
	num_tasks: int = 12,
	scenario_file: Optional[str] = None,
	out_pdf_dir: Optional[str] = None,
	out_json_dir: Optional[str] = None,
	temperature: float = 1.0,
):
	base_dir = os.path.dirname(__file__)
	scenario_file = scenario_file or os.path.join(base_dir, "Szenario.txt")
	out_pdf_dir = out_pdf_dir or os.path.join(base_dir, "PDF-output")
	out_json_dir = out_json_dir or os.path.join(base_dir, "Json-Output")
	os.makedirs(out_pdf_dir, exist_ok=True)
	os.makedirs(out_json_dir, exist_ok=True)

	scenarios = read_scenarios(scenario_file)
	if not scenarios:
		raise RuntimeError("Keine Szenario-Snippets gefunden.")

	# Ziehe ohne Zurücklegen bis zu num_tasks; wenn weniger vorhanden, mit Wiederholung auffüllen
	random.shuffle(scenarios)
	chosen = scenarios[:num_tasks]
	if len(chosen) < num_tasks:
		while len(chosen) < num_tasks:
			chosen.append(random.choice(scenarios))

	all_tasks: List[Optional[Dict[str, Any]]] = [None] * num_tasks

	def worker(index_snippet):
		index, snip = index_snippet
		print(f"[API] Generiere Aufgabe {index+1}/{num_tasks} …")
		try:
			return index, generate_task_from_scenario(client, snip, temperature=temperature)
		except Exception as e:
			print(f"Warnung: Erster Versuch fehlgeschlagen (Aufgabe {index+1}): {e}. Zweiter Versuch …")
			return index, generate_task_from_scenario(client, snip, temperature=min(0.95, temperature + 0.1))

	if num_tasks > 0:
		client = LLMClient()
		# Parallel: Threads (geeignet für I/O-lastige API-Calls)
		max_workers = min(8, max(2, num_tasks))
		with ThreadPoolExecutor(max_workers=max_workers) as ex:
			futures = [ex.submit(worker, (i, snip)) for i, snip in enumerate(chosen)]
			for fut in as_completed(futures):
				idx, task = fut.result()
				all_tasks[idx] = task

	# type: ignore - alle Einträge sind gefüllt
	all_tasks = [t for t in all_tasks if t is not None]  # type: ignore

	# Gesamt-JSON speichern
	ts = datetime.now().strftime("%Y%m%d_%H%M%S")
	json_path = os.path.join(out_json_dir, f"ER_Set_{ts}.json")
	with open(json_path, "w", encoding="utf-8") as f:
		json.dump(all_tasks, f, ensure_ascii=False, indent=2)
	print(f"JSON gespeichert: {json_path}")

	# PDF speichern
	pdf_path = os.path.join(out_pdf_dir, f"ER_Set_{ts}.pdf")
	create_pdf(all_tasks, pdf_path)
	print(f"PDF gespeichert: {pdf_path}")


def run_batch_generation(
	batch_count: int = 1,
	num_tasks: int = 12,
	scenario_file: Optional[str] = None,
	out_pdf_dir: Optional[str] = None,
	out_json_dir: Optional[str] = None,
	temperature: float = 0.7,
):
	"""Erzeugt mehrere Sets nacheinander."""
	for b in range(batch_count):
		print(f"=== Starte Batch {b+1}/{batch_count} ===")
		run_generation(
			num_tasks=num_tasks,
			scenario_file=scenario_file,
			out_pdf_dir=out_pdf_dir,
			out_json_dir=out_json_dir,
			temperature=temperature,
		)
		print(f"=== Batch {b+1} abgeschlossen ===\n")


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="MedAT ER Generator (LLM-basiert)")
	parser.add_argument("--batches", type=int, default=1, help="Anzahl der Sets (PDF+JSON), die erzeugt werden")
	parser.add_argument("--tasks", type=int, default=12, help="Anzahl Aufgaben pro Set")
	parser.add_argument("--temp", type=float, default=0.7, help="LLM Temperature")
	parser.add_argument("--scenario", type=str, default=None, help="Pfad zur Szenario-Datei")
	parser.add_argument("--pdf-out", type=str, default=None, help="Zielordner für PDFs (Default: ER/PDF-output)")
	parser.add_argument("--json-out", type=str, default=None, help="Zielordner für JSONs (Default: ER/Json-Output)")
	args = parser.parse_args()

	try:
		print(VERSION)
		if args.batches > 1:
			run_batch_generation(
				batch_count=args.batches,
				num_tasks=args.tasks,
				scenario_file=args.scenario,
				out_pdf_dir=args.pdf_out,
				out_json_dir=args.json_out,
				temperature=args.temp,
			)
		else:
			run_generation(
				num_tasks=args.tasks,
				scenario_file=args.scenario,
				out_pdf_dir=args.pdf_out,
				out_json_dir=args.json_out,
				temperature=args.temp,
			)
	except Exception as e:
		print(f"FEHLER: {e}")

