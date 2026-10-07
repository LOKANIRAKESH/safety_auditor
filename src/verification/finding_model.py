"""Phase 7 — Pydantic model for a single audit finding."""
from __future__ import annotations
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
import uuid


class FindingType(str, Enum):
    OMISSION = "OMISSION"               # Required safety rule is missing from specification
    CONTRADICTION = "CONTRADICTION"     # Two rules are logically inconsistent
    UNSAFE_STATE = "UNSAFE_STATE"       # Reachable system state violates a safety invariant
    INCONSISTENCY = "INCONSISTENCY"     # Rule exists but conflicts with safety invariant threshold
    TAG_MISMATCH = "TAG_MISMATCH"       # Same physical entity referenced with different tags across modalities


class FindingSeverity(str, Enum):
    HIGH = "HIGH"       # Direct safety consequence; must be resolved before PLC generation
    MEDIUM = "MEDIUM"   # Significant risk; should be resolved
    LOW = "LOW"         # Minor inconsistency; advisory


class AuditFinding(BaseModel):
    finding_id: str = Field(default_factory=lambda: f"F-{uuid.uuid4().hex[:6].upper()}")
    finding_type: FindingType
    severity: FindingSeverity
    equipment_tag: str
    invariant_id: Optional[str] = None
    invariant_iec_clause: Optional[str] = None
    description: str
    evidence_pages: List[int] = Field(default_factory=list)
    evidence_docs: List[str] = Field(default_factory=list)
    evidence_modalities: List[str] = Field(default_factory=list)
    current_state: str = ""    # What the specification currently says
    expected_state: str = ""   # What IEC 61511 / invariant requires
    recommendation: str = ""
    z3_result: Optional[str] = None  # "unsat" | "sat" | "timeout"
    related_rule_ids: List[str] = Field(default_factory=list)

    def evidence_summary(self) -> str:
        pages = ", ".join(f"p.{p}" for p in self.evidence_pages)
        docs = ", ".join(set(self.evidence_docs))
        return f"{docs} [{pages}]" if pages else docs

    def to_row(self) -> dict:
        return {
            "Finding ID": self.finding_id,
            "Type": self.finding_type.value,
            "Severity": self.severity.value,
            "Equipment": self.equipment_tag,
            "IEC Clause": self.invariant_iec_clause or "",
            "Description": self.description,
            "Evidence": self.evidence_summary(),
            "Recommendation": self.recommendation,
        }
