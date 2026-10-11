"""
Standards Knowledge Base — SQLite storage for extracted SafetyRule objects.

Schema:
  safety_rules   — one row per extracted rule
  rule_equipment — M:M join: rule_id → equipment_class
  rule_sensors   — M:M join: rule_id → sensor_class

The DB also generates invariant template JSON files (same format as the
existing 19-rule corpus in data/invariant_templates/) so the verification
engine automatically picks up new rules without any code changes.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from loguru import logger

from src.standards.rule_extractor import SafetyRule


_DDL = """
CREATE TABLE IF NOT EXISTS safety_rules (
    rule_id            TEXT PRIMARY KEY,
    source_id          TEXT NOT NULL,
    standard_ref       TEXT NOT NULL,
    clause_ref         TEXT NOT NULL,
    requirement_text   TEXT NOT NULL,
    requirement_type   TEXT NOT NULL,
    condition_type     TEXT NOT NULL,
    action_required    TEXT NOT NULL,
    severity_if_missing TEXT NOT NULL,
    setpoint_role      TEXT NOT NULL,
    iec_equivalent     TEXT,
    confidence         REAL DEFAULT 0.8,
    notes              TEXT DEFAULT '',
    created_at         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rule_equipment (
    rule_id         TEXT NOT NULL REFERENCES safety_rules(rule_id),
    equipment_class TEXT NOT NULL,
    PRIMARY KEY (rule_id, equipment_class)
);

CREATE TABLE IF NOT EXISTS rule_sensors (
    rule_id      TEXT NOT NULL REFERENCES safety_rules(rule_id),
    sensor_class TEXT NOT NULL,
    PRIMARY KEY (rule_id, sensor_class)
);

CREATE INDEX IF NOT EXISTS idx_rules_type     ON safety_rules(requirement_type);
CREATE INDEX IF NOT EXISTS idx_rules_source   ON safety_rules(source_id);
CREATE INDEX IF NOT EXISTS idx_rules_severity ON safety_rules(severity_if_missing);
CREATE INDEX IF NOT EXISTS idx_equip_class    ON rule_equipment(equipment_class);
"""


class StandardsDB:
    """
    Persistent SQLite store for the standards knowledge base.

    Usage:
        db = StandardsDB()
        db.insert_rules(rules)            # store extracted rules
        alarm_rules = db.query_by_type("alarm")
        db.export_invariant_templates()   # write JSON files for verifier
    """

    def __init__(self, db_path: Path = None):
        if db_path is None:
            from src.config import PipelineConfig
            db_path = PipelineConfig().data_dir / "standards" / "knowledge_base.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_DDL)
        self._conn.commit()
        logger.debug(f"Standards DB opened: {self.db_path}")

    # ── Write ────────────────────────────────────────────────────────────────

    def insert_rules(self, rules: List[SafetyRule]) -> int:
        """Insert a list of SafetyRule objects; skip duplicates by rule_id. Returns count inserted."""
        cur     = self._conn.cursor()
        ts      = datetime.utcnow().isoformat()
        inserted = 0
        for r in rules:
            try:
                cur.execute(
                    """INSERT OR IGNORE INTO safety_rules
                       (rule_id,standard_ref,source_id,clause_ref,requirement_text,
                        requirement_type,condition_type,action_required,
                        severity_if_missing,setpoint_role,iec_equivalent,
                        confidence,notes,created_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (r.rule_id, r.standard_ref, r.source_id, r.clause_ref,
                     r.requirement_text, r.requirement_type, r.condition_type,
                     r.action_required, r.severity_if_missing, r.setpoint_role,
                     r.iec_equivalent, r.confidence, r.notes, ts),
                )
                if cur.rowcount:
                    for eq in r.equipment_classes:
                        cur.execute(
                            "INSERT OR IGNORE INTO rule_equipment(rule_id,equipment_class) VALUES(?,?)",
                            (r.rule_id, eq),
                        )
                    for sc in r.sensor_classes:
                        cur.execute(
                            "INSERT OR IGNORE INTO rule_sensors(rule_id,sensor_class) VALUES(?,?)",
                            (r.rule_id, sc),
                        )
                    inserted += 1
            except sqlite3.Error as exc:
                logger.warning(f"DB insert failed for {r.rule_id}: {exc}")
        self._conn.commit()
        logger.info(f"Inserted {inserted}/{len(rules)} new rules into knowledge base")
        return inserted

    def clear_source(self, source_id: str) -> None:
        """Remove all rules from one source (e.g. before re-running extraction on updated file)."""
        cur = self._conn.cursor()
        cur.execute("SELECT rule_id FROM safety_rules WHERE source_id=?", (source_id,))
        ids = [row[0] for row in cur.fetchall()]
        for rid in ids:
            cur.execute("DELETE FROM rule_equipment WHERE rule_id=?", (rid,))
            cur.execute("DELETE FROM rule_sensors WHERE rule_id=?", (rid,))
        cur.execute("DELETE FROM safety_rules WHERE source_id=?", (source_id,))
        self._conn.commit()
        logger.info(f"Cleared {len(ids)} rules for source '{source_id}'")

    # ── Read ─────────────────────────────────────────────────────────────────

    def query_by_type(self, requirement_type: str) -> List[SafetyRule]:
        """Return all rules of a given type (e.g. 'alarm', 'shutdown', 'interlock')."""
        cur = self._conn.cursor()
        cur.execute(
            "SELECT * FROM safety_rules WHERE requirement_type=? ORDER BY severity_if_missing, rule_id",
            (requirement_type.lower(),),
        )
        return [self._row_to_rule(cur, row) for row in cur.fetchall()]

    def query_by_equipment(self, equipment_class: str) -> List[SafetyRule]:
        """Return rules that apply to a specific equipment class."""
        cur = self._conn.cursor()
        cur.execute(
            """SELECT sr.* FROM safety_rules sr
               JOIN rule_equipment re ON sr.rule_id = re.rule_id
               WHERE re.equipment_class=? ORDER BY sr.severity_if_missing, sr.rule_id""",
            (equipment_class,),
        )
        return [self._row_to_rule(cur, row) for row in cur.fetchall()]

    def query_by_severity(self, severity: str) -> List[SafetyRule]:
        """Return rules by severity: HIGH | MEDIUM | LOW."""
        cur = self._conn.cursor()
        cur.execute(
            "SELECT * FROM safety_rules WHERE severity_if_missing=? ORDER BY rule_id",
            (severity.upper(),),
        )
        return [self._row_to_rule(cur, row) for row in cur.fetchall()]

    def query_all(self) -> List[SafetyRule]:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM safety_rules ORDER BY severity_if_missing DESC, rule_id")
        return [self._row_to_rule(cur, row) for row in cur.fetchall()]

    def stats(self) -> dict:
        """Summary statistics for the knowledge base."""
        cur = self._conn.cursor()
        cur.execute("SELECT COUNT(*) FROM safety_rules")
        total = cur.fetchone()[0]
        cur.execute("SELECT requirement_type, COUNT(*) FROM safety_rules GROUP BY requirement_type")
        by_type = dict(cur.fetchall())
        cur.execute("SELECT severity_if_missing, COUNT(*) FROM safety_rules GROUP BY severity_if_missing")
        by_sev = dict(cur.fetchall())
        cur.execute("SELECT COUNT(DISTINCT source_id) FROM safety_rules")
        sources = cur.fetchone()[0]
        return {
            "total_rules": total,
            "sources":     sources,
            "by_type":     by_type,
            "by_severity": by_sev,
        }

    # ── Export invariant templates ────────────────────────────────────────────

    def export_invariant_templates(self, output_dir: Path = None) -> Path:
        """
        Export all HIGH-severity rules as invariant template JSON files
        in the format expected by the IEC 61511 verifier.

        Each file: data/invariant_templates/<requirement_type>.json
        This AUGMENTS the existing 19 hardcoded invariants with
        standards-derived rules — the verifier reads all JSON files
        in that directory at startup.
        """
        if output_dir is None:
            from src.config import PipelineConfig
            output_dir = PipelineConfig().data_dir / "invariant_templates"
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        rules_by_type: dict[str, list] = {}
        for rule in self.query_by_severity("HIGH"):
            t = rule.requirement_type
            rules_by_type.setdefault(t, [])
            rules_by_type[t].append({
                "id":                rule.rule_id,
                "standard_ref":      rule.standard_ref,
                "clause_ref":        rule.clause_ref,
                "description":       rule.requirement_text,
                "requirement_type":  rule.requirement_type,
                "equipment_classes": rule.equipment_classes,
                "sensor_classes":    rule.sensor_classes,
                "condition_type":    rule.condition_type,
                "action_required":   rule.action_required,
                "setpoint_role":     rule.setpoint_role,
                "iec_equivalent":    rule.iec_equivalent,
                "confidence":        rule.confidence,
            })

        written: List[Path] = []
        for req_type, items in rules_by_type.items():
            fname = output_dir / f"standards_kb_{req_type}.json"
            existing: List[dict] = []
            if fname.exists():
                try:
                    existing = json.loads(fname.read_text())
                except Exception:
                    pass
            # Merge: existing rules first, then add new ones by ID
            existing_ids = {r["id"] for r in existing}
            merged = existing + [r for r in items if r["id"] not in existing_ids]
            fname.write_text(json.dumps(merged, indent=2))
            written.append(fname)
            logger.info(f"Exported {len(merged)} {req_type} rules → {fname.name}")

        logger.success(
            f"Invariant templates updated: {len(written)} files in {output_dir}"
        )
        return output_dir

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _row_to_rule(self, cur: sqlite3.Cursor, row: sqlite3.Row) -> SafetyRule:
        rid = row["rule_id"]
        cur.execute("SELECT equipment_class FROM rule_equipment WHERE rule_id=?", (rid,))
        equip = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT sensor_class FROM rule_sensors WHERE rule_id=?", (rid,))
        sensors = [r[0] for r in cur.fetchall()]
        return SafetyRule(
            rule_id           = rid,
            source_id         = row["source_id"],
            standard_ref      = row["standard_ref"],
            clause_ref        = row["clause_ref"],
            requirement_text  = row["requirement_text"],
            requirement_type  = row["requirement_type"],
            equipment_classes = equip,
            sensor_classes    = sensors,
            condition_type    = row["condition_type"],
            action_required   = row["action_required"],
            severity_if_missing = row["severity_if_missing"],
            setpoint_role     = row["setpoint_role"],
            iec_equivalent    = row["iec_equivalent"] or "",
            confidence        = row["confidence"],
            notes             = row["notes"] or "",
        )

    def close(self) -> None:
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
