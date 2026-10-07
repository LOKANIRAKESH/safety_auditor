"""Generates synthetic ICS specification packages with ground-truth defect injections.

Each package represents one industrial subsystem and contains:
  - control_narrative.pdf  (prose description of control logic)
  - cause_effect_table.pdf  (tabular C&E data)
  - pid_tags.txt            (list of equipment tags, simulating P&ID OCR output)
  - injections.json         (ground-truth defect injection log)

The benchmark is designed so that:
  - 80% of packages have at least one injected defect (positive class)
  - 20% are defect-free (negative class, for precision measurement)
  - Defect categories map to real ICS failure modes (ICS-CERT incident taxonomy)
"""
from __future__ import annotations
import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from loguru import logger
from benchmark.defect_injector import DefectInjector, InjectionRecord

# ICS subsystem templates
SUBSYSTEMS = [
    {"name": "pump_pressure_loop", "equip": ["P-{n:03d}", "PT-{n:03d}", "PV-{n:03d}"], "fluid": "hydrocarbon"},
    {"name": "vessel_level_control", "equip": ["TK-{n:03d}", "LT-{n:03d}", "LV-{n:03d}", "P-{n:03d}"], "fluid": "process water"},
    {"name": "compressor_interlock", "equip": ["K-{n:03d}", "PT-{n:03d}", "TT-{n:03d}", "XV-{n:03d}"], "fluid": "natural gas"},
    {"name": "heat_exchanger_control", "equip": ["E-{n:03d}", "TT-{n:03d}", "TV-{n:03d}", "FT-{n:03d}"], "fluid": "steam"},
    {"name": "esd_shutdown_group", "equip": ["ESD-{n:03d}", "P-{n:03d}", "XV-{n:03d}", "PT-{n:03d}"], "fluid": "crude oil"},
]

NARRATIVE_TEMPLATES = [
    """{subsystem_name} Control Narrative

1. INTRODUCTION
This document describes the control philosophy for the {subsystem_name} subsystem.

2. EQUIPMENT DESCRIPTION
{equip_desc}

3. NORMAL OPERATION
Under normal operating conditions, {primary_equip} operates continuously.
The {sensor_tag} monitors {parameter} on the {primary_equip} discharge.
{normal_op_detail}

4. ALARM AND TRIP CONDITIONS
{alarm_section}

5. INTERLOCK DESCRIPTION
{interlock_section}

6. EMERGENCY SHUTDOWN
{esd_section}
""",
]

ALARM_TEMPLATES_FULL = """
4.1 High {parameter} Alarm ({sensor_tag} >= {high_alarm} {unit})
When {sensor_tag} reaches {high_alarm} {unit}, a HIGH alarm is raised on the DCS.
The operator should investigate the cause and take corrective action.

4.2 High-High {parameter} Trip ({sensor_tag} >= {high_high} {unit})
When {sensor_tag} reaches {high_high} {unit}, {primary_equip} shall be stopped immediately
via interlock I-{n:03d}.

4.3 Low-Low {parameter} Trip ({sensor_tag} <= {low_low} {unit})
When {sensor_tag} drops to {low_low} {unit} or below, {primary_equip} shall stop
to prevent mechanical damage.
"""

ALARM_TEMPLATES_MISSING_SHUTDOWN = """
4.1 High {parameter} Alarm ({sensor_tag} >= {high_alarm} {unit})
When {sensor_tag} reaches {high_alarm} {unit}, an alarm is raised. The operator should monitor
{primary_equip} operating conditions carefully.

4.2 High {parameter} Alarm ({sensor_tag} >= {high_high} {unit})
When {sensor_tag} exceeds {high_high} {unit}, the operator should consider taking action.
"""

ALARM_TEMPLATES_CONTRADICTION = """
4.1 High {parameter} Trip ({sensor_tag} >= {high_high} {unit})
{primary_equip} shall be stopped when {sensor_tag} >= {high_high} {unit}.

4.2 Override Note
{primary_equip} shall continue running during high {parameter} conditions to maintain production.
"""


class BenchmarkGenerator:
    """Generates N synthetic ICS specification packages."""

    def __init__(self, seed: int = 42):
        random.seed(seed)
        self.injector = DefectInjector(seed=seed)

    def generate(self, n: int, output_dir: Path) -> List[Path]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        packages: List[Path] = []

        n_clean = max(1, n // 5)  # 20% clean
        n_defective = n - n_clean

        for i in range(1, n + 1):
            pkg_dir = output_dir / f"PKG-{i:03d}"
            pkg_dir.mkdir(exist_ok=True)
            is_clean = i > n_defective
            packages.append(self._generate_package(i, pkg_dir, inject_defect=not is_clean))
            logger.info(f"Generated PKG-{i:03d} ({'clean' if is_clean else 'defective'})")

        logger.info(f"Benchmark: {n} packages ({n_defective} defective, {n_clean} clean) in {output_dir}")
        return packages

    def _generate_package(self, n: int, pkg_dir: Path, inject_defect: bool) -> Path:
        subsystem = random.choice(SUBSYSTEMS)
        equip_tags = [tag.format(n=n) for tag in subsystem["equip"]]
        primary_equip = equip_tags[0]
        sensor_tag = equip_tags[1] if len(equip_tags) > 1 else f"PT-{n:03d}"

        params = {
            "subsystem_name": subsystem["name"].replace("_", " ").title(),
            "primary_equip": primary_equip,
            "sensor_tag": sensor_tag,
            "parameter": self._param_for_sensor(sensor_tag),
            "unit": self._unit_for_sensor(sensor_tag),
            "high_alarm": 45 + random.randint(0, 10),
            "high_high": 55 + random.randint(0, 10),
            "low_low": 5 + random.randint(0, 5),
            "n": n,
            "fluid": subsystem["fluid"],
            "equip_desc": self._equip_desc(equip_tags),
            "normal_op_detail": f"{primary_equip} runs at nominal flow controlled by {equip_tags[-1] if len(equip_tags) > 2 else 'PIC-001'}.",
            "interlock_section": f"Interlock I-{n:03d} monitors {sensor_tag} and trips {primary_equip} on high-high condition.",
            "esd_section": f"ESD-{n:03d} activates on loss of utilities or operator demand, stopping all equipment.",
        }

        # Choose alarm section (possibly with injected defect)
        injections: List[InjectionRecord] = []
        if inject_defect:
            defect_type = random.choice(["missing_shutdown_rule", "contradiction", "missing_alarm"])
            if defect_type == "missing_shutdown_rule":
                params["alarm_section"] = ALARM_TEMPLATES_MISSING_SHUTDOWN.format(**params)
                injections.append(InjectionRecord(
                    package_id=pkg_dir.name,
                    defect_type="missing_shutdown_rule",
                    injected_at="alarm_section",
                    removed_rule=f"{sensor_tag} >= {params['high_high']} -> {primary_equip} STOP",
                    expected_finding=True,
                    expected_severity="HIGH",
                    expected_finding_type="OMISSION",
                ))
            elif defect_type == "contradiction":
                params["alarm_section"] = ALARM_TEMPLATES_CONTRADICTION.format(**params)
                injections.append(InjectionRecord(
                    package_id=pkg_dir.name,
                    defect_type="contradiction",
                    injected_at="alarm_section",
                    removed_rule=None,
                    expected_finding=True,
                    expected_severity="HIGH",
                    expected_finding_type="CONTRADICTION",
                ))
            else:
                params["alarm_section"] = ALARM_TEMPLATES_MISSING_SHUTDOWN.format(**params)
                injections.append(InjectionRecord(
                    package_id=pkg_dir.name,
                    defect_type="missing_alarm",
                    injected_at="alarm_section",
                    removed_rule=f"{sensor_tag} >= {params['high_alarm']} -> ALARM",
                    expected_finding=True,
                    expected_severity="MEDIUM",
                    expected_finding_type="OMISSION",
                ))
        else:
            params["alarm_section"] = ALARM_TEMPLATES_FULL.format(**params)

        # Write narrative as text (will be wrapped in simple PDF)
        narrative_text = NARRATIVE_TEMPLATES[0].format(**params)
        narrative_txt = pkg_dir / "control_narrative.txt"
        narrative_txt.write_text(narrative_text, encoding="utf-8")

        # Write a simple PDF (text-based using fpdf2)
        self._write_text_pdf(narrative_text, pkg_dir / "control_narrative.pdf", title=f"PKG-{n:03d} Control Narrative")

        # Write C&E table as PDF
        self._write_ce_table_pdf(params, pkg_dir / "cause_effect_table.pdf")

        # Write P&ID tag list
        (pkg_dir / "pid_tags.txt").write_text("\n".join(equip_tags), encoding="utf-8")

        # Write injection log
        injection_data = [
            {
                "package_id": inj.package_id,
                "defect_type": inj.defect_type,
                "injected_at": inj.injected_at,
                "removed_rule": inj.removed_rule,
                "expected_finding": inj.expected_finding,
                "expected_severity": inj.expected_severity,
                "expected_finding_type": inj.expected_finding_type,
            }
            for inj in injections
        ]
        (pkg_dir / "injections.json").write_text(
            json.dumps(injection_data, indent=2), encoding="utf-8"
        )

        return pkg_dir

    @staticmethod
    def _ascii_safe(text: str) -> str:
        """Replace common non-ASCII characters with ASCII equivalents for fpdf2 Helvetica."""
        for u, a in [("—", "-"), ("–", "-"), ("‘", "'"), ("’", "'"),
                     ("“", '"'), ("”", '"'), ("°", " deg"),
                     ("≥", ">="), ("≤", "<="), ("±", "+/-")]:
            text = text.replace(u, a)
        return text.encode("ascii", errors="replace").decode("ascii")

    @classmethod
    def _write_text_pdf(cls, text: str, output_path: Path, title: str = "Document") -> None:
        try:
            from fpdf import FPDF, XPos, YPos
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 14)
            pdf.cell(0, 10, cls._ascii_safe(title), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", size=10)
            for line in cls._ascii_safe(text).split("\n"):
                if not line.strip():
                    pdf.ln(4)
                else:
                    pdf.multi_cell(0, 5, line[:200], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.output(str(output_path))
        except Exception as e:
            logger.warning(f"PDF write failed: {e} — writing .txt fallback")
            output_path.with_suffix(".txt").write_text(text, encoding="utf-8")

    @classmethod
    def _write_ce_table_pdf(cls, params: dict, output_path: Path) -> None:
        try:
            from fpdf import FPDF, XPos, YPos
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 12)
            title = cls._ascii_safe(f"Cause and Effect Table - {params['subsystem_name']}")
            pdf.cell(0, 10, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", "B", 9)
            headers = ["Tag", "Cause", "Condition", "Effect", "Action"]
            widths = [25, 40, 40, 30, 40]
            for h, w in zip(headers, widths):
                pdf.cell(w, 8, h, border=1)
            pdf.ln()
            pdf.set_font("Helvetica", size=9)
            rows = [
                [params["sensor_tag"], f"High {params['parameter']}", f">= {params['high_alarm']} {params['unit']}", "ALARM", "DCS alarm"],
                [params["sensor_tag"], f"High-High {params['parameter']}", f">= {params['high_high']} {params['unit']}", "TRIP", f"{params['primary_equip']} STOP"],
                [params["sensor_tag"], f"Low-Low {params['parameter']}", f"<= {params['low_low']} {params['unit']}", "TRIP", f"{params['primary_equip']} STOP"],
            ]
            for row in rows:
                for val, w in zip(row, widths):
                    pdf.cell(w, 7, cls._ascii_safe(str(val))[:20], border=1)
                pdf.ln()
            pdf.output(str(output_path))
        except Exception as e:
            logger.warning(f"C&E table PDF failed: {e}")

    @staticmethod
    def _param_for_sensor(tag: str) -> str:
        if tag.startswith("PT"):
            return "pressure"
        if tag.startswith("TT"):
            return "temperature"
        if tag.startswith("LT"):
            return "level"
        if tag.startswith("FT"):
            return "flow"
        return "process variable"

    @staticmethod
    def _unit_for_sensor(tag: str) -> str:
        if tag.startswith("PT"):
            return "bar"
        if tag.startswith("TT"):
            return "degC"
        if tag.startswith("LT"):
            return "%"
        if tag.startswith("FT"):
            return "m3/h"
        return "units"

    @staticmethod
    def _equip_desc(equip_tags: List[str]) -> str:
        return "\n".join(f"  - {tag}: ICS equipment tag" for tag in equip_tags)


if __name__ == "__main__":
    import typer
    def main(n: int = 50, output: Path = Path("benchmark/corpus"), seed: int = 42):
        gen = BenchmarkGenerator(seed=seed)
        gen.generate(n=n, output_dir=output)
    typer.run(main)
