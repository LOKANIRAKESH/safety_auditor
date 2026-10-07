"""Evaluation package init."""
from evaluation.metrics import compute_metrics, EvaluationResult, DetectionMetrics
from evaluation.run_evaluation import evaluate_corpus, run_full_evaluation
from evaluation.baseline import run_post_generation_baseline, BaselineResult

__all__ = [
    "compute_metrics", "EvaluationResult", "DetectionMetrics",
    "evaluate_corpus", "run_full_evaluation",
    "run_post_generation_baseline", "BaselineResult",
]
