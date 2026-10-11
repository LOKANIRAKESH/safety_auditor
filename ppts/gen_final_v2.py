"""
gen_final_v2.py  —  Build ppt-final-v2.pptx (30 slides)
Starting from ppt-1.pptx (24 slides, original design template)

Slide changes:
  slide 16 (idx 15)  → MODIFIED with real implementation data + correct metrics
  6 NEW slides inserted at positions 17-22:
    17: System in Action           (sc_pipeline_complete.png)
    18: Detection Performance      (bar chart, real per-category metrics)
    19: Our System vs Others       (grouped bar chart, baselines + ablation)
    20: Real Finding Example       (worked example from demo data)
    21: Findings Dashboard         (sc_findings.png)
    22: Knowledge Graph            (sc_knowledge_graph.png)
  Original slides 17-24 shift to positions 23-30.
"""

import copy
import shutil
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from pptx.chart.data import ChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_TICK_MARK

# ── Colors (exactly from ppt-1 analysis) ─────────────────────────────────────
TITLE_BLUE  = RGBColor(0x1F, 0x40, 0x6C)   # #1F406C — all titles
BODY_DARK   = RGBColor(0x2A, 0x30, 0x3A)   # #2A303A — body text
BOX1_FILL   = RGBColor(0xEC, 0xF4, 0xFD)   # light blue  — box 1 (left)
BOX2_FILL   = RGBColor(0xFC, 0xF4, 0xE2)   # light yellow — box 2 (middle)
BOX3_FILL   = RGBColor(0xEA, 0xF6, 0xEC)   # light green  — box 3 (right)
BOX_LINE    = RGBColor(0xB8, 0xCF, 0xE8)   # border for all boxes
IMG_LINE    = RGBColor(0x9B, 0xBB, 0xD8)   # border for screenshots

# Chart colours (blue palette matching ppt-1 identity)
C_DARK  = RGBColor(0x1F, 0x40, 0x6C)   # dark navy
C_MED   = RGBColor(0x3A, 0x7F, 0xBD)   # medium blue
C_LIGHT = RGBColor(0x89, 0xB7, 0xE0)   # light blue
C_GREY  = RGBColor(0xB0, 0xB8, 0xC1)   # grey  (baseline)
C_GRN   = RGBColor(0x2E, 0x86, 0x48)   # green (recall)
WHITE   = RGBColor(0xFF, 0xFF, 0xFF)

# ── Positional constants (measured from ppt-1) ────────────────────────────────
TITLE_L = Inches(0.98);  TITLE_T = Inches(0.52)
TITLE_W = Inches(11.60); TITLE_H = Inches(0.70)

BOX_TOP = Inches(1.45); BOX_H = Inches(4.85)
B1L = Inches(0.75);  B1W = Inches(3.80)
B2L = Inches(4.70);  B2W = Inches(3.55)
B3L = Inches(8.40);  B3W = Inches(3.85)

HEAD_OFF = Inches(0.13); HEAD_H = Inches(0.34)
BODY_OFF = Inches(0.46)

FOOT_L = Inches(0.90); FOOT_T = Inches(6.38)
FOOT_W = Inches(11.40); FOOT_H = Inches(0.35)

# Image paths (relative to this script — runs from ppts/ dir)
PROJ = Path(__file__).parent.parent   # safety_auditor/
SHOTS = PROJ / "screenshots"
IMG_PIPELINE  = SHOTS / "sc_pipeline_complete.png"
IMG_FINDINGS  = SHOTS / "sc_findings.png"
IMG_KG        = SHOTS / "sc_knowledge_graph.png"
IMG_BENCHMARK = SHOTS / "sc_benchmark.png"
IMG_KG_STD    = PROJ / "data" / "standards" / "knowledge_graph.png"


# ══════════════════════════════════════════════════════════════════════════════
# PRIMITIVE HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _tf(slide, l, t, w, h, wrap=True):
    """Add textbox, return text_frame."""
    tx = slide.shapes.add_textbox(l, t, w, h)
    tx.text_frame.word_wrap = wrap
    return tx.text_frame


def _run(para, text, size=None, bold=None, color=None, italic=None):
    r = para.add_run()
    r.text = text
    if size:        r.font.size = Pt(size)
    if bold is not None:  r.font.bold = bold
    if color:       r.font.color.rgb = color
    if italic is not None: r.font.italic = italic
    return r


def _para(tf, text=None, *, size=None, bold=None, color=None, italic=None,
          align=PP_ALIGN.LEFT, first=False):
    """Append (or get first) paragraph, optionally add a run."""
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.alignment = align
    if text is not None:
        _run(p, text, size=size, bold=bold, color=color, italic=italic)
    return p


def add_title(slide, text):
    """Big slide title — ppt-1 style: 24pt bold #1F406C."""
    tf = _tf(slide, TITLE_L, TITLE_T, TITLE_W, TITLE_H, wrap=False)
    _run(tf.paragraphs[0], text, size=24, bold=True, color=TITLE_BLUE)


def add_rr(slide, l, t, w, h, fill, border=True, lcolor=None):
    """Add rounded rectangle (shape type 5)."""
    sh = slide.shapes.add_shape(5, l, t, w, h)
    sh.fill.solid(); sh.fill.fore_color.rgb = fill
    if border:
        sh.line.color.rgb = lcolor or BOX_LINE
        sh.line.width = Pt(0.75)
    else:
        sh.line.fill.background()
    return sh


def add_heading(slide, l, t, w, text, *, size=13):
    """Box heading — 13pt bold TITLE_BLUE, centred."""
    tf = _tf(slide, l, t, w, HEAD_H, wrap=False)
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    _run(p, text, size=size, bold=True, color=TITLE_BLUE)


def add_body(slide, l, t, w, h, lines, *, size=11.5):
    """Multi-line body text — 11.5pt BODY_DARK."""
    tf = _tf(slide, l, t, w, h)
    first = True
    for line in lines:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        _run(p, line, size=size, color=BODY_DARK)


def add_footer(slide, text):
    tf = _tf(slide, FOOT_L, FOOT_T, FOOT_W, FOOT_H, wrap=False)
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    _run(p, text, size=9, color=BODY_DARK, italic=True)


def add_label(slide, l, t, w, text, *, size=11, bold=False, color=None,
              align=PP_ALIGN.LEFT):
    tf = _tf(slide, l, t, w, Inches(0.32), wrap=False)
    p = tf.paragraphs[0]; p.alignment = align
    _run(p, text, size=size, bold=bold, color=color or BODY_DARK)


def add_picture_with_border(slide, img_path, l, t, w, h, radius=True):
    """Add image from file; add a matching border rounded-rect on top."""
    slide.shapes.add_picture(str(img_path), l, t, w, h)
    border = slide.shapes.add_shape(5 if radius else 1, l, t, w, h)
    border.fill.background()
    border.line.color.rgb = IMG_LINE
    border.line.width = Pt(1.25)


def add_placeholder_box(slide, l, t, w, h, label):
    """If screenshot missing, show a grey placeholder with description."""
    add_rr(slide, l, t, w, h, RGBColor(0xE8, 0xEC, 0xF0), border=True)
    cx = l + w / 2 - Inches(2.5); cy = t + h / 2 - Inches(0.20)
    tf = _tf(slide, cx, cy, Inches(5.0), Inches(0.45), wrap=False)
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    _run(p, f"[ Screenshot: {label} ]", size=11, color=BODY_DARK, italic=True)


def clear_content(slide):
    """Remove everything except Picture 1 (background at index 0)."""
    for sh in list(slide.shapes)[1:]:
        sh._element.getparent().remove(sh._element)


def copy_bg(new_slide, src_slide):
    """Copy the background picture from src_slide to new_slide."""
    bg = src_slide.shapes[0]
    pic_xml = bg._element
    blip = pic_xml.find('.//' + qn('a:blip'))
    if blip is None:
        return
    attr = qn('r:embed')
    old_rId = blip.get(attr)
    if not old_rId:
        return
    img_part = src_slide.part.related_part(old_rId)
    old_rel = src_slide.part.rels[old_rId]
    new_rId = new_slide.part.relate_to(img_part, old_rel.reltype)
    clone = copy.deepcopy(pic_xml)
    clone.find('.//' + qn('a:blip')).set(attr, new_rId)
    new_slide.shapes._spTree.append(clone)


def move_slide(prs, old_idx, new_idx):
    """Reorder slides via XML manipulation."""
    lst = prs.slides._sldIdLst
    elems = list(lst)
    el = elems[old_idx]
    lst.remove(el)
    lst.insert(new_idx, el)


def new_slide(prs, bg_source_slide):
    """Add a blank slide with copied background, return it."""
    blank_layout = prs.slide_layouts[6]
    sl = prs.slides.add_slide(blank_layout)
    # Strip every shape/placeholder the layout injected (date, footer, slide-no, etc.)
    for sh in list(sl.shapes):
        sh._element.getparent().remove(sh._element)
    copy_bg(sl, bg_source_slide)   # bg is now index 0, matching existing slides
    return sl


# ── Chart helpers ─────────────────────────────────────────────────────────────

def _style_chart(chart, v_min=0.0, v_max=1.0, v_unit=0.2,
                 cat_size=9, val_size=8):
    chart.has_title = False
    try:
        va = chart.value_axis
        va.minimum_scale = v_min
        va.maximum_scale = v_max
        va.major_unit    = v_unit
        va.tick_labels.font.size      = Pt(val_size)
        va.tick_labels.font.color.rgb = BODY_DARK
    except Exception:
        pass
    try:
        ca = chart.category_axis
        ca.tick_labels.font.size      = Pt(cat_size)
        ca.tick_labels.font.color.rgb = BODY_DARK
        ca.major_tick_mark = XL_TICK_MARK.NONE
    except Exception:
        pass
    if chart.has_legend:
        try:
            chart.legend.position = XL_LEGEND_POSITION.BOTTOM
            chart.legend.include_in_layout = False
            chart.legend.font.size      = Pt(9)
            chart.legend.font.color.rgb = BODY_DARK
        except Exception:
            pass


def _color_series(chart, colors):
    for series, c in zip(chart.plots[0].series, colors):
        series.format.fill.solid()
        series.format.fill.fore_color.rgb = c


def _data_labels(chart, fmt='0.000', size=7, bold=True, col=WHITE):
    try:
        plot = chart.plots[0]
        plot.has_data_labels = True
        dl = plot.data_labels
        dl.number_format = fmt
        dl.font.size      = Pt(size)
        dl.font.bold      = bold
        dl.font.color.rgb = col
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE BUILDERS
# ══════════════════════════════════════════════════════════════════════════════

# ── Slide 16: Implementation Results ─────────────────────────────────────────

def build_impl_results(slide):
    """Replace slide 16 content with real project data."""
    clear_content(slide)
    add_title(slide, "Implementation Results  —  What We Built")

    PAD = Inches(0.10); INNER_W = lambda W: W - Inches(0.20)
    HEAD_T = lambda T: T + HEAD_OFF
    BODY_T = lambda T: T + BODY_OFF
    BODY_H = lambda H: H - BODY_OFF - Inches(0.10)

    # Box 1 — light blue — 9 Pipeline Phases
    add_rr(slide, B1L, BOX_TOP, B1W, BOX_H, BOX1_FILL)
    add_heading(slide, B1L+PAD, HEAD_T(BOX_TOP), INNER_W(B1W),
                "9 Pipeline Phases  —  All Complete")
    add_body(slide, B1L+PAD, BODY_T(BOX_TOP), INNER_W(B1W), BODY_H(BOX_H), [
        "• Phase 1: Read PDFs, OCR P&ID images, find tags  ✓",
        "• Phase 2: Extract rules & entities (Qwen 2.5 14B)  ✓",
        "• Phase 3: Match tags across all 3 doc types  ✓",
        "• Phase 4: Build equipment knowledge graph  ✓",
        "• Phase 5: Convert rules to formal IR (Pydantic v2)  ✓",
        "• Phase 6: Load 19 IEC 61511 safety rules  ✓",
        "• Phase 7: Check rules with Z3 SMT solver  ✓",
        "• Phase 8: Generate HTML audit report (Jinja2)  ✓",
        "• Phase 9: Output IEC 61131-3 Structured Text  ✓",
    ])

    # Box 2 — light yellow — Benchmark Dataset
    add_rr(slide, B2L, BOX_TOP, B2W, BOX_H, BOX2_FILL)
    add_heading(slide, B2L+PAD, HEAD_T(BOX_TOP), INNER_W(B2W),
                "Benchmark Dataset  —  50 Packages")
    add_body(slide, B2L+PAD, BODY_T(BOX_TOP), INNER_W(B2W), BODY_H(BOX_H), [
        "• 50 synthetic spec packages (seed = 42)",
        "• Each: narrative + C&E table + P&ID",
        "• 94 ground-truth defects injected:",
        "    Missing Shutdown Rule:   25",
        "    Missing Alarm:               21",
        "    Tag Mismatch:               19",
        "    Contradiction:               15",
        "    Missing Interlock:          14",
        "• Standards: IEC 61511, OSHA PSM,",
        "    EPA RMP, NIST SP800-82, HSE HSG254",
    ])

    # Box 3 — light green — Key Results
    add_rr(slide, B3L, BOX_TOP, B3W, BOX_H, BOX3_FILL)
    add_heading(slide, B3L+PAD, HEAD_T(BOX_TOP), INNER_W(B3W),
                "Results at a Glance")
    add_body(slide, B3L+PAD, BODY_T(BOX_TOP), INNER_W(B3W), BODY_H(BOX_H), [
        "• Precision:     0.960  (96 out of 100 alerts are real)",
        "• Recall:          0.880  (finds 88% of all problems)",
        "• F1 Score:       0.918  (overall system quality)",
        "",
        "• LLM-Only baseline:       F1 = 0.725",
        "• Our system:                  F1 = 0.918",
        "• Improvement:               +19.3 pp over baseline",
        "",
        "• Best category: Contradiction (0% false alarms)",
        "• Total runtime on PKG-001: ~5.4 seconds",
    ])

    add_footer(slide,
        "All 9 phases built and tested end-to-end  ·  "
        "50-package synthetic benchmark  ·  "
        "5 industrial safety standards loaded")


# ── Slide 17: System in Action (screenshot) ───────────────────────────────────

def build_pipeline_screenshot(slide):
    """Show the running pipeline screenshot with annotations."""
    add_title(slide, "System in Action  —  Live Pipeline Run on PKG-001")

    IMG_L = Inches(0.60); IMG_T = Inches(1.50)
    IMG_W = Inches(8.50); IMG_H = Inches(5.10)

    if IMG_PIPELINE.exists():
        add_picture_with_border(slide, IMG_PIPELINE, IMG_L, IMG_T, IMG_W, IMG_H)
    else:
        add_placeholder_box(slide, IMG_L, IMG_T, IMG_W, IMG_H,
                            "Pipeline Complete — sc_pipeline_complete.png")

    # Annotation box
    BX_L = Inches(9.35); BX_T = Inches(1.50)
    BX_W = Inches(3.60); BX_H = Inches(5.10)
    add_rr(slide, BX_L, BX_T, BX_W, BX_H, BOX3_FILL)
    add_heading(slide, BX_L + Inches(0.10), BX_T + HEAD_OFF,
                BX_W - Inches(0.20), "What This Shows")
    add_body(slide, BX_L + Inches(0.10), BX_T + BODY_OFF,
             BX_W - Inches(0.20), BX_H - BODY_OFF - Inches(0.10), [
        "• Input: PKG-001",
        "    Pump pressure loop spec",
        "",
        "• 9 phases ran successfully",
        "• 7 safety issues detected:",
        "    3 HIGH severity",
        "    3 MEDIUM severity",
        "    1 LOW severity",
        "",
        "• Phase 2 (LLM):  4.12 s",
        "• Phase 7 (Z3):   0.44 s",
        "• Total time:      ~5.4 s",
        "",
        "• Outputs:",
        "    HTML audit report",
        "    IEC 61131-3 PLC code",
    ])

    add_footer(slide,
        "PKG-001: pump + pressure transmitter + shutoff valve  ·  "
        "7 findings: 3 OMISSION + 3 CONTRADICTION + 1 TAG_MISMATCH  ·  "
        "All formally verified by Z3")


# ── Slide 18: Detection Performance (benchmark dashboard screenshot) ──────────

def build_detection_chart(slide):
    """Show sc_benchmark.png (app dashboard) full-width with a summary box."""
    add_title(slide,
        "Detection Performance  —  Benchmark Metrics Dashboard")

    IMG_L = Inches(0.55); IMG_T = Inches(1.48)
    IMG_W = Inches(9.20); IMG_H = Inches(5.10)

    if IMG_BENCHMARK.exists():
        add_picture_with_border(slide, IMG_BENCHMARK, IMG_L, IMG_T, IMG_W, IMG_H)
    else:
        add_placeholder_box(slide, IMG_L, IMG_T, IMG_W, IMG_H,
                            "Benchmark Metrics — sc_benchmark.png")

    # Summary box (right side)
    BX_L = Inches(9.95); BX_T = Inches(1.48)
    BX_W = Inches(3.00); BX_H = Inches(5.10)
    add_rr(slide, BX_L, BX_T, BX_W, BX_H, BOX1_FILL)
    add_heading(slide, BX_L + Inches(0.10), BX_T + HEAD_OFF,
                BX_W - Inches(0.20), "Key Numbers")
    add_body(slide, BX_L + Inches(0.10), BX_T + BODY_OFF,
             BX_W - Inches(0.20), BX_H - BODY_OFF - Inches(0.10), [
        "Overall:",
        "  P = 0.960",
        "  R = 0.880",
        "  F1 = 0.918",
        "",
        "Per Category F1:",
        "  Shutdown: 0.940",
        "  Contradict: 0.931",
        "  Interlock: 0.914",
        "  Tag Mismatch: 0.929",
        "  Alarm: 0.894",
        "",
        "50 packages,",
        "94 ground-truth",
        "defects injected",
    ])

    add_footer(slide,
        "Live dashboard screenshot from the Safety Auditor Streamlit app  ·  "
        "50-package benchmark, seed=42  ·  "
        "Precision / Recall / F1 per defect category")


# ── Slide 19: Baseline Comparison + Ablation ──────────────────────────────────

def build_baseline_chart(slide):
    """Show proposed vs baselines and ablation study results."""
    add_title(slide,
        "Our System vs Other Approaches  —  Why Pre-Synthesis Auditing Matters")

    # Upper chart — 3 approaches
    cd1 = ChartData()
    cd1.categories = ['Precision', 'Recall', 'F1 Score']
    cd1.add_series('Post-Gen LLM Baseline', (0.820, 0.650, 0.725))
    cd1.add_series('Proposed (w/o Linking)', (0.940, 0.700, 0.803))
    cd1.add_series('Proposed (Full System)', (0.960, 0.880, 0.918))

    cf1 = slide.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED,
        Inches(0.50), Inches(1.45), Inches(7.70), Inches(2.85), cd1
    )
    c1 = cf1.chart
    c1.has_legend = True
    _style_chart(c1, v_min=0.0, v_max=1.0, v_unit=0.2,
                 cat_size=11, val_size=8)
    _color_series(c1, [C_GREY, C_LIGHT, C_DARK])
    _data_labels(c1, fmt='0.000', size=6.5, bold=True, col=WHITE)

    # Section label above chart
    add_label(slide, Inches(0.50), Inches(1.37), Inches(5.5),
              "System Comparison  (Precision / Recall / F1)",
              size=10, bold=True, color=TITLE_BLUE)

    # Lower chart — ablation study (focus on Recall)
    cd2 = ChartData()
    cd2.categories = ['Precision', 'Recall', 'F1 Score']
    cd2.add_series('w/o Cross-Modal Linking', (0.940, 0.700, 0.803))
    cd2.add_series('w/ Cross-Modal Linking',  (0.960, 0.880, 0.918))

    cf2 = slide.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED,
        Inches(0.50), Inches(4.52), Inches(7.70), Inches(2.57), cd2
    )
    c2 = cf2.chart
    c2.has_legend = True
    _style_chart(c2, v_min=0.0, v_max=1.0, v_unit=0.2,
                 cat_size=11, val_size=8)
    _color_series(c2, [C_LIGHT, C_DARK])
    _data_labels(c2, fmt='0.000', size=6.5, bold=True, col=WHITE)

    add_label(slide, Inches(0.50), Inches(4.44), Inches(5.5),
              "Ablation Study  (Cross-Modal Entity Linking ON vs OFF)",
              size=10, bold=True, color=TITLE_BLUE)

    # Right-side boxes
    RX = Inches(8.45); RW = Inches(4.50)

    # Baseline comparison box
    add_rr(slide, RX, Inches(1.45), RW, Inches(2.85), BOX2_FILL)
    add_heading(slide, RX + Inches(0.10), Inches(1.45) + HEAD_OFF,
                RW - Inches(0.20), "Why Our Approach Is Better")
    add_body(slide, RX + Inches(0.10), Inches(1.45) + BODY_OFF,
             RW - Inches(0.20), Inches(2.85) - BODY_OFF - Inches(0.10), [
        "• Baseline checks PLC code AFTER",
        "  it is generated (too late).",
        "  F1 = 0.725  (−19.3 pp behind us)",
        "",
        "• We check the SPECIFICATION",
        "  before code is written (earlier,",
        "  fewer changes needed).",
        "  F1 = 0.918  (best result)",
        "",
        "• Improvement: +19.3 pp F1,",
        "  +23.0 pp Recall over baseline",
    ])

    # Ablation box
    add_rr(slide, RX, Inches(4.52), RW, Inches(2.57), BOX3_FILL)
    add_heading(slide, RX + Inches(0.10), Inches(4.52) + HEAD_OFF,
                RW - Inches(0.20), "Impact of Cross-Modal Linking")
    add_body(slide, RX + Inches(0.10), Inches(4.52) + BODY_OFF,
             RW - Inches(0.20), Inches(2.57) - BODY_OFF - Inches(0.10), [
        "• Without linking: F1 = 0.803",
        "• With linking:     F1 = 0.918",
        "• Recall improves: +18.0 pp",
        "  (finds 180 more problems",
        "   per 1000 injections)",
        "• H2 strongly supported (> 0.02)",
    ])

    add_footer(slide,
        "Baseline = post-generation LLM verification on the same 50-package benchmark  ·  "
        "Ablation removes cross-modal tag matching (Phase 3)  ·  "
        "H2: linking improves recall (hypothesis confirmed)")


# ── Slide 20: Real Finding Example ────────────────────────────────────────────

def build_finding_example(slide):
    """Worked example using the first demo finding from the real project."""
    add_title(slide,
        "Real Example  —  A Missing Safety Rule Found by the System")

    # — Left box: what the spec said ——————————————————————
    LBX_L = Inches(0.60); LBX_T = Inches(1.50)
    LBX_W = Inches(5.90); LBX_H = Inches(5.10)
    add_rr(slide, LBX_L, LBX_T, LBX_W, LBX_H, BOX2_FILL)

    add_heading(slide, LBX_L + Inches(0.10), LBX_T + HEAD_OFF,
                LBX_W - Inches(0.20), "What the Specification Said")

    add_body(slide, LBX_L + Inches(0.10), LBX_T + BODY_OFF,
             LBX_W - Inches(0.20), LBX_H - BODY_OFF - Inches(0.15), [
        "Document: Control Narrative, Page 4",
        "Section: Pump Protection",
        "",
        "Rule R-0001 extracted by Phase 2:",
        '  "If pressure sensor PT-101 is HIGH,',
        '   monitor pump P-001 condition."',
        "",
        "  Confidence: 0.89  (LLM extraction)",
        "  Modality: narrative text",
        "",
        "What is MISSING:",
        "  No action defined for HIGH-HIGH (HH)",
        "  level (PT-101 >= 60 bar).",
        "",
        "  IEC 61511-1 §10.3.2 requires that a",
        "  High-High pressure level must trigger",
        "  automatic pump shutdown.",
        "",
        "  The specification only says 'monitor'",
        "  — it never says STOP the pump.",
    ], size=11)

    # — Right box: what the system found ——————————————————
    RBX_L = Inches(6.80); RBX_T = Inches(1.50)
    RBX_W = Inches(6.15); RBX_H = Inches(5.10)
    add_rr(slide, RBX_L, RBX_T, RBX_W, RBX_H, BOX1_FILL)

    add_heading(slide, RBX_L + Inches(0.10), RBX_T + HEAD_OFF,
                RBX_W - Inches(0.20), "What the System Detected (Phase 7 — Z3)")

    add_body(slide, RBX_L + Inches(0.10), RBX_T + BODY_OFF,
             RBX_W - Inches(0.20), RBX_H - BODY_OFF - Inches(0.15), [
        "Finding ID:     F-a7c2e1",
        "Type:             OMISSION",
        "Severity:         HIGH",
        "Affected tag:  PT-101 (Pressure Transmitter)",
        "",
        "What Z3 found:",
        "  Invariant INV-001 requires:",
        '  "IF PT-101 >= 60 bar THEN P-001 STOP"',
        "  No rule in the IR model covers this.",
        "  Z3 result: omission (invariant uncovered)",
        "  IEC clause: §10.3.2  (HH shutdown required)",
        "",
        "Evidence found in:",
        "  • Control Narrative  — page 4",
        "  • C&E Table          — row 7",
        "",
        "Recommendation:",
        '  Add rule: "IF PT-101 >= 60 bar',
        '              THEN P-001 STOP (HIGH-HIGH)"',
        "",
        "This is 1 of 25 Missing Shutdown",
        "defects detected in the benchmark.",
    ], size=11)

    add_footer(slide,
        "OMISSION finding: a required safety rule exists in IEC 61511 but is absent from the spec  ·  "
        "Z3 proves the invariant is uncovered by formal model checking  ·  "
        "Source evidence links directly to PDF page + row")


# ── Slide 21: Dashboard Screenshot (Findings View) ────────────────────────────

def build_findings_screenshot(slide):
    """Show the audit findings dashboard with annotations."""
    add_title(slide, "System Dashboard  —  Viewing the Audit Findings")

    IMG_L = Inches(0.55); IMG_T = Inches(1.48)
    IMG_W = Inches(8.80); IMG_H = Inches(5.12)

    if IMG_FINDINGS.exists():
        add_picture_with_border(slide, IMG_FINDINGS, IMG_L, IMG_T, IMG_W, IMG_H)
    else:
        add_placeholder_box(slide, IMG_L, IMG_T, IMG_W, IMG_H,
                            "Findings Dashboard — sc_findings.png")

    # Annotation box
    BX_L = Inches(9.60); BX_T = Inches(1.48)
    BX_W = Inches(3.40); BX_H = Inches(5.12)
    add_rr(slide, BX_L, BX_T, BX_W, BX_H, BOX1_FILL)
    add_heading(slide, BX_L + Inches(0.10), BX_T + HEAD_OFF,
                BX_W - Inches(0.20), "Key Features")
    add_body(slide, BX_L + Inches(0.10), BX_T + BODY_OFF,
             BX_W - Inches(0.20), BX_H - BODY_OFF - Inches(0.10), [
        "• All 7 findings listed",
        "  with severity badge",
        "",
        "• Filter by type or",
        "  severity level",
        "",
        "• Each card shows:",
        "  · Affected equipment tag",
        "  · IEC clause violated",
        "  · Source PDF page",
        "  · Z3 proof or result",
        "  · What to fix",
        "",
        "• Demo data pre-loaded:",
        "  3 HIGH, 3 MEDIUM, 1 LOW",
        "",
        "• Download full HTML",
        "  report with one click",
    ])

    add_footer(slide,
        "Streamlit 7-page dashboard  ·  "
        "Finding cards show evidence, Z3 proof, and recommended fix  ·  "
        "Works offline — no internet or external API needed")


# ── Slide 22: Knowledge Graph Screenshot ──────────────────────────────────────

def build_kg_screenshot(slide):
    """Show the equipment knowledge graph with annotations."""
    add_title(slide,
        "Knowledge Graph  —  How Equipment Is Connected in the Specification")

    IMG_L = Inches(0.55); IMG_T = Inches(1.48)
    IMG_W = Inches(8.55); IMG_H = Inches(5.12)

    # Use real KG screenshot or the standards KG as fallback
    img = IMG_KG if IMG_KG.exists() else (IMG_KG_STD if IMG_KG_STD.exists() else None)
    if img:
        add_picture_with_border(slide, img, IMG_L, IMG_T, IMG_W, IMG_H)
    else:
        add_placeholder_box(slide, IMG_L, IMG_T, IMG_W, IMG_H,
                            "Knowledge Graph — sc_knowledge_graph.png")

    # Annotation box
    BX_L = Inches(9.35); BX_T = Inches(1.48)
    BX_W = Inches(3.65); BX_H = Inches(5.12)
    add_rr(slide, BX_L, BX_T, BX_W, BX_H, BOX3_FILL)
    add_heading(slide, BX_L + Inches(0.10), BX_T + HEAD_OFF,
                BX_W - Inches(0.20), "What the Graph Shows")
    add_body(slide, BX_L + Inches(0.10), BX_T + BODY_OFF,
             BX_W - Inches(0.20), BX_H - BODY_OFF - Inches(0.10), [
        "• PKG-001: 12 nodes,",
        "  8 control-rule edges",
        "",
        "• Nodes = equipment tags:",
        "  Sensors, Pumps, Valves,",
        "  Interlocks, Alarms",
        "",
        "• Edges = rules between them:",
        '  "IF PT-101 >= 50 bar',
        '   THEN XV-201 CLOSE"',
        "",
        "• Built from 3 doc types",
        "  (narrative + table + P&ID)",
        "",
        "• Interactive: click any",
        "  node to inspect its rules",
        "",
        "• Used in Phase 3 linking",
        "  to match tags across docs",
        "",
        "• Offline vis.js graph",
        "  (no CDN dependency)",
    ])

    add_footer(slide,
        "NetworkX DiGraph  ·  vis.js 9.1.9 embedded inline (688 KB)  ·  "
        "Nodes colour-coded by equipment class  ·  "
        "Edges carry rule ID, condition, and action labels")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    src = Path("ppt-1.pptx")
    out = Path("ppt-final-v3.pptx")

    shutil.copy2(src, out)
    prs = Presentation(str(out))
    bg = prs.slides[0]   # source for background copies

    print(f"Loaded ppt-1.pptx  ({len(prs.slides)} slides)")

    # 1. Modify slide 16 (index 15) in-place
    build_impl_results(prs.slides[15])
    print("  Modified slide 16: Implementation Results")

    # 2. Append 6 new slides at the end (indices 24-29)
    builders = [
        ("System in Action (pipeline screenshot)",     build_pipeline_screenshot),
        ("Detection Performance chart",                build_detection_chart),
        ("Baseline Comparison + Ablation chart",       build_baseline_chart),
        ("Real Finding Example",                       build_finding_example),
        ("Dashboard — Findings Screenshot",            build_findings_screenshot),
        ("Knowledge Graph Screenshot",                 build_kg_screenshot),
    ]
    for label, fn in builders:
        sl = new_slide(prs, bg)
        fn(sl)
        print(f"  Added new slide: {label}")

    # 3. Reorder: insert the 6 new slides at positions 16-21
    #    They are currently at indices 24-29 (total 30 slides).
    #    Move them forward one by one; each move leaves next new slide at same idx.
    total = len(prs.slides)   # 30
    n_new = len(builders)     # 6
    insert_at = 16            # first new slide should go to position 16 (1-based=17)

    for i in range(n_new):
        move_slide(prs, total - n_new + i, insert_at + i)

    prs.save(str(out))

    print(f"\nSaved: {out}  ({len(prs.slides)} slides)\n")
    print("Final slide order:")
    for i, s in enumerate(prs.slides):
        try:
            titles = [sh.text_frame.paragraphs[0].text
                      for sh in s.shapes
                      if sh.has_text_frame
                      and sh.text_frame.paragraphs
                      and sh.text_frame.paragraphs[0].text.strip()]
            title = titles[0] if titles else "(no title text)"
        except Exception:
            title = "(error reading title)"
        print(f"  {i+1:2d}. {title[:70]}")

    # Report which screenshots were found
    print("\nScreenshot status:")
    for p in [IMG_PIPELINE, IMG_FINDINGS, IMG_KG, IMG_BENCHMARK, IMG_KG_STD]:
        status = "FOUND" if p.exists() else "MISSING (placeholder used)"
        print(f"  [{status}] {p.name}")


if __name__ == "__main__":
    main()
