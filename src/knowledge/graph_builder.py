"""Phase 4 — NetworkX knowledge graph from linked entities and rules."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import networkx as nx
from loguru import logger
from src.linking.cross_modal_linker import LinkedEntity
from src.extraction.entity_extractor import ExtractedRule


@dataclass
class EquipmentGraph:
    graph: nx.DiGraph
    node_count: int
    edge_count: int

    def to_pyvis_html(self, output_path: Path) -> Path:
        """Export as interactive PyVis HTML for Streamlit embedding."""
        try:
            from pyvis.network import Network
            net = Network(height="600px", width="100%", directed=True, bgcolor="#1e1e2e", font_color="white")
            net.from_nx(self.graph)
            # Style nodes by entity class
            for node_id, attrs in self.graph.nodes(data=True):
                color = _CLASS_COLORS.get(attrs.get("entity_class", "Unknown"), "#888888")
                net.get_node(node_id)["color"] = color
                net.get_node(node_id)["title"] = attrs.get("description", node_id)
            net.save_graph(str(output_path))
            return output_path
        except ImportError:
            logger.warning("PyVis not installed — skipping interactive graph export.")
            return output_path

    def get_equipment_by_class(self, entity_class: str) -> List[str]:
        return [n for n, d in self.graph.nodes(data=True) if d.get("entity_class") == entity_class]


_CLASS_COLORS = {
    "Pump": "#4fc3f7",
    "Valve": "#81c784",
    "Sensor": "#ffb74d",
    "Controller": "#ce93d8",
    "Interlock": "#ef9a9a",
    "EmergencyShutdown": "#f44336",
    "Motor": "#4db6ac",
    "Tank": "#a5d6a7",
    "Compressor": "#90caf9",
    "Alarm": "#fff176",
}


class KnowledgeGraphBuilder:
    """Builds a NetworkX directed graph from linked entities and extracted rules."""

    def build(
        self, linked_entities: List[LinkedEntity], rules: List[ExtractedRule]
    ) -> EquipmentGraph:
        G = nx.DiGraph()

        # Add nodes
        for entity in linked_entities:
            G.add_node(
                entity.canonical_tag,
                entity_class=entity.entity_class,
                subclass=entity.subclass,
                description=entity.description,
                modalities=",".join(entity.modalities),
                needs_review=entity.needs_review,
            )

        # Add edges from rules
        for rule in rules:
            src = rule.condition_tag
            dst = rule.equipment_tag

            # Ensure both nodes exist
            if src not in G:
                G.add_node(src, entity_class="Unknown", description=f"Referenced in rule {rule.rule_id}")
            if dst not in G:
                G.add_node(dst, entity_class="Unknown", description=f"Referenced in rule {rule.rule_id}")

            edge_label = f"{rule.condition_operator}{rule.condition_threshold}{rule.condition_unit}→{rule.action}"
            G.add_edge(
                src, dst,
                rule_id=rule.rule_id,
                action=rule.action,
                rule_type=rule.rule_type,
                label=edge_label,
                confidence=rule.confidence,
            )

        # Add relationships based on entity classes
        self._add_class_relationships(G, linked_entities)

        graph = EquipmentGraph(graph=G, node_count=G.number_of_nodes(), edge_count=G.number_of_edges())
        logger.info(f"Knowledge graph: {graph.node_count} nodes, {graph.edge_count} edges")
        return graph

    @staticmethod
    def _add_class_relationships(G: nx.DiGraph, entities: List[LinkedEntity]) -> None:
        """Add semantic edges based on entity class pairings (sensor → equipment it measures)."""
        sensors = {e.canonical_tag: e for e in entities if "Sensor" in e.entity_class or "Transmitter" in e.subclass}
        equipment = {e.canonical_tag: e for e in entities if e.entity_class in ("Pump", "Valve", "Motor", "Compressor")}

        # Heuristic: sensors and equipment sharing numeric suffix likely co-located
        for s_tag, sensor in sensors.items():
            s_num = "".join(c for c in s_tag if c.isdigit())
            for e_tag, equip in equipment.items():
                e_num = "".join(c for c in e_tag if c.isdigit())
                if s_num and s_num == e_num and not G.has_edge(s_tag, e_tag):
                    G.add_edge(s_tag, e_tag, label="monitors", rule_type="structural")
