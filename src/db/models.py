"""
SQLAlchemy ORM Models — Persistent Audit Store
===============================================

This module defines the four database tables that together form the
"audit store" — a SQLite database that persists every pipeline run.

WHY SQLITE?
  SQLite is a file-based, embedded database. No server, no Docker, no
  configuration required. The entire database is the file
  output/audit_store.db. You can copy it, email it, open it with DB
  Browser for SQLite, or query it from any language. For a research
  tool this is the right choice: zero-ops, reproducible, portable.

  The schema is designed so that swapping SQLite for PostgreSQL or
  MySQL requires changing exactly one line in session.py (the
  create_engine() call). Everything else — models, repository, UI —
  stays the same.

TABLE RELATIONSHIPS
  audit_runs  ─┬─< findings    (one run → many findings)
               ├─< kg_nodes    (one run → many KG nodes)
               └─< kg_edges    (one run → many KG edges)

  All child tables cascade-delete when a run is deleted.

USAGE
  These models are never used directly by application code.
  All reads/writes go through AuditRepository in repository.py.
  The tables are created automatically by init_db() in session.py.
"""
from __future__ import annotations
import json
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, Text, Float, ForeignKey, Index
)
from sqlalchemy.orm import relationship, DeclarativeBase


class Base(DeclarativeBase):
    """Base class that all ORM models inherit from (SQLAlchemy 2.0 style)."""
    pass


class AuditRun(Base):
    """
    One complete pipeline execution against a specification document.

    Created once per call to SafetyAuditor.run(). Acts as the parent
    record that all findings, KG nodes, and KG edges link back to via
    run_id (a human-readable timestamp + short UUID).

    Example run_id: "run-20261007-143022-a9f3b1"
    """
    __tablename__ = "audit_runs"

    # Primary key — auto-incrementing integer for internal joins
    id              = Column(Integer, primary_key=True, autoincrement=True)

    # Human-readable unique identifier, e.g. "run-20261007-143022-a9f3b1"
    run_id          = Column(String(64), unique=True, nullable=False, index=True)

    # Path or filename of the PDF that was audited
    input_source    = Column(String(512), nullable=False)

    # UTC timestamp of when the pipeline finished
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Which Ollama model was used for extraction (e.g. "qwen2.5", "llama3")
    llm_model       = Column(String(64))

    # Whether cross-modal entity linking was enabled (False = ablation mode)
    cross_modal_linking = Column(Boolean, default=True)

    # Finding counts — denormalized for fast dashboard queries
    total_findings  = Column(Integer, default=0)
    high_count      = Column(Integer, default=0)
    medium_count    = Column(Integer, default=0)
    low_count       = Column(Integer, default=0)

    # Pipeline statistics — stored for the "Audit History" UI page
    total_rules     = Column(Integer, default=0)    # IR rules after filtering
    total_entities  = Column(Integer, default=0)    # linked canonical entities
    invariants_checked = Column(Integer, default=0) # how many IEC 61511 invariants were evaluated

    # Paths to generated artefacts (relative to project root)
    report_path     = Column(String(512))   # HTML audit report
    plc_path        = Column(String(512))   # IEC 61131-3 Structured Text file

    # "completed" | "failed" | "partial"
    status          = Column(String(32), default="completed")

    # SQLAlchemy relationships — allow `run.findings`, `run.kg_nodes`, `run.kg_edges`
    findings  = relationship("Finding", back_populates="run", cascade="all, delete-orphan")
    kg_nodes  = relationship("KGNode",  back_populates="run", cascade="all, delete-orphan")
    kg_edges  = relationship("KGEdge",  back_populates="run", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        """Serialize to plain dict for Streamlit dataframes and API responses."""
        return {
            "run_id":           self.run_id,
            "input_source":     self.input_source,
            "created_at":       self.created_at.isoformat() if self.created_at else None,
            "llm_model":        self.llm_model,
            "cross_modal_linking": self.cross_modal_linking,
            "total_findings":   self.total_findings,
            "high_count":       self.high_count,
            "medium_count":     self.medium_count,
            "low_count":        self.low_count,
            "total_rules":      self.total_rules,
            "total_entities":   self.total_entities,
            "status":           self.status,
        }


class Finding(Base):
    """
    A single safety finding produced by the Z3 verification pass (Phase 7).

    Each finding links to the AuditRun that produced it and carries
    enough context for an engineer to understand and act on it:
      - WHAT type of defect was found (finding_type)
      - HOW severe it is (severity)
      - WHICH equipment is affected (equipment_tag)
      - WHICH IEC 61511 clause it violates (iec_clause)
      - WHAT the evidence is (evidence_pages, evidence_docs)
      - WHAT the engineer should do (recommendation)
      - WHAT Z3 reported (z3_result: "omission" | "unsat" | "sat")
    """
    __tablename__ = "findings"

    id           = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key back to the parent run — cascades delete
    run_id       = Column(String(64), ForeignKey("audit_runs.run_id", ondelete="CASCADE"),
                          nullable=False, index=True)

    # OMISSION | CONTRADICTION | UNSAFE_STATE | TAG_MISMATCH | INCONSISTENCY
    finding_type = Column(String(32), nullable=False)

    # HIGH | MEDIUM | LOW
    severity     = Column(String(16), nullable=False)

    # ICS tag of affected equipment, e.g. "P-101". "*" means package-wide.
    equipment_tag = Column(String(64))

    # Which invariant template triggered this finding, e.g. "SD-001"
    invariant_id  = Column(String(32))

    # The IEC 61511 clause number, e.g. "IEC 61511-1 Cl. 9.2.2"
    iec_clause    = Column(String(32))

    # Full human-readable description of the finding
    description   = Column(Text)

    # Actionable recommendation for the process safety engineer
    recommendation = Column(Text)

    # JSON-encoded list of page numbers where evidence was found, e.g. "[3, 7]"
    evidence_pages = Column(Text)

    # JSON-encoded list of source documents, e.g. '["narrative.pdf"]'
    evidence_docs  = Column(Text)

    # What Z3 returned: "omission" (no clause to check), "unsat" (contradiction), "sat" (unsafe)
    z3_result      = Column(String(16))

    run = relationship("AuditRun", back_populates="findings")

    # Compound index for fast severity-filtered queries on the History page
    Index("ix_findings_run_severity", "run_id", "severity")

    def to_dict(self) -> dict:
        """Serialize to plain dict for Streamlit dataframes."""
        return {
            "finding_type":  self.finding_type,
            "severity":      self.severity,
            "equipment_tag": self.equipment_tag,
            "invariant_id":  self.invariant_id,
            "iec_clause":    self.iec_clause,
            "description":   self.description,
            "recommendation": self.recommendation,
            "evidence_pages": json.loads(self.evidence_pages) if self.evidence_pages else [],
            "z3_result":     self.z3_result,
        }


class KGNode(Base):
    """
    A node in the equipment knowledge graph for one audit run.

    Each canonical entity (pump, valve, sensor, etc.) identified by the
    cross-modal linker (Phase 3) becomes one KGNode. Storing the graph
    in the database means the History page can display the graph topology
    for any past run without re-running the pipeline.

    node_type values: "Pump" | "Valve" | "Sensor" | "Controller" | "Interlock" etc.
    """
    __tablename__ = "kg_nodes"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    run_id     = Column(String(64), ForeignKey("audit_runs.run_id", ondelete="CASCADE"),
                        nullable=False, index=True)

    # ICS tag string, e.g. "PT-101", "P-101", "XV-201"
    node_id    = Column(String(128), nullable=False)

    # Entity class from the LLM: "Pump", "PressureTransmitter", etc.
    node_type  = Column(String(32))

    # Human-readable label shown in the PyVis graph
    label      = Column(String(256))

    # JSON blob for any extra attributes from the NetworkX node data dict
    properties = Column(Text)

    run = relationship("AuditRun", back_populates="kg_nodes")
    Index("ix_kgnodes_run_type", "run_id", "node_type")


class KGEdge(Base):
    """
    A directed edge in the equipment knowledge graph.

    Edges represent control relationships:
      source_id (sensor/condition) → target_id (equipment being controlled)

    rel_type values:
      "controls"   — extracted rule: sensor condition → equipment action
      "monitors"   — structural inference: sensor co-located with equipment
      "interlocks" — ESD or interlock relationship
    """
    __tablename__ = "kg_edges"

    id        = Column(Integer, primary_key=True, autoincrement=True)
    run_id    = Column(String(64), ForeignKey("audit_runs.run_id", ondelete="CASCADE"),
                       nullable=False, index=True)

    # Tag of the source node (typically a sensor)
    source_id = Column(String(128), nullable=False)

    # Tag of the target node (typically equipment being controlled)
    target_id = Column(String(128), nullable=False)

    # Relationship type: "controls" | "monitors" | "interlocks"
    rel_type  = Column(String(64))

    # Edge label shown in the PyVis graph, e.g. ">=50bar→STOP"
    label     = Column(String(256))

    # Confidence-derived edge weight from the source rule
    weight    = Column(Float, default=1.0)

    # JSON blob for extra attributes (rule_id, rule_type, etc.)
    properties = Column(Text)

    run = relationship("AuditRun", back_populates="kg_edges")
