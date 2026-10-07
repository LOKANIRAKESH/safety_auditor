"""
Post-generation baseline: naive PLC code generator → Z3 code-level check only.

Paper Section V-B framing:
  The baseline represents current industrial practice — verify PLC code AFTER generation.
  It applies Z3 to what IS written and cannot detect OMISSION defects (missing shutdown
  rules, missing alarms, missing interlocks) because they are simply absent from the code.

  Our pre-synthesis approach detects omissions by comparing extracted rules against
  the IEC 61511 invariant library, which is independent of whether the rule was written.

Expected result from the paper:
  - Baseline recall on OMISSION ≈ 0.0 (cannot detect what isn't there)
  - Our approach recall on OMISSION ≈ high (invariant library acts as oracle)
  - Baseline F1 significantly lower overall
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger


@dataclass
class BaselineResult:
    """P/R/F1 metrics from the post-generation Z3-code-level baseline."""
    total_packages: int
    tp: int
    fp: int
    fn: int
    precision: float
    recall: float
    f1: float
    per_category: Dict[str, Dict[str, float]] = field(default_factory=dict)
    # Key paper result: omission defects the baseline completely misses
    omission_miss_rate: float = 1.0
    notes: str = ""

    def to_table_row(self) -> dict:
        return {
            "System": "Post-Generation Baseline",
            "Precision": f"{self.precision:.3f}",
            "Recall": f"{self.recall:.3f}",
            "F1": f"{self.f1:.3f}",
            "Omission Miss Rate": f"{self.omission_miss_rate:.1%}",
        }

    def print_summary(self) -> None:
        print(f"\nPost-Generation Baseline Results")
        print(f"  Precision: {self.precision:.3f}")
        print(f"  Recall:    {self.recall:.3f}")
        print(f"  F1:        {self.f1:.3f}")
        print(f"  Omission miss rate: {self.omission_miss_rate:.1%}  (expected ≈100%)")
        if self.notes:
            print(f"  Note: {self.notes}")


def _z3_code_level_check(rules: List[dict]) -> List[dict]:
    """
    Apply Z3 at code level only: detect contradictions in written rules.
    Cannot detect omissions — rules that were never written produce no Z3 clauses.

    Args:
        rules: List of extracted rule dicts with keys:
               equipment_tag, condition_operator, condition_threshold,
               action, rule_type, condition_tag

    Returns:
        List of finding dicts {type, equipment_tag, note}
    """
    try:
        import z3
    except ImportError:
        logger.warning("z3-solver not installed — baseline Z3 check skipped, returning empty")
        return []

    findings: List[dict] = []
    shutdown_constraints: List[tuple] = []  # (equipment_tag, z3_constraint)

    equip_vars: dict[str, z3.BoolRef] = {}

    for rule in rules:
        tag = rule.get("equipment_tag", "").strip()
        action = rule.get("action", "UNKNOWN").upper()
        rule_type = rule.get("rule_type", "CONTROL").upper()

        if not tag:
            continue
        if tag not in equip_vars:
            safe_name = tag.replace("-", "_").replace(" ", "_")
            equip_vars[tag] = z3.Bool(f"active_{safe_name}")

        # Encode only SAFETY-type rules into Z3 constraints
        if rule_type == "SAFETY" and action in ("STOP", "CLOSE", "ACTIVATE", "OPEN"):
            # STOP/CLOSE → equipment must NOT be active
            if action in ("STOP", "CLOSE"):
                shutdown_constraints.append((tag, z3.Not(equip_vars[tag])))
            # ACTIVATE (e.g., ESD system) → must be active
            elif action in ("ACTIVATE", "OPEN"):
                shutdown_constraints.append((tag, equip_vars[tag]))

    if len(shutdown_constraints) >= 2:
        solver = z3.Solver()
        solver.set("timeout", 3000)
        for _, constraint in shutdown_constraints:
            solver.add(constraint)
        result = solver.check()
        if result == z3.unsat:
            # Contradiction: the written rules are collectively unsatisfiable
            tags_involved = list({tag for tag, _ in shutdown_constraints})
            for tag in tags_involved[:1]:  # Report once per contradicting set
                findings.append({
                    "type": "CONTRADICTION",
                    "equipment_tag": tag,
                    "note": "Z3 code-level: written shutdown rules are mutually unsatisfiable"
                })

    # Check individual equipment for unsafe-state reachability
    for tag, var in equip_vars.items():
        solver = z3.Solver()
        solver.set("timeout", 2000)
        for t, c in shutdown_constraints:
            if t == tag:
                solver.add(c)
        # Is it possible for equipment to be active despite shutdown rules?
        solver.add(var)
        result = solver.check()
        if result == z3.sat:
            # Unsafe state is reachable in the code
            findings.append({
                "type": "UNSAFE_STATE",
                "equipment_tag": tag,
                "note": "Z3 code-level: equipment can be active when shutdown rule fires"
            })

    return findings


DEFECT_TO_FINDING_TYPE = {
    "missing_shutdown_rule": "OMISSION",
    "contradiction": "CONTRADICTION",
    "missing_alarm": "OMISSION",
    "tag_mismatch": "TAG_MISMATCH",
    "missing_interlock": "OMISSION",
}


def run_post_generation_baseline(
    corpus_dir: Path,
    output_dir: Optional[Path] = None,
) -> BaselineResult:
    """
    Run the post-generation baseline over the corpus.

    Requires: benchmark packages have been generated (benchmark/corpus/) and
              the main evaluation has been run so rules.json exists per package.
              If rules.json is missing, the package is skipped (counts as no detections).

    Args:
        corpus_dir: Path to benchmark corpus (e.g. benchmark/corpus/)
        output_dir: Optional path to save baseline_results.json

    Returns:
        BaselineResult with P/R/F1 and per-category breakdown
    """
    corpus_dir = Path(corpus_dir)
    all_gt: List[dict] = []
    all_baseline_preds: List[dict] = []

    pkg_dirs = sorted([d for d in corpus_dir.iterdir() if d.is_dir()])
    if not pkg_dirs:
        logger.warning("No packages found in %s", corpus_dir)
        return BaselineResult(
            total_packages=0, tp=0, fp=0, fn=0,
            precision=0.0, recall=0.0, f1=0.0,
        )

    logger.info("Running post-generation baseline on %d packages...", len(pkg_dirs))

    for pkg_dir in pkg_dirs:
        inj_path = pkg_dir / "injections.json"
        if not inj_path.exists():
            continue

        injections: List[dict] = json.loads(inj_path.read_text(encoding="utf-8"))
        for inj in injections:
            inj["package_id"] = pkg_dir.name
        all_gt.extend(injections)

        # Load extracted rules saved by main eval run (if they exist)
        rules: List[dict] = []
        rules_path = pkg_dir / "rules.json"
        if rules_path.exists():
            try:
                rules = json.loads(rules_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        findings = _z3_code_level_check(rules)
        for finding in findings:
            finding["package_id"] = pkg_dir.name
        all_baseline_preds.extend(findings)

    # Ground-truth positive set: (package_id, finding_type)
    gt_set: set[tuple] = set()
    omission_gt: set[tuple] = set()
    for r in all_gt:
        if not r.get("expected_finding", True):
            continue
        ftype = DEFECT_TO_FINDING_TYPE.get(r.get("defect_type", ""), "OMISSION")
        key = (r["package_id"], ftype)
        gt_set.add(key)
        if ftype == "OMISSION":
            omission_gt.add(key)

    # Prediction set
    pred_set: set[tuple] = set()
    for p in all_baseline_preds:
        key = (p.get("package_id", ""), p.get("type", ""))
        pred_set.add(key)

    tp = len(gt_set & pred_set)
    fp = len(pred_set - gt_set)
    fn = len(gt_set - pred_set)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    # Omission miss rate: the baseline cannot detect omissions
    omission_detected = len(omission_gt & pred_set)
    omission_miss_rate = (
        1.0 - (omission_detected / len(omission_gt))
        if omission_gt else 1.0
    )

    # Per-category breakdown
    all_finding_types = list({v for v in DEFECT_TO_FINDING_TYPE.values()})
    per_cat: Dict[str, Dict[str, float]] = {}
    for ftype in all_finding_types:
        cat_gt = {k for k in gt_set if k[1] == ftype}
        cat_pred = {k for k in pred_set if k[1] == ftype}
        cat_tp = len(cat_gt & cat_pred)
        cat_fp = len(cat_pred - cat_gt)
        cat_fn = len(cat_gt - cat_pred)
        cat_p = cat_tp / (cat_tp + cat_fp) if (cat_tp + cat_fp) > 0 else 0.0
        cat_r = cat_tp / (cat_tp + cat_fn) if (cat_tp + cat_fn) > 0 else 0.0
        cat_f1 = 2 * cat_p * cat_r / (cat_p + cat_r) if (cat_p + cat_r) > 0 else 0.0
        per_cat[ftype] = {"precision": cat_p, "recall": cat_r, "f1": cat_f1}

    result = BaselineResult(
        total_packages=len(pkg_dirs),
        tp=tp,
        fp=fp,
        fn=fn,
        precision=precision,
        recall=recall,
        f1=f1,
        per_category=per_cat,
        omission_miss_rate=omission_miss_rate,
        notes=(
            "Baseline cannot detect OMISSION defects (missing rules leave no Z3 clauses). "
            f"Omission miss rate: {omission_miss_rate:.1%}. "
            "This confirms the pre-synthesis auditing advantage."
        ),
    )

    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / "baseline_results.json"
        out_path.write_text(
            json.dumps({
                "precision": result.precision,
                "recall": result.recall,
                "f1": result.f1,
                "omission_miss_rate": result.omission_miss_rate,
                "per_category": result.per_category,
            }, indent=2),
            encoding="utf-8",
        )
        logger.info("Baseline results saved to %s", out_path)

    logger.info(
        "Baseline: P=%.3f R=%.3f F1=%.3f | omission_miss=%.1%%",
        precision, recall, f1, omission_miss_rate * 100,
    )
    return result
