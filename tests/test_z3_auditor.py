"""Tests for Phase 7 — Z3 Formal Verification."""
import pytest
from src.verification.z3_auditor import Z3Auditor
from src.verification.finding_model import FindingType, FindingSeverity
from src.ir.rule_model import ControlRule, Condition, RuleAction, RuleType, ComparisonOperator
from src.invariants.library import SafetyInvariantLibrary, InvariantCoverageResult, SafetyInvariant


def make_rule(rule_id, equip, sensor, op, threshold, action, unit="bar", conf=0.95) -> ControlRule:
    return ControlRule(
        rule_id=rule_id,
        equipment_id=equip,
        condition=Condition(sensor_tag=sensor, operator=op, threshold=threshold, unit=unit),
        action=action,
        rule_type=RuleType.SHUTDOWN if action == RuleAction.STOP else RuleType.CONTROL,
        source_doc="test.pdf", source_page=1, confidence=conf,
    )


def make_invariant(inv_id="SD-001", equip_classes=None, action="STOP", severity="HIGH") -> SafetyInvariant:
    return SafetyInvariant(
        invariant_id=inv_id,
        iec_clause="IEC 61511-1 Cl. 9.2.2",
        category="emergency_shutdown",
        description="Test invariant",
        applicable_equipment_classes=equip_classes or ["Pump"],
        applicable_sensor_classes=["PressureTransmitter"],
        trigger_action=action,
        severity_if_missing=severity,
        z3_template={},
    )


def test_omission_finding_when_no_covering_rule(config):
    auditor = Z3Auditor(config)
    inv = make_invariant()
    coverage = InvariantCoverageResult(invariant=inv, is_covered=False)
    # _check_omissions now takes (rules, coverage_results)
    findings = auditor._check_omissions([], [coverage])
    assert len(findings) == 1
    assert findings[0].finding_type == FindingType.OMISSION
    assert findings[0].severity == FindingSeverity.HIGH


def test_no_omission_when_rule_covers_invariant(config):
    auditor = Z3Auditor(config)
    inv = make_invariant()
    rule = make_rule("R001", "P-101", "PT-101", ComparisonOperator.GTE, 50.0, RuleAction.STOP)
    coverage = InvariantCoverageResult(invariant=inv, is_covered=True, covered_by=[rule], coverage_confidence=0.95)
    findings = auditor._check_omissions([rule], [coverage])
    assert len(findings) == 0


def test_unsafe_state_detected(config):
    auditor = Z3Auditor(config)
    # For unsafe state: need BOTH a stop rule AND a start rule that can override it
    stop_rule  = make_rule("R001", "P-101", "PT-101", ComparisonOperator.GTE, 50.0, RuleAction.STOP)
    start_rule = make_rule("R002", "P-101", "PT-101", ComparisonOperator.GTE, 40.0, RuleAction.START)
    findings = auditor.check_unsafe_states([stop_rule, start_rule])
    unsafe = [f for f in findings if f.finding_type == FindingType.UNSAFE_STATE]
    assert len(unsafe) >= 1


def test_low_confidence_rules_flagged_as_tag_mismatch(config):
    auditor = Z3Auditor(config)
    rule = make_rule("R001", "P-101", "PT-101", ComparisonOperator.GTE, 50.0, RuleAction.STOP, conf=0.5)
    rule.needs_review = True
    rule.ambiguity_note = "Ambiguous tag reference"
    findings = auditor._check_tag_mismatches([rule])
    assert len(findings) == 1
    assert findings[0].finding_type == FindingType.TAG_MISMATCH
    assert findings[0].severity == FindingSeverity.MEDIUM
