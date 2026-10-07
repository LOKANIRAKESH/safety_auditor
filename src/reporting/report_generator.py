"""Phase 8 — Jinja2 HTML audit report generation."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, List
from jinja2 import Environment, FileSystemLoader, select_autoescape
from loguru import logger
from src.verification.finding_model import AuditFinding, FindingSeverity
from src.ir.rule_model import ControlRule
from src.config import PipelineConfig


@dataclass
class AuditReport:
    input_source: str
    generated_at: datetime
    findings: List[AuditFinding]
    rules: List[ControlRule]
    invariant_summary: List[dict]
    extraction_stats: dict
    is_real_data: bool = False
    report_path: Path = field(default=Path("output/report.html"))

    @property
    def total_findings(self) -> int:
        return len(self.findings)

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == FindingSeverity.HIGH)

    @property
    def medium_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == FindingSeverity.MEDIUM)

    @property
    def low_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == FindingSeverity.LOW)


class ReportGenerator:
    """Generates Jinja2 HTML audit reports from Z3 findings."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        templates_dir = config.report_templates_dir
        self._env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(["html"]),
        )

    def generate(self, report: AuditReport, output_path: Path) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        template = self._env.get_template("audit_report.html.j2")
        html = template.render(
            report=report,
            findings=report.findings,
            rules=report.rules,
            invariant_summary=report.invariant_summary,
            extraction_stats=report.extraction_stats,
            generated_at=report.generated_at.strftime("%Y-%m-%d %H:%M:%S"),
            severity_colors={
                "HIGH": "#ef4444",
                "MEDIUM": "#f59e0b",
                "LOW": "#22c55e",
            },
        )
        output_path.write_text(html, encoding="utf-8")
        logger.info(f"HTML report saved: {output_path}")

        if self.config.report_format == "pdf":
            pdf_path = output_path.with_suffix(".pdf")
            self._export_pdf(html, pdf_path)
            return pdf_path

        return output_path

    @staticmethod
    def _export_pdf(html: str, output_path: Path) -> None:
        try:
            from weasyprint import HTML
            HTML(string=html).write_pdf(str(output_path))
            logger.info(f"PDF report saved: {output_path}")
        except ImportError:
            logger.warning("weasyprint not installed — PDF export skipped.")
        except Exception as e:
            logger.error(f"PDF export failed: {e}")
