"""
Generate a professional 2-page methodology document:
  "Verification Methodology — Neuro-Symbolic ICS Safety Auditor"

Covers:
  Page 1 — Core verification idea: what we check, how we prove it, why images matter
  Page 2 — Complete end-to-end pipeline flow with roles, standards, and image checkpoints

Output: Verification_Methodology.docx
"""
from __future__ import annotations
import io
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
import numpy as np

from docx import Document
from docx.shared import Inches, Pt, RGBColor, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# ── Palette ───────────────────────────────────────────────────────────────────
NAVY   = RGBColor(0x1F, 0x3F, 0x6B)
RED    = RGBColor(0xA3, 0x1F, 0x24)
STEEL  = RGBColor(0x2E, 0x74, 0xB5)
TEAL   = RGBColor(0x00, 0x7A, 0x80)
GREEN  = RGBColor(0x1A, 0x7F, 0x37)
AMBER  = RGBColor(0xCC, 0x66, 0x00)
WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
BLACK  = RGBColor(0x12, 0x14, 0x1B)
GREY   = RGBColor(0x55, 0x57, 0x6A)
LGREY  = RGBColor(0xF2, 0xF4, 0xF8)
LBLUE  = RGBColor(0xE8, 0xF2, 0xFB)
LGREEN = RGBColor(0xE8, 0xF5, 0xE9)
LYELLOW= RGBColor(0xFF, 0xF8, 0xE1)
LRED   = RGBColor(0xFF, 0xEB, 0xEE)

DARK   = "#1A1C27"
C_HIGH = "#FF6B6B"
C_MED  = "#FFA94D"
C_LOW  = "#69DB7C"
C_BLUE = "#4FC3F7"
C_PURP = "#CE93D8"
C_TEAL = "#00C5CD"


# ── XML helpers ───────────────────────────────────────────────────────────────
def _shd(cell, rgb: RGBColor):
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    s    = OxmlElement('w:shd')
    h6   = f"{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"
    s.set(qn('w:val'),   'clear')
    s.set(qn('w:color'), 'auto')
    s.set(qn('w:fill'),  h6)
    tcPr.append(s)

def _pshd(para, hex6: str):
    pPr = para._p.get_or_add_pPr()
    s   = OxmlElement('w:shd')
    s.set(qn('w:val'),   'clear')
    s.set(qn('w:color'), 'auto')
    s.set(qn('w:fill'),  hex6)
    pPr.append(s)

def _borders(table, color="2E74B5", sz=6):
    for tc in table._tbl.iter(qn('w:tc')):
        tcPr   = tc.get_or_add_tcPr()
        tcBord = OxmlElement('w:tcBorders')
        for side in ('top','bottom','left','right'):
            b = OxmlElement(f'w:{side}')
            b.set(qn('w:val'),   'single')
            b.set(qn('w:sz'),    str(sz))
            b.set(qn('w:space'), '0')
            b.set(qn('w:color'), color)
            tcBord.append(b)
        tcPr.append(tcBord)


# ── Doc helpers ───────────────────────────────────────────────────────────────
def _h1(doc, text, color=NAVY):
    p = doc.add_paragraph()
    _pshd(p, "1F3F6B")
    r = p.add_run(f"  {text}  ")
    r.font.size  = Pt(16)
    r.font.bold  = True
    r.font.color.rgb = WHITE
    return p

def _h2(doc, text, color=NAVY):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.size  = Pt(13)
    r.font.bold  = True
    r.font.color.rgb = color
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after  = Pt(3)
    return p

def _body(doc, text, color=BLACK, italic=False, size=11):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.size   = Pt(size)
    r.font.color.rgb = color
    r.font.italic = italic
    p.paragraph_format.space_after = Pt(3)
    return p

def _bullet(doc, text, color=BLACK, size=10.5, bold_prefix: str = ""):
    p = doc.add_paragraph(style='List Bullet')
    if bold_prefix:
        rb = p.add_run(bold_prefix)
        rb.font.bold      = True
        rb.font.size      = Pt(size)
        rb.font.color.rgb = color
    r = p.add_run(text)
    r.font.size      = Pt(size)
    r.font.color.rgb = color
    return p

def _callout(doc, label, body_text, bg="EBF2F9", lc=NAVY):
    for txt, bold in [(f"  {label}", True), (f"  {body_text}", False)]:
        p = doc.add_paragraph()
        _pshd(p, bg)
        r = p.add_run(txt)
        r.font.bold  = bold
        r.font.size  = Pt(10.5)
        r.font.color.rgb = lc if bold else BLACK

def _table(doc, headers, rows, col_w, hdr=NAVY, alt=LGREY):
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.style = 'Table Grid'
    # header
    hcells = t.rows[0].cells
    for i, h in enumerate(headers):
        _shd(hcells[i], hdr)
        p = hcells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h)
        r.bold = True; r.font.size = Pt(10); r.font.color.rgb = WHITE
    # rows
    for ri, row in enumerate(rows):
        bg = alt if ri % 2 == 0 else RGBColor(0xFF,0xFF,0xFF)
        cs = t.rows[ri+1].cells
        for ci, val in enumerate(row):
            _shd(cs[ci], bg if ci > 0 else LBLUE)
            p = cs[ci].paragraphs[0]
            r = p.add_run(val)
            r.font.size = Pt(10)
            r.font.color.rgb = NAVY if ci == 0 else BLACK
            if ci == 0: r.bold = True
    # widths
    for ci, w in enumerate(col_w):
        for row in t.rows:
            row.cells[ci].width = Inches(w)
    return t

def _embed(doc, fig, w=6.2, caption=""):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=160, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    buf.seek(0); plt.close(fig)
    doc.add_picture(buf, width=Inches(w))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    if caption:
        p = doc.add_paragraph(caption)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.runs[0].font.italic = True
        p.runs[0].font.size   = Pt(9)
        p.runs[0].font.color.rgb = GREY


# ── Charts ────────────────────────────────────────────────────────────────────

def _fig_verification_logic():
    """
    Three-column visual showing OMISSION / CONTRADICTION / TAG_MISMATCH
    with the Z3 proof chain underneath each.
    """
    fig, axes = plt.subplots(1, 3, figsize=(11, 5.5), facecolor=DARK)
    titles  = ["OMISSION",         "CONTRADICTION",              "TAG MISMATCH"]
    colors  = [C_HIGH,             C_MED,                        C_TEAL]
    icons   = ["[X]  MISSING RULE",  "[!]  CONFLICTING RULES",      "[T]  NAMING INCONSISTENCY"]
    iec     = ["IEC 61511 §10.3.2","IEC 61511 §9.4.1",          "IEC 61511 §8.2.3"]
    proofs  = [
        "IEC template requires\nHH shutdown rule for PT-101\n\nZ3 query:\n∃ rule: trigger=PT-101\n  AND action∈{STOP,CLOSE}\n\nResult: UNSAT\n→ No such rule exists",
        "R-07: TT-501>80 → XV-301 OPEN\nR-12: TT-501>80 → XV-301 CLOSE\n\nZ3 encodes:\nImplies(cond, open)\nImplies(cond, Not(open))\nAssert(cond)\n\nResult: UNSAT\n→ Proved contradiction",
        "Narrative: 'PT-101A'\nC&E Table: 'PT101A'\n\nFuzzy score: 0.923 ≥ 0.85\n→ Same instrument,\n  different name format\n\nZ3 role-check: SAT\n→ TAG_MISMATCH confirmed",
    ]
    for ax, title, col, icon, iec_c, proof in zip(axes, titles, colors, icons, iec, proofs):
        ax.set_facecolor(DARK)
        ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis("off")

        # Header band
        ax.add_patch(mpatches.FancyBboxPatch((0.3, 8.2), 9.4, 1.5,
            boxstyle="round,pad=0.1", facecolor=col+"33", edgecolor=col, lw=2))
        ax.text(5, 9.25, title, ha="center", va="center", fontsize=13,
                fontweight="bold", color=col)
        ax.text(5, 8.65, icon, ha="center", va="center", fontsize=9.5, color="white")

        # IEC clause chip
        ax.add_patch(mpatches.FancyBboxPatch((1.5, 7.3), 7, 0.7,
            boxstyle="round,pad=0.05", facecolor="#2A2C3A", edgecolor=col, lw=1))
        ax.text(5, 7.65, iec_c, ha="center", va="center", fontsize=8.5, color=col)

        # Proof box
        ax.add_patch(mpatches.FancyBboxPatch((0.3, 0.4), 9.4, 6.6,
            boxstyle="round,pad=0.15", facecolor="#12141F", edgecolor="#444", lw=1))
        ax.text(5, 3.8, proof, ha="center", va="center",
                fontsize=8.2, color="#CCCCEE", family="monospace",
                multialignment="center")

    fig.suptitle(
        "Three Verification Passes — What is Checked and How it is Proved",
        color="white", fontsize=13, fontweight="bold", y=0.97
    )
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    return fig


def _fig_pipeline_flow():
    """
    Complete horizontal pipeline flow with image-check annotations.
    Uses a swim-lane style:  top lane = documents/data, bottom lane = outputs.
    """
    fig, ax = plt.subplots(figsize=(13, 6.5), facecolor=DARK)
    ax.set_facecolor(DARK)
    ax.set_xlim(0, 26); ax.set_ylim(0, 9); ax.axis("off")

    phases = [
        # (x_center, label, sublabel, color, lane)
        (1.2,  "INPUT\nPDF",            "Control\nNarrative",          "#4FC3F7", 7.0),
        (3.2,  "PHASE 1\nIngestion",    "Text + Tables\n+ Image OCR",  "#4FC3F7", 5.0),
        (5.8,  "PHASE 1b\nImages",      "Scanned pages\nEmbedded P&ID","#CE93D8", 5.0),
        (8.4,  "PHASE 2\nLLM Extract",  "Qwen 2.5\n+ Registry",        "#69DB7C", 5.0),
        (11.0, "PHASE 3\nEntity Link",  "Exact→Fuzzy\n→Embedding",     "#FFA94D", 5.0),
        (13.6, "PHASE 4\nKG Build",     "NetworkX\n+ PyVis",           "#4FC3F7", 5.0),
        (16.2, "PHASE 5-6\nIR + Cover", "Pydantic v2\n19 Invariants",  "#CE93D8", 5.0),
        (18.8, "PHASE 7\nZ3 Verify",    "OMISSION\nCONTRADICTION\nTAG_MISMATCH", "#FF6B6B", 5.0),
        (21.4, "PHASE 8\nReport",       "HTML\nAudit Report",          "#69DB7C", 5.0),
        (24.0, "PHASE 9\nPLC Code",     "IEC 61131-3\nST + Findings",  "#FFA94D", 5.0),
    ]

    bw, bh = 1.9, 1.55

    for i, (cx, label, sub, col, ly) in enumerate(phases):
        bx = cx - bw/2
        by = ly - bh/2
        ax.add_patch(mpatches.FancyBboxPatch(
            (bx, by), bw, bh,
            boxstyle="round,pad=0.12",
            facecolor="#1F2133", edgecolor=col, lw=1.8
        ))
        lines = label.split("\n")
        ax.text(cx, ly + 0.22, lines[0], ha="center", va="center",
                fontsize=8.5, fontweight="bold", color=col)
        if len(lines) > 1:
            ax.text(cx, ly - 0.08, lines[1], ha="center", va="center",
                    fontsize=7.5, color=col)
        ax.text(cx, ly - 0.55, sub, ha="center", va="center",
                fontsize=7.2, color="#AAAACC", multialignment="center")

        # Arrow to next
        if i < len(phases) - 1:
            nx = phases[i+1][0]
            ax.annotate("", xy=(nx - bw/2 - 0.05, ly),
                        xytext=(cx + bw/2 + 0.05, ly),
                        arrowprops=dict(arrowstyle="->", color="#666", lw=1.3))

    # ── Image checkpoint annotation ────────────────────────────────────
    # Vertical dotted line from Phase 1b down
    img_x = 5.8
    ax.plot([img_x, img_x], [3.2, 4.22], color="#CE93D8", lw=1.4, linestyle="--")
    ax.add_patch(mpatches.FancyBboxPatch(
        (3.8, 1.2), 4.0, 1.8,
        boxstyle="round,pad=0.1",
        facecolor="#1A1040", edgecolor="#CE93D8", lw=1.5
    ))
    ax.text(5.8, 2.55, "IMAGE VERIFICATION CHECKPOINTS",
            ha="center", fontsize=8, fontweight="bold", color="#CE93D8")
    ax.text(5.8, 2.15, "① Scanned page → full-page OCR @ 300 DPI",
            ha="center", fontsize=7.5, color="#CCCCEE")
    ax.text(5.8, 1.80, "② P&ID image (≥800px) → ISA symbol + tag extract",
            ha="center", fontsize=7.5, color="#CCCCEE")
    ax.text(5.8, 1.45, "③ Embedded figure → Tesseract PSM 6 text labels",
            ha="center", fontsize=7.5, color="#CCCCEE")

    # ── Cross-page context annotation ──────────────────────────────────
    reg_x = 8.4
    ax.plot([reg_x, reg_x], [3.2, 4.22], color="#69DB7C", lw=1.4, linestyle="--")
    ax.add_patch(mpatches.FancyBboxPatch(
        (6.4, 1.2), 4.0, 1.8,
        boxstyle="round,pad=0.1",
        facecolor="#0A2010", edgecolor="#69DB7C", lw=1.5
    ))
    ax.text(8.4, 2.55, "GLOBAL ENTITY REGISTRY",
            ha="center", fontsize=8, fontweight="bold", color="#69DB7C")
    ax.text(8.4, 2.15, "Fast regex scan → all ISA tags in document",
            ha="center", fontsize=7.5, color="#CCCCEE")
    ax.text(8.4, 1.80, "Injected into every LLM chunk prompt",
            ha="center", fontsize=7.5, color="#CCCCEE")
    ax.text(8.4, 1.45, "Page 100 rule → knows equipment from page 3",
            ha="center", fontsize=7.5, color="#CCCCEE")

    # ── Z3 proof annotation ────────────────────────────────────────────
    z3_x = 18.8
    ax.plot([z3_x, z3_x], [3.2, 4.22], color="#FF6B6B", lw=1.4, linestyle="--")
    ax.add_patch(mpatches.FancyBboxPatch(
        (16.8, 1.2), 4.0, 1.8,
        boxstyle="round,pad=0.1",
        facecolor="#2A0A0A", edgecolor="#FF6B6B", lw=1.5
    ))
    ax.text(18.8, 2.55, "Z3 SMT FORMAL PROOF",
            ha="center", fontsize=8, fontweight="bold", color="#FF6B6B")
    ax.text(18.8, 2.15, "UNSAT → Contradiction / Omission proved",
            ha="center", fontsize=7.5, color="#CCCCEE")
    ax.text(18.8, 1.80, "SAT + model → Unsafe state witness found",
            ha="center", fontsize=7.5, color="#CCCCEE")
    ax.text(18.8, 1.45, "Machine-checked proof, not heuristic",
            ha="center", fontsize=7.5, color="#CCCCEE")

    # ── Standard label ─────────────────────────────────────────────────
    ax.add_patch(mpatches.FancyBboxPatch(
        (0.1, 7.8), 25.8, 0.9,
        boxstyle="round,pad=0.05",
        facecolor="#111320", edgecolor="#333", lw=1
    ))
    ax.text(13, 8.25,
            "Standard: IEC 61511-1 (Safety Instrumented Systems)  ·  "
            "IEC 61131-3 (PLC Structured Text)  ·  ISA 5.1 (Instrument Tagging)",
            ha="center", fontsize=8.5, color="#AAAACC")

    fig.suptitle(
        "Complete Pipeline Flow — Neuro-Symbolic ICS Safety Auditor",
        color="white", fontsize=13, fontweight="bold", y=0.98
    )
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    return fig


# ── Page 1 ────────────────────────────────────────────────────────────────────

def page1(doc: Document):
    _h1(doc, "  Verification Methodology — How Safety Rules are Checked")

    doc.add_paragraph()
    _h2(doc, "Core Idea", NAVY)
    _body(doc,
        "The system automates what a HAZOP (Hazard and Operability Study) team does manually: "
        "it reads every control rule from the specification document and asks three questions "
        "that a process safety engineer would ask. The difference is that our answers are "
        "mathematical proofs — not human judgement — using the Z3 SMT solver from Microsoft Research.")

    doc.add_paragraph()
    _embed(doc, _fig_verification_logic(), w=6.5,
           caption="Figure 1.  Three verification passes — each with its IEC 61511 clause and Z3 proof chain.")

    doc.add_paragraph()
    _h2(doc, "The Three Verification Questions", NAVY)

    _table(doc,
        headers=["Verification Pass",  "Question Asked",
                 "Z3 Encoding",        "Result if Failed"],
        rows=[
            ["OMISSION",
             "Does this spec contain every safety rule required by IEC 61511?",
             "∃ rule satisfying template T? → check() == unsat → no such rule",
             "HIGH finding: missing shutdown / alarm / interlock rule"],
            ["CONTRADICTION",
             "Can two rules for the same equipment both be true at the same time?",
             "Implies(cond,OPEN) ∧ Implies(cond,CLOSE) ∧ Assert(cond) → unsat",
             "HIGH finding: valve cannot be open and closed simultaneously"],
            ["TAG MISMATCH",
             "Is the same physical instrument named consistently across all documents?",
             "Fuzzy ≥ 85 → candidate; Z3 role-check confirms semantic match",
             "MEDIUM finding: same instrument, different name → rule may be silently lost"],
        ],
        col_w=[1.5, 2.3, 2.1, 1.8])

    doc.add_paragraph()
    _h2(doc, "Why Formal Proof — Not Heuristic Matching?", RED)
    _body(doc,
        "A heuristic like 'check if the word shutdown appears' produces false positives and "
        "false negatives. Z3 operates on the logical structure of the rules. When Z3 returns "
        "UNSAT it means: no assignment of variables can satisfy both constraints simultaneously "
        "— this is a mathematical certificate, not a probability. For a safety-critical system "
        "deployed at a refinery or power plant, this distinction is the difference between "
        "a finding you can defend in a regulatory audit and one you cannot.")

    _callout(doc,
        "Industrial context:",
        "The 2005 BP Texas City explosion (15 fatalities) was partly attributed to operators "
        "following a procedure that contained an implicit contradiction — a manual HAZOP would "
        "have caught it. Our system catches this class of error automatically, at document-review "
        "time, before the specification ever reaches the plant floor.",
        bg="FFE8E8", lc=RED)


# ── Page 2 ────────────────────────────────────────────────────────────────────

def page2(doc: Document):
    _h1(doc, "  Complete Pipeline Flow — From PDF to Verified PLC Code")

    doc.add_paragraph()
    _embed(doc, _fig_pipeline_flow(), w=7.2,
           caption=(
               "Figure 2.  Full 9-phase pipeline. "
               "Three annotations (purple, green, red) mark where images, "
               "cross-page context, and formal proof operate."
           ))

    doc.add_paragraph()
    _h2(doc, "Where Images Are Verified", RGBColor(0x6A, 0x1B, 0x9A))

    _body(doc,
        "P&ID drawings are the engineering ground truth — the physical layout the plant "
        "is actually built to. Three image cases are handled in Phase 1b:")

    _table(doc,
        headers=["Image Type",   "Detection",
                 "Processing",   "Why It Matters"],
        rows=[
            ["Scanned page\n(image-only PDF page)",
             "Page text < 30 chars but page has raster images",
             "Full page rendered at 300 DPI → PIDExtractor (PSM 11 OCR + contour detection)",
             "A scanned P&ID page contains ALL instrument tags. Without this step, every tag on that page is invisible to the pipeline."],
            ["Embedded P&ID diagram\n(≥ 800 px wide)",
             "PyMuPDF page.get_images() + pixel dimensions",
             "fitz.Pixmap extracted → PIDExtractor full pipeline: preprocessing → OCR → ISA 5.1 symbol detection",
             "Large engineering drawings contain tag–symbol spatial relationships. Symbol type (circle=transmitter, diamond=valve) is used to infer entity class without LLM."],
            ["Embedded figure\n(100–800 px wide)",
             "Pixel dimensions 100–800",
             "Tesseract PSM 6 (uniform text block) — extracts numeric thresholds and tag labels printed on process flow diagrams",
             "Small figures often contain alarm setpoints (e.g. '45 bar HH') that are not repeated in the narrative text. Missing these means missing the threshold value for a rule."],
        ],
        col_w=[1.8, 1.7, 2.1, 2.1])

    doc.add_paragraph()
    _h2(doc, "Cross-Page Reference — How Page 100 Knows About Page 3", TEAL)
    _body(doc,
        "A 200-page control narrative defines equipment on early pages and references it on "
        "late pages. Without the Global Entity Registry, an LLM processing a chunk at page 100 "
        "sees the tag 'P-001' with no context and may misclassify it or hallucinate its role. "
        "The registry is built in one fast pass (regex, no LLM) before any chunking starts, "
        "then prepended to every chunk prompt:")

    _callout(doc,
        "Registry prompt injection (example):",
        "Equipment tags in this document: P-001 (p.3), PT-101 (p.3), LT-201 (p.5), "
        "XV-301 (p.7), ESD-001 (p.11), TT-501 (p.18) ...\n\n"
        "SECTION: 3.1 Emergency Shutdown  (pages 98–101)\n"
        "On ESD-001 DEMAND, stop P-001 and close XV-201 ...\n\n"
        "→ LLM now knows P-001 was defined on page 3 as a pump — correct entity class, "
        "correct invariant coverage.",
        bg="E8F5E9", lc=TEAL)

    doc.add_paragraph()
    _h2(doc, "Standards Alignment", NAVY)
    _table(doc,
        headers=["Standard",         "Where Applied",             "Mechanism"],
        rows=[
            ["IEC 61511-1",          "Phase 6 — Invariant check\nPhase 7 — Z3 verification",
             "19 safety requirement templates covering §8 (tag naming), §9 (contradictions), §10 (shutdown rules), §11 (alarms)"],
            ["IEC 61131-3",          "Phase 9 — PLC code generation",
             "Structured Text output with AUDIT NOTE comments at every finding location"],
            ["ISA 5.1",              "Phase 1b — Image OCR\nPhase 3 — Entity linking",
             "Instrument tag regex [A-Z]{1-3}-[0-9]{3-4} matches all standard ISA tag formats"],
            ["HAZOP methodology",    "Phase 6-7 — Full audit",
             "Automates the HAZOP 'guide word' analysis: What if a rule is missing? What if two rules conflict?"],
        ],
        col_w=[1.7, 2.1, 3.9])

    doc.add_paragraph()
    _callout(doc,
        "What makes this research novel:",
        "Existing tools (HAZOP software, SIL calculators) require a human engineer to manually "
        "enter rules into a structured form. Our system reads unstructured prose PDFs — the actual "
        "documents produced in industry — and produces machine-verified findings automatically. "
        "The cross-modal image pipeline closes the gap between what is written in text and what "
        "is drawn on the P&ID, which is where real safety gaps most often hide.",
        bg="EBF2F9", lc=NAVY)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    doc = Document()
    for sec in doc.sections:
        sec.top_margin    = Inches(0.75)
        sec.bottom_margin = Inches(0.75)
        sec.left_margin   = Inches(1.0)
        sec.right_margin  = Inches(1.0)

    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)

    page1(doc)
    doc.add_page_break()
    page2(doc)

    out = "Verification_Methodology.docx"
    doc.save(out)
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
