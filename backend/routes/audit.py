"""Audit routes — upload PDF, run pipeline in background, poll job status."""
import sys
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from db import AuditRepository
from db.models import User
from backend.deps import get_db_session, get_current_user, require_engineer
from backend.schemas import FindingOut, GraphEdge, GraphNode, GraphOut, RunSummary

router = APIRouter()

_UPLOADS_DIR = Path(__file__).parent.parent.parent / "output" / "uploads"
_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# ── In-memory job store (pipeline runs take 1-3 min; we return job_id instantly) ──
_jobs: Dict[str, dict] = {}

PHASES = [
    "PDF Extraction",
    "LLM Entity Extraction",
    "Cross-Modal Linking",
    "Knowledge Graph",
    "Rule IR",
    "Invariant Coverage",
    "Z3 Verification",
    "Audit Report",
    "PLC Sketch",
    "Persisting to DB",
]


def _run_pipeline(job_id: str, pdf_path: Path, output_dir: Path) -> None:
    """Runs in a daemon thread. Updates _jobs[job_id] as phases complete."""
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    _jobs[job_id].update(status="running", phase="Starting pipeline…", progress=0)
    try:
        from src.config import config
        from src.pipeline.auditor import SafetyAuditor

        # Monkey-patch loguru so we can capture phase transitions
        from loguru import logger
        _phase_idx = [0]

        original_info = logger.info
        def _info_hook(msg, *a, **kw):
            original_info(msg, *a, **kw)
            for i, name in enumerate(PHASES):
                key = name.lower().replace(" ", "_")
                if any(kw_hint in str(msg).lower() for kw_hint in [f"phase {i+1}", key, name.lower()]):
                    _phase_idx[0] = i
                    _jobs[job_id]["phase"] = name
                    _jobs[job_id]["progress"] = int((i / len(PHASES)) * 90)

        logger.info = _info_hook  # type: ignore

        auditor = SafetyAuditor(config)
        result = auditor.run(input_path=pdf_path, output_dir=output_dir)

        logger.info = original_info  # restore

        _jobs[job_id].update(
            status="completed",
            phase="Complete",
            progress=100,
            run_id=result.run_id,
            total_findings=result.total_findings,
            high_count=result.high_count,
            medium_count=result.medium_count,
            low_count=result.low_count,
            completed_at=datetime.utcnow().isoformat(),
        )
    except Exception as exc:
        _jobs[job_id].update(status="failed", phase="Failed", error=str(exc))


@router.post("/run")
async def run_audit(
    file: UploadFile = File(...),
    _: User = Depends(require_engineer),
):
    """Start an audit in the background. Returns job_id immediately."""
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    job_id = str(uuid.uuid4())
    run_dir = _UPLOADS_DIR / job_id
    run_dir.mkdir(parents=True)
    pdf_path = run_dir / (file.filename or "upload.pdf")
    pdf_path.write_bytes(await file.read())
    output_dir = run_dir / "output"
    output_dir.mkdir()

    _jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "phase": "Queued",
        "progress": 0,
        "filename": file.filename,
        "run_id": None,
        "error": None,
        "created_at": datetime.utcnow().isoformat(),
        "completed_at": None,
        "total_findings": 0,
        "high_count": 0,
        "medium_count": 0,
        "low_count": 0,
    }

    thread = threading.Thread(
        target=_run_pipeline, args=(job_id, pdf_path, output_dir), daemon=True
    )
    thread.start()

    return {"job_id": job_id, "status": "queued"}


@router.get("/job/{job_id}")
def get_job(job_id: str, _: User = Depends(get_current_user)):
    """Poll job status. Frontend polls this every 2s."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return _jobs[job_id]


@router.get("/stats")
def get_stats(
    session: Session = Depends(get_db_session),
    _: User = Depends(get_current_user),
):
    """Overview stats for the dashboard home page."""
    repo = AuditRepository(session)
    history = repo.get_history(limit=200)
    total_findings = sum(r.total_findings for r in history)
    total_high = sum(r.high_count for r in history)
    summary = repo.get_finding_type_summary()
    return {
        "total_runs": len(history),
        "total_findings": total_findings,
        "total_high": total_high,
        "finding_summary": summary,
        "recent_runs": [r.to_dict() for r in history[:5]],
    }


@router.get("/history", response_model=List[RunSummary])
def get_history(
    limit: int = 50,
    session: Session = Depends(get_db_session),
    _: User = Depends(get_current_user),
):
    repo = AuditRepository(session)
    return repo.get_history(limit=limit)


@router.get("/{run_id}", response_model=RunSummary)
def get_run(
    run_id: str,
    session: Session = Depends(get_db_session),
    _: User = Depends(get_current_user),
):
    repo = AuditRepository(session)
    run = repo.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/{run_id}/findings", response_model=List[FindingOut])
def get_findings(
    run_id: str,
    session: Session = Depends(get_db_session),
    _: User = Depends(get_current_user),
):
    repo = AuditRepository(session)
    return repo.get_findings(run_id)


@router.get("/{run_id}/graph", response_model=GraphOut)
def get_graph(
    run_id: str,
    session: Session = Depends(get_db_session),
    _: User = Depends(get_current_user),
):
    repo = AuditRepository(session)
    nodes = repo.get_kg_nodes(run_id)
    edges = repo.get_kg_edges(run_id)
    return GraphOut(
        nodes=[
            GraphNode(id=n.node_id, label=n.label or n.node_id, node_type=n.node_type or "Unknown")
            for n in nodes
        ],
        edges=[
            GraphEdge(
                from_id=e.source_id, to_id=e.target_id,
                label=e.label or "", rel_type=e.rel_type or "controls",
            )
            for e in edges
        ],
    )
