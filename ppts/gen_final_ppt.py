"""
Generate ppt-final.pptx from ppt-1.pptx.
- Modifies slide 16 (Implementation Results) with full delivery status
- Inserts slide 17: Defect Detection bar chart
- Inserts slide 18: Baseline Comparison + Ablation charts
- All design follows ppt-1 patterns exactly (colors, fonts, layout)
"""
import copy
import shutil
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from pptx.chart.data import ChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_TICK_MARK

# ── Colors from ppt-1 analysis ───────────────────────────────────────────────
TITLE_BLUE  = RGBColor(0x1F, 0x40, 0x6C)
BODY_DARK   = RGBColor(0x2A, 0x30, 0x3A)
BOX1_FILL   = RGBColor(0xEC, 0xF4, 0xFD)   # light blue
BOX2_FILL   = RGBColor(0xFC, 0xF4, 0xE2)   # light yellow
BOX3_FILL   = RGBColor(0xEA, 0xF6, 0xEC)   # light green
BOX_LINE    = RGBColor(0xB8, 0xCF, 0xE8)

CHART_DARK  = RGBColor(0x1F, 0x40, 0x6C)   # dark blue — proposed system
CHART_MED   = RGBColor(0x3A, 0x7F, 0xBD)   # medium blue
CHART_LIGHT = RGBColor(0x89, 0xB7, 0xE0)   # light blue
CHART_GREY  = RGBColor(0xB0, 0xB8, 0xC1)   # grey — baselines
CHART_TEAL  = RGBColor(0x17, 0x7D, 0x7D)
CHART_GRN   = RGBColor(0x2E, 0x86, 0x48)

WHITE       = RGBColor(0xFF, 0xFF, 0xFF)

# ── Positional constants (measured from ppt-1) ───────────────────────────────
TITLE_L = Inches(0.98); TITLE_T = Inches(0.52)
TITLE_W = Inches(11.60); TITLE_H = Inches(0.70)

BOX_TOP = Inches(1.45); BOX_H = Inches(4.85)
BOX1_L = Inches(0.75);  BOX1_W = Inches(3.80)
BOX2_L = Inches(4.70);  BOX2_W = Inches(3.55)
BOX3_L = Inches(8.40);  BOX3_W = Inches(3.85)

HEAD_OFF = Inches(0.13); HEAD_H = Inches(0.34)
BODY_OFF = Inches(0.46)

FOOT_L = Inches(0.90); FOOT_T = Inches(6.38)
FOOT_W = Inches(11.40); FOOT_H = Inches(0.35)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _tb(slide, l, t, w, h, wrap=True):
    tx = slide.shapes.add_textbox(l, t, w, h)
    tx.text_frame.word_wrap = wrap
    return tx.text_frame


def _run(para, text, size=None, bold=None, color=None, italic=None):
    r = para.add_run()
    r.text = text
    if size:   r.font.size = Pt(size)
    if bold is not None: r.font.bold = bold
    if color:  r.font.color.rgb = color
    if italic is not None: r.font.italic = italic
    return r


def add_title(slide, text):
    tf = _tb(slide, TITLE_L, TITLE_T, TITLE_W, TITLE_H, wrap=False)
    _run(tf.paragraphs[0], text, size=24, bold=True, color=TITLE_BLUE)


def add_rr(slide, l, t, w, h, fill, border=True):
    """Add rounded rectangle."""
    sh = slide.shapes.add_shape(5, l, t, w, h)   # 5 = ROUNDED_RECTANGLE
    sh.fill.solid(); sh.fill.fore_color.rgb = fill
    if border:
        sh.line.color.rgb = BOX_LINE
        sh.line.width = Pt(0.75)
    else:
        sh.line.fill.background()
    return sh


def add_heading(slide, l, t, w, text):
    tf = _tb(slide, l, t, w, HEAD_H, wrap=False)
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    _run(p, text, size=13, bold=True, color=TITLE_BLUE)


def add_bullets(slide, l, t, w, h, items):
    tf = _tb(slide, l, t, w, h)
    first = True
    for item in items:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.alignment = PP_ALIGN.LEFT
        _run(p, item, size=11.5, color=BODY_DARK)


def add_footer(slide, text):
    tf = _tb(slide, FOOT_L, FOOT_T, FOOT_W, FOOT_H, wrap=False)
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    _run(p, text, size=9, color=BODY_DARK, italic=True)


def add_label(slide, l, t, w, text, size=11, bold=False, color=None, align=PP_ALIGN.LEFT):
    tf = _tb(slide, l, t, w, Inches(0.30), wrap=False)
    p = tf.paragraphs[0]; p.alignment = align
    _run(p, text, size=size, bold=bold, color=color or BODY_DARK)


def copy_bg(new_slide, src_slide):
    """Copy the full-slide background picture from src_slide to new_slide."""
    bg = src_slide.shapes[0]            # Picture 1 is always first
    pic_xml = bg._element
    blip = pic_xml.find('.//' + qn('a:blip'))
    if blip is None:
        return
    attr = qn('r:embed')
    old_rId = blip.get(attr)
    if not old_rId:
        return
    img_part = src_slide.part.related_part(old_rId)
    old_rel  = src_slide.part.rels[old_rId]
    new_rId  = new_slide.part.relate_to(img_part, old_rel.reltype)
    clone    = copy.deepcopy(pic_xml)
    clone.find('.//' + qn('a:blip')).set(attr, new_rId)
    new_slide.shapes._spTree.append(clone)


def clear_content(slide):
    """Remove all shapes except the background (index 0)."""
    for sh in list(slide.shapes)[1:]:
        sh._element.getparent().remove(sh._element)


def move_slide(prs, old_idx, new_idx):
    """Reorder slides in the presentation XML."""
    lst = prs.slides._sldIdLst
    elems = list(lst)
    el = elems[old_idx]
    lst.remove(el)
    lst.insert(new_idx, el)


def _style_chart(chart, v_min=0.0, v_max=1.0, v_unit=0.2, cat_size=9, val_size=9):
    """Apply baseline styling to a chart."""
    chart.has_title = False

    va = chart.value_axis
    va.minimum_scale = v_min
    va.maximum_scale = v_max
    va.major_unit    = v_unit
    va.tick_labels.font.size  = Pt(val_size)
    va.tick_labels.font.color.rgb = BODY_DARK
    va.major_tick_mark = XL_TICK_MARK.OUTSIDE

    ca = chart.category_axis
    ca.tick_labels.font.size  = Pt(cat_size)
    ca.tick_labels.font.color.rgb = BODY_DARK
    ca.major_tick_mark = XL_TICK_MARK.NONE

    if chart.has_legend:
        chart.legend.include_in_layout = False
        try:
            chart.legend.position = XL_LEGEND_POSITION.BOTTOM
            chart.legend.font.size = Pt(9)
            chart.legend.font.color.rgb = BODY_DARK
        except Exception:
            pass


def _color_series(chart, colors):
    """Set fill colors for each series."""
    for series, color in zip(chart.plots[0].series, colors):
        series.format.fill.solid()
        series.format.fill.fore_color.rgb = color


def _add_data_labels(chart, fmt='0.000', size=7.5, bold=True, color=WHITE):
    plot = chart.plots[0]
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.number_format = fmt
    dl.font.size  = Pt(size)
    dl.font.bold  = bold
    dl.font.color.rgb = color


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE BUILDERS
# ═══════════════════════════════════════════════════════════════════════════════

def build_impl_results(slide):
    """Slide 16  —  Implementation Results — System Delivery Status"""
    clear_content(slide)
    add_title(slide, "Implementation Results — System Delivery")

    # ── Box 1: Pipeline Phases ────────────────────────────────────────────
    add_rr(slide, BOX1_L, BOX_TOP, BOX1_W, BOX_H, BOX1_FILL)
    add_heading(slide, BOX1_L + Inches(0.10), BOX_TOP + HEAD_OFF,
                BOX1_W - Inches(0.20), "Pipeline Phases (All ✓)")
    add_bullets(slide,
                BOX1_L + Inches(0.10), BOX_TOP + BODY_OFF,
                BOX1_W - Inches(0.20), BOX_H - BODY_OFF - Inches(0.10), [
        "• Phase 1  —  Multimodal Ingestion            ✓",
        "• Phase 2  —  LLM Entity Extraction          ✓",
        "• Phase 3  —  Cross-Modal Entity Linking     ✓",
        "• Phase 4  —  Knowledge Graph Builder        ✓",
        "• Phase 5  —  Control Rule IR                   ✓",
        "• Phase 6  —  Safety Invariant Engine          ✓",
        "• Phase 7  —  Z3 Formal Verification            ✓",
        "• Phase 8  —  Audit Report Generator           ✓",
        "• Phase 9  —  PLC Code Generation                ✓",
    ])

    # ── Box 2: Benchmark Dataset ──────────────────────────────────────────
    add_rr(slide, BOX2_L, BOX_TOP, BOX2_W, BOX_H, BOX2_FILL)
    add_heading(slide, BOX2_L + Inches(0.10), BOX_TOP + HEAD_OFF,
                BOX2_W - Inches(0.20), "Benchmark Dataset")
    add_bullets(slide,
                BOX2_L + Inches(0.10), BOX_TOP + BODY_OFF,
                BOX2_W - Inches(0.20), BOX_H - BODY_OFF - Inches(0.10), [
        "• 50 specification packages (synthetic)",
        "• Each: control narrative + C&E",
        "    table + simplified P&ID",
        "• 5 defect categories x 10 packages",
        "• Ground truth logged per injection",
        "• ICS-CERT taxonomy alignment",
        "• 5 clean (defect-free) packages",
        "• 19 IEC 61511 safety invariants",
    ])

    # ── Box 3: Key Metrics ────────────────────────────────────────────────
    add_rr(slide, BOX3_L, BOX_TOP, BOX3_W, BOX_H, BOX3_FILL)
    add_heading(slide, BOX3_L + Inches(0.10), BOX_TOP + HEAD_OFF,
                BOX3_W - Inches(0.20), "Prototype Key Metrics")
    add_bullets(slide,
                BOX3_L + Inches(0.10), BOX_TOP + BODY_OFF,
                BOX3_W - Inches(0.20), BOX_H - BODY_OFF - Inches(0.10), [
        "• Overall F1:        0.918",
        "• Precision:         0.924",
        "• Recall:              0.912",
        "• LLM-Only F1:    0.610",
        "• Post-Gen F1:    0.670",
        "• Best: Tag Mismatch     (F1 = 0.943)",
        "• Hardest: Missing Alarm (F1 = 0.881)",
        "• Ablation: +18.2 pp recall",
        "    with cross-modal linking",
    ])

    add_footer(slide,
        "All 9 phases implemented end-to-end  ·  "
        "50-package synthetic benchmark  ·  "
        "IEC 61511-aligned safety invariants")


def build_detection_chart(slide):
    """
    Slide 17  —  Defect Detection by Category
    Grouped column chart: Precision / F1 / Recall per defect type
    + summary stats box
    """
    clear_content(slide)
    add_title(slide, "Evaluation Results — Defect Detection by Category")

    # ── Chart data ─────────────────────────────────────────────────────────
    cats = ['Miss. Shutdown', 'Miss. Interlock', 'Contradiction',
            'Tag Mismatch',  'Miss. Alarm']
    prec  = (0.951, 0.921, 0.897, 0.962, 0.889)
    f1    = (0.943, 0.912, 0.889, 0.943, 0.881)
    rec   = (0.935, 0.903, 0.881, 0.924, 0.872)

    cd = ChartData()
    cd.categories = cats
    cd.add_series('Precision', prec)
    cd.add_series('F1 Score',  f1)
    cd.add_series('Recall',    rec)

    cf = slide.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED,
        Inches(0.60), Inches(1.50),
        Inches(8.00), Inches(4.90),
        cd,
    )
    chart = cf.chart
    chart.has_legend = True
    _style_chart(chart, v_min=0.70, v_max=1.00, v_unit=0.05,
                 cat_size=9, val_size=8)
    _color_series(chart, [CHART_LIGHT, CHART_DARK, CHART_MED])
    _add_data_labels(chart, fmt='0.000', size=6.5, bold=True, color=WHITE)

    # ── Info / summary box ────────────────────────────────────────────────
    BX_L = Inches(8.90); BX_T = Inches(1.50)
    BX_W = Inches(4.05); BX_H = Inches(4.90)
    add_rr(slide, BX_L, BX_T, BX_W, BX_H, BOX1_FILL)
    add_heading(slide, BX_L + Inches(0.10), BX_T + HEAD_OFF,
                BX_W - Inches(0.20), "Summary Statistics")
    add_bullets(slide,
                BX_L + Inches(0.12), BX_T + BODY_OFF,
                BX_W - Inches(0.24), BX_H - BODY_OFF - Inches(0.15), [
        "• Packages evaluated:    50",
        "• Defects injected:        50",
        "• Findings generated:   347",
        "• True positives:          46 / 50",
        "",
        "• Overall F1:               0.918",
        "• Precision:                0.924",
        "• Recall:                     0.912",
        "",
        "• IEC 61511 invariants: 19",
        "• Defect categories:     5",
        "",
        "• Macro-averaged across",
        "    50 injected packages",
    ])

    add_footer(slide,
        "Bars: Precision | F1 | Recall per defect category  ·  "
        "Axis starts at 0.70 to highlight differences  ·  "
        "All metrics macro-averaged")


def build_baseline_chart(slide):
    """
    Slide 18  —  Baseline Comparison & Ablation Study
    Upper: grouped column chart  (LLM-Only / Post-Gen / Proposed)
    Lower: grouped column chart  (w/o linking vs w/ linking)
    """
    clear_content(slide)
    add_title(slide, "Evaluation Results — Baseline Comparison & Ablation Study")

    # ── Upper chart: baseline comparison ──────────────────────────────────
    cd1 = ChartData()
    cd1.categories = ['Precision', 'Recall', 'F1 Score']
    cd1.add_series('LLM-Only Audit',    (0.650, 0.580, 0.610))
    cd1.add_series('Post-Gen Verify',   (0.710, 0.640, 0.670))
    cd1.add_series('Proposed System',   (0.924, 0.912, 0.918))

    cf1 = slide.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED,
        Inches(0.50), Inches(1.45),
        Inches(7.70), Inches(2.90),
        cd1,
    )
    c1 = cf1.chart
    c1.has_legend = True
    _style_chart(c1, v_min=0.0, v_max=1.0, v_unit=0.2, cat_size=11, val_size=9)
    _color_series(c1, [CHART_GREY, CHART_LIGHT, CHART_DARK])
    _add_data_labels(c1, fmt='0.000', size=7, bold=True, color=WHITE)

    # ── Lower chart: ablation study ────────────────────────────────────────
    cd2 = ChartData()
    cd2.categories = ['Precision', 'Recall', 'F1 Score']
    cd2.add_series('w/o Cross-Modal Linking', (0.820, 0.730, 0.772))
    cd2.add_series('w/ Cross-Modal Linking',  (0.924, 0.912, 0.918))

    cf2 = slide.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED,
        Inches(0.50), Inches(4.55),
        Inches(7.70), Inches(2.65),
        cd2,
    )
    c2 = cf2.chart
    c2.has_legend = True
    _style_chart(c2, v_min=0.0, v_max=1.0, v_unit=0.2, cat_size=11, val_size=9)
    _color_series(c2, [CHART_LIGHT, CHART_DARK])
    _add_data_labels(c2, fmt='0.000', size=7, bold=True, color=WHITE)

    # ── Chart section labels ───────────────────────────────────────────────
    add_label(slide, Inches(0.50), Inches(1.38), Inches(4.0),
              "Baseline Comparison", size=10, bold=True, color=TITLE_BLUE)
    add_label(slide, Inches(0.50), Inches(4.47), Inches(4.0),
              "Ablation Study — Cross-Modal Linking", size=10, bold=True, color=TITLE_BLUE)

    # ── Right-side annotation boxes ────────────────────────────────────────
    RX = Inches(8.45); RW = Inches(4.50)

    # Baseline box
    add_rr(slide, RX, Inches(1.45), RW, Inches(2.90), BOX2_FILL)
    add_heading(slide, RX + Inches(0.10), Inches(1.45) + HEAD_OFF,
                RW - Inches(0.20), "Baseline Comparison")
    add_bullets(slide,
                RX + Inches(0.12), Inches(1.45) + BODY_OFF,
                RW - Inches(0.24), Inches(2.90) - BODY_OFF - Inches(0.15), [
        "• LLM-Only: no formal audit layer",
        "    F1 = 0.610  (− 30.8 pp)",
        "• Post-Gen: verifies PLC code",
        "    F1 = 0.670  (− 24.8 pp)",
        "• Proposed: pre-synthesis Z3 audit",
        "    F1 = 0.918  (best across all)",
        "• Pre-synthesis audit detects",
        "    spec-level defects missed by",
        "    forward/post-gen approaches",
    ])

    # Ablation box
    add_rr(slide, RX, Inches(4.55), RW, Inches(2.65), BOX3_FILL)
    add_heading(slide, RX + Inches(0.10), Inches(4.55) + HEAD_OFF,
                RW - Inches(0.20), "Ablation: Cross-Modal Linking")
    add_bullets(slide,
                RX + Inches(0.12), Inches(4.55) + BODY_OFF,
                RW - Inches(0.24), Inches(2.65) - BODY_OFF - Inches(0.15), [
        "• Without linking: F1 = 0.772",
        "• With linking:      F1 = 0.918",
        "• Δ F1:  +0.146  (+14.6 pp)",
        "• Δ Recall: +0.182  (+18.2 pp)",
        "• H2 strongly supported (> 0.02)",
    ])

    add_footer(slide,
        "Baselines: LLM-only and post-generation Z3 verification  ·  "
        "Ablation over same 50-package benchmark  ·  "
        "Δ Recall validates H2 (cross-modal linking hypothesis)")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    src  = Path("ppt-1.pptx")
    out  = Path("ppt-final.pptx")

    shutil.copy2(src, out)
    prs = Presentation(str(out))

    # ── 1. Modify existing slide 16 (index 15) ────────────────────────────
    slide16 = prs.slides[15]
    build_impl_results(slide16)

    # ── 2. Add 2 new slides at the end (blank layout) ─────────────────────
    blank_layout = prs.slide_layouts[6]   # blank

    new17 = prs.slides.add_slide(blank_layout)
    copy_bg(new17, prs.slides[0])         # copy background from slide 1
    build_detection_chart(new17)

    new18 = prs.slides.add_slide(blank_layout)
    copy_bg(new18, prs.slides[0])
    build_baseline_chart(new18)

    # ── 3. Reorder: insert the 2 new slides after slide 16 (index 15) ─────
    #   Current order after appends:  [0..14, 15(mod), 16..23, 24(new17), 25(new18)]
    #   Desired:                       [0..14, 15(mod), 24(new17), 25(new18), 16..23]
    total = len(prs.slides)           # should be 26
    move_slide(prs, total - 2, 16)   # new17 → index 16
    move_slide(prs, total - 1, 17)   # new18 → index 17

    prs.save(str(out))
    print(f"Saved {out}  ({len(prs.slides)} slides)")
    print("Slide structure:")
    for i, s in enumerate(prs.slides):
        titles = [sh.text_frame.paragraphs[0].text
                  for sh in s.shapes
                  if sh.has_text_frame and sh.text_frame.paragraphs
                  and sh.text_frame.paragraphs[0].text.strip()]
        print(f"  {i+1:2d}. {titles[0] if titles else '(no text)'}")


if __name__ == "__main__":
    main()
