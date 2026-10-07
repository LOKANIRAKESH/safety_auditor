"""Phase 5 — Pydantic v2 Intermediate Representation for ICS control rules.

The ControlRule IR is the bridge between the neural extraction layer (Phase 2)
and the formal verification layer (Phase 7). Every rule is normalised to a
canonical, machine-checkable form before being passed to Z3.
"""
from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, model_validator
import uuid


class RuleType(str, Enum):
    SHUTDOWN = "shutdown"
    CONTROL = "control"
    EMERGENCY_SHUTDOWN = "emergency_shutdown"
    INTERLOCK = "interlock"
    ALARM = "alarm"
    PERMISSIVE = "permissive"


class RuleAction(str, Enum):
    STOP = "STOP"
    START = "START"
    OPEN = "OPEN"
    CLOSE = "CLOSE"
    ALARM = "ALARM"
    ACTIVATE = "ACTIVATE"
    INHIBIT = "INHIBIT"
    UNKNOWN = "UNKNOWN"


class ComparisonOperator(str, Enum):
    GTE = ">="
    LTE = "<="
    GT = ">"
    LT = "<"
    EQ = "=="
    NEQ = "!="


class Condition(BaseModel):
    """A single condition: sensor_tag operator threshold unit."""
    sensor_tag: str = Field(..., description="Tag of the sensing element (e.g. PT-101)")
    operator: ComparisonOperator
    threshold: float
    unit: str = ""

    def to_z3_expr(self, z3_var_name: str) -> str:
        """Return a Z3 Python API expression string for this condition."""
        op_map = {
            ComparisonOperator.GTE: ">=",
            ComparisonOperator.LTE: "<=",
            ComparisonOperator.GT: ">",
            ComparisonOperator.LT: "<",
            ComparisonOperator.EQ: "==",
            ComparisonOperator.NEQ: "!=",
        }
        return f"({z3_var_name} {op_map[self.operator]} {self.threshold})"

    def __str__(self) -> str:
        return f"{self.sensor_tag} {self.operator.value} {self.threshold} {self.unit}".strip()


class ControlRule(BaseModel):
    """Canonical IR for a single ICS control rule extracted from a specification."""
    rule_id: str = Field(default_factory=lambda: f"R-{uuid.uuid4().hex[:6].upper()}")
    equipment_id: str = Field(..., description="Tag of the equipment this rule governs (e.g. P-101)")
    condition: Condition
    action: RuleAction
    rule_type: RuleType = RuleType.CONTROL
    trigger_tag: Optional[str] = None  # interlock or ESD tag, if present
    source_page: int = 0
    source_doc: str = ""
    source_modality: str = "narrative"  # narrative | table | pid
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    needs_review: bool = False
    ambiguity_note: Optional[str] = None

    @model_validator(mode="after")
    def flag_low_confidence(self) -> "ControlRule":
        if self.confidence < 0.7:
            self.needs_review = True
        return self

    def evidence_ref(self) -> str:
        return f"{self.source_doc} p.{self.source_page} [{self.source_modality}]"

    def __str__(self) -> str:
        return (
            f"{self.rule_id}: IF {self.condition} THEN {self.equipment_id} {self.action.value} "
            f"[{self.rule_type.value}] (conf={self.confidence:.2f})"
        )
