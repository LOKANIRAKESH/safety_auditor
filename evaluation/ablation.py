"""Ablation study: cross-modal linking ON vs OFF — tests H2 from the proposal."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from loguru import logger


@dataclass
class AblationResult:
    with_linking_f1: float
    without_linking_f1: float
    with_linking_precision: float
    without_linking_precision: float
    with_linking_recall: float
    without_linking_recall: float
    delta_f1: float
    conclusion: str

    def to_table_row(self) -> dict:
        return {
            "Configuration": ["With Cross-Modal Linking", "Without Cross-Modal Linking"],
            "Precision": [f"{self.with_linking_precision:.3f}", f"{self.without_linking_precision:.3f}"],
            "Recall": [f"{self.with_linking_recall:.3f}", f"{self.without_linking_recall:.3f}"],
            "F1": [f"{self.with_linking_f1:.3f}", f"{self.without_linking_f1:.3f}"],
        }


def run_ablation(corpus_dir: Path, output_dir: Path) -> AblationResult:
    """
    Runs the full evaluation twice:
      Run A: enable_cross_modal_linking = True
      Run B: enable_cross_modal_linking = False
    Compares F1 scores to test H2.
    """
    from src.config import PipelineConfig
    from evaluation.run_evaluation import evaluate_corpus

    logger.info("Ablation study: Run A (cross-modal linking ENABLED)...")
    config_a = PipelineConfig()
    config_a.enable_cross_modal_linking = True
    result_a = evaluate_corpus(corpus_dir, output_dir / "ablation_with_linking", config_a)

    logger.info("Ablation study: Run B (cross-modal linking DISABLED)...")
    config_b = PipelineConfig()
    config_b.enable_cross_modal_linking = False
    result_b = evaluate_corpus(corpus_dir, output_dir / "ablation_without_linking", config_b)

    delta = result_a.overall.f1 - result_b.overall.f1
    conclusion = (
        f"Cross-modal linking {'improves' if delta > 0 else 'does not improve'} F1 by {abs(delta):.3f}. "
        f"H2 {'supported' if delta > 0.02 else 'not strongly supported'} at this threshold."
    )
    logger.info(f"Ablation conclusion: {conclusion}")

    ablation = AblationResult(
        with_linking_f1=result_a.overall.f1,
        without_linking_f1=result_b.overall.f1,
        with_linking_precision=result_a.overall.precision,
        without_linking_precision=result_b.overall.precision,
        with_linking_recall=result_a.overall.recall,
        without_linking_recall=result_b.overall.recall,
        delta_f1=delta,
        conclusion=conclusion,
    )
    return ablation
