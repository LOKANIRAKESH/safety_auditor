"""Tests for Phase 1 — Document Ingestion."""
import pytest
from pathlib import Path
from src.ingestion.pid_extractor import PIDExtractor, TAG_PATTERN


def test_tag_pattern_matches_standard_ics_tags():
    test_cases = ["PT-101", "P-101", "XV-201", "TT-101A", "FT-2001", "ESD-001", "LT-102"]
    for tag in test_cases:
        assert TAG_PATTERN.match(tag), f"TAG_PATTERN should match ICS tag: {tag}"


def test_tag_pattern_rejects_non_tags():
    non_tags = ["hello", "123", "P101", "PT101", "ABC-DEFG"]
    for non_tag in non_tags:
        assert not TAG_PATTERN.match(non_tag), f"TAG_PATTERN should NOT match: {non_tag}"


def test_pid_extractor_from_tag_list(tmp_path):
    tag_file = tmp_path / "pid_tags.txt"
    tag_file.write_text("PT-101\nP-101\nXV-201\nTT-102\nP-200", encoding="utf-8")
    extractor = PIDExtractor()
    result = extractor.extract_from_tag_list(tag_file)
    assert len(result.tags) == 5
    assert "PT-101" in result.tags
    assert "P-101" in result.tags
    assert result.source_doc == "pid_tags.txt"


def test_table_extractor_ce_detection():
    import pandas as pd
    from src.ingestion.table_extractor import TableExtractor
    df = pd.DataFrame({
        "Tag": ["PT-101"], "Cause": ["High Pressure"], "Condition": [">= 50 bar"],
        "Effect": ["TRIP"], "Action": ["P-101 STOP"]
    })
    assert TableExtractor.is_cause_effect_table(df) is True


def test_table_extractor_non_ce():
    import pandas as pd
    from src.ingestion.table_extractor import TableExtractor
    df = pd.DataFrame({"Name": ["Alice"], "Date": ["2024-01-01"], "Amount": [100]})
    assert TableExtractor.is_cause_effect_table(df) is False
