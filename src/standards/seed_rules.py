"""
Seed rules — 20 critical safety requirements hand-coded from publicly available
standards (OSHA 29 CFR 1910.119 and IEC 61511 clause summaries).

These are inserted into the knowledge base immediately (no LLM, no download)
so the verifier has working rules from day one.  The full LLM extraction
(run_standards_update.py extract) adds hundreds more rules but takes hours on CPU.

Sources:
  - OSHA 29 CFR 1910.119 (PSM standard — US public domain)
  - IEC 61511-1:2016 clause summaries (paraphrased — no copyrighted text)
"""
from __future__ import annotations
from src.standards.rule_extractor import SafetyRule

SEED_RULES: list[SafetyRule] = [

    # ── OSHA PSM 1910.119 — Mechanical Integrity ──────────────────────────────
    SafetyRule(
        rule_id="OSHA_PSM-SEED-001",
        source_id="OSHA_PSM_1910_119",
        standard_ref="OSHA 29 CFR 1910.119",
        clause_ref="1910.119(d)(3)(i)",
        requirement_text=(
            "Process safety information must include relief system design and design basis "
            "for all process equipment operating above atmospheric pressure."
        ),
        requirement_type="documentation",
        equipment_classes=["PressureVessel", "Reactor", "Separator", "Column"],
        sensor_classes=["PressureTransmitter"],
        condition_type="ANY",
        action_required="DOCUMENT",
        severity_if_missing="HIGH",
        setpoint_role="NONE",
        iec_equivalent="IEC 61511 Cl.10.3.2",
        confidence=1.0,
    ),
    SafetyRule(
        rule_id="OSHA_PSM-SEED-002",
        source_id="OSHA_PSM_1910_119",
        standard_ref="OSHA 29 CFR 1910.119",
        clause_ref="1910.119(j)(4)(ii)",
        requirement_text=(
            "Written procedures must be established and implemented for maintaining the "
            "mechanical integrity of safety relief devices."
        ),
        requirement_type="documentation",
        equipment_classes=["ReliefValve", "SafetyValve", "RuptureDisc"],
        sensor_classes=["PressureTransmitter"],
        condition_type="ANY",
        action_required="DOCUMENT",
        severity_if_missing="HIGH",
        setpoint_role="NONE",
        iec_equivalent="IEC 61511 Cl.16",
        confidence=1.0,
    ),
    SafetyRule(
        rule_id="OSHA_PSM-SEED-003",
        source_id="OSHA_PSM_1910_119",
        standard_ref="OSHA 29 CFR 1910.119",
        clause_ref="1910.119(j)(3)",
        requirement_text=(
            "Each employer must ensure that each employee involved in operating a process "
            "has been trained in an overview of the process and in the operating procedures."
        ),
        requirement_type="documentation",
        equipment_classes=[],
        sensor_classes=[],
        condition_type="ANY",
        action_required="DOCUMENT",
        severity_if_missing="MEDIUM",
        setpoint_role="NONE",
        iec_equivalent="IEC 61511 Cl.5",
        confidence=1.0,
    ),
    SafetyRule(
        rule_id="OSHA_PSM-SEED-004",
        source_id="OSHA_PSM_1910_119",
        standard_ref="OSHA 29 CFR 1910.119",
        clause_ref="1910.119(e)(1)",
        requirement_text=(
            "The employer must perform an initial process hazard analysis (PHA) on "
            "processes covered by this standard."
        ),
        requirement_type="documentation",
        equipment_classes=[],
        sensor_classes=[],
        condition_type="ANY",
        action_required="DOCUMENT",
        severity_if_missing="HIGH",
        setpoint_role="NONE",
        iec_equivalent="IEC 61511 Cl.8",
        confidence=1.0,
    ),
    SafetyRule(
        rule_id="OSHA_PSM-SEED-005",
        source_id="OSHA_PSM_1910_119",
        standard_ref="OSHA 29 CFR 1910.119",
        clause_ref="1910.119(f)(1)",
        requirement_text=(
            "The employer must develop and implement written operating procedures that "
            "provide clear instructions for safely conducting activities involved in each "
            "covered process, including emergency shutdown."
        ),
        requirement_type="shutdown",
        equipment_classes=["Pump", "Compressor", "Reactor", "Column"],
        sensor_classes=[],
        condition_type="ANY",
        action_required="STOP",
        severity_if_missing="HIGH",
        setpoint_role="TRIP",
        iec_equivalent="IEC 61511 Cl.11.8",
        confidence=1.0,
    ),

    # ── Alarm setpoint hierarchy rules ─────────────────────────────────────────
    SafetyRule(
        rule_id="IEC61511-SEED-001",
        source_id="EMERSON_IEC61511_GUIDE",
        standard_ref="IEC 61511-1:2016",
        clause_ref="IEC 61511 Cl.9.2.3",
        requirement_text=(
            "HIGH alarm setpoint must be set below the HIGH-HIGH trip setpoint "
            "to ensure an alarm is raised before the protective shutdown activates."
        ),
        requirement_type="setpoint_hierarchy",
        equipment_classes=["PressureVessel", "Tank", "Reactor", "Separator"],
        sensor_classes=["PressureTransmitter", "LevelTransmitter", "TemperatureSensor"],
        condition_type="HIGH",
        action_required="ALARM",
        severity_if_missing="HIGH",
        setpoint_role="ALARM",
        iec_equivalent="IEC 61511 Cl.9.2.3",
        confidence=1.0,
    ),
    SafetyRule(
        rule_id="IEC61511-SEED-002",
        source_id="EMERSON_IEC61511_GUIDE",
        standard_ref="IEC 61511-1:2016",
        clause_ref="IEC 61511 Cl.9.2.3",
        requirement_text=(
            "HIGH-HIGH trip setpoint must be set below the equipment MAWP "
            "(Maximum Allowable Working Pressure) with appropriate safety margin."
        ),
        requirement_type="setpoint_hierarchy",
        equipment_classes=["PressureVessel", "Reactor", "Separator", "Compressor"],
        sensor_classes=["PressureTransmitter"],
        condition_type="HIGH_HIGH",
        action_required="STOP",
        severity_if_missing="HIGH",
        setpoint_role="TRIP",
        iec_equivalent="IEC 61511 Cl.9.2.3",
        confidence=1.0,
    ),
    SafetyRule(
        rule_id="IEC61511-SEED-003",
        source_id="EMERSON_IEC61511_GUIDE",
        standard_ref="IEC 61511-1:2016",
        clause_ref="IEC 61511 Cl.9.2.3",
        requirement_text=(
            "LOW alarm setpoint must be set above the LOW-LOW trip setpoint "
            "so an alarm warns the operator before a low-level protective trip activates."
        ),
        requirement_type="setpoint_hierarchy",
        equipment_classes=["Tank", "Separator", "Column", "Drum"],
        sensor_classes=["LevelTransmitter"],
        condition_type="LOW",
        action_required="ALARM",
        severity_if_missing="HIGH",
        setpoint_role="ALARM",
        iec_equivalent="IEC 61511 Cl.9.2.3",
        confidence=1.0,
    ),

    # ── Pump protection rules ──────────────────────────────────────────────────
    SafetyRule(
        rule_id="IEC61511-SEED-004",
        source_id="EMERSON_IEC61511_GUIDE",
        standard_ref="IEC 61511-1:2016",
        clause_ref="IEC 61511 Cl.11.6.2",
        requirement_text=(
            "A pump must have a low-flow or low-suction-pressure interlock that "
            "trips the pump motor to prevent cavitation and mechanical damage."
        ),
        requirement_type="interlock",
        equipment_classes=["Pump"],
        sensor_classes=["FlowTransmitter", "PressureTransmitter"],
        condition_type="LOW_LOW",
        action_required="STOP",
        severity_if_missing="HIGH",
        setpoint_role="TRIP",
        iec_equivalent="IEC 61511 Cl.11.6",
        confidence=0.95,
    ),
    SafetyRule(
        rule_id="IEC61511-SEED-005",
        source_id="EMERSON_IEC61511_GUIDE",
        standard_ref="IEC 61511-1:2016",
        clause_ref="IEC 61511 Cl.11.6.2",
        requirement_text=(
            "A high-temperature alarm must be provided for pump bearing temperature "
            "monitored by a temperature sensor."
        ),
        requirement_type="alarm",
        equipment_classes=["Pump"],
        sensor_classes=["TemperatureSensor"],
        condition_type="HIGH",
        action_required="ALARM",
        severity_if_missing="MEDIUM",
        setpoint_role="ALARM",
        iec_equivalent="IEC 61511 Cl.11.6",
        confidence=0.9,
    ),

    # ── Compressor / vessel protection ────────────────────────────────────────
    SafetyRule(
        rule_id="IEC61511-SEED-006",
        source_id="EMERSON_IEC61511_GUIDE",
        standard_ref="IEC 61511-1:2016",
        clause_ref="IEC 61511 Cl.11.6.3",
        requirement_text=(
            "A compressor must have a high-high discharge pressure trip that stops "
            "the compressor before pressure exceeds its design pressure."
        ),
        requirement_type="shutdown",
        equipment_classes=["Compressor"],
        sensor_classes=["PressureTransmitter"],
        condition_type="HIGH_HIGH",
        action_required="STOP",
        severity_if_missing="HIGH",
        setpoint_role="TRIP",
        iec_equivalent="IEC 61511 Cl.11.6",
        confidence=0.95,
    ),
    SafetyRule(
        rule_id="IEC61511-SEED-007",
        source_id="EMERSON_IEC61511_GUIDE",
        standard_ref="IEC 61511-1:2016",
        clause_ref="IEC 61511 Cl.11.6.4",
        requirement_text=(
            "A pressure vessel operating above atmospheric pressure must have a "
            "pressure relief device sized to prevent pressure exceeding MAWP."
        ),
        requirement_type="interlock",
        equipment_classes=["PressureVessel", "Reactor", "Separator"],
        sensor_classes=["PressureTransmitter"],
        condition_type="HIGH_HIGH",
        action_required="CLOSE",
        severity_if_missing="HIGH",
        setpoint_role="TRIP",
        iec_equivalent="IEC 61511 Cl.11.6",
        confidence=0.95,
    ),

    # ── Emergency Shutdown (ESD) rules ────────────────────────────────────────
    SafetyRule(
        rule_id="IEC61511-SEED-008",
        source_id="EMERSON_IEC61511_GUIDE",
        standard_ref="IEC 61511-1:2016",
        clause_ref="IEC 61511 Cl.11.8",
        requirement_text=(
            "An Emergency Shutdown (ESD) system must be able to bring the process "
            "to a safe state from any normal operating condition."
        ),
        requirement_type="shutdown",
        equipment_classes=["ESD", "ShutdownValve", "Pump", "Compressor"],
        sensor_classes=["PressureTransmitter", "LevelTransmitter", "GasDetector"],
        condition_type="ANY",
        action_required="STOP",
        severity_if_missing="HIGH",
        setpoint_role="TRIP",
        iec_equivalent="IEC 61511 Cl.11.8",
        confidence=1.0,
    ),
    SafetyRule(
        rule_id="IEC61511-SEED-009",
        source_id="EMERSON_IEC61511_GUIDE",
        standard_ref="IEC 61511-1:2016",
        clause_ref="IEC 61511 Cl.11.8.3",
        requirement_text=(
            "ESD system must be independent of the basic process control system (BPCS) "
            "to prevent common-cause failure."
        ),
        requirement_type="interlock",
        equipment_classes=["ESD"],
        sensor_classes=[],
        condition_type="ANY",
        action_required="VERIFY",
        severity_if_missing="HIGH",
        setpoint_role="NONE",
        iec_equivalent="IEC 61511 Cl.11.8",
        confidence=1.0,
    ),

    # ── Valve / actuator rules ─────────────────────────────────────────────────
    SafetyRule(
        rule_id="IEC61511-SEED-010",
        source_id="EMERSON_IEC61511_GUIDE",
        standard_ref="IEC 61511-1:2016",
        clause_ref="IEC 61511 Cl.11.6.5",
        requirement_text=(
            "Safety instrumented function (SIF) final elements (valves, motors) must "
            "fail to a safe state on loss of power or signal (fail-safe design)."
        ),
        requirement_type="interlock",
        equipment_classes=["Valve", "ShutdownValve", "ControlValve", "Motor"],
        sensor_classes=[],
        condition_type="ANY",
        action_required="CLOSE",
        severity_if_missing="HIGH",
        setpoint_role="NONE",
        iec_equivalent="IEC 61511 Cl.11.6",
        confidence=1.0,
    ),

    # ── Gas / fire detection ───────────────────────────────────────────────────
    SafetyRule(
        rule_id="IEC61511-SEED-011",
        source_id="OSHA_PSM_1910_119",
        standard_ref="OSHA 29 CFR 1910.119",
        clause_ref="1910.119(d)(3)(i)(B)",
        requirement_text=(
            "Process safety information must document relief system design basis "
            "for toxic or highly hazardous chemicals."
        ),
        requirement_type="documentation",
        equipment_classes=["GasDetector", "FireDetector", "SafetyValve"],
        sensor_classes=["GasDetector", "FireDetector"],
        condition_type="ANY",
        action_required="ALARM",
        severity_if_missing="HIGH",
        setpoint_role="NONE",
        iec_equivalent="IEC 61511 Cl.10.3",
        confidence=0.9,
    ),
    SafetyRule(
        rule_id="IEC61511-SEED-012",
        source_id="EMERSON_IEC61511_GUIDE",
        standard_ref="IEC 61511-1:2016",
        clause_ref="IEC 61511 Cl.11.6.6",
        requirement_text=(
            "A combustible or toxic gas detector must trigger a HIGH alarm before "
            "concentration reaches the LEL/IDLH threshold."
        ),
        requirement_type="alarm",
        equipment_classes=["GasDetector"],
        sensor_classes=["GasDetector"],
        condition_type="HIGH",
        action_required="ALARM",
        severity_if_missing="HIGH",
        setpoint_role="ALARM",
        iec_equivalent="IEC 61511 Cl.11.6",
        confidence=0.9,
    ),

    # ── SIL verification / proof test ────────────────────────────────────────
    SafetyRule(
        rule_id="IEC61511-SEED-013",
        source_id="EMERSON_IEC61511_GUIDE",
        standard_ref="IEC 61511-1:2016",
        clause_ref="IEC 61511 Cl.16.4",
        requirement_text=(
            "Every safety instrumented function must be proof-tested at a frequency "
            "sufficient to maintain the required SIL."
        ),
        requirement_type="documentation",
        equipment_classes=[],
        sensor_classes=[],
        condition_type="ON_DEMAND",
        action_required="VERIFY",
        severity_if_missing="HIGH",
        setpoint_role="NONE",
        iec_equivalent="IEC 61511 Cl.16.4",
        confidence=1.0,
    ),

    # ── Sensor redundancy ─────────────────────────────────────────────────────
    SafetyRule(
        rule_id="IEC61511-SEED-014",
        source_id="EMERSON_IEC61511_GUIDE",
        standard_ref="IEC 61511-1:2016",
        clause_ref="IEC 61511 Cl.11.4.3",
        requirement_text=(
            "SIL 2 or higher safety instrumented functions require redundant sensors "
            "(1oo2 or 2oo3 voting) to achieve the required probability of failure on demand."
        ),
        requirement_type="interlock",
        equipment_classes=["PressureVessel", "Reactor", "Compressor"],
        sensor_classes=["PressureTransmitter", "LevelTransmitter", "TemperatureSensor"],
        condition_type="ANY",
        action_required="VERIFY",
        severity_if_missing="HIGH",
        setpoint_role="NONE",
        iec_equivalent="IEC 61511 Cl.11.4",
        confidence=0.9,
    ),

    # ── Tag naming / documentation ────────────────────────────────────────────
    SafetyRule(
        rule_id="IEC61511-SEED-015",
        source_id="EMERSON_IEC61511_GUIDE",
        standard_ref="IEC 61511-1:2016",
        clause_ref="IEC 61511 Cl.10.3.2",
        requirement_text=(
            "All safety instrumented functions must be uniquely identified with a "
            "tag number that is consistent between the P&ID, cause-and-effect matrix, "
            "and control narrative."
        ),
        requirement_type="tagging",
        equipment_classes=[],
        sensor_classes=[],
        condition_type="ANY",
        action_required="DOCUMENT",
        severity_if_missing="MEDIUM",
        setpoint_role="NONE",
        iec_equivalent="IEC 61511 Cl.10.3",
        confidence=1.0,
    ),

    # ── NIST SP 800-82: ICS cybersecurity ─────────────────────────────────────
    SafetyRule(
        rule_id="NIST-SEED-001",
        source_id="NIST_SP800_82",
        standard_ref="NIST SP 800-82 Rev.3",
        clause_ref="NIST SP 800-82 §5.3",
        requirement_text=(
            "Safety instrumented systems must be isolated from corporate IT networks; "
            "any connection must be through a DMZ with a data diode or unidirectional gateway."
        ),
        requirement_type="documentation",
        equipment_classes=["ESD"],
        sensor_classes=[],
        condition_type="ANY",
        action_required="DOCUMENT",
        severity_if_missing="HIGH",
        setpoint_role="NONE",
        iec_equivalent="IEC 61511 Cl.8.2.4",
        confidence=0.9,
    ),

    # ── EPA RMP: worst-case release ────────────────────────────────────────────
    SafetyRule(
        rule_id="EPA_RMP-SEED-001",
        source_id="EPA_RMP_40CFR68",
        standard_ref="EPA 40 CFR Part 68",
        clause_ref="40 CFR 68.67(c)(6)",
        requirement_text=(
            "Process hazard analysis must address engineering and administrative controls "
            "applicable to the hazards and their interrelationships."
        ),
        requirement_type="documentation",
        equipment_classes=[],
        sensor_classes=[],
        condition_type="ANY",
        action_required="DOCUMENT",
        severity_if_missing="HIGH",
        setpoint_role="NONE",
        iec_equivalent="IEC 61511 Cl.8.2",
        confidence=1.0,
    ),
    SafetyRule(
        rule_id="EPA_RMP-SEED-002",
        source_id="EPA_RMP_40CFR68",
        standard_ref="EPA 40 CFR Part 68",
        clause_ref="40 CFR 68.69",
        requirement_text=(
            "Operating procedures must address steps for each operating phase including "
            "startup, normal operations, temporary operations, emergency shutdown, and "
            "emergency operations."
        ),
        requirement_type="documentation",
        equipment_classes=["Pump", "Compressor", "Reactor", "Column"],
        sensor_classes=[],
        condition_type="ANY",
        action_required="DOCUMENT",
        severity_if_missing="MEDIUM",
        setpoint_role="NONE",
        iec_equivalent="IEC 61511 Cl.11.8",
        confidence=1.0,
    ),
]
