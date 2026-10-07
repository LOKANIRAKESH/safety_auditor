"""
Audit Repository — Data Access Layer
======================================

All database reads and writes go through this class.
Application code (pipeline, UI) never writes SQL directly.

DESIGN PATTERN: Repository Pattern
  The repository is the single point of contact between the application
  and the database. This means:
    - The pipeline doesn't know or care that SQLite is being used
    - The UI doesn't know or care about table structure
    - Tests can swap in a fake repository without touching the DB
    - If we ever migrate to PostgreSQL, only session.py changes

USAGE
  with get_session() as session:
      repo = AuditRepository(session)

      # Write
      run = repo.save_run(input_source="spec.pdf", findings=[...], graph=G)
      print(run.run_id)   # "run-20261007-143022-a9f3b1"

      # Read
      history = repo.get_history(limit=10)
      findings = repo.get_findings(run.run_id)
"""
from __future__ import annotations
import json
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
import networkx as nx

from .models import AuditRun, Finding, KGNode, KGEdge
from src.verification.finding_model import AuditFinding


def _new_run_id() -> str:
    """
    Generate a human-readable, sortable run identifier.
    Format: "run-YYYYMMDD-HHMMSS-XXXXXX"
    Example: "run-20261007-143022-a9f3b1"
    The timestamp prefix makes runs sortable by creation time.
    """
    return f"run-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"


class AuditRepository:
    """
    All database operations for one session.

    Instantiate inside a `with get_session() as session:` block.
    The session is committed/rolled back by the context manager —
    do not call session.commit() here.
    """

    def __init__(self, session: Session):
        self.session = session

    # ══════════════════════════════════════════════════════════════════
    # WRITE METHODS
    # ══════════════════════════════════════════════════════════════════

    def save_run(
        self,
        *,
        input_source: str,
        findings: List[AuditFinding],
        llm_model: str = "",
        cross_modal_linking: bool = True,
        total_rules: int = 0,
        total_entities: int = 0,
        invariants_checked: int = 0,
        report_path: str = "",
        plc_path: str = "",
        graph: Optional[nx.DiGraph] = None,
        run_id: Optional[str] = None,
    ) -> AuditRun:
        """
        Persist one complete audit run to the database.

        Args:
            input_source:        Path to the audited specification file.
            findings:            List of AuditFinding objects from the Z3 pass.
            llm_model:           Name of the Ollama model used (e.g. "qwen2.5").
            cross_modal_linking: Whether cross-modal linking was enabled.
            total_rules:         Number of IR rules passed to Z3.
            total_entities:      Number of canonical entities after linking.
            invariants_checked:  Number of IEC 61511 invariants evaluated.
            report_path:         Path to the generated HTML report.
            plc_path:            Path to the generated .st PLC file.
            graph:               NetworkX DiGraph — nodes and edges are stored
                                 in kg_nodes / kg_edges tables if provided.
            run_id:              Optional override. Auto-generated if None.

        Returns:
            The persisted AuditRun ORM object (not yet committed —
            the calling context manager commits on clean exit).
        """
        from src.verification.finding_model import FindingSeverity

        rid = run_id or _new_run_id()

        # ── Create the parent AuditRun record ──────────────────────────
        run = AuditRun(
            run_id=rid,
            input_source=input_source,
            created_at=datetime.utcnow(),
            llm_model=llm_model,
            cross_modal_linking=cross_modal_linking,
            total_findings=len(findings),
            # Count by severity for fast dashboard queries (avoid N+1 queries)
            high_count=sum(1 for f in findings if f.severity == FindingSeverity.HIGH),
            medium_count=sum(1 for f in findings if f.severity == FindingSeverity.MEDIUM),
            low_count=sum(1 for f in findings if f.severity == FindingSeverity.LOW),
            total_rules=total_rules,
            total_entities=total_entities,
            invariants_checked=invariants_checked,
            report_path=str(report_path),
            plc_path=str(plc_path),
            status="completed",
        )
        self.session.add(run)

        # ── Store each finding as a child record ───────────────────────
        for f in findings:
            self.session.add(Finding(
                run_id=rid,
                finding_type=f.finding_type.value,
                severity=f.severity.value,
                equipment_tag=f.equipment_tag,
                invariant_id=f.invariant_id,
                # invariant_iec_clause is set on AuditFinding in z3_auditor
                iec_clause=getattr(f, "invariant_iec_clause", None),
                description=f.description,
                recommendation=getattr(f, "recommendation", None),
                # Serialize page list to JSON string for storage
                evidence_pages=json.dumps(f.evidence_pages or []),
                evidence_docs=json.dumps(getattr(f, "evidence_docs", []) or []),
                z3_result=f.z3_result,
            ))

        # ── Store knowledge graph topology ─────────────────────────────
        if graph is not None:
            self._save_graph(rid, graph)

        return run

    def _save_graph(self, run_id: str, graph: nx.DiGraph) -> None:
        """
        Store all nodes and edges of the NetworkX graph in the DB.

        This allows the Audit History page to show graph statistics and
        future graph queries without re-running the pipeline.
        Each node stores its ICS tag, entity type, and any extra attrs as JSON.
        Each edge stores source tag, target tag, relationship type, and label.
        """
        for node_id, data in graph.nodes(data=True):
            self.session.add(KGNode(
                run_id=run_id,
                node_id=str(node_id),
                node_type=data.get("entity_class", "equipment"),
                label=data.get("label", str(node_id)),
                # Extra attributes stored as JSON (modalities, needs_review, etc.)
                properties=json.dumps(
                    {k: v for k, v in data.items() if k not in ("entity_class", "label")}
                ),
            ))

        for src, tgt, data in graph.edges(data=True):
            self.session.add(KGEdge(
                run_id=run_id,
                source_id=str(src),
                target_id=str(tgt),
                rel_type=data.get("relationship", "controls"),
                label=data.get("label", ""),
                weight=float(data.get("weight", 1.0)),
                properties=json.dumps(
                    {k: v for k, v in data.items() if k not in ("relationship", "label", "weight")}
                ),
            ))

    # ══════════════════════════════════════════════════════════════════
    # READ METHODS
    # ══════════════════════════════════════════════════════════════════

    def get_history(self, limit: int = 50) -> List[AuditRun]:
        """
        Return the most recent audit runs, newest first.

        Used by the "Audit History" page to populate the runs table.
        Results include denormalized finding counts (high/medium/low)
        so the UI can show them without a second query.
        """
        return (
            self.session.query(AuditRun)
            .order_by(AuditRun.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_run(self, run_id: str) -> Optional[AuditRun]:
        """Return a single AuditRun by its run_id, or None if not found."""
        return self.session.query(AuditRun).filter_by(run_id=run_id).first()

    def get_findings(self, run_id: str) -> List[Finding]:
        """Return all findings for a specific run, used in the History drill-down."""
        return self.session.query(Finding).filter_by(run_id=run_id).all()

    def get_kg_nodes(self, run_id: str) -> List[KGNode]:
        """Return all knowledge graph nodes for a specific run."""
        return self.session.query(KGNode).filter_by(run_id=run_id).all()

    def get_kg_edges(self, run_id: str) -> List[KGEdge]:
        """Return all knowledge graph edges for a specific run."""
        return self.session.query(KGEdge).filter_by(run_id=run_id).all()

    def count_runs(self) -> int:
        """Return total number of audit runs across all sessions."""
        return self.session.query(AuditRun).count()

    def get_finding_type_summary(self) -> List[dict]:
        """
        Aggregate finding counts by type and severity across ALL runs.

        Used by the "Audit History" page to draw the all-time finding
        distribution chart. Returns rows like:
            [{"type": "OMISSION", "severity": "HIGH", "count": 142}, ...]
        """
        from sqlalchemy import func
        rows = (
            self.session.query(
                Finding.finding_type,
                Finding.severity,
                func.count(Finding.id).label("count")
            )
            .group_by(Finding.finding_type, Finding.severity)
            .all()
        )
        return [{"type": r[0], "severity": r[1], "count": r[2]} for r in rows]
