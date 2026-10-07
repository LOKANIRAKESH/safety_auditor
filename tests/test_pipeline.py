"""Integration test for the full pipeline (no LLM calls — uses rule builder directly)."""
import pytest
from pathlib import Path
from src.config import PipelineConfig
from src.ir.rule_model import ControlRule, Condition, RuleAction, RuleType, ComparisonOperator
from src.invariants.library import SafetyInvariantLibrary
from src.verification.z3_auditor import Z3Auditor
from src.verification.finding_model import FindingType


def test_pipeline_finds_omission_on_missing_shutdown(config):
    """End-to-end: a Pump with NO rules at all should produce OMISSION findings."""
    # Empty rule set: no rules extracted from this spec
    rules = []

    class FakeEntity:
        canonical_tag = "P-101"
        entity_class = "Pump"

    library = SafetyInvariantLibrary(config).load()
    coverage = library.evaluate_coverage(rules, [FakeEntity()])

    auditor = Z3Auditor(config)
    findings = auditor.audit(rules, coverage)

    omissions = [f for f in findings if f.finding_type == FindingType.OMISSION]
    assert len(omissions) > 0, "Expected at least one OMISSION when a Pump has no rules at all"
    high_omissions = [f for f in omissions if f.severity.value == "HIGH"]
    assert len(high_omissions) > 0, "Missing shutdown rules should produce HIGH severity omissions"


def test_ir_rule_model_confidence_flags_review():
    from src.ir.rule_model import ControlRule, Condition, RuleAction, RuleType, ComparisonOperator
    rule = ControlRule(
        rule_id="R999",
        equipment_id="P-999",
        condition=Condition(sensor_tag="PT-999", operator=ComparisonOperator.GTE, threshold=50.0, unit="bar"),
        action=RuleAction.STOP,
        rule_type=RuleType.SHUTDOWN,
        confidence=0.5,  # below threshold
    )
    assert rule.needs_review is True


def test_benchmark_generator_creates_packages(tmp_path):
    from benchmark.generator import BenchmarkGenerator
    gen = BenchmarkGenerator(seed=42)
    packages = gen.generate(n=3, output_dir=tmp_path)
    assert len(packages) == 3
    for pkg in packages:
        assert (pkg / "control_narrative.txt").exists()
        assert (pkg / "pid_tags.txt").exists()
        assert (pkg / "injections.json").exists()
