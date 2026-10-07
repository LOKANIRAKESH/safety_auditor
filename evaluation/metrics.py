"""Evaluation metrics: Precision, Recall, F1, AUROC for safety defect detection."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List
import numpy as np


@dataclass
class DetectionMetrics:
    """Metrics for a single defect category or overall."""
    category: str
    precision: float
    recall: float
    f1: float
    tp: int
    fp: int
    fn: int
    tn: int

    @property
    def accuracy(self) -> float:
        total = self.tp + self.fp + self.fn + self.tn
        return (self.tp + self.tn) / total if total > 0 else 0.0

    def to_row(self) -> dict:
        return {
            "Category": self.category,
            "Precision": f"{self.precision:.3f}",
            "Recall": f"{self.recall:.3f}",
            "F1": f"{self.f1:.3f}",
            "TP": self.tp, "FP": self.fp, "FN": self.fn,
        }


@dataclass
class EvaluationResult:
    overall: DetectionMetrics
    per_category: Dict[str, DetectionMetrics] = field(default_factory=dict)
    per_severity: Dict[str, DetectionMetrics] = field(default_factory=dict)
    package_count: int = 0
    defective_count: int = 0
    clean_count: int = 0


def compute_metrics(
    ground_truth: List[dict],   # List of injection records from injections.json
    predictions: List[dict],    # List of findings from the auditor
    defect_categories: List[str] = None,
) -> EvaluationResult:
    """
    Compute detection metrics by matching auditor findings against ground-truth injections.
    A finding MATCHES an injection if:
      - expected_finding_type matches finding_type (or is a parent category), AND
      - expected_severity matches severity
    """
    if defect_categories is None:
        defect_categories = ["missing_shutdown_rule", "contradiction", "missing_alarm", "tag_mismatch", "missing_interlock"]

    # Build sets
    expected_positive = {(r["package_id"], r["expected_finding_type"]) for r in ground_truth if r["expected_finding"]}
    detected_positive = {(p.get("package_id", ""), p.get("Type", "")) for p in predictions}

    tp = len(expected_positive & detected_positive)
    fp = len(detected_positive - expected_positive)
    fn = len(expected_positive - detected_positive)
    tn = 0  # estimated from clean packages

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    overall = DetectionMetrics(
        category="overall",
        precision=precision, recall=recall, f1=f1,
        tp=tp, fp=fp, fn=fn, tn=tn,
    )

    # Per-category breakdown
    per_cat: Dict[str, DetectionMetrics] = {}
    finding_type_map = {
        "missing_shutdown_rule": "OMISSION",
        "contradiction": "CONTRADICTION",
        "missing_alarm": "OMISSION",
        "tag_mismatch": "TAG_MISMATCH",
        "missing_interlock": "OMISSION",
    }
    for cat in defect_categories:
        ft = finding_type_map.get(cat, "OMISSION")
        cat_expected = {(r["package_id"], ft) for r in ground_truth if r.get("defect_type") == cat and r["expected_finding"]}
        cat_detected = {(p.get("package_id", ""), p.get("Type", "")) for p in predictions if p.get("Type") == ft}
        cat_tp = len(cat_expected & cat_detected)
        cat_fp = len(cat_detected - cat_expected)
        cat_fn = len(cat_expected - cat_detected)
        cat_p = cat_tp / (cat_tp + cat_fp) if (cat_tp + cat_fp) > 0 else 0.0
        cat_r = cat_tp / (cat_tp + cat_fn) if (cat_tp + cat_fn) > 0 else 0.0
        cat_f1 = 2 * cat_p * cat_r / (cat_p + cat_r) if (cat_p + cat_r) > 0 else 0.0
        per_cat[cat] = DetectionMetrics(category=cat, precision=cat_p, recall=cat_r, f1=cat_f1,
                                         tp=cat_tp, fp=cat_fp, fn=cat_fn, tn=0)

    return EvaluationResult(overall=overall, per_category=per_cat)
