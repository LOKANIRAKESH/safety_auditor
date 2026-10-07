"""
Generate paper-ready figures from evaluation results.

Usage (after running the full evaluation):
    python scripts/generate_figures.py

Reads:   evaluation/results/main/metrics.json
         evaluation/results/ablation_table.csv (if it exists)
         evaluation/results/main/baseline_results.json (if it exists)

Outputs: paper/figures/fig_results_bar.pdf
         paper/figures/fig_per_category.pdf
         paper/figures/fig_ablation.pdf
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running from project root: python scripts/generate_figures.py
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

RESULTS_DIR = ROOT / "evaluation" / "results" / "main"
FIGURES_DIR = ROOT / "paper" / "figures"


def _require_matplotlib() -> None:
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        print("matplotlib is required: pip install matplotlib")
        sys.exit(1)


def fig_results_comparison() -> None:
    """Bar chart: Our Approach vs. Post-Gen Baseline (P, R, F1)."""
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import numpy as np

    metrics_path = RESULTS_DIR / "metrics.json"
    if not metrics_path.exists():
        print(f"[skip] {metrics_path} not found — run the evaluation first")
        return

    with metrics_path.open() as f:
        our_metrics = json.load(f)["overall"]

    baseline_path = RESULTS_DIR / "baseline_results.json"
    if baseline_path.exists():
        with baseline_path.open() as f:
            base_metrics = json.load(f)
    else:
        # Placeholder baseline numbers — replace once baseline is run
        base_metrics = {"precision": 0.0, "recall": 0.0, "f1": 0.0}
        print("[warn] baseline_results.json not found — using zeros as placeholder")

    metrics = ["Precision", "Recall", "F1"]
    ours = [our_metrics["precision"], our_metrics["recall"], our_metrics["f1"]]
    base = [base_metrics["precision"], base_metrics["recall"], base_metrics["f1"]]

    x = np.arange(len(metrics))
    width = 0.32

    fig, ax = plt.subplots(figsize=(5, 3.5))
    bars_ours = ax.bar(x - width / 2, ours, width, label="Our Approach", color="#2563eb")
    bars_base = ax.bar(x + width / 2, base, width, label="Post-Gen Baseline", color="#dc2626")

    ax.set_ylabel("Score")
    ax.set_title("Detection Performance: Pre-Synthesis vs. Post-Generation")
    ax.set_xticks(x)
    ax.set_xticklabels(metrics)
    ax.set_ylim(0, 1.1)
    ax.legend(loc="lower right")
    ax.bar_label(bars_ours, fmt="%.2f", padding=2, fontsize=8)
    ax.bar_label(bars_base, fmt="%.2f", padding=2, fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    out = FIGURES_DIR / "fig_results_bar.pdf"
    fig.savefig(out, bbox_inches="tight", dpi=150)
    print(f"Saved {out}")
    plt.close()


def fig_per_category() -> None:
    """Horizontal bar chart: F1 score per defect category."""
    import matplotlib.pyplot as plt
    import numpy as np

    metrics_path = RESULTS_DIR / "metrics.json"
    if not metrics_path.exists():
        print(f"[skip] {metrics_path} not found")
        return

    with metrics_path.open() as f:
        data = json.load(f)

    per_cat = data.get("per_category", {})
    if not per_cat:
        print("[skip] no per_category data in metrics.json")
        return

    LABEL_MAP = {
        "OMISSION": "Missing Rule (Omission)",
        "CONTRADICTION": "Contradiction",
        "UNSAFE_STATE": "Unsafe State",
        "TAG_MISMATCH": "Tag Mismatch",
        "INCONSISTENCY": "Inconsistency",
    }

    categories = list(per_cat.keys())
    labels = [LABEL_MAP.get(c, c) for c in categories]
    f1_scores = [per_cat[c]["f1"] for c in categories]

    # Sort by F1 descending
    sorted_pairs = sorted(zip(labels, f1_scores), key=lambda x: x[1], reverse=True)
    labels, f1_scores = zip(*sorted_pairs) if sorted_pairs else ([], [])

    fig, ax = plt.subplots(figsize=(5.5, 3))
    colors = ["#2563eb" if s >= 0.7 else "#f59e0b" if s >= 0.5 else "#dc2626"
              for s in f1_scores]
    bars = ax.barh(range(len(labels)), f1_scores, color=colors)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("F1 Score")
    ax.set_title("Per-Category Detection F1")
    ax.set_xlim(0, 1.1)
    ax.bar_label(bars, fmt="%.2f", padding=3, fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    out = FIGURES_DIR / "fig_per_category.pdf"
    fig.savefig(out, bbox_inches="tight", dpi=150)
    print(f"Saved {out}")
    plt.close()


def fig_ablation() -> None:
    """Bar chart: F1 with vs. without cross-modal linking (ablation study)."""
    import matplotlib.pyplot as plt
    import numpy as np

    abl_path = ROOT / "evaluation" / "results" / "ablation_table.csv"
    if not abl_path.exists():
        print(f"[skip] {abl_path} not found — run evaluation with --ablation flag")
        return

    import csv
    rows = []
    with abl_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if len(rows) < 2:
        print("[skip] ablation_table.csv has fewer than 2 rows")
        return

    labels = [r["Configuration"] for r in rows]
    f1_vals = [float(r["F1"]) for r in rows]

    fig, ax = plt.subplots(figsize=(4.5, 3))
    colors = ["#2563eb", "#6b7280"]
    bars = ax.bar(labels, f1_vals, color=colors, width=0.45)
    ax.set_ylabel("F1 Score")
    ax.set_title("Ablation Study: Cross-Modal Linking (H2)")
    ax.set_ylim(0, 1.1)
    ax.bar_label(bars, fmt="%.3f", padding=2, fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    delta = f1_vals[0] - f1_vals[1] if len(f1_vals) >= 2 else 0
    ax.annotate(
        f"ΔF1 = {delta:+.3f}",
        xy=(0.98, 0.05), xycoords="axes fraction",
        ha="right", fontsize=9,
        color="#16a34a" if delta > 0 else "#dc2626",
    )

    fig.tight_layout()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    out = FIGURES_DIR / "fig_ablation.pdf"
    fig.savefig(out, bbox_inches="tight", dpi=150)
    print(f"Saved {out}")
    plt.close()


def main() -> None:
    _require_matplotlib()
    print("Generating paper figures...")
    print(f"  Reading from: {RESULTS_DIR}")
    print(f"  Writing to:   {FIGURES_DIR}")
    fig_results_comparison()
    fig_per_category()
    fig_ablation()
    print("\nDone. Include figures in paper/main.tex:")
    print("  \\includegraphics[width=\\columnwidth]{figures/fig_results_bar}")
    print("  \\includegraphics[width=\\columnwidth]{figures/fig_per_category}")
    print("  \\includegraphics[width=\\columnwidth]{figures/fig_ablation}")


if __name__ == "__main__":
    main()
