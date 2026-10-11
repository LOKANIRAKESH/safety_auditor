"""
Create realistic mock screenshots of the Streamlit Safety Auditor UI.
Uses Pillow to draw the UI.
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import os

OUT = Path("screenshots")
OUT.mkdir(exist_ok=True)

# ── Color palette (Streamlit dark theme) ──────────────────────────────────────
BG         = (14,  17,  23)     # #0e1117  main background
BG2        = (38,  39,  48)     # #262730  secondary bg / card
BG3        = (26,  28,  36)     # sidebar bg
ACCENT     = (255, 75,  75)     # streamlit red
BLUE       = (76,  195, 247)    # info blue
GREEN      = (105, 219, 124)    # low severity / success
ORANGE     = (255, 169, 77)     # medium severity
RED_DARK   = (255, 107, 107)    # high severity
TEXT       = (250, 250, 250)    # primary text
TEXT2      = (163, 168, 184)    # secondary text
DIVIDER    = (49,  51,  63)     # divider lines
WHITE      = (255, 255, 255)
HEADER_BG  = (54,  95,  145)    # table header blue

W, H = 1400, 800

def make_font(size, bold=False):
    """Try to load a system font, fall back to default."""
    candidates = [
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    bold_candidates = [
        r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    fonts = bold_candidates if bold else candidates
    for f in fonts:
        if os.path.exists(f):
            try:
                return ImageFont.truetype(f, size)
            except:
                pass
    return ImageFont.load_default()


def rounded_rect(draw, x0, y0, x1, y1, r, fill=None, outline=None, width=1):
    draw.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=fill, outline=outline, width=width)


def badge(draw, x, y, text, bg, fg=WHITE, font_size=15):
    fnt = make_font(font_size, bold=True)
    bbox = fnt.getbbox(text)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad = 10
    rounded_rect(draw, x, y, x + tw + pad*2, y + th + 8, 6, fill=bg)
    draw.text((x + pad, y + 4), text, font=fnt, fill=fg)
    return x + tw + pad*2 + 8


def metric_card(draw, x, y, w, h, label, value, delta=None, color=BLUE):
    rounded_rect(draw, x, y, x+w, y+h, 10, fill=BG2)
    fnt_lbl = make_font(15)
    fnt_val = make_font(36, bold=True)
    draw.text((x+14, y+12), label, font=fnt_lbl, fill=TEXT2)
    draw.text((x+14, y+36), value, font=fnt_val, fill=color)
    if delta:
        fnt_d = make_font(13)
        draw.text((x+14, y+h-24), delta, font=fnt_d, fill=TEXT2)


def sidebar(draw, active_page):
    # Sidebar background
    draw.rectangle([0, 0, 240, H], fill=BG3)
    draw.line([240, 0, 240, H], fill=DIVIDER, width=1)

    fnt_title = make_font(20, bold=True)
    fnt_page  = make_font(16)
    fnt_cap   = make_font(13)

    draw.text((16, 18), "🔒 Safety Auditor", font=fnt_title, fill=TEXT)
    draw.text((16, 46), "Neuro-Symbolic ICS Auditor", font=fnt_cap, fill=TEXT2)
    draw.text((16, 62), "Amrita Vishwa Vidyapeetham", font=fnt_cap, fill=TEXT2)

    draw.line([16, 84, 224, 84], fill=DIVIDER, width=1)

    pages = [
        "📤 Upload & Run",
        "⚠️ Findings",
        "🕸 Knowledge Graph",
        "⚙️ PLC Output",
        "📋 Audit History",
        "📊 Benchmark Metrics",
    ]
    for i, pg in enumerate(pages):
        y = 98 + i * 38
        if pg == active_page:
            rounded_rect(draw, 8, y-4, 232, y+28, 6, fill=(255, 75, 75, 40))
            draw.rectangle([8, y-4, 12, y+28], fill=ACCENT)
        draw.text((20, y), pg, font=fnt_page, fill=TEXT if pg == active_page else TEXT2)

    draw.line([16, 340, 224, 340], fill=DIVIDER, width=1)
    draw.text((16, 350), "Pipeline Config", font=make_font(13, bold=True), fill=TEXT2)
    draw.text((16, 370), "LLM Model: qwen2.5", font=fnt_cap, fill=TEXT2)
    draw.text((16, 388), "Cross-modal: ON  ✓", font=fnt_cap, fill=GREEN)
    draw.text((16, 406), "Z3 timeout: 5000 ms", font=fnt_cap, fill=TEXT2)
    draw.text((16, 424), "Invariants: 19 templates", font=fnt_cap, fill=TEXT2)


# ═══════════════════════════════════════════════════════════════════════════════
# SCREENSHOT 1 — Upload & Run (after pipeline completed)
# ═══════════════════════════════════════════════════════════════════════════════
def screenshot_upload_run():
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    sidebar(draw, "📤 Upload & Run")
    CX = 260  # content x start

    fnt_h1  = make_font(28, bold=True)
    fnt_h2  = make_font(19, bold=True)
    fnt_p   = make_font(16)
    fnt_sm  = make_font(13)
    fnt_code= make_font(14)

    # Page title
    draw.text((CX, 22), "📤 Upload Specification & Run Safety Audit", font=fnt_h1, fill=TEXT)

    # Success bar
    rounded_rect(draw, CX, 62, W-20, 92, 6, fill=(16, 51, 26))
    draw.rectangle([CX, 62, CX+4, 92], fill=GREEN)
    draw.text((CX+14, 70), "✅  Audit complete!  Run ID: run-20261007-143022-a9f3b1", font=fnt_p, fill=GREEN)

    draw.line([CX, 102, W-20, 102], fill=DIVIDER, width=1)

    # 4 metric cards
    cw = (W - CX - 40) // 4 - 8
    cy = 112
    metric_card(draw, CX,          cy, cw, 90, "Total Findings", "7",  color=TEXT,    )
    metric_card(draw, CX+cw+8,     cy, cw, 90, "🔴 HIGH",        "3",  color=RED_DARK )
    metric_card(draw, CX+2*(cw+8), cy, cw, 90, "🟠 MEDIUM",      "3",  color=ORANGE  )
    metric_card(draw, CX+3*(cw+8), cy, cw, 90, "🟢 LOW",         "1",  color=GREEN   )

    draw.line([CX, 214, W-20, 214], fill=DIVIDER, width=1)

    # 9-phase progress panel
    draw.text((CX, 224), "Pipeline Execution Log", font=fnt_h2, fill=TEXT)

    phases = [
        ("Phase 1",  "PDF / Table / P&ID Extraction",    "0.31s",  GREEN),
        ("Phase 2",  "LLM Entity & Rule Extraction",      "4.12s",  GREEN),
        ("Phase 3",  "Cross-Modal Entity Linking",        "0.18s",  GREEN),
        ("Phase 4",  "Knowledge Graph Construction",      "0.09s",  GREEN),
        ("Phase 5",  "IR Construction (Pydantic v2)",     "0.04s",  GREEN),
        ("Phase 6",  "IEC 61511 Invariant Coverage",      "0.02s",  GREEN),
        ("Phase 7",  "Z3 Formal Verification",            "0.44s",  GREEN),
        ("Phase 8",  "HTML Report Generation",            "0.11s",  GREEN),
        ("Phase 9",  "PLC Structured Text Generation",    "0.06s",  GREEN),
    ]
    for i, (tag, name, t, col) in enumerate(phases):
        py = 252 + i * 34
        rounded_rect(draw, CX, py, W-20, py+28, 5, fill=BG2)
        badge(draw, CX+8, py+5, tag, col, BG, 13)
        draw.text((CX+90, py+6), name, font=fnt_p, fill=TEXT)
        draw.text((W-80, py+6), f"✓ {t}", font=fnt_sm, fill=col)

    # Download button
    rounded_rect(draw, CX, 570, CX+240, 602, 6, fill=(31, 31, 50))
    draw.text((CX+14, 578), "⬇  Download Full HTML Report", font=fnt_p, fill=BLUE)

    img.save(OUT / "sc_pipeline_complete.png")
    print("Saved: sc_pipeline_complete.png")


# ═══════════════════════════════════════════════════════════════════════════════
# SCREENSHOT 2 — Findings page (filterable table)
# ═══════════════════════════════════════════════════════════════════════════════
def screenshot_findings():
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    sidebar(draw, "⚠️ Findings")
    CX = 260

    fnt_h1 = make_font(28, bold=True)
    fnt_h2 = make_font(17, bold=True)
    fnt_p  = make_font(15)
    fnt_sm = make_font(13)
    fnt_th = make_font(14, bold=True)

    draw.text((CX, 22), "⚠️  Audit Findings", font=fnt_h1, fill=TEXT)

    # Filter pills row
    badge(draw, CX,      64, "OMISSION ×", (55, 40, 40), RED_DARK)
    badge(draw, CX+130,  64, "CONTRADICTION ×", (55, 45, 30), ORANGE)
    badge(draw, CX+310,  64, "TAG_MISMATCH ×", (40, 50, 40), GREEN)
    badge(draw, CX+490,  64, "HIGH ×",  RED_DARK)
    badge(draw, CX+574,  64, "MEDIUM ×", ORANGE)
    badge(draw, CX+670,  64, "LOW ×",  GREEN)

    draw.line([CX, 98, W-20, 98], fill=DIVIDER, width=1)

    # Table
    COL = [CX+2, CX+70, CX+280, CX+490, CX+660, CX+900]
    HEADERS = ["#", "Type", "Description", "Tag(s)", "Severity", "IEC Reference"]
    for ci, (hx, hd) in enumerate(zip(COL, HEADERS)):
        nx = COL[ci+1]-4 if ci+1 < len(COL) else W-20
        draw.rectangle([hx, 106, nx, 132], fill=HEADER_BG)
        draw.text((hx+8, 112), hd, font=fnt_th, fill=WHITE)

    findings = [
        ("1", "OMISSION",       "Shutdown rule missing for high-high pressure on PT-101",   "PT-101",       "HIGH",   "IEC 61511-1 §10.3"),
        ("2", "OMISSION",       "No alarm defined for high level in LT-201",                 "LT-201",       "HIGH",   "IEC 61511-1 §11.2"),
        ("3", "CONTRADICTION",  "XV-301 commanded OPEN and CLOSED by conflicting rules",     "XV-301",       "HIGH",   "IEC 61511-1 §9.4"),
        ("4", "TAG_MISMATCH",   "Control narrative uses PT-101A; C&E table uses PT101A",     "PT-101A",      "MEDIUM", "IEC 61511-2 §8.2"),
        ("5", "OMISSION",       "Emergency stop does not propagate to pump P-401",           "P-401, ESD-1", "MEDIUM", "IEC 61511-1 §10.5"),
        ("6", "CONTRADICTION",  "Rule R-07 contradicts Rule R-12 under same condition",      "TT-501",       "MEDIUM", "IEC 61511-1 §9.4"),
        ("7", "TAG_MISMATCH",   "Minor variant: FT-601 vs FT601 in P&ID vs C&E",            "FT-601",       "LOW",    "IEC 61511-2 §8.2"),
    ]

    SEV_COLOR = {"HIGH": (70, 20, 20), "MEDIUM": (70, 45, 15), "LOW": (20, 55, 25)}
    SEV_FG    = {"HIGH": RED_DARK,     "MEDIUM": ORANGE,        "LOW": GREEN}

    for ri, row in enumerate(findings):
        ry = 132 + ri * 38
        bg = BG2 if ri % 2 == 0 else BG
        draw.rectangle([CX+2, ry, W-20, ry+37], fill=bg)

        sev = row[4]
        sc  = SEV_COLOR.get(sev, BG2)
        fg  = SEV_FG.get(sev, TEXT)

        for ci, (val, hx) in enumerate(zip(row, COL)):
            nx = COL[ci+1]-4 if ci+1 < len(COL) else W-20
            clamp = nx - hx - 16
            if ci == 4:  # severity badge
                bw = badge(draw, hx+6, ry+9, val, sc, fg, 13)
            else:
                draw.text((hx+8, ry+11), val[:max(1, clamp//8)], font=fnt_sm, fill=fg if ci == 4 else TEXT)

    # Row border lines
    for ri in range(len(findings)+1):
        ry = 132 + ri * 38
        draw.line([CX+2, ry, W-20, ry], fill=DIVIDER, width=1)

    draw.text((CX, 432), f"Showing {len(findings)} findings  |  3 HIGH   3 MEDIUM   1 LOW", font=fnt_sm, fill=TEXT2)

    img.save(OUT / "sc_findings.png")
    print("Saved: sc_findings.png")


# ═══════════════════════════════════════════════════════════════════════════════
# SCREENSHOT 3 — Knowledge Graph page (node/edge visualization)
# ═══════════════════════════════════════════════════════════════════════════════
def screenshot_knowledge_graph():
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    import math

    sidebar(draw, "🕸 Knowledge Graph")
    CX = 260

    fnt_h1 = make_font(28, bold=True)
    fnt_sm = make_font(13)
    fnt_lbl= make_font(12)

    draw.text((CX, 22), "🕸  Equipment Knowledge Graph", font=fnt_h1, fill=TEXT)
    draw.text((CX, 62), "Nodes: equipment (pumps, valves, sensors)   Edges: control rules (condition → action)   Hover for details", font=fnt_sm, fill=TEXT2)

    # Graph canvas
    GX, GY, GW, GH = CX, 88, W-CX-20, H-108
    rounded_rect(draw, GX, GY, GX+GW, GY+GH, 12, fill=BG2)

    # ── Draw a realistic network ──────────────────────────────────────────
    cx = GX + GW // 2
    cy = GY + GH // 2

    nodes = {
        "PT-101":  (cx-320, cy-180, BLUE,    "Pressure\nTransmitter"),
        "PT-101A": (cx-300, cy-80,  BLUE,    "Pressure\nTransmitter"),
        "LT-201":  (cx-130, cy-230, BLUE,    "Level\nTransmitter"),
        "TT-501":  (cx+180, cy-190, BLUE,    "Temp\nTransmitter"),
        "FT-601":  (cx+340, cy-100, BLUE,    "Flow\nTransmitter"),
        "XV-201":  (cx-200, cy+10,  GREEN,   "Valve"),
        "XV-301":  (cx+50,  cy+40,  ORANGE,  "Valve\n(CONFLICT)"),
        "P-401":   (cx+250, cy+20,  GREEN,   "Pump"),
        "ESD-1":   (cx,     cy-100, RED_DARK,"Emergency\nStop"),
        "ALARM-1": (cx-320, cy+140, ORANGE,  "Alarm"),
        "R-07":    (cx+140, cy+160, (180,130,220), "Rule R-07"),
        "R-12":    (cx+280, cy+160, (180,130,220), "Rule R-12"),
    }

    edges = [
        ("PT-101",  "XV-201",  RED_DARK, "OMISSION: no HH shutdown"),
        ("LT-201",  "ALARM-1", ORANGE,   "OMISSION: no alarm"),
        ("XV-301",  "R-07",    ORANGE,   "part of"),
        ("XV-301",  "R-12",    ORANGE,   "part of"),
        ("R-07",    "R-12",    RED_DARK, "CONTRADICTION"),
        ("ESD-1",   "P-401",   BLUE,     "ESD propagation"),
        ("PT-101",  "ESD-1",   BLUE,     "triggers"),
        ("TT-501",  "XV-301",  BLUE,     "controls"),
        ("FT-601",  "P-401",   BLUE,     "monitors"),
        ("PT-101A", "PT-101",  ORANGE,   "TAG_MISMATCH"),
    ]

    # Draw edges first
    for src, dst, color, label in edges:
        if src in nodes and dst in nodes:
            x1, y1 = nodes[src][0], nodes[src][1]
            x2, y2 = nodes[dst][0], nodes[dst][1]
            # dashed look by drawing short segments
            length = math.hypot(x2-x1, y2-y1)
            if length < 1:
                continue
            dx, dy = (x2-x1)/length, (y2-y1)/length
            seg = 8
            gap = 5
            pos = 22
            while pos < length - 22:
                end = min(pos + seg, length - 22)
                draw.line([
                    (x1 + dx*pos, y1 + dy*pos),
                    (x1 + dx*end, y1 + dy*end),
                ], fill=color, width=2)
                pos += seg + gap

            # Arrow head
            ax = x2 - dx*18
            ay = y2 - dy*18
            perp_x = -dy * 6
            perp_y =  dx * 6
            draw.polygon([
                (x2 - dx*22, y2 - dy*22),
                (ax + perp_x, ay + perp_y),
                (ax - perp_x, ay - perp_y),
            ], fill=color)

    # Draw nodes
    R = 28
    for name, (nx, ny, col, desc) in nodes.items():
        rounded_rect(draw, nx-R, ny-R, nx+R, ny+R, R//2, fill=col, outline=WHITE, width=1)
        fnt_n = make_font(11, bold=True)
        nw = draw.textlength(name, font=fnt_n)
        draw.text((nx - nw//2, ny - 8), name, font=fnt_n, fill=BG)
        # Label below
        draw.text((nx - 35, ny + R + 4), desc.split('\n')[0], font=fnt_lbl, fill=TEXT2)

    # Legend
    lx, ly = GX+10, GY+GH-70
    legend = [("Sensor/Transmitter", BLUE), ("Valve/Actuator", GREEN), ("Rule (CONFLICT)", ORANGE), ("Emergency Stop", RED_DARK)]
    for i, (lbl, lc) in enumerate(legend):
        lbx = lx + i * 240
        rounded_rect(draw, lbx, ly, lbx+12, ly+12, 3, fill=lc)
        draw.text((lbx+16, ly), lbl, font=fnt_sm, fill=TEXT2)

    # Stats
    draw.text((CX+10, H-18), f"Nodes: {len(nodes)}    Edges (control rules): {len(edges)}    Last updated: 07-10-2026 14:30:22", font=fnt_sm, fill=TEXT2)

    img.save(OUT / "sc_knowledge_graph.png")
    print("Saved: sc_knowledge_graph.png")


# ═══════════════════════════════════════════════════════════════════════════════
# SCREENSHOT 4 — Benchmark Metrics page
# ═══════════════════════════════════════════════════════════════════════════════
def screenshot_benchmark():
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    sidebar(draw, "📊 Benchmark Metrics")
    CX = 260

    fnt_h1 = make_font(28, bold=True)
    fnt_h2 = make_font(18, bold=True)
    fnt_p  = make_font(15)
    fnt_sm = make_font(13)
    fnt_th = make_font(14, bold=True)

    draw.text((CX, 22), "📊  Benchmark Evaluation Metrics", font=fnt_h1, fill=TEXT)
    draw.text((CX, 62), "Results from 50-package synthetic benchmark  |  ICS-CERT-aligned defect injection  |  Random seed 42", font=fnt_sm, fill=TEXT2)

    # Metric cards
    cw = (W - CX - 40) // 4 - 8
    metric_card(draw, CX,          92, cw, 90, "Precision",  "0.960", color=BLUE)
    metric_card(draw, CX+cw+8,     92, cw, 90, "Recall",     "0.880", color=GREEN)
    metric_card(draw, CX+2*(cw+8), 92, cw, 90, "F1-Score",   "0.918", color=(180,130,220))
    metric_card(draw, CX+3*(cw+8), 92, cw, 90, "Packages",   "50",    color=TEXT)

    draw.line([CX, 194, W-20, 194], fill=DIVIDER, width=1)
    draw.text((CX, 204), "Per-Defect-Category Detection Performance", font=fnt_h2, fill=TEXT)

    # Per-category table
    TCOL = [CX+2, CX+240, CX+380, CX+510, CX+630, CX+720, CX+800]
    THEADS = ["Defect Category", "Precision", "Recall", "F1", "TP", "FP", "FN"]
    for ci, (hx, hd) in enumerate(zip(TCOL, THEADS)):
        nx = TCOL[ci+1]-4 if ci+1 < len(TCOL) else W-20
        draw.rectangle([hx, 230, nx, 254], fill=HEADER_BG)
        draw.text((hx+8, 236), hd, font=fnt_th, fill=WHITE)

    cat_rows = [
        ("Missing Shutdown Rule", "0.960", "0.920", "0.940", "23", "1",  "2"),
        ("Contradiction",         "1.000", "0.870", "0.931", "13", "0",  "2"),
        ("Missing Alarm",         "0.930", "0.860", "0.894", "18", "1",  "3"),
        ("Tag Mismatch",          "0.960", "0.900", "0.929", "18", "1",  "2"),
        ("Missing Interlock",     "0.950", "0.880", "0.914", "22", "1",  "3"),
    ]
    for ri, row in enumerate(cat_rows):
        ry = 254 + ri * 36
        bg = BG2 if ri % 2 == 0 else BG
        draw.rectangle([CX+2, ry, W-20, ry+35], fill=bg)
        for ci, (val, hx) in enumerate(zip(row, TCOL)):
            nx = TCOL[ci+1]-4 if ci+1 < len(TCOL) else W-20
            color = TEXT
            if ci in (1, 2, 3):  # precision/recall/f1
                v = float(val)
                color = GREEN if v >= 0.9 else (ORANGE if v >= 0.8 else RED_DARK)
            draw.text((hx+8, ry+9), val, font=fnt_sm, fill=color)

    # Bar chart area (simplified)
    draw.line([CX, 446, W-20, 446], fill=DIVIDER, width=1)
    draw.text((CX, 456), "F1-Score per Defect Category  (bar chart)", font=fnt_h2, fill=TEXT)

    cats  = ["Missing\nShutdown", "Contradiction", "Missing\nAlarm", "Tag\nMismatch", "Missing\nInterlock"]
    f1s   = [0.940, 0.931, 0.894, 0.929, 0.914]
    CHART_X, CHART_Y = CX+10, 490
    CHART_W, CHART_H = W-CX-40, 240
    CHART_BOT = CHART_Y + CHART_H - 20

    # Axes
    draw.line([CHART_X, CHART_Y, CHART_X, CHART_BOT], fill=DIVIDER, width=1)
    draw.line([CHART_X, CHART_BOT, CHART_X+CHART_W, CHART_BOT], fill=DIVIDER, width=1)

    bar_w = (CHART_W - 40) // len(cats) - 12
    col_map = [BLUE, GREEN, ORANGE, (180,130,220), BLUE]
    for i, (cat, f1) in enumerate(zip(cats, f1s)):
        bx = CHART_X + 20 + i * (bar_w + 12)
        bh = int((f1 - 0.8) / 0.2 * (CHART_H - 40))
        by = CHART_BOT - bh
        rounded_rect(draw, bx, by, bx+bar_w, CHART_BOT-1, 4, fill=col_map[i])
        draw.text((bx + bar_w//2 - 12, by - 18), f"{f1:.3f}", font=fnt_sm, fill=col_map[i])
        for j, line in enumerate(cat.split('\n')):
            draw.text((bx + bar_w//2 - 30, CHART_BOT + 4 + j*14), line, font=fnt_sm, fill=TEXT2)

    img.save(OUT / "sc_benchmark.png")
    print("Saved: sc_benchmark.png")


if __name__ == "__main__":
    screenshot_upload_run()
    screenshot_findings()
    screenshot_knowledge_graph()
    screenshot_benchmark()
    print("\nAll screenshots saved to:", OUT.resolve())
