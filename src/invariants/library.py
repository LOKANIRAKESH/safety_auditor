"""Phase 6 — SafetyInvariantLibrary: matches invariants to extracted rules."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from loguru import logger
from src.invariants.loader import InvariantLoader
from src.ir.rule_model import ControlRule, RuleAction, RuleType
from src.config import PipelineConfig


@dataclass
class SafetyInvariant:
    invariant_id: str
    iec_clause: str
    category: str
    description: str
    applicable_equipment_classes: List[str]
    applicable_sensor_classes: List[str]
    trigger_action: str
    severity_if_missing: str
    z3_template: Dict[str, Any]
    source_file: str = ""
    isa_clause: str = ""

    def covers_equipment_class(self, entity_class: str) -> bool:
        return any(
            ec.lower() in entity_class.lower() or entity_class.lower() in ec.lower()
            for ec in self.applicable_equipment_classes
        )

    def covers_action(self, action: RuleAction) -> bool:
        trigger = self.trigger_action.upper()
        return action.value.upper() == trigger or trigger in ("STOP", "SHUTDOWN") and action in (
            RuleAction.STOP,
        )


@dataclass
class InvariantCoverageResult:
    invariant: SafetyInvariant
    covered_by: List[ControlRule] = field(default_factory=list)
    is_covered: bool = False
    coverage_confidence: float = 0.0


class SafetyInvariantLibrary:
    """
    Loads IEC 61511-aligned safety invariants and evaluates which are covered
    by the extracted rule set. Uncovered invariants are candidate OMISSION findings.
    """

    def __init__(self, config: PipelineConfig):
        self.config = config
        self._invariants: List[SafetyInvariant] = []

    def load(self) -> "SafetyInvariantLibrary":
        loader = InvariantLoader()
        raw = loader.load_all(self.config.invariants_dir)
        self._invariants = [self._parse(r) for r in raw if r]
        logger.info(f"SafetyInvariantLibrary: {len(self._invariants)} invariants loaded")
        return self

    def evaluate_coverage(
        self, rules: List[ControlRule], linked_entities: List[Any]
    ) -> List[InvariantCoverageResult]:
        """
        For each invariant, determine if the rule set contains a rule that satisfies it.
        Only evaluates invariants whose applicable equipment class is present in this package.
        Returns a list of InvariantCoverageResult — uncovered ones are OMISSION candidates.
        """
        # Build entity class map: canonical_tag → class, plus all appearance tags → class
        entity_class_map: Dict[str, str] = {}
        for entity in linked_entities:
            entity_class_map[entity.canonical_tag] = entity.entity_class
            for appearance in getattr(entity, "appearances", []):
                entity_class_map[appearance.tag] = entity.entity_class

        # Collect all non-Unknown entity classes present in this package
        present_classes = {ec for ec in entity_class_map.values() if ec and ec.lower() != "unknown"}

        results: List[InvariantCoverageResult] = []
        for invariant in self._invariants:
            # Skip invariants whose equipment type is not present in this package
            if present_classes and not any(
                invariant.covers_equipment_class(ec) for ec in present_classes
            ):
                continue

            result = InvariantCoverageResult(invariant=invariant)

            for rule in rules:
                if rule.needs_review:
                    continue
                equip_class = entity_class_map.get(rule.equipment_id, "Unknown")
                if not invariant.covers_equipment_class(equip_class):
                    continue
                if not invariant.covers_action(rule.action):
                    continue
                result.covered_by.append(rule)
                result.is_covered = True
                result.coverage_confidence = max(result.coverage_confidence, rule.confidence)

            results.append(result)

        covered = sum(1 for r in results if r.is_covered)
        logger.info(
            f"Invariant coverage: {covered}/{len(results)} covered "
            f"({len(results) - covered} potential omissions)"
        )
        return results

    def get_all(self) -> List[SafetyInvariant]:
        return self._invariants

    def summary_table(self) -> List[Dict[str, str]]:
        """Returns a list of dicts for pandas DataFrame / paper Table."""
        return [
            {
                "ID": inv.invariant_id,
                "IEC Clause": inv.iec_clause,
                "Category": inv.category,
                "Description": inv.description[:80],
                "Severity": inv.severity_if_missing,
            }
            for inv in self._invariants
        ]

    @staticmethod
    def _parse(raw: Dict[str, Any]) -> Optional[SafetyInvariant]:
        try:
            return SafetyInvariant(
                invariant_id=raw["invariant_id"],
                iec_clause=raw.get("iec_clause", ""),
                isa_clause=raw.get("isa_clause", ""),
                category=raw.get("category", ""),
                description=raw.get("description", ""),
                applicable_equipment_classes=raw.get("applicable_equipment_classes", []),
                applicable_sensor_classes=raw.get("applicable_sensor_classes", []),
                trigger_action=raw.get("trigger_action", "STOP"),
                severity_if_missing=raw.get("severity_if_missing", raw.get("severity_if_violated", "MEDIUM")),
                z3_template=raw.get("z3_template", {}),
                source_file=raw.get("_source_file", ""),
            )
        except KeyError as e:
            logger.error(f"Invalid invariant template: missing key {e}")
            return None
