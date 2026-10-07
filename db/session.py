"""
SQLite Engine and Session Factory
===================================

WHY SQLite?
  SQLite is a serverless, file-based relational database built into Python.
  Advantages for this project:
    - Zero setup: no installation, no server, no credentials
    - Single file: output/audit_store.db — copy it, share it, back it up
    - Full SQL: joins, aggregates, foreign keys all work
    - Thread-safe with WAL mode (required for Streamlit's multi-thread UI)
    - Drop-in swappable: change create_engine() to use PostgreSQL in one line

  The schema is created automatically the first time init_db() is called.
  If the file already exists and tables exist, create_all() is a no-op.

USAGE PATTERN (context manager — always use this form)
  from src.db import get_session, AuditRepository

  with get_session() as session:
      repo = AuditRepository(session)
      runs = repo.get_history()
      # session auto-commits on exit, auto-rolls back on exception

SESSION LIFECYCLE
  get_session() returns a context manager (not a raw Session).
  Inside the `with` block:
    - The session is open and usable
    - On normal exit → session.commit() then session.close()
    - On exception → session.rollback() then session.close() then re-raise
  Never call session.commit() or session.close() manually.
"""
from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from .models import Base

# Path to the SQLite database file.
# Default: output/audit_store.db  (relative to the project root).
# Override by passing a Path to init_db(db_path=...).
_DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "output" / "audit_store.db"

# Module-level engine and session factory — initialised once by init_db().
# Both are None until init_db() is called.
engine = None
_SessionLocal = None


def init_db(db_path: Path | None = None) -> None:
    """
    Initialise the SQLite database.

    Creates the database file and all tables if they do not exist.
    Safe to call multiple times — create_all() is idempotent.

    Args:
        db_path: Optional path override. If None, uses output/audit_store.db.

    Called automatically by SafetyAuditor.__init__() and by the Streamlit
    UI cache resource, so application code rarely needs to call this directly.
    """
    global engine, _SessionLocal

    path = Path(db_path) if db_path else _DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    # SQLite connection string. check_same_thread=False is required because
    # Streamlit's server runs the UI in a different thread from the pipeline.
    engine = create_engine(
        f"sqlite:///{path}",
        connect_args={"check_same_thread": False},
        echo=False,  # Set True to log all SQL to stdout (useful for debugging)
    )

    # WAL (Write-Ahead Logging) mode: allows concurrent reads while writing.
    # Required for Streamlit which may read the DB while the pipeline is writing.
    # PRAGMA foreign_keys=ON enforces referential integrity (cascade deletes).
    @event.listens_for(engine, "connect")
    def set_pragmas(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA journal_mode=WAL")
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    # Create all tables defined in models.py. No-op if they already exist.
    Base.metadata.create_all(bind=engine)

    # sessionmaker is a factory that creates Session objects on demand.
    # autocommit=False: we control commits explicitly (or via context manager).
    # autoflush=False: don't flush to DB until we commit.
    _SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@contextmanager
def get_session() -> Session:
    """
    Context manager yielding a database session.

    Usage:
        with get_session() as session:
            repo = AuditRepository(session)
            repo.save_run(...)

    The session commits automatically on clean exit and rolls back on any
    exception, then closes either way. Never call session.commit() manually.

    Calls init_db() automatically if the engine has not been initialised yet
    (e.g. if the session is opened before SafetyAuditor is instantiated).
    """
    if _SessionLocal is None:
        init_db()

    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
