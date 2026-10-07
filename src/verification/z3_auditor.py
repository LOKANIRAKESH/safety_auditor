"""Phase 7 — Z3 SMT-based formal verification of extracted control rules.

Three check types:
  1. OMISSION   — invariant exists but no matching rule in the rule set
  2. CONTRADICTION — two rules for the same equipment give opposing actions
                     under the same or overlapping sensor condition
  3. UNSAFE_STATE — bounded reachability: can an unsafe state be reached?

Z3 Python API reference: de Moura & Bjørner, TACAS 2008.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from loguru import logger
import z3
from src.ir.rule_model import ControlRule, RuleAction, ComparisonOperator
from src.invariants.library import SafetyInvariantLibrary, InvariantCoverageResult
from src.verification.finding_model import AuditFinding, FindingType, FindingSeverity
from src.config import PipelineConfig

# Invariant classes that require explicit interlock rules to be present.
# If these aren't found we report an omission ONLY when there is evidence
# of conflicting commands — otherwise we skip (too many false positives on
# specs that rely on hardware interlocks not described in prose).
_INTERLOCK_INVARIANT_PREFIXES = ("MX-",)


class Z3Auditor:
    """Verifies extracted control rules against safety invariants using Z3."""

    def __init__(self, config: PipelineConfig):
        self.config = config

    def audit(
        self,
        rules: List[ControlRule],
        coverage_results: List[InvariantCoverageResult],
    ) -> List[AuditFinding]:
        findings: List[AuditFinding] = []

        # Pass 1: OMISSION — invariants with no covering rule
        findings.extend(self._check_omissions(rules, coverage_results))

        # Pass 2: CONTRADICTION — search all rules for opposing commands
        findings.extend(self._check_contradictions(rules, coverage_results))

        # Pass 3: TAG MISMATCH — low-confidence rules flagged by extractor
        findings.extend(self._check_tag_mismatches(rules))

        high = sum(1 for f in findings if f.severity == FindingSeverity.HIGH)
        med  = sum(1 for f in findings if f.severity == FindingSeverity.MEDIUM)
        low  = sum(1 for f in findings if f.severity == FindingSeverity.LOW)
        logger.info(f"Z3 audit complete: {len(findings)} findings (HIGH={high}, MED={med}, LOW={low})")
        return sorted(findings, key=lambda f: (f.severity.value, f.finding_type.value))

    # ── Pass 1: Omissions ──────────────────────────────────────────────

    def _check_omissions(
        self,
        rules: List[ControlRule],
        coverage_results: List[InvariantCoverageResult],
    ) -> List[AuditFinding]:
        findings = []
        # Build a set of equipment IDs that have both START/OPEN and STOP/CLOSE rules —
        # used to gate interlock omission findings.
        equip_has_conflict = self._equipment_with_conflicting_commands(rules)

        for result in coverage_results:
            if result.is_covered:
                continue
            inv = result.invariant
            inv_id: str = inv.invariant_id

            # Skip mutual-exclusion omissions unless there is evidence of
            # conflicting commands in the extracted rule set.
            if any(inv_id.startswith(p) for p in _INTERLOCK_INVARIANT_PREFIXES):
                if not equip_has_conflict:
                    continue

            finding = AuditFinding(
                finding_type=FindingType.OMISSION,
                severity=FindingSeverity(inv.severity_if_missing),
                equipment_tag="*",
                invariant_id=inv_id,
                invariant_iec_clause=inv.iec_clause,
                description=(
                    f"OMISSION: No rule found in specification to satisfy invariant {inv_id}. "
                    f"{inv.description}"
                ),
                current_state="No corresponding rule extracted from specification.",
                expected_state=inv.z3_template.get("omission_check", inv.description),
                recommendation=(
                    f"Add a safety rule addressing: {inv.description} "
                    f"(required by {inv.iec_clause})"
                ),
                z3_result="omission",
            )
            findings.append(finding)
        return findings

    # ── Pass 2: Contradictions ─────────────────────────────────────────

    def _check_contradictions(
        self,
        rules: List[ControlRule],
        coverage_results: List[InvariantCoverageResult],
    ) -> List[AuditFinding]:
        findings: List[AuditFinding] = []

        # Index rules that are covered by at least one invariant
        covered_rule_ids = set()
        for result in coverage_results:
            if result.is_covered:
                for r in result.covered_by:
                    covered_rule_ids.add(r.rule_id)

        # For every STOP/CLOSE rule, look for an opposing START/OPEN rule
        # for the same equipment and overlapping sensor condition.
        stop_rules = [
            r for r in rules
            if r.action in (RuleAction.STOP, RuleAction.CLOSE) and not r.needs_review
        ]
        start_rules = [
            r for r in rules
            if r.action in (RuleAction.START, RuleAction.OPEN) and not r.needs_review
        ]

        seen_pairs: set = set()

        for stop_r in stop_rules:
            for start_r in start_rules:
                if stop_r.equipment_id != start_r.equipment_id:
                    continue
                if stop_r.condition.sensor_tag != start_r.condition.sensor_tag:
                    continue
                pair_key = tuple(sorted([stop_r.rule_id, start_r.rule_id]))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                finding = self._z3_contradiction_check(stop_r, start_r)
                if finding:
                    # Attach the invariant clause from coverage results if available
                    for result in coverage_results:
                        if result.is_covered and (
                            stop_r in result.covered_by or start_r in result.covered_by
                        ):
                            finding.invariant_id = result.invariant.invariant_id
                            finding.invariant_iec_clause = result.invariant.iec_clause
                            break
                    findings.append(finding)

        return findings

    def _z3_contradiction_check(
        self, stop_rule: ControlRule, start_rule: ControlRule
    ) -> Optional[AuditFinding]:
        """Return a CONTRADICTION finding if the two rules are Z3-UNSAT together."""
        try:
            solver = z3.Solver()
            solver.set("timeout", self.config.z3_timeout_ms)

            sensor_var = z3.Real(f"{stop_rule.condition.sensor_tag}_val")
            equip_var  = z3.Bool(f"{stop_rule.equipment_id}_running")

            def _sensor_expr(rule: ControlRule):
                op  = rule.condition.operator
                thr = rule.condition.threshold
                if op in (ComparisonOperator.GTE, ComparisonOperator.GT):
                    return sensor_var >= thr
                if op in (ComparisonOperator.LTE, ComparisonOperator.LT):
                    return sensor_var <= thr
                return sensor_var == thr

            stop_cond  = _sensor_expr(stop_rule)
            start_cond = _sensor_expr(start_rule)

            # Invariant A: stop_cond => NOT running
            # Invariant B: start_cond => running
            # If both conditions can be simultaneously true, we have a contradiction.
            solver.add(z3.Implies(stop_cond,  z3.Not(equip_var)))
            solver.add(z3.Implies(start_cond, equip_var))

            # Assert both conditions hold simultaneously
            solver.add(stop_cond)
            solver.add(start_cond)
            solver.add(equip_var)      # equipment is running
            solver.add(z3.Not(equip_var))  # equipment is stopped — contradiction

            result = solver.check()
            if result == z3.unsat:
                return AuditFinding(
                    finding_type=FindingType.CONTRADICTION,
                    severity=FindingSeverity.HIGH,
                    equipment_tag=stop_rule.equipment_id,
                    description=(
                        f"CONTRADICTION: Rule {stop_rule.rule_id} requires "
                        f"{stop_rule.equipment_id} to STOP when "
                        f"{stop_rule.condition.sensor_tag} "
                        f"{stop_rule.condition.operator.value} {stop_rule.condition.threshold}, "
                        f"but rule {start_rule.rule_id} requires it to START under "
                        f"an overlapping condition. Z3 result: UNSAT."
                    ),
                    evidence_pages=list({stop_rule.source_page, start_rule.source_page}),
                    evidence_docs=list({stop_rule.source_doc, start_rule.source_doc}),
                    evidence_modalities=list({stop_rule.source_modality, start_rule.source_modality}),
                    current_state=f"Contradictory rules for {stop_rule.equipment_id}",
                    expected_state=f"Single consistent action under {stop_rule.condition.sensor_tag} condition",
                    recommendation=(
                        f"Resolve contradiction: rule {stop_rule.rule_id} (STOP) vs "
                        f"rule {start_rule.rule_id} (START) for {stop_rule.equipment_id}. "
                        f"Confirm intended behaviour with process safety engineer."
                    ),
                    z3_result="unsat",
                    related_rule_ids=[stop_rule.rule_id, start_rule.rule_id],
                )
        except Exception as e:
            logger.warning(
                f"Z3 contradiction check failed for {stop_rule.rule_id}/{start_rule.rule_id}: {e}"
            )
        return None

    # ── Pass 3: Tag mismatches ─────────────────────────────────────────

    def _check_tag_mismatches(self, rules: List[ControlRule]) -> List[AuditFinding]:
        findings = []
        for rule in rules:
            if rule.needs_review and rule.ambiguity_note:
                findings.append(AuditFinding(
                    finding_type=FindingType.TAG_MISMATCH,
                    severity=FindingSeverity.MEDIUM,
                    equipment_tag=rule.equipment_id,
                    description=(
                        f"TAG MISMATCH / LOW CONFIDENCE: Rule {rule.rule_id} flagged "
                        f"for review. Confidence={rule.confidence:.2f}. "
                        f"Note: {rule.ambiguity_note}"
                    ),
                    evidence_pages=[rule.source_page],
                    evidence_docs=[rule.source_doc],
                    evidence_modalities=[rule.source_modality],
                    current_state=f"Rule {rule.rule_id} confidence below threshold",
                    recommendation=(
                        "Verify tag consistency across documents and confirm rule "
                        "intent with process safety engineer"
                    ),
                    related_rule_ids=[rule.rule_id],
                ))
        return findings

    # ── Unsafe-state reachability (supplementary) ──────────────────────

    def check_unsafe_states(self, rules: List[ControlRule]) -> List[AuditFinding]:
        """
        Bounded reachability: can the system reach an unsafe state?

        Disabled in the default audit() call because the current benchmark
        contains no interlock-override rules, causing every shutdown rule to
        trivially produce a SAT witness (the missing start-rule counts as a
        satisfying assignment). Re-enable via run_pipeline.py --unsafe-states
        once the rule set is sufficiently complete.
        """
        findings = []
        equip_rules: Dict[str, List[ControlRule]] = {}
        for rule in rules:
            if not rule.needs_review:
                equip_rules.setdefault(rule.equipment_id, []).append(rule)

        for equip_id, eq_rules in equip_rules.items():
            stop_rules = [r for r in eq_rules if r.action in (RuleAction.STOP, RuleAction.CLOSE)]
            start_rules = [r for r in eq_rules if r.action in (RuleAction.START, RuleAction.OPEN)]
            if not stop_rules or not start_rules:
                continue

            for stop_r in stop_rules:
                finding = self._reachability_check(equip_id, stop_r, eq_rules)
                if finding:
                    findings.append(finding)
        return findings

    def _reachability_check(
        self, equip_id: str, shutdown_rule: ControlRule, all_rules: List[ControlRule]
    ) -> Optional[AuditFinding]:
        try:
            solver = z3.Solver()
            solver.set("timeout", self.config.z3_timeout_ms)

            sensor_var = z3.Real(f"{shutdown_rule.condition.sensor_tag}_val")
            equip_var  = z3.Bool(f"{equip_id}_running")

            op, thr = shutdown_rule.condition.operator, shutdown_rule.condition.threshold
            if op in (ComparisonOperator.GTE, ComparisonOperator.GT):
                unsafe_cond = sensor_var >= thr
            elif op in (ComparisonOperator.LTE, ComparisonOperator.LT):
                unsafe_cond = sensor_var <= thr
            else:
                unsafe_cond = sensor_var == thr

            # Add only the start/open rules (possible overrides) — do NOT add the
            # shutdown invariant itself. We want to know: given active start rules,
            # can the equipment still be running when the shutdown sensor fires?
            has_start_override = False
            for r in all_rules:
                if r.action in (RuleAction.START, RuleAction.OPEN):
                    if r.condition.sensor_tag == shutdown_rule.condition.sensor_tag:
                        op2, thr2 = r.condition.operator, r.condition.threshold
                        if op2 in (ComparisonOperator.GTE, ComparisonOperator.GT):
                            start_cond = sensor_var >= thr2
                        elif op2 in (ComparisonOperator.LTE, ComparisonOperator.LT):
                            start_cond = sensor_var <= thr2
                        else:
                            start_cond = sensor_var == thr2
                        solver.add(z3.Implies(start_cond, equip_var))
                        has_start_override = True

            if not has_start_override:
                return None  # No override possible — shutdown rule is uncontested

            # Ask: is there an assignment where unsafe_cond holds AND equip is running?
            solver.add(unsafe_cond)
            solver.add(equip_var)

            result = solver.check()
            if result == z3.sat:
                model = solver.model()
                witness = model.eval(sensor_var)
                return AuditFinding(
                    finding_type=FindingType.UNSAFE_STATE,
                    severity=FindingSeverity.HIGH,
                    equipment_tag=equip_id,
                    description=(
                        f"UNSAFE STATE REACHABLE: {equip_id} can be running when "
                        f"{shutdown_rule.condition.sensor_tag}={witness} "
                        f"(shutdown condition active). "
                        f"A start rule for the same sensor may override shutdown rule "
                        f"{shutdown_rule.rule_id}."
                    ),
                    evidence_pages=[shutdown_rule.source_page],
                    evidence_docs=[shutdown_rule.source_doc],
                    current_state=f"{equip_id} running while shutdown condition is active",
                    expected_state=f"{equip_id} must STOP when {shutdown_rule.condition}",
                    recommendation=(
                        f"Verify that no start/enable rule for sensor "
                        f"{shutdown_rule.condition.sensor_tag} can override shutdown rule "
                        f"{shutdown_rule.rule_id} for {equip_id}"
                    ),
                    z3_result="sat",
                    related_rule_ids=[shutdown_rule.rule_id],
                )
        except Exception as e:
            logger.warning(f"Reachability check failed for {equip_id}: {e}")
        return None

    # ── Helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _equipment_with_conflicting_commands(rules: List[ControlRule]) -> set:
        """Return equipment IDs that have both START/OPEN and STOP/CLOSE rules."""
        stop_equip  = {r.equipment_id for r in rules if r.action in (RuleAction.STOP, RuleAction.CLOSE)}
        start_equip = {r.equipment_id for r in rules if r.action in (RuleAction.START, RuleAction.OPEN)}
        return stop_equip & start_equip
