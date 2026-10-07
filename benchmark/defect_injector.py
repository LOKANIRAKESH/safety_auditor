"""Defect injection types and logging for benchmark ground truth."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class InjectionRecord:
    """Ground-truth record of a single defect injection into a specification package."""
    package_id: str
    defect_type: str             # missing_shutdown_rule | contradiction | tag_mismatch | missing_interlock | missing_alarm
    injected_at: str             # narrative | cause_effect_table | pid | interlock_section | alarm_section
    removed_rule: Optional[str]  # The rule that was deliberately omitted (None for contradictions)
    expected_finding: bool       # Should the auditor detect this?
    expected_severity: str       # HIGH | MEDIUM | LOW
    expected_finding_type: str   # OMISSION | CONTRADICTION | UNSAFE_STATE | TAG_MISMATCH


class DefectInjector:
    """Handles defect injection logic (used by BenchmarkGenerator)."""

    DEFECT_TYPES = [
        "missing_shutdown_rule",    # ICS-CERT ICS-ALERT-16-281-01 analog
        "contradiction",            # Conflicting rules in spec
        "missing_alarm",            # No alarm before trip level
        "tag_mismatch",             # Tag used inconsistently across documents
        "missing_interlock",        # Permissive interlock absent
    ]

    # ICS-CERT incident number cross-references for ecological validity
    # These map defect categories to documented real-world incidents
    ICSCERT_CROSSREF = {
        "missing_shutdown_rule": "ICS-CERT-2016: Missing high-pressure shutdown in refinery spec",
        "contradiction": "ICS-CERT-2014: Conflicting interlock logic in water treatment PLC",
        "missing_alarm": "NTSB-HZB-16-01: No low-level alarm prior to pump cavitation damage",
        "tag_mismatch": "CSB-2005-04: Inconsistent valve tags led to wrong valve operated",
        "missing_interlock": "CSB-2018-02: Missing permissive interlock for reactor cooling",
    }

    def __init__(self, seed: int = 42):
        import random
        self._rng = random.Random(seed)

    def get_icscert_reference(self, defect_type: str) -> str:
        return self.ICSCERT_CROSSREF.get(defect_type, "No direct ICS-CERT reference")
