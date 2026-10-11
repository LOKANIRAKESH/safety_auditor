"""
Standards Knowledge Graph — NetworkX graph built from extracted SafetyRule objects.

Node types:
  Standard   — the parent document (OSHA PSM, IEC 61511, etc.)
  Clause     — section/clause within a standard
  Requirement— a single safety rule (= SafetyRule from rule_extractor)
  EquipmentClass — e.g. "Pump", "Compressor", "PressureVessel"
  SensorClass    — e.g. "PressureTransmitter", "TemperatureSensor"
  Action         — what must happen: STOP, ALARM, CLOSE, DOCUMENT
  Condition      — when it applies: HIGH_HIGH, LOW_LOW, ON_DEMAND ...

Edge types:
  (Standard, "has_clause", Clause)
  (Clause, "contains", Requirement)
  (Requirement, "applies_to", EquipmentClass)
  (Requirement, "monitored_by", SensorClass)
  (Requirement, "triggers", Action)
  (Requirement, "when_condition", Condition)
  (Clause, "references", Clause)            — cross-references between standards
  (Requirement, "iec_equivalent", Clause)   — maps to IEC 61511 clause
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Dict, Any
from loguru import logger

try:
    import networkx as nx
    NX_OK = True
except ImportError:
    NX_OK = False

from src.standards.rule_extractor import SafetyRule


class StandardsKnowledgeGraph:
    """
    In-memory NetworkX DiGraph built from SafetyRule objects.

    Usage:
        kg = StandardsKnowledgeGraph()
        kg.add_rules(rules)

        # Query: which rules apply to a Pump?
        pump_rules = kg.rules_for_equipment("Pump")

        # Query: what actions does a HIGH_HIGH pressure condition require?
        actions = kg.actions_for_condition("HIGH_HIGH", equipment="Pump")

        # Visualise
        kg.draw(output_path="standards_graph.png")
    """

    # Node type labels
    NT_STANDARD  = "Standard"
    NT_CLAUSE    = "Clause"
    NT_REQUIRE   = "Requirement"
    NT_EQUIPMENT = "EquipmentClass"
    NT_SENSOR    = "SensorClass"
    NT_ACTION    = "Action"
    NT_CONDITION = "Condition"

    def __init__(self):
        if not NX_OK:
            raise ImportError("networkx not installed. Run: pip install networkx")
        self.G: nx.DiGraph = nx.DiGraph()
        self._rules: Dict[str, SafetyRule] = {}

    # ── Build ─────────────────────────────────────────────────────────────────

    def add_rules(self, rules: List[SafetyRule]) -> None:
        """Populate the graph from a list of SafetyRule objects."""
        for rule in rules:
            self._add_rule(rule)
        logger.info(
            f"Knowledge graph: {self.G.number_of_nodes()} nodes, "
            f"{self.G.number_of_edges()} edges, {len(rules)} rules added"
        )

    def _add_rule(self, rule: SafetyRule) -> None:
        G = self.G
        self._rules[rule.rule_id] = rule

        # Standard node
        std_id = f"STD:{rule.source_id}"
        if not G.has_node(std_id):
            G.add_node(std_id, type=self.NT_STANDARD, label=rule.standard_ref,
                       source_id=rule.source_id)

        # Clause node
        clause_id = f"CLAUSE:{rule.source_id}:{rule.clause_ref}"
        if not G.has_node(clause_id):
            G.add_node(clause_id, type=self.NT_CLAUSE, label=rule.clause_ref,
                       standard=rule.standard_ref)
        G.add_edge(std_id, clause_id, rel="has_clause")

        # Requirement node
        req_id = f"REQ:{rule.rule_id}"
        G.add_node(
            req_id,
            type         = self.NT_REQUIRE,
            label        = rule.requirement_text[:80],
            rule_id      = rule.rule_id,
            severity     = rule.severity_if_missing,
            confidence   = rule.confidence,
            req_type     = rule.requirement_type,
        )
        G.add_edge(clause_id, req_id, rel="contains")

        # Equipment class nodes
        for eq in rule.equipment_classes:
            eq_id = f"EQ:{eq}"
            if not G.has_node(eq_id):
                G.add_node(eq_id, type=self.NT_EQUIPMENT, label=eq)
            G.add_edge(req_id, eq_id, rel="applies_to")

        # Sensor class nodes
        for sc in rule.sensor_classes:
            sc_id = f"SC:{sc}"
            if not G.has_node(sc_id):
                G.add_node(sc_id, type=self.NT_SENSOR, label=sc)
            G.add_edge(req_id, sc_id, rel="monitored_by")

        # Action node
        act_id = f"ACT:{rule.action_required}"
        if not G.has_node(act_id):
            G.add_node(act_id, type=self.NT_ACTION, label=rule.action_required)
        G.add_edge(req_id, act_id, rel="triggers")

        # Condition node
        cond_id = f"COND:{rule.condition_type}"
        if not G.has_node(cond_id):
            G.add_node(cond_id, type=self.NT_CONDITION, label=rule.condition_type)
        G.add_edge(req_id, cond_id, rel="when_condition")

        # IEC 61511 cross-reference edge
        if rule.iec_equivalent:
            iec_id = f"CLAUSE:IEC61511:{rule.iec_equivalent}"
            if not G.has_node(iec_id):
                G.add_node(iec_id, type=self.NT_CLAUSE, label=rule.iec_equivalent,
                           standard="IEC 61511")
            G.add_edge(req_id, iec_id, rel="iec_equivalent")

    # ── Query ─────────────────────────────────────────────────────────────────

    def rules_for_equipment(self, equipment_class: str) -> List[SafetyRule]:
        """Return all rules that apply to a given equipment class."""
        eq_id = f"EQ:{equipment_class}"
        if not self.G.has_node(eq_id):
            return []
        rule_ids = [
            n.replace("REQ:", "")
            for n in self.G.predecessors(eq_id)
            if self.G.nodes[n].get("type") == self.NT_REQUIRE
        ]
        return [self._rules[rid] for rid in rule_ids if rid in self._rules]

    def rules_for_condition(
        self, condition_type: str, equipment_class: str = ""
    ) -> List[SafetyRule]:
        """Return rules that apply under a given condition (optionally filtered by equipment)."""
        cond_id = f"COND:{condition_type.upper()}"
        if not self.G.has_node(cond_id):
            return []
        candidates = [
            n.replace("REQ:", "")
            for n in self.G.predecessors(cond_id)
            if self.G.nodes[n].get("type") == self.NT_REQUIRE
        ]
        rules = [self._rules[rid] for rid in candidates if rid in self._rules]
        if equipment_class:
            rules = [r for r in rules if equipment_class in r.equipment_classes]
        return rules

    def actions_for_condition(
        self, condition_type: str, equipment_class: str = ""
    ) -> List[str]:
        """What actions are required for a given condition?"""
        rules = self.rules_for_condition(condition_type, equipment_class)
        return sorted({r.action_required for r in rules})

    def rules_from_standard(self, source_id: str) -> List[SafetyRule]:
        std_id = f"STD:{source_id}"
        if not self.G.has_node(std_id):
            return []
        rule_nodes = nx.descendants(self.G, std_id)
        return [
            self._rules[n.replace("REQ:", "")]
            for n in rule_nodes
            if self.G.nodes[n].get("type") == self.NT_REQUIRE
            and n.replace("REQ:", "") in self._rules
        ]

    def find_gaps(self, required_iec_clauses: List[str]) -> List[str]:
        """
        Given a list of required IEC 61511 clause IDs,
        return the ones for which no rule has been extracted yet.
        """
        covered = {
            n.replace("CLAUSE:IEC61511:", "")
            for n in self.G.nodes
            if n.startswith("CLAUSE:IEC61511:")
        }
        return [c for c in required_iec_clauses if c not in covered]

    def summary(self) -> dict:
        return {
            "nodes":       self.G.number_of_nodes(),
            "edges":       self.G.number_of_edges(),
            "requirements": len(self._rules),
            "standards":   len([n for n,d in self.G.nodes(data=True) if d.get("type")==self.NT_STANDARD]),
            "equipment":   len([n for n,d in self.G.nodes(data=True) if d.get("type")==self.NT_EQUIPMENT]),
            "sensors":     len([n for n,d in self.G.nodes(data=True) if d.get("type")==self.NT_SENSOR]),
        }

    # ── Serialise ─────────────────────────────────────────────────────────────

    def save_graphml(self, path: Path) -> None:
        """Save graph as GraphML for import into Gephi / yEd."""
        nx.write_graphml(self.G, str(path))
        logger.info(f"Knowledge graph saved: {path}")

    def load_graphml(self, path: Path) -> None:
        """Load a previously saved graph."""
        self.G = nx.read_graphml(str(path))
        logger.info(f"Knowledge graph loaded: {path}")

    # ── Visualisation ─────────────────────────────────────────────────────────

    def draw(self, output_path: Path = None, max_nodes: int = 120) -> Optional[Path]:
        """
        Save a PNG overview of the knowledge graph.
        Uses a spring layout; colour-codes node types.
        Skips gracefully if matplotlib is not installed.
        """
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning("matplotlib not available — skipping graph visualisation")
            return None

        if output_path is None:
            from src.config import PipelineConfig
            output_path = PipelineConfig().data_dir / "standards" / "knowledge_graph.png"
        output_path = Path(output_path)

        G = self.G
        if G.number_of_nodes() > max_nodes:
            # Draw a representative subgraph: first max_nodes nodes
            nodes_subset = list(G.nodes)[:max_nodes]
            G = G.subgraph(nodes_subset)

        colour_map = {
            self.NT_STANDARD:  "#E74C3C",
            self.NT_CLAUSE:    "#E67E22",
            self.NT_REQUIRE:   "#3498DB",
            self.NT_EQUIPMENT: "#2ECC71",
            self.NT_SENSOR:    "#1ABC9C",
            self.NT_ACTION:    "#9B59B6",
            self.NT_CONDITION: "#F39C12",
        }
        node_colours = [
            colour_map.get(G.nodes[n].get("type", ""), "#95A5A6")
            for n in G.nodes
        ]
        labels = {n: G.nodes[n].get("label", n)[:20] for n in G.nodes}

        fig, ax = plt.subplots(figsize=(18, 12), facecolor="#1a1a2e")
        ax.set_facecolor("#1a1a2e")
        pos = nx.spring_layout(G, k=1.5, seed=42)
        nx.draw_networkx(
            G, pos, ax=ax, labels=labels,
            node_color=node_colours, node_size=300,
            font_size=6, font_color="white",
            edge_color="#444466", width=0.6, arrows=True, arrowsize=8,
        )

        # Legend
        for node_type, colour in colour_map.items():
            ax.plot([], [], "o", color=colour, label=node_type, markersize=8)
        ax.legend(loc="upper left", fontsize=8, facecolor="#2a2a3e",
                  labelcolor="white", framealpha=0.8)
        ax.set_title("Standards Knowledge Graph", color="white", fontsize=14, pad=10)

        plt.tight_layout()
        plt.savefig(str(output_path), dpi=150, bbox_inches="tight",
                    facecolor="#1a1a2e")
        plt.close()
        logger.success(f"Knowledge graph visualised → {output_path}")
        return output_path
