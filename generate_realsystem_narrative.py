"""Generate a realistic control narrative PDF for RealSystem Pvt. Ltd."""
from fpdf import FPDF
from pathlib import Path


class NarrativePDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(80, 80, 80)
        self.cell(0, 6, "RealSystem Pvt. Ltd.  |  CONFIDENTIAL  |  Control Narrative Rev 2.1", align="C")
        self.ln(2)
        self.set_draw_color(180, 180, 180)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)

    def footer(self):
        self.set_y(-13)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(130, 130, 130)
        self.cell(0, 6, f"Page {self.page_no()} | DOC-RS-CN-001 Rev 2.1 | FOR REVIEW ONLY  -  NOT FOR CONSTRUCTION", align="C")

    def chapter_title(self, text):
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(10, 40, 80)
        self.set_fill_color(230, 237, 248)
        self.cell(0, 8, text, fill=True, ln=True)
        self.ln(2)
        self.set_text_color(0, 0, 0)

    def section_title(self, text):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(20, 20, 20)
        self.ln(2)
        self.cell(0, 7, text, ln=True)
        self.set_text_color(0, 0, 0)

    def body(self, text):
        self.set_font("Helvetica", "", 9)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5, text)
        self.ln(1)

    def rule_box(self, rule_id, condition, action, iec_ref, severity):
        colors = {"HIGH": (220, 50, 50), "MEDIUM": (200, 130, 0), "LOW": (30, 140, 60)}
        r, g, b = colors.get(severity, (100, 100, 100))
        self.set_fill_color(245, 245, 245)
        self.set_draw_color(r, g, b)
        self.set_line_width(0.6)
        x, y = self.get_x(), self.get_y()
        self.rect(10, y, 190, 13, style="FD")
        self.set_xy(13, y + 1.5)
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(r, g, b)
        self.cell(20, 5, rule_id)
        self.set_font("Courier", "", 8)
        self.set_text_color(0, 0, 0)
        self.cell(100, 5, condition)
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(r, g, b)
        self.cell(30, 5, action)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, iec_ref)
        self.set_xy(13, y + 7)
        self.set_draw_color(200, 200, 200)
        self.set_line_width(0.2)
        self.ln(7)

    def table_row(self, cols, widths, bold=False):
        self.set_font("Helvetica", "B" if bold else "", 8)
        if bold:
            self.set_fill_color(210, 220, 240)
            fill = True
        else:
            self.set_fill_color(248, 248, 248)
            fill = True
        for col, w in zip(cols, widths):
            self.cell(w, 6, col, border=1, fill=fill)
        self.ln()


pdf = NarrativePDF()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()

# ── TITLE PAGE ─────────────────────────────────────────────────────────────────
pdf.set_font("Helvetica", "B", 20)
pdf.set_text_color(10, 40, 80)
pdf.ln(10)
pdf.cell(0, 12, "RealSystem Pvt. Ltd.", align="C", ln=True)
pdf.set_font("Helvetica", "B", 14)
pdf.set_text_color(40, 40, 40)
pdf.cell(0, 8, "Crude Oil Transfer Pump Station", align="C", ln=True)
pdf.set_font("Helvetica", "B", 11)
pdf.cell(0, 7, "Safety Control Narrative  -  Unit RS-100", align="C", ln=True)
pdf.ln(6)

pdf.set_font("Helvetica", "", 9)
pdf.set_text_color(80, 80, 80)
meta = [
    ("Document Number",  "DOC-RS-CN-001"),
    ("Revision",         "2.1"),
    ("Date",             "2024-09-15"),
    ("Prepared by",      "Process Safety Group, RealSystem Pvt. Ltd."),
    ("Reviewed by",      "Lead ICS Safety Engineer"),
    ("Classification",   "CONFIDENTIAL  -  INTERNAL USE ONLY"),
    ("Applicable Standard", "IEC 61511-1:2016 / ISA-84.00.01"),
]
pdf.set_x(40)
for k, v in meta:
    pdf.set_x(40)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(55, 6, k + ":", border="B")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(100, 6, v, border="B")
    pdf.ln()

pdf.ln(8)
pdf.set_font("Helvetica", "I", 8)
pdf.set_text_color(150, 50, 50)
pdf.multi_cell(0, 5,
    "CAUTION: This document contains safety-critical control logic for the RS-100 crude oil "
    "transfer pump station. All shutdown setpoints and interlock parameters must be verified "
    "by a qualified process safety engineer before commissioning. Unauthorized modification "
    "of logic described herein may result in loss of containment, fire, explosion, or fatality.")

# ── PAGE 2: INTRODUCTION & EQUIPMENT LIST ─────────────────────────────────────
pdf.add_page()
pdf.chapter_title("1. Introduction and Scope")
pdf.body(
    "This Control Narrative defines the automated safety and control logic for the RealSystem "
    "RS-100 Crude Oil Transfer Pump Station located at the Kakinada Terminal Facility. The pump "
    "station transfers crude oil from the tank farm (TK-001 to TK-004) to the pipeline manifold "
    "at a nominal flow rate of 250 m3/h at a discharge pressure of 45 to 60 bar.\n\n"
    "This document covers:\n"
    "  - Normal operating procedures and start/stop sequences\n"
    "  - Alarm setpoints and operator response guidance\n"
    "  - Safety instrumented system (SIS) shutdown logic\n"
    "  - Emergency shutdown (ESD) philosophy\n"
    "  - Interlock descriptions and IEC 61511 invariant mapping\n\n"
    "All safety logic described in this document is implemented in the RealSystem Safety PLC "
    "(model RS-SIL2-PLC) and verified to SIL 2 per IEC 61511."
)

pdf.chapter_title("2. Equipment Register")
pdf.body("The following equipment is addressed by this control narrative:")
pdf.ln(1)

headers = ["Tag", "Type", "Description", "Process Connection"]
widths  = [25, 35, 80, 50]
pdf.table_row(headers, widths, bold=True)

equip = [
    ("P-001",  "Centrifugal Pump",       "Crude Oil Transfer Pump #1 (Duty)",         "Suction: 16\" ANSI 300, Discharge: 12\" ANSI 600"),
    ("P-002",  "Centrifugal Pump",       "Crude Oil Transfer Pump #2 (Standby)",       "Suction: 16\" ANSI 300, Discharge: 12\" ANSI 600"),
    ("PT-001", "Pressure Transmitter",   "P-001/P-002 Common Discharge Pressure",      "1\" NPT on 12\" discharge header"),
    ("PT-002", "Pressure Transmitter",   "Pump Suction Header Pressure",               "1\" NPT on 16\" suction header"),
    ("FT-001", "Flow Transmitter",       "Discharge Pipeline Flow (Coriolis)",         "4\" inline on discharge header"),
    ("LT-001", "Level Transmitter",      "Feed Tank TK-001 Level (Guided Radar)",      "Tank nozzle N7, top of TK-001"),
    ("TT-001", "Temperature Transmitter","P-001 Drive-End Bearing Temperature",        "PT100 in bearing housing"),
    ("TT-002", "Temperature Transmitter","P-002 Drive-End Bearing Temperature",        "PT100 in bearing housing"),
    ("XV-001", "Motorised Ball Valve",   "P-001 Discharge Isolation Valve",            "12\" ANSI 600, fail-closed"),
    ("XV-002", "Motorised Ball Valve",   "P-002 Discharge Isolation Valve",            "12\" ANSI 600, fail-closed"),
    ("XV-003", "Motorised Ball Valve",   "Suction Header Isolation Valve",             "16\" ANSI 300, fail-closed"),
    ("ESD-001","Emergency Shutdown",     "Station-Wide Emergency Shutdown System",     "Hardwired to SIL 2 Safety PLC"),
    ("I-001",  "Safety Interlock",       "High-High Discharge Pressure Interlock",     "Trips P-001, P-002 on PT-001 HH"),
    ("I-002",  "Safety Interlock",       "Low-Low Suction Pressure Interlock",         "Trips P-001, P-002 on PT-002 LL"),
    ("I-003",  "Safety Interlock",       "Low-Low Tank Level Interlock",               "Trips P-001, P-002 on LT-001 LL"),
    ("I-004",  "Safety Interlock",       "High Bearing Temperature Interlock",         "Trips affected pump on TT-001/TT-002 HH"),
]
for row in equip:
    pdf.table_row(list(row), widths)

# ── PAGE 3: NORMAL OPERATION ───────────────────────────────────────────────────
pdf.add_page()
pdf.chapter_title("3. Normal Operating Conditions")

pdf.section_title("3.1 Pump Start Sequence")
pdf.body(
    "Prior to starting P-001 or P-002, the following permissives must be satisfied:\n"
    "  (a) XV-003 (suction isolation valve) is confirmed OPEN\n"
    "  (b) PT-002 (suction pressure) reads >= 3.5 bar\n"
    "  (c) LT-001 (tank level) reads >= 30%\n"
    "  (d) No active HIGH or HIGH-HIGH alarms on TT-001 (for P-001) or TT-002 (for P-002)\n"
    "  (e) ESD-001 is in RESET state (not tripped)\n\n"
    "The start sequence is: (1) Open discharge isolation valve XV-001 (or XV-002 for P-002), "
    "(2) Start pump motor, (3) Confirm flow indication on FT-001 > 30 m3/h within 15 seconds. "
    "If flow is not confirmed, the pump shall trip and a START FAILURE alarm shall be raised."
)

pdf.section_title("3.2 Normal Operating Ranges")
pdf.body("Under steady-state operation the following process parameters are expected:")
pdf.ln(1)
headers2 = ["Parameter", "Tag", "Normal Range", "Units"]
widths2   = [60, 20, 40, 30]
pdf.table_row(headers2, widths2, bold=True)
normal_ranges = [
    ("Discharge Pressure",      "PT-001", "45 - 60",   "bar"),
    ("Suction Pressure",        "PT-002", "3.5 - 6.0", "bar"),
    ("Pipeline Flow",           "FT-001", "200 - 280", "m3/h"),
    ("Tank TK-001 Level",       "LT-001", "30 - 90",   "% of height"),
    ("P-001 Bearing Temperature","TT-001", "40 - 65",  "degC"),
    ("P-002 Bearing Temperature","TT-002", "40 - 65",  "degC"),
]
for row in normal_ranges:
    pdf.table_row(list(row), widths2)

pdf.ln(4)
pdf.section_title("3.3 Duty/Standby Changeover")
pdf.body(
    "P-001 is designated as the duty pump and P-002 as standby. Automatic changeover from P-001 "
    "to P-002 occurs if:\n"
    "  - P-001 trips on any interlock condition, OR\n"
    "  - P-001 motor fault signal is received from the MCC\n\n"
    "Manual changeover is permitted from the DCS only when both pumps are in READY state and no "
    "alarms are active. Changeover logic ensures XV-002 is fully open before P-002 starts, "
    "preventing dead-head startup."
)

# ── PAGE 4: ALARM SETPOINTS ────────────────────────────────────────────────────
pdf.add_page()
pdf.chapter_title("4. Alarm and Trip Setpoints")

pdf.body(
    "The following table defines all alarm and trip setpoints for the RS-100 pump station. "
    "HIGH (H) alarms are operator warnings. HIGH-HIGH (HH) and LOW-LOW (LL) setpoints trigger "
    "automatic safety actions via the SIS interlocks described in Section 5."
)
pdf.ln(2)

headers3 = ["Tag", "Alarm Level", "Setpoint", "Unit", "Action", "IEC Clause"]
widths3   = [18, 22, 22, 14, 60, 30]
pdf.table_row(headers3, widths3, bold=True)

alarms = [
    ("PT-001", "HIGH (H)",        "65",  "bar",   "ALARM  -  operator to reduce flow or check for blockage", "IEC 61511 Cl.9.2.2"),
    ("PT-001", "HIGH-HIGH (HH)",  "75",  "bar",   "TRIP P-001 and P-002 via I-001. Close XV-001 and XV-002", "IEC 61511 Cl.9.2.2"),
    ("PT-002", "LOW (L)",         "3.5", "bar",   "ALARM  -  operator to check suction valve and feed tank", "IEC 61511 Cl.9.2.2"),
    ("PT-002", "LOW-LOW (LL)",    "2.0", "bar",   "TRIP P-001 and P-002 via I-002. Close XV-003",          "IEC 61511 Cl.9.2.2"),
    ("FT-001", "LOW (L)",         "50",  "m3/h",  "ALARM  -  check for valve restriction or pump cavitation","IEC 61511 Cl.9.2.3"),
    ("FT-001", "LOW-LOW (LL)",    "20",  "m3/h",  "ALARM  -  deadhead condition suspected, operator action",  "IEC 61511 Cl.9.2.3"),
    ("LT-001", "LOW (L)",         "25",  "% ht",  "ALARM  -  switch to alternate tank or reduce flow",       "IEC 61511 Cl.9.2.2"),
    ("LT-001", "LOW-LOW (LL)",    "10",  "% ht",  "TRIP P-001 and P-002 via I-003. Prevent cavitation",    "IEC 61511 Cl.9.2.2"),
    ("TT-001", "HIGH (H)",        "75",  "degC",  "ALARM  -  P-001 bearing temperature rising",              "IEC 61511 Cl.9.2.3"),
    ("TT-001", "HIGH-HIGH (HH)",  "90",  "degC",  "TRIP P-001 via I-004. Protect pump bearings",           "IEC 61511 Cl.9.2.3"),
    ("TT-002", "HIGH (H)",        "75",  "degC",  "ALARM  -  P-002 bearing temperature rising",              "IEC 61511 Cl.9.2.3"),
    ("TT-002", "HIGH-HIGH (HH)",  "90",  "degC",  "TRIP P-002 via I-004. Protect pump bearings",           "IEC 61511 Cl.9.2.3"),
]
for row in alarms:
    pdf.table_row(list(row), widths3)

# ── PAGE 5: SHUTDOWN LOGIC ─────────────────────────────────────────────────────
pdf.add_page()
pdf.chapter_title("5. Safety Interlock and Shutdown Logic")

pdf.body(
    "This section describes all safety interlocks implemented in the RealSystem SIL 2 Safety PLC. "
    "Each interlock is associated with an IEC 61511 invariant requirement. The interlock logic "
    "uses 1oo1 voting (single transmitter) for most functions; PT-001 HH shutdown uses 2oo3 voting "
    "per the SIL 2 requirement."
)

pdf.section_title("5.1 Interlock I-001  -  High-High Discharge Pressure Shutdown")
pdf.body(
    "Sensor:      PT-001 (Discharge Pressure Transmitter)\n"
    "Trip Level:  HIGH-HIGH at 75 bar\n"
    "Voting:      2oo3 (three independent pressure transmitters PT-001A, PT-001B, PT-001C)\n"
    "SIL Target:  SIL 2 (IEC 61511-1 Clause 9.2.2)\n\n"
    "When discharge pressure sensor PT-001 reads greater than or equal to 75 bar, interlock I-001 "
    "shall activate immediately. Upon activation of I-001, pump P-001 shall be stopped and pump "
    "P-002 shall be stopped. Additionally, discharge isolation valves XV-001 and XV-002 shall be "
    "closed. The interlock shall latch and require manual reset from the DCS by an authorised "
    "operator after the root cause has been identified and resolved.\n\n"
    "Pre-trip alarm: PT-001 >= 65 bar raises a HIGH pressure alarm to give the operator a "
    "30-second window to take corrective action before the automatic trip fires."
)

pdf.section_title("5.2 Interlock I-002  -  Low-Low Suction Pressure Shutdown")
pdf.body(
    "Sensor:      PT-002 (Suction Pressure Transmitter)\n"
    "Trip Level:  LOW-LOW at 2.0 bar\n"
    "Voting:      1oo1\n"
    "SIL Target:  SIL 1 (IEC 61511-1 Clause 9.2.2)\n\n"
    "When suction pressure sensor PT-002 reads less than or equal to 2.0 bar, interlock I-002 "
    "shall activate. Upon activation, pump P-001 shall be stopped and pump P-002 shall be stopped "
    "to prevent cavitation and mechanical damage to pump seals. Suction isolation valve XV-003 "
    "shall be closed to isolate the suction header. The interlock shall latch pending manual reset."
)

pdf.section_title("5.3 Interlock I-003  -  Low-Low Feed Tank Level Shutdown")
pdf.body(
    "Sensor:      LT-001 (Tank TK-001 Level Transmitter)\n"
    "Trip Level:  LOW-LOW at 10% of tank height\n"
    "Voting:      1oo1\n"
    "SIL Target:  SIL 1 (IEC 61511-1 Clause 9.2.2)\n\n"
    "When feed tank level transmitter LT-001 reads less than or equal to 10 percent of tank height, "
    "interlock I-003 shall activate. Upon activation, pump P-001 shall be stopped and pump P-002 "
    "shall be stopped to prevent dry running and pump cavitation. A LOW-LOW LEVEL alarm shall be "
    "raised on the DCS. The interlock shall latch pending manual reset after tank level is restored "
    "above 20 percent."
)

pdf.section_title("5.4 Interlock I-004  -  High Bearing Temperature Shutdown")
pdf.body(
    "Sensor:      TT-001 (P-001 Bearing Temperature) / TT-002 (P-002 Bearing Temperature)\n"
    "Trip Level:  HIGH-HIGH at 90 degC\n"
    "Voting:      1oo1 per pump (independent for each pump)\n"
    "SIL Target:  SIL 1 (IEC 61511-1 Clause 9.2.3)\n\n"
    "When bearing temperature transmitter TT-001 reads greater than or equal to 90 degC, interlock "
    "I-004 shall trip pump P-001 only. P-001 shall be stopped immediately and its discharge "
    "isolation valve XV-001 shall close. P-002 may continue or start as standby pump.\n\n"
    "Similarly, when bearing temperature transmitter TT-002 reads greater than or equal to 90 degC, "
    "interlock I-004 shall trip pump P-002 only. XV-002 shall close. P-001 may continue or start.\n\n"
    "Pre-trip alarm at TT-001 >= 75 degC and TT-002 >= 75 degC provides early warning."
)

# ── PAGE 6: ESD ────────────────────────────────────────────────────────────────
pdf.add_page()
pdf.chapter_title("6. Emergency Shutdown (ESD) Philosophy")

pdf.body(
    "The Emergency Shutdown System ESD-001 is a station-wide safety layer independent of the "
    "process control system. ESD-001 activates under any of the following conditions:\n\n"
    "  (a) Manual pushbutton activation from the local field panel or control room\n"
    "  (b) Loss of instrument air supply (< 4.5 bar)\n"
    "  (c) Loss of 24VDC safety bus\n"
    "  (d) Fire and Gas system F&G-001 trip signal received\n"
    "  (e) High-High pressure on PT-001 confirmed by 2oo3 voting (redundant path to I-001)\n\n"
    "Upon activation of ESD-001, the following actions are executed simultaneously and "
    "unconditionally within 500 milliseconds:\n\n"
    "  1. Pump P-001 is stopped\n"
    "  2. Pump P-002 is stopped\n"
    "  3. Discharge isolation valve XV-001 is closed (fail-closed actuator)\n"
    "  4. Discharge isolation valve XV-002 is closed (fail-closed actuator)\n"
    "  5. Suction isolation valve XV-003 is closed (fail-closed actuator)\n"
    "  6. ESD active signal is sent to the pipeline SCADA system\n\n"
    "ESD-001 is a hardwired latch circuit. Reset requires physical key-switch at the local panel "
    "and DCS confirmation from a Level 3 authorised engineer. Bypassing ESD-001 is not permitted "
    "during normal operation and requires a Management of Change (MoC) approval."
)

pdf.chapter_title("7. Cause and Effect Summary")
pdf.body("The following cause-and-effect matrix summarises all shutdown actions:")
pdf.ln(1)

headers4 = ["Cause (Initiating Event)", "Tag", "Setpoint", "Effect: P-001", "Effect: P-002", "Effect: Valves"]
widths4   = [52, 16, 18, 22, 22, 50]
pdf.table_row(headers4, widths4, bold=True)

ce_rows = [
    ("Discharge pressure HIGH-HIGH",  "PT-001", ">= 75 bar",   "STOP",  "STOP",  "CLOSE XV-001, XV-002"),
    ("Suction pressure LOW-LOW",      "PT-002", "<= 2.0 bar",  "STOP",  "STOP",  "CLOSE XV-003"),
    ("Tank level LOW-LOW",            "LT-001", "<= 10% ht",   "STOP",  "STOP",  "No valve action"),
    ("P-001 bearing temp HIGH-HIGH",  "TT-001", ">= 90 degC",  "STOP",  "RUN",   "CLOSE XV-001 only"),
    ("P-002 bearing temp HIGH-HIGH",  "TT-002", ">= 90 degC",  "RUN",   "STOP",  "CLOSE XV-002 only"),
    ("ESD-001 activated",             "ESD-001","Any trigger",  "STOP",  "STOP",  "CLOSE XV-001, XV-002, XV-003"),
]
for row in ce_rows:
    pdf.table_row(list(row), widths4)

# ── PAGE 7: RULE SUMMARY ───────────────────────────────────────────────────────
pdf.add_page()
pdf.chapter_title("8. Control Rule Summary (Machine-Readable Format)")

pdf.body(
    "The following rules are extracted directly from Sections 4 and 5 for use in the "
    "RealSystem Automated Safety Audit System (RS-ASAS). Each rule is stated in IF/THEN form "
    "with explicit sensor tags, numeric thresholds, and equipment actions."
)
pdf.ln(3)

rules = [
    ("R-001", "IF PT-001 >= 75 bar",   "STOP P-001",  "IEC 61511 Cl.9.2.2", "HIGH"),
    ("R-002", "IF PT-001 >= 75 bar",   "STOP P-002",  "IEC 61511 Cl.9.2.2", "HIGH"),
    ("R-003", "IF PT-001 >= 65 bar",   "ALARM P-001", "IEC 61511 Cl.9.2.2", "MEDIUM"),
    ("R-004", "IF PT-002 <= 2.0 bar",  "STOP P-001",  "IEC 61511 Cl.9.2.2", "HIGH"),
    ("R-005", "IF PT-002 <= 2.0 bar",  "STOP P-002",  "IEC 61511 Cl.9.2.2", "HIGH"),
    ("R-006", "IF PT-002 <= 3.5 bar",  "ALARM P-001", "IEC 61511 Cl.9.2.2", "MEDIUM"),
    ("R-007", "IF LT-001 <= 10%",      "STOP P-001",  "IEC 61511 Cl.9.2.2", "HIGH"),
    ("R-008", "IF LT-001 <= 10%",      "STOP P-002",  "IEC 61511 Cl.9.2.2", "HIGH"),
    ("R-009", "IF LT-001 <= 25%",      "ALARM P-001", "IEC 61511 Cl.9.2.2", "MEDIUM"),
    ("R-010", "IF TT-001 >= 90 degC",  "STOP P-001",  "IEC 61511 Cl.9.2.3", "HIGH"),
    ("R-011", "IF TT-002 >= 90 degC",  "STOP P-002",  "IEC 61511 Cl.9.2.3", "HIGH"),
    ("R-012", "IF TT-001 >= 75 degC",  "ALARM P-001", "IEC 61511 Cl.9.2.3", "MEDIUM"),
    ("R-013", "IF TT-002 >= 75 degC",  "ALARM P-002", "IEC 61511 Cl.9.2.3", "MEDIUM"),
    ("R-014", "IF FT-001 <= 50 m3/h",  "ALARM P-001", "IEC 61511 Cl.9.2.3", "LOW"),
    ("R-015", "IF ESD-001 == ACTIVE",  "STOP P-001",  "IEC 61511 Cl.9.2.2", "HIGH"),
    ("R-016", "IF ESD-001 == ACTIVE",  "STOP P-002",  "IEC 61511 Cl.9.2.2", "HIGH"),
    ("R-017", "IF ESD-001 == ACTIVE",  "CLOSE XV-001","IEC 61511 Cl.9.2.2", "HIGH"),
    ("R-018", "IF ESD-001 == ACTIVE",  "CLOSE XV-002","IEC 61511 Cl.9.2.2", "HIGH"),
    ("R-019", "IF ESD-001 == ACTIVE",  "CLOSE XV-003","IEC 61511 Cl.9.2.2", "HIGH"),
]

for r in rules:
    pdf.rule_box(*r)

# ── PAGE 8: REVISION HISTORY ───────────────────────────────────────────────────
pdf.add_page()
pdf.chapter_title("9. Document Revision History")
pdf.ln(2)
headers5 = ["Rev", "Date", "Author", "Description of Change"]
widths5   = [12, 25, 45, 108]
pdf.table_row(headers5, widths5, bold=True)
revisions = [
    ("1.0", "2023-03-10", "P. Safety Group",        "Initial issue for HAZOP review"),
    ("1.1", "2023-06-22", "P. Safety Group",         "Incorporated HAZOP action items A-014 to A-031"),
    ("2.0", "2024-01-15", "Lead ICS Safety Engineer","Added TT-001/TT-002 bearing temp interlocks (I-004)"),
    ("2.1", "2024-09-15", "P. Safety Group",         "Updated PT-001 trip setpoint from 70 to 75 bar (MoC-2024-017)"),
]
for row in revisions:
    pdf.table_row(list(row), widths5)

pdf.ln(8)
pdf.chapter_title("10. Applicable Standards and References")
pdf.body(
    "1.  IEC 61511-1:2016  -  Functional safety: Safety instrumented systems for the process "
    "industry sector  -  Part 1: Framework, definitions, system, hardware and application "
    "programming requirements.\n\n"
    "2.  ISA-84.00.01-2004 (IEC 61511 Mod)  -  Functional Safety: Safety Instrumented Systems "
    "for the Process Industry Sector.\n\n"
    "3.  IEC 61508-1:2010  -  Functional safety of E/E/PE safety-related systems.\n\n"
    "4.  API RP 14C  -  Analysis, Design, Installation, and Testing of Basic Surface Safety "
    "Systems for Offshore Production Platforms.\n\n"
    "5.  RealSystem Internal Standard RS-ENG-005 Rev 3  -  Safety PLC Programming Guidelines.\n\n"
    "6.  RealSystem SIL Determination Study  -  DOC-RS-SIL-001 Rev 1.0.\n\n"
    "7.  RealSystem Piping and Instrumentation Diagram  -  DWG-RS-PID-100-001 Rev 4."
)

pdf.ln(6)
pdf.set_font("Helvetica", "B", 9)
pdf.set_text_color(10, 40, 80)
pdf.cell(0, 6, "END OF DOCUMENT  -  DOC-RS-CN-001 Rev 2.1", align="C", ln=True)
pdf.set_font("Helvetica", "I", 8)
pdf.set_text_color(130, 130, 130)
pdf.cell(0, 5, "RealSystem Pvt. Ltd. | Kakinada Terminal Facility | IEC 61511 SIL 2 Certified", align="C", ln=True)

# Save
out = Path("C:/Users/I781541/Desktop/m-tech/safety_auditor/data/realsystem_control_narrative.pdf")
out.parent.mkdir(parents=True, exist_ok=True)
pdf.output(str(out))
print(f"Generated: {out}")
print(f"Pages: {pdf.page}")
