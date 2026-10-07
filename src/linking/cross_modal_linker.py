"""Phase 3 — Cross-modal entity linking via tag matching and embedding similarity.

Three-step resolution:
  1. Exact tag string match (PT-101 == PT-101)
  2. Fuzzy tag match via Levenshtein (handles OCR noise: PT-1O1 → PT-101)
  3. Contextual embedding similarity (sentence-transformers) for borderline cases

Borderline matches (similarity 0.65–0.75) are flagged for engineer review.
The linker can be disabled entirely via config.enable_cross_modal_linking for ablation studies.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from loguru import logger
from src.extraction.entity_extractor import ExtractedEntity, ExtractedRule
from src.config import PipelineConfig


@dataclass
class LinkedEntity:
    canonical_tag: str
    entity_class: str
    subclass: str
    description: str
    appearances: List[ExtractedEntity] = field(default_factory=list)
    linked_rules: List[ExtractedRule] = field(default_factory=list)
    modalities: List[str] = field(default_factory=list)  # which source types contributed
    needs_review: bool = False
    link_method: str = "exact"  # exact | fuzzy | embedding | borderline


class CrossModalLinker:
    """Resolves entity mentions across narrative, table, and P&ID modalities."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self._embedder = None  # lazy-loaded

    def link(
        self,
        entities: List[ExtractedEntity],
        rules: List[ExtractedRule],
        pid_tags: Optional[List[str]] = None,
    ) -> Tuple[List[LinkedEntity], List[ExtractedRule]]:
        """
        Returns (linked_entities, updated_rules).
        Rules have their equipment_tag and condition_tag resolved to canonical tags.
        """
        if not self.config.enable_cross_modal_linking:
            # Ablation: skip linking, return entities as-is with no cross-modal grounding
            logger.info("Cross-modal linking DISABLED (ablation mode)")
            return self._no_link_passthrough(entities, rules)

        registry: Dict[str, LinkedEntity] = {}

        # Step 1 & 2: resolve each entity by tag
        for entity in entities:
            canonical = self._resolve_tag(entity.tag, registry)
            if canonical not in registry:
                registry[canonical] = LinkedEntity(
                    canonical_tag=canonical,
                    entity_class=entity.entity_class,
                    subclass=entity.subclass,
                    description=entity.description,
                )
            linked = registry[canonical]
            linked.appearances.append(entity)
            if entity.source_modality not in linked.modalities:
                linked.modalities.append(entity.source_modality)
            if entity.needs_review:
                linked.needs_review = True

        # Step 3: embedding similarity for unresolved tags with low fuzzy scores
        if self.config.embedding_similarity_threshold > 0:
            self._embedding_pass(registry, entities)

        # Incorporate P&ID tags as "pid" modality entities if not already present
        if pid_tags:
            for tag in pid_tags:
                canonical = self._resolve_tag(tag, registry)
                if canonical not in registry:
                    registry[canonical] = LinkedEntity(
                        canonical_tag=canonical,
                        entity_class="Unknown",
                        subclass="",
                        description=f"Tag found in P&ID: {tag}",
                    )
                if "pid" not in registry[canonical].modalities:
                    registry[canonical].modalities.append("pid")

        # Resolve rule tags to canonical form and update the rule objects
        updated_rules = []
        for rule in rules:
            canon_equip = self._resolve_tag(rule.equipment_tag, registry)
            canon_cond = self._resolve_tag(rule.condition_tag, registry)
            # Update rule to use canonical tags so downstream lookups work
            rule.equipment_tag = canon_equip
            rule.condition_tag = canon_cond
            # Attach rule to its equipment entity
            if canon_equip in registry:
                registry[canon_equip].linked_rules.append(rule)
            updated_rules.append(rule)

        linked_entities = list(registry.values())
        logger.info(
            f"Cross-modal linking: {len(entities)} raw entities -> {len(linked_entities)} unique entities "
            f"across {len(set(e.source_modality for e in entities))} modalities"
        )
        return linked_entities, updated_rules

    def _resolve_tag(self, tag: str, registry: Dict[str, LinkedEntity]) -> str:
        """Find the canonical tag in registry for the given tag string."""
        tag = tag.upper().strip()

        # Exact match
        if tag in registry:
            return tag

        # Fuzzy match against existing canonical tags — only match tags with the SAME
        # ISA instrument-type prefix (e.g. PT-001 won't absorb P-001; different types)
        from fuzzywuzzy import fuzz
        import re
        tag_prefix = re.match(r"^([A-Z]{1,3})", tag)
        tag_prefix_str = tag_prefix.group(1) if tag_prefix else ""

        best_score, best_match = 0, None
        for canonical in registry:
            # Require matching ISA prefix to avoid merging different instrument types
            canon_prefix = re.match(r"^([A-Z]{1,3})", canonical)
            canon_prefix_str = canon_prefix.group(1) if canon_prefix else ""
            if tag_prefix_str and canon_prefix_str and tag_prefix_str != canon_prefix_str:
                continue
            score = fuzz.ratio(tag, canonical)
            if score > best_score:
                best_score, best_match = score, canonical

        if best_score >= self.config.fuzzy_match_threshold:
            logger.debug(f"Fuzzy match: {tag} → {best_match} (score={best_score})")
            return best_match

        # No match found — this is a new canonical tag
        return tag

    def _embedding_pass(self, registry: Dict[str, LinkedEntity], entities: List[ExtractedEntity]) -> None:
        """Use sentence embeddings to merge entities with similar contextual descriptions."""
        tags = list(registry.keys())
        if len(tags) < 2:
            return
        try:
            embedder = self._get_embedder()
            descriptions = [registry[t].description for t in tags]
            embeddings = embedder.encode(descriptions, convert_to_numpy=True)

            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np
            sim_matrix = cosine_similarity(embeddings)

            merged = set()
            for i in range(len(tags)):
                for j in range(i + 1, len(tags)):
                    if i in merged or j in merged:
                        continue
                    sim = sim_matrix[i][j]
                    if sim >= self.config.embedding_similarity_threshold:
                        # High confidence merge: absorb j into i
                        for appearance in registry[tags[j]].appearances:
                            registry[tags[i]].appearances.append(appearance)
                        for mod in registry[tags[j]].modalities:
                            if mod not in registry[tags[i]].modalities:
                                registry[tags[i]].modalities.append(mod)
                        registry[tags[i]].link_method = "embedding"
                        merged.add(j)
                    elif self.config.embedding_borderline_low <= sim < self.config.embedding_similarity_threshold:
                        # Borderline: flag both for engineer review
                        registry[tags[i]].needs_review = True
                        registry[tags[i]].link_method = "borderline"

            for idx in sorted(merged, reverse=True):
                del registry[tags[idx]]
        except Exception as e:
            logger.warning(f"Embedding pass failed: {e}. Skipping embedding-based linking.")

    def _get_embedder(self):
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer(self.config.embedding_model)
        return self._embedder

    @staticmethod
    def _no_link_passthrough(
        entities: List[ExtractedEntity], rules: List[ExtractedRule]
    ) -> Tuple[List[LinkedEntity], List[ExtractedRule]]:
        linked = []
        for e in entities:
            linked.append(LinkedEntity(
                canonical_tag=e.tag,
                entity_class=e.entity_class,
                subclass=e.subclass,
                description=e.description,
                appearances=[e],
                modalities=[e.source_modality],
                link_method="none",
            ))
        return linked, rules
