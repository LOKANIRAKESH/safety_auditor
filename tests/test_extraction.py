"""Tests for Phase 3 — Cross-Modal Entity Linking."""
import pytest
from src.linking.cross_modal_linker import CrossModalLinker
from src.extraction.entity_extractor import ExtractedEntity, ExtractedRule
from src.ir.rule_model import ComparisonOperator


def make_entity(tag: str, modality: str = "narrative", conf: float = 0.9) -> ExtractedEntity:
    return ExtractedEntity(
        tag=tag, entity_class="Pump", subclass="CentrifugalPump",
        description=f"{tag} description", source_doc="test.pdf",
        source_page=1, source_modality=modality, confidence=conf
    )


def test_exact_match_links_same_tag(config):
    linker = CrossModalLinker(config)
    entities = [
        make_entity("PT-101", "narrative"),
        make_entity("PT-101", "table"),
    ]
    linked, _ = linker.link(entities, [])
    assert len(linked) == 1
    assert linked[0].canonical_tag == "PT-101"
    assert "narrative" in linked[0].modalities
    assert "table" in linked[0].modalities


def test_disabled_linking_passthrough(config):
    config.enable_cross_modal_linking = False
    linker = CrossModalLinker(config)
    entities = [make_entity("PT-101", "narrative"), make_entity("PT-101", "table")]
    linked, _ = linker.link(entities, [])
    assert len(linked) == 2  # no merging when disabled


def test_pid_tags_added_to_registry(config):
    linker = CrossModalLinker(config)
    entities = [make_entity("PT-101", "narrative")]
    pid_tags = ["PT-101", "P-102", "XV-301"]
    linked, _ = linker.link(entities, [], pid_tags=pid_tags)
    tags = {e.canonical_tag for e in linked}
    assert "P-102" in tags
    assert "XV-301" in tags
    pt101 = next(e for e in linked if e.canonical_tag == "PT-101")
    assert "pid" in pt101.modalities
