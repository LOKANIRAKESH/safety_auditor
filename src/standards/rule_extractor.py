"""
Standards Rule Extractor — runs the existing LLM pipeline on downloaded
standard documents to extract structured safety rules.

This is the same LLM extraction used for control narratives (Phase 2),
but with a standards-specific prompt that maps clause text to the
SafetyRule schema rather than ControlRule schema.

Output: List[SafetyRule] — stored in the standards knowledge base DB.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from loguru import logger

try:
    import ollama
    OLLAMA_OK = True
except ImportError:
    OLLAMA_OK = False


# ── Output schema ─────────────────────────────────────────────────────────────

@dataclass
class SafetyRule:
    """
    A single safety requirement extracted from a standard document.

    This is the building block of the Standards Knowledge Base.
    Each rule maps to one or more of our IEC 61511 invariant templates
    but is sourced from the actual standard text, not hand-written.
    """
    rule_id:           str         # e.g. "OSHA_PSM_1910_119-R001"
    source_id:         str         # matches StandardSource.source_id
    standard_ref:      str         # e.g. "OSHA 29 CFR 1910.119"
    clause_ref:        str         # e.g. "29 CFR 1910.119(d)(2)"
    requirement_text:  str         # verbatim or paraphrased clause text
    requirement_type:  str         # shutdown | alarm | interlock | setpoint_hierarchy | documentation | tagging
    equipment_classes: List[str]   # e.g. ["Pump", "Compressor", "Valve"]
    sensor_classes:    List[str]   # e.g. ["PressureTransmitter", "TemperatureSensor"]
    condition_type:    str         # HIGH_HIGH | HIGH | LOW | LOW_LOW | ANY | ON_DEMAND
    action_required:   str         # STOP | CLOSE | ALARM | DOCUMENT | VERIFY
    severity_if_missing: str       # HIGH | MEDIUM | LOW
    setpoint_role:     str         # TRIP | ALARM | NORMAL | NONE
    iec_equivalent:    str         # mapped IEC 61511 clause
    confidence:        float = 1.0
    notes:             str = ""


# ── Prompt for standards extraction ───────────────────────────────────────────

_SYSTEM_PROMPT = """You are a process safety expert and IEC 61511 specialist.
You extract structured safety requirements from industrial safety standard documents.
You output only valid JSON. Never output prose."""

def _build_standards_prompt(text: str, source_ref: str, clause_hint: str = "") -> str:
    # Keep the text window short — CPU inference is slow; 2000 chars ≈ 500 tokens
    return f"""Extract safety REQUIREMENTS from this {source_ref} text.
{f'Section: {clause_hint}' if clause_hint else ''}

Return JSON: {{"rules": [{{
  "clause_ref": "...",
  "requirement_text": "one sentence",
  "requirement_type": "shutdown|alarm|interlock|setpoint_hierarchy|documentation|tagging",
  "equipment_classes": ["Pump", ...],
  "sensor_classes": ["PressureTransmitter", ...],
  "condition_type": "HIGH_HIGH|HIGH|LOW|LOW_LOW|ANY|ON_DEMAND",
  "action_required": "STOP|CLOSE|ALARM|DOCUMENT|VERIFY",
  "severity_if_missing": "HIGH|MEDIUM|LOW",
  "setpoint_role": "TRIP|ALARM|NORMAL|NONE",
  "iec_equivalent": "IEC 61511 Cl.X",
  "confidence": 0.0-1.0
}}]}}

Text:
---
{text[:2000]}
---"""


# ── Extractor class ───────────────────────────────────────────────────────────

class StandardsRuleExtractor:
    """
    Runs LLM extraction on downloaded standards PDFs/HTML to produce SafetyRule objects.

    The extraction pipeline mirrors Phase 2 of the main audit pipeline
    (SemanticChunker → EntityExtractor) but uses a standards-specific prompt
    and output schema.
    """

    def __init__(self, llm_model: str = "qwen2.5", llm_temperature: float = 0.05):
        self.llm_model       = llm_model
        self.llm_temperature = llm_temperature
        self._rule_counter   = 0

    # ── Public API ────────────────────────────────────────────────────────────

    # Keywords that signal a chunk is relevant to SIS/safety instrumentation.
    # Non-matching chunks in very large documents are skipped to avoid hours of LLM calls.
    _RELEVANCE_KEYWORDS = re.compile(
        r"safety instrumented|SIS|SIL|interlock|shutdown|relief valve|setpoint|"
        r"alarm|high.high|low.low|trip|ESD|pressure relief|process safety|"
        r"IEC 61511|LOPA|safety integrity|SIF|final element|logic solver",
        re.IGNORECASE,
    )

    def extract_from_pdf(
        self,
        pdf_path:   Path,
        source_id:  str,
        standard_ref: str,
        max_chunks: int = 0,
    ) -> List[SafetyRule]:
        """
        Extract safety rules from a downloaded standards PDF.

        max_chunks: if > 0, skip chunks that don't match _RELEVANCE_KEYWORDS
                    and stop after max_chunks relevant chunks (prevents multi-hour
                    runs on large documents like NIST SP 800-82).
        """
        pdf_path = Path(pdf_path)

        # Auto-detect HTML-disguised-as-PDF (e.g. Emerson page-behind-login)
        with open(pdf_path, "rb") as fh:
            header = fh.read(15)
        if header.lstrip().startswith(b"<"):
            logger.warning(
                f"{pdf_path.name} is HTML not PDF (likely a login wall or redirect). "
                "Routing to extract_from_html()."
            )
            return self.extract_from_html(pdf_path, source_id, standard_ref)

        from src.ingestion.chunker import SemanticChunker
        from src.ingestion.pdf_extractor import PDFExtractor

        logger.info(f"Extracting rules from {pdf_path.name} ({standard_ref})")
        extractor = PDFExtractor()
        blocks    = extractor.extract(pdf_path)

        if not blocks:
            logger.warning(f"{pdf_path.name}: 0 text blocks extracted (scanned/image PDF?)")
            return []

        chunker = SemanticChunker(max_chars=4000, overlap_chars=200)
        chunks  = chunker.chunk(blocks)
        logger.info(f"{pdf_path.name}: {len(blocks)} blocks → {len(chunks)} chunks")

        all_rules: List[SafetyRule] = []
        processed = 0
        skipped   = 0
        for chunk in chunks:
            # For large documents, only process chunks that mention SIS concepts
            if max_chunks > 0 and not self._RELEVANCE_KEYWORDS.search(chunk.text):
                skipped += 1
                continue
            rules = self._extract_chunk(
                chunk.text,
                source_id    = source_id,
                standard_ref = standard_ref,
                clause_hint  = chunk.section_title,
            )
            all_rules.extend(rules)
            processed += 1
            if max_chunks > 0 and processed >= max_chunks:
                logger.info(f"Reached max_chunks={max_chunks} — stopping early")
                break

        if skipped:
            logger.info(f"Skipped {skipped} non-SIS chunks (relevance filter)")
        logger.success(f"Extracted {len(all_rules)} safety rules from {pdf_path.name}")
        return all_rules

    def extract_from_html(
        self, html_path: Path, source_id: str, standard_ref: str
    ) -> List[SafetyRule]:
        """Extract safety rules from a downloaded standards HTML page."""
        try:
            from bs4 import BeautifulSoup
            soup    = BeautifulSoup(html_path.read_text(encoding="utf-8", errors="replace"), "html.parser")
            text    = soup.get_text(separator="\n", strip=True)
        except ImportError:
            # Fallback: strip HTML tags with regex
            raw  = html_path.read_text(encoding="utf-8", errors="replace")
            text = re.sub(r"<[^>]+>", " ", raw)
            text = re.sub(r"[ \t\r]+", " ", text).strip()  # preserve \n for line splitting

        from src.ingestion.chunker import SemanticChunker
        from src.ingestion.pdf_extractor import TextBlock

        # Convert plain text into synthetic TextBlocks for the chunker
        lines  = text.split("\n")
        blocks = []
        for i, line in enumerate(lines):
            if len(line.strip()) < 10:
                continue
            is_heading = (
                len(line.strip()) < 120 and
                (re.match(r"^\d+(\.\d+)*\s", line.strip()) or line.strip().isupper())
            )
            blocks.append(TextBlock(
                text       = line.strip(),
                page       = (i // 40) + 1,
                bbox       = (0, 0, 1, 1),
                source_doc = html_path.name,
                block_type = "heading" if is_heading else "text",
            ))

        chunker   = SemanticChunker(max_chars=4000, overlap_chars=200)
        chunks    = chunker.chunk(blocks)
        all_rules: List[SafetyRule] = []
        for chunk in chunks:
            rules = self._extract_chunk(
                chunk.text,
                source_id    = source_id,
                standard_ref = standard_ref,
                clause_hint  = chunk.section_title,
            )
            all_rules.extend(rules)

        logger.success(f"Extracted {len(all_rules)} rules from {html_path.name}")
        return all_rules

    def extract_from_text(
        self,
        text:         str,
        source_id:    str,
        standard_ref: str,
        clause_hint:  str = "",
    ) -> List[SafetyRule]:
        """Extract rules from a plain text string (e.g. pasted clause text)."""
        from src.ingestion.chunker import SemanticChunker
        from src.ingestion.pdf_extractor import TextBlock

        paras  = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 20]
        blocks = [
            TextBlock(text=p, page=i+1, bbox=(0,0,1,1), source_doc="manual",
                      block_type="text")
            for i, p in enumerate(paras)
        ]
        chunker = SemanticChunker(max_chars=4000, overlap_chars=200)
        chunks  = chunker.chunk(blocks)
        all_rules: List[SafetyRule] = []
        for chunk in chunks:
            rules = self._extract_chunk(
                chunk.text,
                source_id    = source_id,
                standard_ref = standard_ref,
                clause_hint  = clause_hint or chunk.section_title,
            )
            all_rules.extend(rules)
        return all_rules

    # ── Internals ─────────────────────────────────────────────────────────────

    def _extract_chunk(
        self,
        text:         str,
        source_id:    str,
        standard_ref: str,
        clause_hint:  str,
    ) -> List[SafetyRule]:
        if not OLLAMA_OK:
            logger.warning("ollama not available — skipping LLM extraction")
            return []
        if len(text.strip()) < 50:
            return []

        prompt = _build_standards_prompt(text, standard_ref, clause_hint)
        try:
            resp = ollama.chat(
                model    = self.llm_model,
                messages = [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                options  = {"temperature": self.llm_temperature, "num_predict": 512},
                format   = "json",
            )
            raw    = resp["message"]["content"]
            parsed = self._parse_json(raw)
            if not parsed:
                return []
            return [
                self._build_rule(r, source_id, standard_ref)
                for r in parsed.get("rules", [])
            ]
        except Exception as exc:
            logger.warning(f"LLM extraction failed for chunk ({clause_hint}): {exc}")
            return []

    def _build_rule(self, data: dict, source_id: str, standard_ref: str) -> SafetyRule:
        self._rule_counter += 1
        rule_id = f"{source_id}-R{self._rule_counter:04d}"
        return SafetyRule(
            rule_id           = rule_id,
            source_id         = source_id,
            standard_ref      = standard_ref,
            clause_ref        = str(data.get("clause_ref", "")).strip(),
            requirement_text  = str(data.get("requirement_text", "")).strip(),
            requirement_type  = str(data.get("requirement_type", "shutdown")).lower(),
            equipment_classes = data.get("equipment_classes", []),
            sensor_classes    = data.get("sensor_classes", []),
            condition_type    = str(data.get("condition_type", "ANY")).upper(),
            action_required   = str(data.get("action_required", "VERIFY")).upper(),
            severity_if_missing = str(data.get("severity_if_missing", "MEDIUM")).upper(),
            setpoint_role     = str(data.get("setpoint_role", "NONE")).upper(),
            iec_equivalent    = str(data.get("iec_equivalent", "")).strip(),
            confidence        = float(data.get("confidence", 0.8)),
        )

    @staticmethod
    def _parse_json(text: str) -> Optional[dict]:
        text  = text.strip()
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            text = match.group(1)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
        return None
