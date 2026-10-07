"""Pydantic request/response schemas for the REST API."""
from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class RunSummary(BaseModel):
    run_id: str
    input_source: str
    created_at: Optional[datetime]
    llm_model: Optional[str]
    total_findings: int
    high_count: int
    medium_count: int
    low_count: int
    total_rules: int
    total_entities: int
    invariants_checked: int
    status: Optional[str]
    report_path: Optional[str]
    plc_path: Optional[str]

    class Config:
        from_attributes = True


class FindingOut(BaseModel):
    id: int
    finding_type: str
    severity: str
    equipment_tag: Optional[str]
    invariant_id: Optional[str]
    iec_clause: Optional[str]
    description: Optional[str]
    recommendation: Optional[str]
    z3_result: Optional[str]

    class Config:
        from_attributes = True


class GraphNode(BaseModel):
    id: str
    label: str
    node_type: str


class GraphEdge(BaseModel):
    from_id: str
    to_id: str
    label: str
    rel_type: str


class GraphOut(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


class UserOut(BaseModel):
    id: int
    username: str
    email: Optional[str]
    role: str
    is_active: bool
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    username: str
    email: Optional[str] = None
    password: str
    role: str = "engineer"
