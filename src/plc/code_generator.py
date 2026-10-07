"""Phase 9 — IEC 61131-3 Structured Text code generation from verified rules."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List
from jinja2 import Environment, FileSystemLoader, select_autoescape
from loguru import logger
from src.ir.rule_model import ControlRule, RuleAction
from src.config import PipelineConfig


@dataclass
class PLCOutput:
    program_text: str
    function_blocks: List[str]
    equipment_count: int
    rule_count: int
    output_path: Path = field(default=Path("output/plc_output.st"))


class PLCCodeGenerator:
    """
    Generates IEC 61131-3 Structured Text from verified ControlRule IR.
    Only rules with confidence >= threshold and no HIGH findings are used.
    Targets OpenPLC runtime format.
    """

    def __init__(self, config: PipelineConfig):
        self.config = config
        self._env = Environment(
            loader=FileSystemLoader(str(config.plc_templates_dir)),
            autoescape=False,
        )

    def generate(
        self,
        rules: List[ControlRule],
        output_path: Path,
        program_name: str = "SAFETY_AUDIT_PROGRAM",
    ) -> PLCOutput:
        # Only use rules with sufficient confidence
        verified_rules = [
            r for r in rules
            if not r.needs_review and r.confidence >= self.config.extraction_confidence_threshold
        ]

        # Group by equipment
        equipment_rules: Dict[str, List[ControlRule]] = {}
        for rule in verified_rules:
            equipment_rules.setdefault(rule.equipment_id, []).append(rule)

        template = self._env.get_template("structured_text.j2")
        st_code = template.render(
            program_name=program_name,
            equipment_rules=equipment_rules,
            RuleAction=RuleAction,
        )

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(st_code, encoding="utf-8")
        logger.info(f"PLC Structured Text generated: {output_path} ({len(verified_rules)} rules)")

        return PLCOutput(
            program_text=st_code,
            function_blocks=list(equipment_rules.keys()),
            equipment_count=len(equipment_rules),
            rule_count=len(verified_rules),
            output_path=output_path,
        )
