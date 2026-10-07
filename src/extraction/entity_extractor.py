"""Phase 2 — LLM entity and rule extraction via Ollama."""
from __future__ import annotations
import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import ollama
from loguru import logger
from src.extraction.prompts import SYSTEM_PROMPT, build_extraction_prompt
from src.config import PipelineConfig


@dataclass
class ExtractedEntity:
    tag: str
    entity_class: str
    subclass: str
    description: str
    source_doc: str
    source_page: int
    source_modality: str  # "narrative" | "table" | "pid"
    confidence: float = 1.0
    needs_review: bool = False


@dataclass
class ExtractedRule:
    rule_id: str
    equipment_tag: str
    condition_tag: str
    condition_operator: str   # >=, <=, >, <, ==, !=
    condition_threshold: float
    condition_unit: str
    action: str               # STOP, START, OPEN, CLOSE, ALARM, ACTIVATE
    rule_type: str            # shutdown, control, emergency_shutdown, interlock, alarm
    trigger_tag: Optional[str]
    source_doc: str
    source_page: int
    source_modality: str
    confidence: float = 1.0
    needs_review: bool = False
    ambiguity_note: Optional[str] = None


@dataclass
class ExtractionResult:
    entities: List[ExtractedEntity] = field(default_factory=list)
    rules: List[ExtractedRule] = field(default_factory=list)
    low_confidence_count: int = 0
    extraction_errors: List[str] = field(default_factory=list)


class EntityExtractor:
    """Extracts ICS entities and control rules from text using a local LLM via Ollama."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self._rule_counter = 0

    def extract_from_text_blocks(
        self, text_blocks: List[Any], source_modality: str = "narrative"
    ) -> ExtractionResult:
        result = ExtractionResult()

        # Group blocks by page for efficiency (send page-sized chunks to LLM)
        pages: Dict[int, List[str]] = {}
        for block in text_blocks:
            pages.setdefault(block.page, []).append(block.text)

        for page_num, texts in sorted(pages.items()):
            combined = "\n".join(texts)
            if len(combined.strip()) < 20:
                continue
            page_result = self._extract_page(
                text=combined,
                source_doc=text_blocks[0].source_doc if text_blocks else "unknown",
                page=page_num,
                source_modality=source_modality,
            )
            result.entities.extend(page_result.entities)
            result.rules.extend(page_result.rules)
            result.low_confidence_count += page_result.low_confidence_count
            result.extraction_errors.extend(page_result.extraction_errors)

        logger.info(
            f"Extraction complete: {len(result.entities)} entities, {len(result.rules)} rules, "
            f"{result.low_confidence_count} flagged for review"
        )
        return result

    def extract_from_table(self, table: Any, source_modality: str = "table") -> ExtractionResult:
        """Convert a cause-effect table into extraction results directly."""
        result = ExtractionResult()
        df = table.dataframe

        for _, row in df.iterrows():
            row_text = " | ".join(f"{col}: {val}" for col, val in row.items() if str(val).strip())
            if len(row_text) < 10:
                continue
            page_result = self._extract_page(
                text=row_text,
                source_doc=table.source_doc,
                page=table.page,
                source_modality=source_modality,
            )
            result.entities.extend(page_result.entities)
            result.rules.extend(page_result.rules)

        return result

    def _extract_page(
        self, text: str, source_doc: str, page: int, source_modality: str
    ) -> ExtractionResult:
        prompt = build_extraction_prompt(text, source_doc=source_doc, page=page)
        result = ExtractionResult()

        try:
            raw = self._call_llm(prompt)
            parsed = self._parse_json(raw)
            if not parsed:
                result.extraction_errors.append(f"JSON parse failed on {source_doc} p.{page}")
                return result

            for e_data in parsed.get("entities", []):
                try:
                    entity = self._build_entity(e_data, source_doc, page, source_modality)
                    if entity.confidence < self.config.extraction_confidence_threshold:
                        entity.needs_review = True
                        result.low_confidence_count += 1
                    result.entities.append(entity)
                except (KeyError, ValueError) as err:
                    result.extraction_errors.append(f"Entity parse error: {err}")

            for r_data in parsed.get("rules", []):
                try:
                    rule = self._build_rule(r_data, source_doc, page, source_modality)
                    if rule.confidence < self.config.extraction_confidence_threshold:
                        rule.needs_review = True
                        result.low_confidence_count += 1
                    result.rules.append(rule)
                except (KeyError, ValueError) as err:
                    result.extraction_errors.append(f"Rule parse error: {err}")

        except Exception as exc:
            logger.error(f"LLM extraction failed on {source_doc} p.{page}: {exc}")
            result.extraction_errors.append(str(exc))

        return result

    def _call_llm(self, prompt: str) -> str:
        try:
            response = ollama.chat(
                model=self.config.llm_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                options={"temperature": self.config.llm_temperature},
                format="json",
            )
            return response["message"]["content"]
        except Exception as e:
            logger.warning(f"Primary model {self.config.llm_model} failed: {e}. Trying fallback.")
            response = ollama.chat(
                model=self.config.llm_fallback_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                options={"temperature": self.config.llm_temperature},
            )
            return response["message"]["content"]

    @staticmethod
    def _parse_json(text: str) -> Optional[Dict]:
        text = text.strip()
        # Extract JSON block if wrapped in markdown code fences
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            text = match.group(1)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract the first JSON object
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
        return None

    def _build_entity(self, data: Dict, source_doc: str, page: int, modality: str) -> ExtractedEntity:
        return ExtractedEntity(
            tag=str(data.get("tag", "UNKNOWN")).upper().strip(),
            entity_class=data.get("class", "Unknown"),
            subclass=data.get("subclass", ""),
            description=data.get("description", ""),
            source_doc=source_doc,
            source_page=page,
            source_modality=modality,
            confidence=float(data.get("confidence", 0.8)),
        )

    def _build_rule(self, data: Dict, source_doc: str, page: int, modality: str) -> ExtractedRule:
        self._rule_counter += 1
        cond = data.get("condition", {}) or {}
        rule_id = f"R{self._rule_counter:04d}" if data.get("rule_id") == "auto" else data.get("rule_id", f"R{self._rule_counter:04d}")
        return ExtractedRule(
            rule_id=rule_id,
            equipment_tag=str(data.get("equipment") or "UNKNOWN").upper().strip(),
            condition_tag=str(cond.get("tag") or "UNKNOWN").upper().strip(),
            condition_operator=cond.get("operator") or ">=",
            condition_threshold=float(cond.get("threshold") or 0.0),
            condition_unit=cond.get("unit", ""),
            action=str(data.get("action", "UNKNOWN")).upper().strip(),
            rule_type=data.get("rule_type", "control"),
            trigger_tag=data.get("trigger_tag"),
            source_doc=source_doc,
            source_page=page,
            source_modality=modality,
            confidence=float(data.get("confidence", 0.8)),
            ambiguity_note=data.get("ambiguity_note"),
        )
