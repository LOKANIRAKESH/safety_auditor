"""Pytest fixtures shared across all test modules."""
import pytest
from pathlib import Path
from src.config import PipelineConfig


@pytest.fixture
def config():
    cfg = PipelineConfig()
    cfg.extraction_confidence_threshold = 0.5  # lower for testing
    cfg.z3_timeout_ms = 2000
    return cfg


@pytest.fixture
def sample_text_blocks():
    from src.ingestion.pdf_extractor import TextBlock
    return [
        TextBlock(
            text="If pressure transmitter PT-101 reads above 50 bar, pump P-101 shall stop immediately.",
            page=1, bbox=(0, 0, 500, 20), source_doc="test_narrative.pdf"
        ),
        TextBlock(
            text="ESD-001 activates when PT-102 reads above 75 bar. All pumps must stop.",
            page=2, bbox=(0, 0, 500, 20), source_doc="test_narrative.pdf"
        ),
        TextBlock(
            text="Valve XV-201 shall close when flow FT-201 drops below 5 m3/h.",
            page=3, bbox=(0, 0, 500, 20), source_doc="test_narrative.pdf"
        ),
    ]


@pytest.fixture
def sample_ir_rules():
    from src.ir.rule_model import ControlRule, Condition, RuleAction, RuleType, ComparisonOperator
    return [
        ControlRule(
            rule_id="R0001",
            equipment_id="P-101",
            condition=Condition(sensor_tag="PT-101", operator=ComparisonOperator.GTE, threshold=50.0, unit="bar"),
            action=RuleAction.STOP,
            rule_type=RuleType.SHUTDOWN,
            source_doc="test.pdf", source_page=1, confidence=0.95,
        ),
        ControlRule(
            rule_id="R0002",
            equipment_id="XV-201",
            condition=Condition(sensor_tag="FT-201", operator=ComparisonOperator.LTE, threshold=5.0, unit="m3/h"),
            action=RuleAction.CLOSE,
            rule_type=RuleType.CONTROL,
            source_doc="test.pdf", source_page=3, confidence=0.88,
        ),
    ]
