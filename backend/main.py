"""FastAPI backend — Neuro-Symbolic Safety Auditing Framework."""
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure project root is on path so `db`, `src` are importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from db import init_db, get_session
from db.models import User
from backend.auth import hash_password
from backend.routes.audit import router as audit_router
from backend.routes.users import router as users_router
from backend.auth import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialise DB and seed admin user if none exist."""
    init_db()
    _seed_admin()
    yield


def _seed_admin():
    """Create default admin/admin123 on first run if no users exist."""
    with get_session() as session:
        count = session.query(User).count()
        if count == 0:
            session.add(User(
                username="admin",
                email="admin@safety-auditor.local",
                hashed_password=hash_password("admin123"),
                role="admin",
                is_active=True,
            ))


app = FastAPI(
    title="ICS Safety Auditor API",
    description="Neuro-Symbolic Pre-Synthesis Safety Auditing Framework",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated audit reports and PLC files as static files
output_dir = Path(__file__).parent.parent / "output"
output_dir.mkdir(exist_ok=True)
app.mount("/output", StaticFiles(directory=str(output_dir)), name="output")

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(audit_router, prefix="/audit", tags=["audit"])
app.include_router(users_router, prefix="/users", tags=["users"])


@app.get("/health")
def health():
    return {"status": "ok"}
