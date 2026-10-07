"""Phase 5 — Converts raw ExtractedRule objects to canonical ControlRule IR."""
from __future__ import annotations
from typing import List
from loguru import logger
from src.extraction.entity_extractor import ExtractedRule
from src.ir.rule_model import ControlRule, Condition, RuleAction, RuleType, ComparisonOperator


_OPERATOR_MAP = {
    ">=": ComparisonOperator.GTE,
    "<=": ComparisonOperator.LTE,
    ">":  ComparisonOperator.GT,
    "<":  ComparisonOperator.LT,
    "==": ComparisonOperator.EQ,
    "=":  ComparisonOperator.EQ,
    "!=": ComparisonOperator.NEQ,
    "≥":  ComparisonOperator.GTE,
    "≤":  ComparisonOperator.LTE,
}

_ACTION_MAP = {
    "STOP": RuleAction.STOP,
    "SHUTDOWN": RuleAction.STOP,
    "TRIP": RuleAction.STOP,
    "START": RuleAction.START,
    "OPEN": RuleAction.OPEN,
    "CLOSE": RuleAction.CLOSE,
    "CLOSED": RuleAction.CLOSE,
    "ALARM": RuleAction.ALARM,
    "ALERT": RuleAction.ALARM,
    "ACTIVATE": RuleAction.ACTIVATE,
    "TRIGGER": RuleAction.ACTIVATE,
    "INHIBIT": RuleAction.INHIBIT,
    "BYPASS": RuleAction.INHIBIT,
}

_RULE_TYPE_MAP = {
    "shutdown": RuleType.SHUTDOWN,
    "control": RuleType.CONTROL,
    "emergency_shutdown": RuleType.EMERGENCY_SHUTDOWN,
    "interlock": RuleType.INTERLOCK,
    "alarm": RuleType.ALARM,
    "permissive": RuleType.PERMISSIVE,
}


class RuleBuilder:
    """Converts extracted rules to canonical ControlRule IR."""

    def build(self, extracted_rules: List[ExtractedRule]) -> List[ControlRule]:
        ir_rules: List[ControlRule] = []
        skipped = 0

        for er in extracted_rules:
            try:
                ir = self._convert(er)
                ir_rules.append(ir)
            except (ValueError, KeyError) as exc:
                logger.warning(f"Skipping rule {er.rule_id}: {exc}")
                skipped += 1

        logger.info(f"RuleBuilder: {len(ir_rules)} IR rules built, {skipped} skipped")
        return ir_rules

    def _convert(self, er: ExtractedRule) -> ControlRule:
        operator = _OPERATOR_MAP.get(er.condition_operator, ComparisonOperator.GTE)
        action = _ACTION_MAP.get(er.action.upper(), RuleAction.UNKNOWN)
        rule_type = _RULE_TYPE_MAP.get(er.rule_type.lower(), RuleType.CONTROL)

        if action == RuleAction.UNKNOWN:
            logger.warning(f"Unknown action '{er.action}' in rule {er.rule_id} — marking for review")

        condition = Condition(
            sensor_tag=er.condition_tag,
            operator=operator,
            threshold=er.condition_threshold,
            unit=er.condition_unit,
        )

        return ControlRule(
            rule_id=er.rule_id,
            equipment_id=er.equipment_tag,
            condition=condition,
            action=action,
            rule_type=rule_type,
            trigger_tag=er.trigger_tag,
            source_page=er.source_page,
            source_doc=er.source_doc,
            source_modality=er.source_modality,
            confidence=er.confidence,
            needs_review=er.needs_review,
            ambiguity_note=er.ambiguity_note,
        )
