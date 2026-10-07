#!/usr/bin/env python3
"""
CLI entry point for the Neuro-Symbolic Safety Auditing Framework.

Usage:
    python run_pipeline.py --input <path-to-spec-dir-or-pdf>
    python run_pipeline.py --input data/schneider_electric/narrative.pdf --real-data
    python run_pipeline.py --input benchmark/corpus/PKG-001/ --output output/PKG-001/
"""
import typer
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from src.pipeline.auditor import SafetyAuditor
from src.config import config

app = typer.Typer(help="Neuro-Symbolic Safety Auditing Framework for ICS Specifications")
console = Console()


@app.command()
def audit(
    input: Path = typer.Option(..., "--input", "-i", help="Path to specification PDF or directory of spec packages"),
    output: Path = typer.Option(None, "--output", "-o", help="Output directory (default: output/<stem>)"),
    model: str = typer.Option(None, "--model", "-m", help="Ollama model override (e.g. qwen2.5, llama3)"),
    real_data: bool = typer.Option(False, "--real-data", help="Flag to mark this as a real-data run (not synthetic)"),
    no_linking: bool = typer.Option(False, "--no-linking", help="Disable cross-modal entity linking (ablation study)"),
    report_format: str = typer.Option("html", "--format", "-f", help="Report format: html or pdf"),
):
    """Run the full safety auditing pipeline on an ICS specification."""
    console.print(Panel.fit(
        "[bold cyan]Neuro-Symbolic Safety Auditing Framework[/bold cyan]\n"
        "Pre-Synthesis Safety Auditing for Industrial Control Specifications",
        border_style="cyan"
    ))

    if not input.exists():
        console.print(f"[red]Error:[/red] Input path does not exist: {input}")
        raise typer.Exit(1)

    if output is None:
        stem = input.stem if input.is_file() else input.name
        output = Path("output") / stem
    output.mkdir(parents=True, exist_ok=True)

    if model:
        config.llm_model = model
    if no_linking:
        config.enable_cross_modal_linking = False
    config.report_format = report_format

    auditor = SafetyAuditor(config)
    result = auditor.run(input_path=input, output_dir=output, is_real_data=real_data)

    console.print(f"\n[green]Audit complete.[/green]")
    console.print(f"  Findings: [bold]{result.total_findings}[/bold] "
                  f"([red]{result.high_count} HIGH[/red] / "
                  f"[yellow]{result.medium_count} MEDIUM[/yellow] / "
                  f"[green]{result.low_count} LOW[/green])")
    console.print(f"  Report:   {result.report_path}")
    console.print(f"  PLC code: {result.plc_output_path}")


@app.command()
def benchmark(
    n: int = typer.Option(50, "--n", help="Number of specification packages to generate"),
    output: Path = typer.Option(Path("benchmark/corpus"), "--output", "-o"),
    seed: int = typer.Option(42, "--seed", help="Random seed for reproducibility"),
):
    """Generate the synthetic benchmark corpus with ground-truth defect injections."""
    from benchmark.generator import BenchmarkGenerator
    console.print(f"Generating [bold]{n}[/bold] synthetic specification packages...")
    gen = BenchmarkGenerator(seed=seed)
    gen.generate(n=n, output_dir=output)
    console.print(f"[green]Done.[/green] Packages saved to: {output}")


@app.command()
def evaluate(
    corpus: Path = typer.Option(Path("benchmark/corpus"), "--corpus"),
    output: Path = typer.Option(Path("evaluation/results"), "--output"),
    ablation: bool = typer.Option(False, "--ablation", help="Run ablation study"),
    baseline: bool = typer.Option(False, "--baseline", help="Run post-generation baseline comparison"),
):
    """Run the full evaluation on the benchmark corpus."""
    from evaluation.run_evaluation import run_full_evaluation
    console.print("[bold]Running evaluation...[/bold]")
    run_full_evaluation(corpus_dir=corpus, output_dir=output, run_ablation=ablation)
    console.print(f"[green]Evaluation complete.[/green] Results: {output}")

    if baseline:
        console.print("[bold]Running post-generation baseline comparison...[/bold]")
        from evaluation.baseline import run_post_generation_baseline
        baseline_result = run_post_generation_baseline(
            corpus_dir=corpus,
            output_dir=output / "main",
        )
        baseline_result.print_summary()


@app.command()
def figures():
    """Generate paper-ready matplotlib figures from evaluation results."""
    import subprocess
    import sys
    console.print("Generating paper figures...")
    subprocess.run([sys.executable, "scripts/generate_figures.py"], check=True)
    console.print("[green]Figures saved to paper/figures/[/green]")


if __name__ == "__main__":
    app()
