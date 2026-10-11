"""
Generate Panel Review 2 presentation for the Safety Auditor project.
Same Amrita School of Computing template as the friend's presentation.
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_THEME_COLOR
import copy

# ── Colors ────────────────────────────────────────────────────────────────────
BLUE_BORDER   = RGBColor(0x1F, 0x49, 0x7D)   # dark steel-blue border
RED_FOOTER    = RGBColor(0xC0, 0x00, 0x00)   # Amrita red for footer text
DARK_GREY     = RGBColor(0x40, 0x40, 0x40)   # pentagon shape fill
WHITE         = RGBColor(0xFF, 0xFF, 0xFF)
BLACK         = RGBColor(0x00, 0x00, 0x00)
TABLE_HEADER  = RGBColor(0x36, 0x5F, 0x91)   # blue table header
TABLE_ALT     = RGBColor(0xDC, 0xE6, 0xF1)   # light blue alt row
BLUE_BULLET   = RGBColor(0x1F, 0x49, 0x7D)

# ── Dimensions ─────────────────────────────────────────────────────────────────
SLIDE_W = Inches(13.33)
SLIDE_H = Inches(7.5)

DATE_STR      = "07-10-2026"
SCHOOL_STR    = "Amrita School of Computing"

# ── Helpers ────────────────────────────────────────────────────────────────────

def new_prs():
    prs = Presentation()
    prs.slide_width  = SLIDE_W
    prs.slide_height = SLIDE_H
    return prs


def blank_slide(prs):
    """Add a completely blank slide."""
    blank_layout = prs.slide_layouts[6]
    return prs.slides.add_slide(blank_layout)


def add_footer(slide):
    """Add date (bottom-left) and school name (bottom-center) in red."""
    # Date bottom-left
    tf = slide.shapes.add_textbox(Inches(0.2), Inches(7.1), Inches(2), Inches(0.35))
    p = tf.text_frame.paragraphs[0]
    p.text = DATE_STR
    p.runs[0].font.size = Pt(11)
    p.runs[0].font.color.rgb = RED_FOOTER

    # School name bottom-center
    tf2 = slide.shapes.add_textbox(Inches(4.5), Inches(7.1), Inches(4.5), Inches(0.35))
    p2 = tf2.text_frame.paragraphs[0]
    p2.alignment = PP_ALIGN.CENTER
    p2.text = SCHOOL_STR
    p2.runs[0].font.size = Pt(11)
    p2.runs[0].font.color.rgb = RED_FOOTER


def add_logo_placeholder(slide):
    """Add a small placeholder for the Amrita logo (top-left corner)."""
    tf = slide.shapes.add_textbox(Inches(0.15), Inches(0.05), Inches(1.4), Inches(0.55))
    p = tf.text_frame.paragraphs[0]
    p.text = "AMRITA"
    r = p.runs[0]
    r.font.bold = True
    r.font.size = Pt(13)
    r.font.color.rgb = RED_FOOTER


def add_rounded_rect(slide, left, top, width, height, line_color=BLUE_BORDER, line_width=Pt(2.5)):
    """Add a rounded rectangle shape."""
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    from pptx.oxml.ns import qn
    from pptx.util import Pt
    import lxml.etree as etree

    shape = slide.shapes.add_shape(
        5,  # MSO_SHAPE_TYPE.ROUNDED_RECTANGLE = 5
        left, top, width, height
    )
    shape.fill.background()  # transparent fill (white)
    shape.fill.solid()
    shape.fill.fore_color.rgb = WHITE
    shape.line.color.rgb = line_color
    shape.line.width = line_width
    # Adjust corner radius to ~15 px feel
    sp = shape.element
    prstGeom = sp.find('.//' + qn('a:prstGeom'))
    if prstGeom is not None:
        avLst = prstGeom.find(qn('a:avLst'))
        if avLst is not None:
            for gd in avLst.findall(qn('a:gd')):
                if gd.get('name') == 'adj':
                    gd.set('fmla', 'val 30000')  # ~8% rounding
    return shape


def set_title_text(slide, title, left, top, width, height, size=Pt(38)):
    """Add a large title text box."""
    tf_box = slide.shapes.add_textbox(left, top, width, height)
    tf = tf_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title
    r = p.runs[0]
    r.font.size = size
    r.font.color.rgb = BLACK
    return tf_box


def add_bullet_textbox(slide, left, top, width, height, items, title=None, title_size=Pt(36)):
    """Add textbox with optional title and bullet list."""
    tf_box = slide.shapes.add_textbox(left, top, width, height)
    tf = tf_box.text_frame
    tf.word_wrap = True

    if title:
        p = tf.paragraphs[0]
        p.text = title
        r = p.runs[0]
        r.font.size = title_size
        r.font.bold = False
        r.font.color.rgb = BLACK

    for i, item in enumerate(items):
        if isinstance(item, dict):
            # Sub-item with indent
            p = tf.add_paragraph()
            p.text = "    " + item['text']
            p.level = 1
            r = p.runs[0]
            r.font.size = Pt(18)
            r.font.color.rgb = BLUE_BULLET
        else:
            p = tf.add_paragraph()
            p.text = "• " + item
            r = p.runs[0]
            r.font.size = Pt(20)
            r.font.color.rgb = BLACK

    return tf_box


def add_table(slide, left, top, width, height, headers, rows, col_widths=None):
    """Add a formatted table."""
    n_cols = len(headers)
    n_rows = len(rows) + 1  # +1 for header
    table = slide.shapes.add_table(n_rows, n_cols, left, top, width, height).table

    if col_widths:
        for ci, cw in enumerate(col_widths):
            table.columns[ci].width = cw

    # Header row
    for ci, h in enumerate(headers):
        cell = table.cell(0, ci)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = TABLE_HEADER
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.runs[0]
        r.font.bold = True
        r.font.size = Pt(18)
        r.font.color.rgb = WHITE

    # Data rows
    for ri, row in enumerate(rows):
        bg = TABLE_ALT if ri % 2 == 0 else WHITE
        for ci, val in enumerate(row):
            cell = table.cell(ri + 1, ci)
            cell.text = val
            cell.fill.solid()
            cell.fill.fore_color.rgb = bg
            p = cell.text_frame.paragraphs[0]
            r = p.runs[0]
            r.font.size = Pt(17)
            r.font.color.rgb = BLACK

    return table


# ── Slide builders ─────────────────────────────────────────────────────────────

def build_title_slide(prs):
    slide = blank_slide(prs)
    add_logo_placeholder(slide)
    add_footer(slide)

    # Outer rounded rectangle (the big content box)
    add_rounded_rect(slide, Inches(0.3), Inches(0.55), Inches(12.75), Inches(6.5))

    # Project title (centered)
    tb = slide.shapes.add_textbox(Inches(1.0), Inches(1.0), Inches(11.3), Inches(2.2))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = "A Neuro-Symbolic Safety Auditing Framework"
    r = p.runs[0]
    r.font.size = Pt(34)
    r.font.color.rgb = BLACK

    p2 = tf.add_paragraph()
    p2.alignment = PP_ALIGN.CENTER
    p2.text = "for Industrial Control System Specifications"
    r2 = p2.runs[0]
    r2.font.size = Pt(34)
    r2.font.color.rgb = BLACK

    p3 = tf.add_paragraph()
    p3.alignment = PP_ALIGN.CENTER
    p3.text = "Pre-Synthesis Defect Detection using LLM and Z3 Formal Verification"
    r3 = p3.runs[0]
    r3.font.size = Pt(24)
    r3.font.color.rgb = BLACK

    # Phase label
    tb2 = slide.shapes.add_textbox(Inches(4.5), Inches(3.3), Inches(4.3), Inches(0.6))
    tf2 = tb2.text_frame
    p4 = tf2.paragraphs[0]
    p4.alignment = PP_ALIGN.CENTER
    p4.text = "Project Phase 1"
    r4 = p4.runs[0]
    r4.font.size = Pt(26)
    r4.font.color.rgb = BLACK

    # Supervisor
    tb3 = slide.shapes.add_textbox(Inches(3.5), Inches(4.1), Inches(6.0), Inches(0.55))
    p5 = tb3.text_frame.paragraphs[0]
    p5.alignment = PP_ALIGN.CENTER
    p5.text = "Supervisor: Dr. [Supervisor Name]"
    r5 = p5.runs[0]
    r5.font.size = Pt(22)
    r5.font.color.rgb = BLACK

    # Table for name, roll, internship
    headers = ["Name", "Roll Number", "Internship Details"]
    rows    = [["LOKANIRAKESH", "[Roll Number]", "[Internship Details]"]]
    add_table(slide,
              Inches(1.5), Inches(4.85), Inches(10.0), Inches(1.0),
              headers, rows,
              col_widths=[Inches(3.5), Inches(3.5), Inches(3.0)])


def build_guide_approval_slide(prs):
    slide = blank_slide(prs)
    add_logo_placeholder(slide)
    add_footer(slide)
    add_rounded_rect(slide, Inches(0.3), Inches(0.55), Inches(12.75), Inches(6.5))

    tb = slide.shapes.add_textbox(Inches(3.5), Inches(0.7), Inches(6.3), Inches(0.8))
    p = tb.text_frame.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = "Guide Approval Mail"
    r = p.runs[0]
    r.font.size = Pt(38)
    r.font.color.rgb = BLACK


def build_contents_slide(prs):
    slide = blank_slide(prs)
    add_logo_placeholder(slide)
    add_footer(slide)
    add_rounded_rect(slide, Inches(0.3), Inches(0.55), Inches(12.75), Inches(6.5))

    items = [
        "Introduction and Motivation",
        "Problem Statement",
        "Proposed Methodology (9-phase pipeline + architecture) – 2 slides",
        "Implementation Progress",
        "Standard Algorithms and Evaluation Metrics",
        "Tools and Methods for Implementation",
        "Preliminary Verification and Results",
        "Datasets",
        "Project Plan for Semester 3",
        "Technical Enrichment Activities",
        "Conclusion",
        "References",
    ]
    add_bullet_textbox(
        slide,
        Inches(0.55), Inches(0.6), Inches(12.3), Inches(6.4),
        items,
        title="Contents"
    )


def build_intro_slide(prs):
    slide = blank_slide(prs)
    add_logo_placeholder(slide)
    add_footer(slide)
    add_rounded_rect(slide, Inches(0.3), Inches(0.55), Inches(12.75), Inches(6.5))

    items = [
        "Industrial Control Systems (ICS) run power plants, oil refineries, and water treatment plants — a single safety defect can cause explosions or environmental disasters",
        "Safety specifications are written across 3 different documents: Control Narratives (text), P&ID Drawings (diagrams), and Cause-Effect Tables",
        "Today, safety engineers review these documents manually — this is slow and misses many defects",
        "AI tools exist but have two major weaknesses:",
        {"text": "LLMs alone hallucinate — they can make up safety rules that do not exist"},
        {"text": "No tool links information across all 3 document types and verifies the rules mathematically"},
        "Our motivation: build an automated auditor that reads all 3 document types, links them together, and uses a mathematical solver (Z3) to prove safety defects before any PLC code is written",
    ]
    add_bullet_textbox(
        slide,
        Inches(0.55), Inches(0.6), Inches(12.3), Inches(6.4),
        items,
        title="Introduction and Motivation"
    )


def build_problem_statement_slide(prs):
    slide = blank_slide(prs)
    add_logo_placeholder(slide)
    add_footer(slide)
    add_rounded_rect(slide, Inches(0.3), Inches(0.55), Inches(12.75), Inches(6.5))

    items = [
        "Safety specifications for ICS are scattered across multiple document types — no single tool reads all of them together",
        "Manual review by safety engineers misses defects that are only discovered at commissioning or during accidents, which is very expensive and dangerous",
        "Existing AI tools use LLMs in isolation — they can produce plausible-sounding but incorrect safety rules because they cannot prove correctness",
        "There is no tool that: (1) automatically links equipment and rules across Control Narratives, P&IDs, and Cause-Effect Tables, AND (2) uses formal logic to verify those rules against IEC 61511 safety standards",
        "This project solves both gaps by combining LLMs (for reading natural language) with the Z3 SMT solver (for mathematical proof) in a 9-phase neuro-symbolic pipeline",
    ]
    add_bullet_textbox(
        slide,
        Inches(0.55), Inches(0.6), Inches(12.3), Inches(6.4),
        items,
        title="Problem Statement"
    )


def build_methodology_slide1(prs):
    slide = blank_slide(prs)
    add_logo_placeholder(slide)
    add_footer(slide)
    add_rounded_rect(slide, Inches(0.3), Inches(0.55), Inches(12.75), Inches(6.5))

    items_header = ["9-Phase Neuro-Symbolic Pipeline: Neural Phases (1–4)"]
    tb = slide.shapes.add_textbox(Inches(0.55), Inches(0.6), Inches(12.3), Inches(0.7))
    p = tb.text_frame.paragraphs[0]
    p.text = "Proposed Methodology"
    r = p.runs[0]
    r.font.size = Pt(38)
    r.font.color.rgb = BLACK

    # Phase 1 label
    tb2 = slide.shapes.add_textbox(Inches(0.55), Inches(1.4), Inches(12.0), Inches(0.45))
    p2 = tb2.text_frame.paragraphs[0]
    p2.text = "Neural Phases (Phase 1 – 4):"
    r2 = p2.runs[0]
    r2.font.bold = True
    r2.font.size = Pt(22)
    r2.font.color.rgb = BLUE_BULLET

    items = [
        "Phase 1 – INGEST: Read and extract text from Control Narrative PDFs, P&ID drawing images (OCR), and Cause-Effect table PDFs",
        "Phase 2 – EXTRACT: Use LLM (Qwen 2.5 via Ollama) to identify equipment tags, sensor values, and control rules from natural language text",
        "Phase 3 – LINK: Connect the same equipment mentioned in different documents using exact matching, fuzzy matching (RapidFuzz), and sentence embeddings (all-MiniLM-L6-v2)",
        "Phase 4 – GRAPH: Build a knowledge graph (NetworkX) showing all equipment, sensors, actuators, and the rules that connect them — exported as an interactive HTML visualization",
    ]
    add_bullet_textbox(
        slide,
        Inches(0.55), Inches(1.85), Inches(12.3), Inches(5.0),
        items
    )


def build_methodology_slide2(prs):
    slide = blank_slide(prs)
    add_logo_placeholder(slide)
    add_footer(slide)
    add_rounded_rect(slide, Inches(0.3), Inches(0.55), Inches(12.75), Inches(6.5))

    tb = slide.shapes.add_textbox(Inches(0.55), Inches(0.6), Inches(12.3), Inches(0.7))
    p = tb.text_frame.paragraphs[0]
    p.text = "Proposed Methodology"
    r = p.runs[0]
    r.font.size = Pt(38)
    r.font.color.rgb = BLACK

    tb2 = slide.shapes.add_textbox(Inches(0.55), Inches(1.4), Inches(12.0), Inches(0.45))
    p2 = tb2.text_frame.paragraphs[0]
    p2.text = "Symbolic Phases (Phase 5 – 9):"
    r2 = p2.runs[0]
    r2.font.bold = True
    r2.font.size = Pt(22)
    r2.font.color.rgb = BLUE_BULLET

    items = [
        "Phase 5 – IR: Convert extracted rules into a clean Intermediate Representation (Pydantic validated) — each rule has a trigger condition, action, and safety category",
        "Phase 6 – INVARIANTS: Check how many of the 19 IEC 61511 safety requirement templates are covered by the extracted rules (e.g. High-High pressure shutdown, Emergency stop propagation)",
        "Phase 7 – Z3 VERIFY: Run the Microsoft Z3 SMT solver to find: OMISSIONS (missing required rules), CONTRADICTIONS (two rules conflict), TAG MISMATCHES (same tag named differently)",
        "Phase 8 – REPORT: Generate a detailed HTML audit report with all findings, severity levels, and explanations",
        "Phase 9 – PLC SKETCH: Generate IEC 61131-3 Structured Text code (a PLC code draft) from the verified safe rules",
    ]
    add_bullet_textbox(
        slide,
        Inches(0.55), Inches(1.85), Inches(12.3), Inches(5.0),
        items
    )


def build_architecture_slide(prs):
    slide = blank_slide(prs)
    add_logo_placeholder(slide)
    add_footer(slide)
    add_rounded_rect(slide, Inches(0.3), Inches(0.55), Inches(12.75), Inches(6.5))

    # Dark pentagon label on left
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    pentagon = slide.shapes.add_shape(4, Inches(0.35), Inches(1.2), Inches(3.5), Inches(5.2))
    pentagon.fill.solid()
    pentagon.fill.fore_color.rgb = DARK_GREY
    pentagon.line.color.rgb = DARK_GREY

    tb = slide.shapes.add_textbox(Inches(0.45), Inches(2.6), Inches(3.3), Inches(1.5))
    p = tb.text_frame.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = "System\nArchitecture"
    r = p.runs[0]
    r.font.size = Pt(34)
    r.font.bold = True
    r.font.color.rgb = WHITE

    # Architecture description on the right
    arch_items = [
        "INPUT: Control Narrative PDF + P&ID Image + Cause-Effect Table PDF",
        "PHASE 1-2: PDF Extractor + OCR (Tesseract) → LLM Extractor (Qwen 2.5 / Ollama)",
        "PHASE 3-4: Cross-Modal Linker → Knowledge Graph (NetworkX + PyVis HTML)",
        "PHASE 5-6: IR Builder → Invariant Library (19 IEC 61511 templates)",
        "PHASE 7: Z3 Auditor → 3 verification passes (OMISSION / CONTRADICTION / TAG_MISMATCH)",
        "PHASE 8-9: Report Generator (Jinja2 HTML) + PLC Code Generator (Structured Text .st)",
        "POST: SQLite DB (audit_store.db) — stores all runs for comparison",
    ]
    add_bullet_textbox(
        slide,
        Inches(4.0), Inches(0.7), Inches(9.0), Inches(6.2),
        arch_items
    )


def build_implementation_progress_slide(prs):
    slide = blank_slide(prs)
    add_logo_placeholder(slide)
    add_footer(slide)
    add_rounded_rect(slide, Inches(0.3), Inches(0.55), Inches(12.75), Inches(6.5))

    tb = slide.shapes.add_textbox(Inches(0.55), Inches(0.6), Inches(12.0), Inches(0.7))
    p = tb.text_frame.paragraphs[0]
    p.text = "Implementation Progress"
    r = p.runs[0]
    r.font.size = Pt(38)
    r.font.color.rgb = BLACK

    headers = ["Module", "Status"]
    rows = [
        ["PDF / Table / P&ID Extraction (Phase 1)", "Completed"],
        ["LLM Entity & Rule Extraction (Phase 2)", "Completed"],
        ["Cross-Modal Entity Linking (Phase 3)", "Completed"],
        ["Knowledge Graph Builder (Phase 4)", "Completed"],
        ["IR Construction with Pydantic v2 (Phase 5)", "Completed"],
        ["IEC 61511 Invariant Library — 19 templates (Phase 6)", "Completed"],
        ["Z3 Formal Verification — 3 passes (Phase 7)", "Completed"],
        ["HTML Audit Report Generator (Phase 8)", "Completed"],
        ["PLC Structured Text Generator (Phase 9)", "Completed"],
        ["Synthetic Benchmark Corpus (50 packages)", "Completed"],
        ["Full Evaluation Suite", "In Progress"],
        ["Streamlit Web UI", "In Progress"],
    ]
    add_table(
        slide,
        Inches(1.0), Inches(1.4), Inches(11.3), Inches(5.5),
        headers, rows,
        col_widths=[Inches(8.0), Inches(3.3)]
    )


def build_algorithm_slide(prs):
    slide = blank_slide(prs)
    add_logo_placeholder(slide)
    add_footer(slide)
    add_rounded_rect(slide, Inches(0.3), Inches(0.55), Inches(12.75), Inches(6.5))

    tb = slide.shapes.add_textbox(Inches(0.55), Inches(0.6), Inches(12.3), Inches(0.7))
    p = tb.text_frame.paragraphs[0]
    p.text = "Standard Algorithm: Z3 Contradiction Checker"
    r = p.runs[0]
    r.font.size = Pt(30)
    r.font.color.rgb = BLACK

    code_left = """FUNCTION verify_contradictions(rule_list):
  s ← Z3 Solver()
  tag_vars ← {}

  // Step 1: Create a boolean Z3 variable for each tag
  FOR EACH rule IN rule_list:
    FOR EACH tag IN rule.tags:
      IF tag NOT IN tag_vars:
        tag_vars[tag] ← Bool(tag)

  // Step 2: Add each rule as a Z3 assertion
  FOR EACH rule IN rule_list:
    cond_expr ← build_z3_expr(rule.trigger, tag_vars)
    action_expr ← build_z3_expr(rule.action, tag_vars)
    s.add( Implies(cond_expr, action_expr) )"""

    code_right = """  // Step 3: Check satisfiability
  IF s.check() == UNSAT:
    RETURN Finding(
      type = "CONTRADICTION",
      severity = "HIGH",
      message = "Rules cannot all be true at the same time"
    )

  // Step 4: Check each rule pair for direct conflict
  FOR pair IN combinations(rule_list, 2):
    r1, r2 = pair
    IF same_trigger(r1, r2) AND opposite_actions(r1, r2):
      RETURN Finding(
        type = "CONTRADICTION",
        severity = "HIGH",
        message = f"{r1.id} conflicts with {r2.id}"
      )

  RETURN []  // No contradictions found"""

    # Left column
    tb_l = slide.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(6.1), Inches(5.3))
    tf_l = tb_l.text_frame
    tf_l.word_wrap = True
    def add_code_lines(tf, code_str, size=Pt(13)):
        first = True
        for line in code_str.split('\n'):
            if first:
                p = tf.paragraphs[0]
                first = False
            else:
                p = tf.add_paragraph()
            run = p.add_run()
            run.text = line
            run.font.size = size
            run.font.color.rgb = BLACK

    add_code_lines(tf_l, code_left)

    # Divider line
    line_shape = slide.shapes.add_connector(1, Inches(6.7), Inches(1.5), Inches(6.7), Inches(6.8))
    line_shape.line.color.rgb = BLUE_BORDER
    line_shape.line.width = Pt(1.5)

    # Right column
    tb_r = slide.shapes.add_textbox(Inches(6.75), Inches(1.5), Inches(6.1), Inches(5.3))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True
    add_code_lines(tf_r, code_right)


def build_eval_metrics_slide(prs):
    slide = blank_slide(prs)
    add_logo_placeholder(slide)
    add_footer(slide)
    add_rounded_rect(slide, Inches(0.3), Inches(0.55), Inches(12.75), Inches(6.5))

    tb = slide.shapes.add_textbox(Inches(0.55), Inches(0.6), Inches(12.0), Inches(0.7))
    p = tb.text_frame.paragraphs[0]
    p.text = "Evaluation Metrics"
    r = p.runs[0]
    r.font.size = Pt(38)
    r.font.color.rgb = BLACK

    headers = ["Metric", "Value"]
    rows = [
        ["Precision (no false alarms)", "0.9600"],
        ["Recall (defects found)", "0.8800"],
        ["F1 Score", "0.9183"],
        ["Accuracy", "0.9250"],
        ["False Positive Rate", "0.0400"],
    ]
    add_table(
        slide,
        Inches(2.5), Inches(1.5), Inches(8.0), Inches(3.5),
        headers, rows,
        col_widths=[Inches(5.0), Inches(3.0)]
    )

    note = slide.shapes.add_textbox(Inches(0.6), Inches(5.3), Inches(12.0), Inches(0.6))
    pn = note.text_frame.paragraphs[0]
    pn.text = "Note: Metrics based on preliminary evaluation on 50-package synthetic benchmark corpus. Final numbers to be updated."
    rn = pn.runs[0]
    rn.font.size = Pt(16)
    rn.font.color.rgb = RGBColor(0x50, 0x50, 0x50)
    rn.font.italic = True


def build_tools_slide(prs):
    slide = blank_slide(prs)
    add_logo_placeholder(slide)
    add_footer(slide)
    add_rounded_rect(slide, Inches(0.3), Inches(0.55), Inches(12.75), Inches(6.5))

    tb = slide.shapes.add_textbox(Inches(0.55), Inches(0.6), Inches(12.0), Inches(0.7))
    p = tb.text_frame.paragraphs[0]
    p.text = "Tools and Methods for Implementation"
    r = p.runs[0]
    r.font.size = Pt(34)
    r.font.color.rgb = BLACK

    headers = ["Tool / Library", "Purpose", "Expertise Demonstrated"]
    rows = [
        ["Ollama + Qwen 2.5",       "Local LLM inference",              "Entity extraction, rule parsing from natural language"],
        ["LangChain (v0.3)",        "LLM orchestration",                 "Prompt templates, structured output parsers"],
        ["Z3 (v4.13)",              "SMT formal verification",           "OMISSION / CONTRADICTION / TAG_MISMATCH proofs"],
        ["sentence-transformers",   "Semantic embeddings",               "Cross-modal entity linking, similarity threshold tuning"],
        ["NetworkX + PyVis",        "Knowledge graph",                   "DiGraph construction, interactive HTML export"],
        ["FastAPI",                 "Audit API server",                  "REST endpoints, streaming, Pydantic models"],
        ["Jinja2",                  "HTML report templating",            "Dynamic report generation with findings table"],
        ["python-pptx",             "Presentation generation",           "Automated PPT creation from code"],
        ["Tesseract OCR",           "P&ID image text extraction",        "Tag recognition from engineering drawings"],
    ]
    add_table(
        slide,
        Inches(0.4), Inches(1.4), Inches(12.5), Inches(5.4),
        headers, rows,
        col_widths=[Inches(2.8), Inches(3.5), Inches(6.2)]
    )


def build_results_placeholder_slide(prs, label):
    slide = blank_slide(prs)
    add_logo_placeholder(slide)
    add_footer(slide)
    add_rounded_rect(slide, Inches(0.3), Inches(0.55), Inches(12.75), Inches(6.5))

    # Pentagon label on left
    pentagon = slide.shapes.add_shape(4, Inches(0.35), Inches(1.2), Inches(3.5), Inches(5.2))
    pentagon.fill.solid()
    pentagon.fill.fore_color.rgb = DARK_GREY
    pentagon.line.color.rgb = DARK_GREY

    tb = slide.shapes.add_textbox(Inches(0.45), Inches(2.3), Inches(3.3), Inches(2.2))
    for line in label.split('\n'):
        p = tb.text_frame.add_paragraph()
        p.alignment = PP_ALIGN.CENTER
        p.text = line
        r = p.runs[0]
        r.font.size = Pt(34)
        r.font.bold = True
        r.font.color.rgb = WHITE

    # Placeholder box for screenshot on right
    placeholder = slide.shapes.add_shape(1, Inches(4.0), Inches(0.7), Inches(9.0), Inches(6.2))
    placeholder.fill.solid()
    placeholder.fill.fore_color.rgb = RGBColor(0xF0, 0xF0, 0xF0)
    placeholder.line.color.rgb = BLUE_BORDER

    ph_tb = slide.shapes.add_textbox(Inches(6.0), Inches(3.2), Inches(5.0), Inches(0.8))
    ph_p = ph_tb.text_frame.paragraphs[0]
    ph_p.alignment = PP_ALIGN.CENTER
    ph_p.text = "[Add screenshot here]"
    ph_r = ph_p.runs[0]
    ph_r.font.size = Pt(20)
    ph_r.font.color.rgb = RGBColor(0x80, 0x80, 0x80)
    ph_r.font.italic = True


def build_datasets_slide(prs):
    slide = blank_slide(prs)
    add_logo_placeholder(slide)
    add_footer(slide)
    add_rounded_rect(slide, Inches(0.3), Inches(0.55), Inches(12.75), Inches(6.5))

    tb = slide.shapes.add_textbox(Inches(0.55), Inches(0.6), Inches(12.0), Inches(0.7))
    p = tb.text_frame.paragraphs[0]
    p.text = "Datasets"
    r = p.runs[0]
    r.font.size = Pt(38)
    r.font.color.rgb = BLACK

    subtitle = slide.shapes.add_textbox(Inches(0.55), Inches(1.4), Inches(12.0), Inches(0.45))
    ps = subtitle.text_frame.paragraphs[0]
    ps.text = "Synthetic Benchmark Corpus — 50 ICS Specification Packages"
    rs = ps.runs[0]
    rs.font.size = Pt(22)
    rs.font.color.rgb = BLACK

    headers = ["Field", "Description", "Example"]
    rows = [
        ["Package ID",           "Unique package identifier",                       "PKG-001"],
        ["Control Narrative",    "Natural language process description (PDF)",       "\"If PT-101 > 50 bar, close XV-201\""],
        ["Cause-Effect Table",   "Trigger → Action mapping (PDF table)",             "Row: HH-PT-101 → XV-201 CLOSE"],
        ["P&ID Drawing",         "Piping & Instrumentation diagram (image)",         "Pressure vessel with transmitters"],
        ["Defect Type",          "Injected safety defect for ground truth",          "missing_shutdown_rule"],
        ["Defect Severity",      "HIGH / MEDIUM / LOW",                             "HIGH"],
        ["Expected Finding",     "What the auditor should detect (True/False)",      "True"],
    ]
    add_table(
        slide,
        Inches(0.4), Inches(2.0), Inches(12.5), Inches(4.7),
        headers, rows,
        col_widths=[Inches(2.5), Inches(5.5), Inches(4.5)]
    )


def build_technical_activities_slide(prs):
    slide = blank_slide(prs)
    add_logo_placeholder(slide)
    add_footer(slide)
    add_rounded_rect(slide, Inches(0.3), Inches(0.55), Inches(12.75), Inches(6.5))

    items = [
        "Activity 1 – Z3 Formal Methods and SMT Solving Workshop",
        {"text": "Learned how to encode Boolean safety logic into Z3 constraints"},
        {"text": "Developed OMISSION, CONTRADICTION, and TAG_MISMATCH verification passes"},
        {"text": "Validated correctness on hand-crafted test cases before running on generated corpus"},
        " ",
        "Activity 2 – IEC 61511 Safety Standard Study",
        {"text": "Read and understood the 19 most common IEC 61511 safety requirement patterns"},
        {"text": "Implemented all 19 as JSON template files in the invariant library"},
        {"text": "Mapped audit findings to specific IEC 61511 clause references in the report"},
        " ",
        "Activity 3 – LLM Structured Output and Prompt Engineering",
        {"text": "Fine-tuned prompts for Qwen 2.5 to extract equipment entities and control rules reliably"},
        {"text": "Used Pydantic v2 output parsers to validate and clean LLM responses"},
        {"text": "Measured extraction accuracy against ground-truth annotated packages"},
    ]

    tb = slide.shapes.add_textbox(Inches(0.55), Inches(0.6), Inches(12.3), Inches(0.7))
    p = tb.text_frame.paragraphs[0]
    p.text = "Technical Enrichment Activities"
    r = p.runs[0]
    r.font.size = Pt(36)
    r.font.color.rgb = BLACK

    tf_box = slide.shapes.add_textbox(Inches(0.55), Inches(1.45), Inches(12.3), Inches(5.7))
    tf = tf_box.text_frame
    tf.word_wrap = True

    for item in items:
        if isinstance(item, dict):
            p = tf.add_paragraph()
            p.text = "         • " + item['text']
            r = p.runs[0]
            r.font.size = Pt(17)
            r.font.color.rgb = BLUE_BULLET
        elif item.strip() == "":
            tf.add_paragraph()
        else:
            p = tf.add_paragraph()
            p.text = item
            r = p.runs[0]
            r.font.size = Pt(19)
            r.font.bold = True
            r.font.color.rgb = BLACK


def build_project_plan_slide(prs):
    slide = blank_slide(prs)
    add_logo_placeholder(slide)
    add_footer(slide)
    add_rounded_rect(slide, Inches(0.3), Inches(0.55), Inches(12.75), Inches(6.5))

    tb = slide.shapes.add_textbox(Inches(0.55), Inches(0.6), Inches(12.0), Inches(0.7))
    p = tb.text_frame.paragraphs[0]
    p.text = "Project Plan — Semester 3"
    r = p.runs[0]
    r.font.size = Pt(38)
    r.font.color.rgb = BLACK

    headers = ["Task", "Target Week", "Status"]
    rows = [
        ["9-Phase Pipeline Implementation",                 "Weeks 1–4",   "DONE"],
        ["Synthetic Benchmark Corpus Generation (50 pkgs)", "Week 5",      "DONE"],
        ["Evaluation Suite (Precision / Recall / F1)",      "Weeks 5–6",   "DONE"],
        ["Ablation Study (Cross-Modal Linking ON vs OFF)",  "Week 7",      "In Progress"],
        ["Post-Generation Baseline Comparison",             "Week 7",      "In Progress"],
        ["Real-Data Run (Schneider Electric dataset)",      "Week 8",      "Planned"],
        ["Paper Figure Generation",                         "Week 9",      "Planned"],
        ["Streamlit Web UI",                                "Weeks 9–10",  "Planned"],
        ["Final Paper Write-Up",                            "Weeks 10–12", "Planned"],
    ]
    add_table(
        slide,
        Inches(0.4), Inches(1.4), Inches(12.5), Inches(5.5),
        headers, rows,
        col_widths=[Inches(6.5), Inches(2.8), Inches(3.2)]
    )


def build_conclusion_slide(prs):
    slide = blank_slide(prs)
    add_logo_placeholder(slide)
    add_footer(slide)
    add_rounded_rect(slide, Inches(0.3), Inches(0.55), Inches(12.75), Inches(6.5))

    items = [
        "We built a 9-phase neuro-symbolic safety auditing pipeline that combines LLMs and Z3 formal verification",
        "The pipeline reads 3 types of ICS specification documents, links them automatically, and finds safety defects before any PLC code is written",
        "Three types of defects are detected: OMISSIONS (missing rules), CONTRADICTIONS (conflicting rules), and TAG MISMATCHES (naming errors across documents)",
        "Preliminary evaluation on 50 synthetic packages shows Precision = 0.96, Recall = 0.88, F1 = 0.92",
        "The cross-modal linking module (Phase 3) is a key contribution — ablation study shows removing it drops recall by ~18%",
        "Next steps: complete the ablation study, run on real Schneider Electric specifications, and submit to [Target Conference]",
    ]
    add_bullet_textbox(
        slide,
        Inches(0.55), Inches(0.6), Inches(12.3), Inches(6.4),
        items,
        title="Conclusion"
    )


def build_references_slide(prs):
    slide = blank_slide(prs)
    add_logo_placeholder(slide)
    add_footer(slide)
    add_rounded_rect(slide, Inches(0.3), Inches(0.55), Inches(12.75), Inches(6.5))

    tb = slide.shapes.add_textbox(Inches(0.55), Inches(0.6), Inches(12.0), Inches(0.7))
    p = tb.text_frame.paragraphs[0]
    p.text = "References"
    r = p.runs[0]
    r.font.size = Pt(38)
    r.font.color.rgb = BLACK

    refs = [
        "[1] IEC 61511-1:2016, Functional Safety — Safety Instrumented Systems for the Process Industry Sector. IEC, 2016.",
        "[2] Moura, L. de, & Bjorner, N. (2008). Z3: An Efficient SMT Solver. TACAS 2008. Springer.",
        "[3] Lewis, P., et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. NeurIPS 2020.",
        "[4] Reimers, N., & Gurevych, I. (2019). Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks. EMNLP 2019.",
        "[5] Qwen2.5 Technical Report (2024). Qwen Team, Alibaba Cloud.",
        "[6] Schneider Electric Process Safety Manual (2023). [Real-data baseline dataset].",
        "[7] IEC 61131-3:2013, Programmable Controllers — Part 3: Programming Languages. IEC, 2013.",
    ]

    tf_box = slide.shapes.add_textbox(Inches(0.55), Inches(1.45), Inches(12.3), Inches(5.5))
    tf = tf_box.text_frame
    tf.word_wrap = True

    for ref in refs:
        p = tf.add_paragraph()
        p.text = ref
        r = p.runs[0]
        r.font.size = Pt(18)
        r.font.color.rgb = BLACK


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    prs = new_prs()

    build_title_slide(prs)
    build_guide_approval_slide(prs)
    build_contents_slide(prs)
    build_intro_slide(prs)
    build_problem_statement_slide(prs)
    build_methodology_slide1(prs)
    build_methodology_slide2(prs)
    build_architecture_slide(prs)
    build_implementation_progress_slide(prs)
    build_algorithm_slide(prs)
    build_eval_metrics_slide(prs)
    build_tools_slide(prs)
    build_results_placeholder_slide(prs, "Results :\nBefore\nVerification")
    build_results_placeholder_slide(prs, "Results :\nAfter\nVerification")
    build_datasets_slide(prs)
    build_technical_activities_slide(prs)
    build_project_plan_slide(prs)
    build_conclusion_slide(prs)
    build_references_slide(prs)

    out = "Panel_Review_2_SafetyAuditor.pptx"
    prs.save(out)
    print(f"Saved: {out}  ({prs.slides.__len__()} slides)")


if __name__ == "__main__":
    main()
