"""Phase 4 — NetworkX knowledge graph from linked entities and rules."""
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import networkx as nx
from loguru import logger
from src.linking.cross_modal_linker import LinkedEntity
from src.extraction.entity_extractor import ExtractedRule

# Load vis-network.js inline once — avoids CDN dependency in corporate/offline environments
_VIS_JS_INLINE: str = ""
try:
    _vis_js_path = Path(__file__).parent.parent.parent / "ui" / "vis-network.min.js"
    if _vis_js_path.exists():
        _VIS_JS_INLINE = _vis_js_path.read_text(encoding="utf-8")
except Exception:
    pass


def _make_vis_html(nodes_data: list, edges_data: list,
                   height: str = "600px", bgcolor: str = "#1e1e2e") -> str:
    """Self-contained vis.js HTML that renders inside Streamlit's iframe."""
    if _VIS_JS_INLINE:
        script_tag = f"<script>{_VIS_JS_INLINE}</script>"
    else:
        script_tag = '<script src="https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js"></script>'
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
{script_tag}
<style>
  html,body{{margin:0;padding:0;background:{bgcolor};overflow:hidden;}}
  #graph{{width:100%;height:{height};background:{bgcolor};}}
</style>
</head>
<body>
<div id="graph"></div>
<script>
  var nodes = new vis.DataSet({json.dumps(nodes_data)});
  var edges = new vis.DataSet({json.dumps(edges_data)});
  var container = document.getElementById("graph");
  var options = {{
    physics:{{stabilization:{{iterations:200,fit:true}},barnesHut:{{gravitationalConstant:-8000,springLength:120}}}},
    nodes:{{font:{{color:"#ffffff",size:13}},borderWidth:1,shape:"dot"}},
    edges:{{font:{{color:"#aaaaaa",size:10,align:"middle"}},arrows:{{to:{{enabled:true,scaleFactor:0.6}}}},smooth:{{type:"dynamic"}}}},
    interaction:{{hover:true,tooltipDelay:80}}
  }};
  new vis.Network(container, {{nodes:nodes, edges:edges}}, options);
</script>
</body>
</html>"""


@dataclass
class EquipmentGraph:
    graph: nx.DiGraph
    node_count: int
    edge_count: int

    def to_pyvis_html(self, output_path: Path) -> Path:
        """Export as a self-contained vis.js HTML for Streamlit embedding."""
        import json

        nodes_data = []
        for node_id, attrs in self.graph.nodes(data=True):
            color = _CLASS_COLORS.get(attrs.get("entity_class", "Unknown"), "#888888")
            nodes_data.append({
                "id":    node_id,
                "label": node_id,
                "color": color,
                "size":  20,
                "title": attrs.get("description", node_id),
            })

        edges_data = []
        for src, dst, attrs in self.graph.edges(data=True):
            edges_data.append({
                "from":  src,
                "to":    dst,
                "label": attrs.get("label", ""),
                "color": "#666699",
                "width": 1,
            })

        html = _make_vis_html(nodes_data, edges_data)
        output_path = Path(output_path)
        output_path.write_text(html, encoding="utf-8")
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
