"""Master evaluation runner — produces paper-ready metrics tables and figures."""
from __future__ import annotations
import json
from pathlib import Path
from typing import List, Optional
import pandas as pd
from loguru import logger
from src.config import PipelineConfig
from src.pipeline.auditor import SafetyAuditor
from evaluation.metrics import compute_metrics, EvaluationResult


def evaluate_corpus(
    corpus_dir: Path,
    output_dir: Path,
    config: Optional[PipelineConfig] = None,
) -> EvaluationResult:
    """Run the auditor on every package in corpus_dir and compute P/R/F1."""
    corpus_dir = Path(corpus_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if config is None:
        config = PipelineConfig()

    auditor = SafetyAuditor(config)
    all_ground_truth: List[dict] = []
    all_predictions: List[dict] = []

    packages = sorted([p for p in corpus_dir.iterdir() if p.is_dir()])
    logger.info(f"Evaluating {len(packages)} packages from {corpus_dir}")

    for pkg_dir in packages:
        injection_file = pkg_dir / "injections.json"
        if not injection_file.exists():
            continue

        injections = json.loads(injection_file.read_text(encoding="utf-8"))
        # Tag ground truth with package_id
        for inj in injections:
            inj["package_id"] = pkg_dir.name
        all_ground_truth.extend(injections)

        try:
            pkg_output = output_dir / pkg_dir.name
            result = auditor.run(pkg_dir, pkg_output)
            for finding in result.findings:
                row = finding.to_row()
                row["package_id"] = pkg_dir.name
                all_predictions.append(row)
        except Exception as e:
            logger.error(f"Audit failed for {pkg_dir.name}: {e}")

    # Compute metrics
    eval_result = compute_metrics(all_ground_truth, all_predictions)
    eval_result.package_count = len(packages)
    eval_result.defective_count = sum(1 for inj_list in all_ground_truth if inj_list.get("expected_finding"))
    eval_result.clean_count = eval_result.package_count - min(eval_result.package_count, eval_result.defective_count)

    # Save results
    _save_results(eval_result, all_ground_truth, all_predictions, output_dir)
    return eval_result


def _save_results(
    result: EvaluationResult,
    ground_truth: List[dict],
    predictions: List[dict],
    output_dir: Path,
) -> None:
    # metrics.json
    metrics_data = {
        "overall": {
            "precision": result.overall.precision,
            "recall": result.overall.recall,
            "f1": result.overall.f1,
            "tp": result.overall.tp,
            "fp": result.overall.fp,
            "fn": result.overall.fn,
        },
        "per_category": {
            cat: {"precision": m.precision, "recall": m.recall, "f1": m.f1,
                  "tp": m.tp, "fp": m.fp, "fn": m.fn}
            for cat, m in result.per_category.items()
        },
        "package_count": result.package_count,
    }
    (output_dir / "metrics.json").write_text(json.dumps(metrics_data, indent=2), encoding="utf-8")

    # metrics_table.csv — ready for paper Table
    rows = [result.overall.to_row()]
    for cat_result in result.per_category.values():
        rows.append(cat_result.to_row())
    pd.DataFrame(rows).to_csv(output_dir / "metrics_table.csv", index=False)

    # ground_truth.json and predictions.json for reproducibility
    (output_dir / "ground_truth.json").write_text(json.dumps(ground_truth, indent=2), encoding="utf-8")
    (output_dir / "predictions.json").write_text(json.dumps(predictions, indent=2), encoding="utf-8")

    logger.info(
        f"Evaluation results saved to {output_dir}\n"
        f"  Overall: Precision={result.overall.precision:.3f} "
        f"Recall={result.overall.recall:.3f} F1={result.overall.f1:.3f}"
    )


def run_full_evaluation(
    corpus_dir: Path,
    output_dir: Path,
    run_ablation: bool = False,
) -> None:
    """Entry point called by run_pipeline.py evaluate command."""
    output_dir = Path(output_dir)
    result = evaluate_corpus(corpus_dir, output_dir / "main")

    if run_ablation:
        from evaluation.ablation import run_ablation as _ablation
        ablation = _ablation(corpus_dir, output_dir)
        abl_rows = ablation.to_table_row()
        import pandas as pd
        pd.DataFrame(abl_rows).to_csv(output_dir / "ablation_table.csv", index=False)
        (output_dir / "ablation_conclusion.txt").write_text(ablation.conclusion, encoding="utf-8")
        logger.info(f"Ablation study saved: ΔF1 = {ablation.delta_f1:+.3f}")

    logger.info(
        f"\nFINAL RESULTS:\n"
        f"  Precision: {result.overall.precision:.3f}\n"
        f"  Recall:    {result.overall.recall:.3f}\n"
        f"  F1:        {result.overall.f1:.3f}"
    )
