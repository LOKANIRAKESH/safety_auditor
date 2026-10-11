"""
Panel Review 2 — Safety Auditor  v3
One dedicated implementation slide per pipeline phase (all 9 phases).
Imports all helpers and colors from generate_ppt_v2.
"""

from generate_ppt_v2 import (
    # helpers
    new_prs, blank, add_rect, add_line, txb, add_run, add_bullet,
    add_chrome, add_slide_title, add_callout_box, add_styled_table,
    _set_cell_bg, _para_spacing,
    # slide functions (reused verbatim)
    slide_title, slide_guide_approval, slide_intro, slide_problem,
    slide_architecture, slide_impl_progress, slide_section_divider,
    slide_algorithm, slide_algorithm_linking, slide_eval_metrics,
    slide_tools, slide_results_pipeline, slide_results_findings,
    slide_results_kg, slide_results_benchmark, slide_datasets,
    slide_tech_activities, slide_project_plan, slide_conclusion,
    slide_references,
    # colors
    AMRITA_MAROON, AMRITA_NAVY, AMRITA_STEEL, ACCENT_TEAL,
    WHITE, NEAR_WHITE, BLACK, GREY_TEXT, GREY_DIVIDER,
    ORANGE, TABLE_HEADER_BG, TABLE_ALT,
    DONE_BG, DONE_FG, INPROG_BG, INPROG_FG,
    SLIDE_W, SLIDE_H, DATE_STR, SCHOOL_STR,
    # pptx primitives
    Inches, Pt, PP_ALIGN, RGBColor,
)

# ── Color helpers ──────────────────────────────────────────────────────────────
CODE_BG       = RGBColor(0x1A, 0x1A, 0x2E)   # dark code panel background
KW_COLOR      = RGBColor(0x79, 0xB8, 0xFF)   # keywords — bright blue
CMT_COLOR     = RGBColor(0x6A, 0x99, 0x55)   # comments — green
STR_COLOR     = RGBColor(0xCE, 0x9B, 0x78)   # strings/decorators — orange
CODE_FG       = RGBColor(0xE0, 0xE0, 0xFF)   # normal code — near-white
ANNOT_LABEL   = RGBColor(0xFF, 0xC5, 0x5E)   # annotation section labels
ANNOT_VAL     = RGBColor(0xD4, 0xE6, 0xF1)   # annotation bullet text
DONE_BADGE_BG = RGBColor(0x1A, 0x7F, 0x37)
PROG_BADGE_BG = RGBColor(0xCC, 0x6A, 0x00)
PLAN_BADGE_BG = RGBColor(0x2E, 0x74, 0xB5)


_KEYWORDS = {
    "class", "def", "return", "if", "elif", "else", "for", "while",
    "import", "from", "try", "except", "yield", "with", "raise",
    "FOR", "IF", "RETURN", "FUNCTION", "WHILE", "AND", "OR", "NOT",
}


def _is_keyword_line(line: str) -> bool:
    stripped = line.strip()
    return any(stripped.startswith(kw + " ") or stripped == kw
               for kw in _KEYWORDS)


def _is_comment_line(line: str) -> bool:
    s = line.strip()
    return s.startswith("#") or s.startswith("//") or s.startswith("(*")


def _is_string_or_deco(line: str) -> bool:
    s = line.strip()
    return s.startswith("@") or s.startswith('"') or s.startswith("'")


# ── Core phase-impl slide builder ─────────────────────────────────────────────

def slide_phase_impl(prs, phase_num: int, title: str, subtitle: str,
                     code_lines: list, annot_sections: list,
                     accent=None):
    """
    Two-panel phase implementation slide.

    code_lines   : list of str — shown in dark code panel on the left
    annot_sections: list of (label_str, [value_str, ...]) — shown on the right
    """
    if accent is None:
        accent = AMRITA_MAROON if phase_num % 2 == 1 else AMRITA_STEEL

    slide = blank(prs)
    add_chrome(slide, accent)
    add_slide_title(
        slide,
        f"Phase {phase_num}  —  {title}  :  Implementation Detail",
        subtitle
    )

    # ── Left: dark code panel ──────────────────────────────────────────────
    CODE_L = Inches(0.3)
    CODE_T = Inches(1.55)
    CODE_W = Inches(7.6)
    CODE_H = Inches(5.55)

    add_rect(slide, CODE_L, CODE_T, CODE_W, CODE_H,
             fill=CODE_BG, line_color=accent, radius=True)

    tb, tf = txb(slide,
                 CODE_L + Inches(0.18), CODE_T + Inches(0.12),
                 CODE_W - Inches(0.36), CODE_H - Inches(0.24),
                 wrap=True)

    first = True
    for line in code_lines:
        if first:
            p = tf.paragraphs[0]
            first = False
        else:
            p = tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        run = p.add_run()
        run.text = line
        run.font.size = Pt(11.5)
        if _is_comment_line(line):
            run.font.color.rgb = CMT_COLOR
            run.font.italic = True
        elif _is_keyword_line(line):
            run.font.color.rgb = KW_COLOR
            run.font.bold = True
        elif _is_string_or_deco(line):
            run.font.color.rgb = STR_COLOR
        else:
            run.font.color.rgb = CODE_FG
        _para_spacing(p, before_pt=0.5)

    # ── Right: annotation panel ────────────────────────────────────────────
    ANN_L = Inches(8.1)
    ANN_T = Inches(1.55)
    ANN_W = Inches(4.9)
    ANN_H = Inches(5.55)

    add_rect(slide, ANN_L, ANN_T, ANN_W, ANN_H,
             fill=AMRITA_NAVY, radius=True)

    y = ANN_T + Inches(0.15)
    for label, values in annot_sections:
        # Section label
        txb(slide, ANN_L + Inches(0.18), y,
            ANN_W - Inches(0.36), Inches(0.34),
            label, size=Pt(12), bold=True, color=ANNOT_LABEL)
        y += Inches(0.34)
        add_line(slide,
                 ANN_L + Inches(0.18), y,
                 ANN_L + ANN_W - Inches(0.18), y,
                 color=RGBColor(0x3A, 0x5F, 0x9A), w=Pt(0.5))
        y += Inches(0.06)

        for v in values:
            # Badge for status values
            badge_bg = None
            vtext = v
            if v.upper() in ("COMPLETE", "COMPLETED", "DONE"):
                badge_bg = DONE_BADGE_BG
            elif "PROGRESS" in v.upper():
                badge_bg = PROG_BADGE_BG
            elif "PLAN" in v.upper():
                badge_bg = PLAN_BADGE_BG

            if badge_bg:
                add_rect(slide, ANN_L + Inches(0.20), y + Inches(0.03),
                         Inches(1.4), Inches(0.26),
                         fill=badge_bg, radius=True)
                txb(slide, ANN_L + Inches(0.22), y,
                    Inches(1.38), Inches(0.32),
                    vtext, size=Pt(11), bold=True,
                    color=WHITE, align=PP_ALIGN.CENTER)
            else:
                txb(slide, ANN_L + Inches(0.22), y,
                    ANN_W - Inches(0.44), Inches(0.32),
                    "·  " + vtext, size=Pt(11), color=ANNOT_VAL, wrap=True)
            y += Inches(0.30)
        y += Inches(0.10)  # gap between sections


# ── Updated contents slide ─────────────────────────────────────────────────────

def slide_contents_v3(prs):
    slide = blank(prs)
    add_chrome(slide, AMRITA_STEEL)
    add_slide_title(slide, "Contents")

    col1 = [
        ("Introduction & Motivation",                    AMRITA_NAVY,   False),
        ("Problem Statement",                            AMRITA_NAVY,   False),
        ("System Architecture & Progress",               AMRITA_NAVY,   False),
        ("Phase 1  —  Multimodal Ingestion",             AMRITA_MAROON, True),
        ("Phase 2  —  LLM Entity Extraction",            AMRITA_STEEL,  True),
        ("Phase 3  —  Cross-Modal Linking",              AMRITA_MAROON, True),
        ("Phase 4  —  Knowledge Graph",                  AMRITA_STEEL,  True),
        ("Phase 5  —  IR Construction",                  AMRITA_MAROON, True),
    ]
    col2 = [
        ("Phase 6  —  Invariant Coverage",               AMRITA_STEEL,  True),
        ("Phase 7  —  Z3 Formal Verification",           AMRITA_MAROON, True),
        ("Phase 8  —  Audit Report",                     AMRITA_STEEL,  True),
        ("Phase 9  —  PLC Code Generation",              AMRITA_MAROON, True),
        ("§01  Algorithms & Evaluation Metrics",         AMRITA_NAVY,   False),
        ("§02  Tools and Methods",                       AMRITA_NAVY,   False),
        ("§03  Preliminary Results",                     AMRITA_NAVY,   False),
        ("Conclusion & References",                      AMRITA_NAVY,   False),
    ]

    for col_items, lx in [(col1, Inches(0.3)), (col2, Inches(6.85))]:
        for i, (txt, col, is_section) in enumerate(col_items):
            y = Inches(1.55) + i * Inches(0.60)
            bar_color = AMRITA_MAROON if is_section else AMRITA_STEEL
            add_rect(slide, lx, y, Inches(0.06), Inches(0.36), fill=bar_color)
            txb(slide, lx + Inches(0.15), y, Inches(6.4), Inches(0.46),
                txt, size=Pt(17), bold=is_section, color=col)


# ══════════════════════════════════════════════════════════════════════════════
# PHASE IMPLEMENTATION SLIDES (1–9)
# ══════════════════════════════════════════════════════════════════════════════

def slide_phase1_impl(prs):
    code = [
        "# src/ingestion/  —  6 modules, ~1400 lines",
        "from src.ingestion.pdf_extractor import PDFExtractor, TextBlock",
        "from src.ingestion.image_extractor import PDFImageExtractor, IMAGE_SCANNED",
        "from src.ingestion.chunker import SemanticChunker, DocumentChunk",
        "from src.ingestion.entity_registry import GlobalEntityRegistry",
        "",
        "class PDFExtractor:",
        "  def extract(pdf_path) -> List[TextBlock]:",
        "    doc = fitz.open(str(pdf_path))",
        "    for page in doc:",
        "      for b in page.get_text('blocks'):",
        "        yield TextBlock(text=b[4], page=page_num,",
        "          block_type='heading' if bold else 'paragraph')",
        "",
        "class PDFImageExtractor:",
        "  def _ocr_full_page(page, pid_ext, config):",
        "    # Pass 1 — PSM 11 + whitelist  → ISA-5.1 tags",
        "    extraction = pid_ext._extract_from_image(img)",
        "    # Pass 2 — PSM 3, no whitelist → full prose text",
        "    full_text = pytesseract.image_to_string(",
        "      denoised, config='--psm 3 --oem 3').strip()",
        "    return ExtractedImage(image_class=IMAGE_SCANNED,",
        "      extracted_tags=extraction.tags,",
        "      full_text_ocr=full_text, width=w, height=h)",
        "",
        "class SemanticChunker:",
        "  def chunk(blocks: List[TextBlock]) -> List[DocumentChunk]:",
        "    # Group blocks by heading boundary",
        "    # Split oversized sections at chunk_max_chars=5000",
        "    # Overlap 300 chars across section boundaries",
        "",
        "class GlobalEntityRegistry:",
        "  def build_from_blocks(blocks):",
        "    TAG_RE = re.compile(r'\\b([A-Z]{1,3}-[0-9]{3,4}[A-Z]?)\\b')",
        "    for block in blocks:",
        "      for m in TAG_RE.finditer(block.text):",
        "        self._entries[m.group(1)] = TagEntry(...)",
        "    return self",
    ]
    annot = [
        ("INPUT", ["PDF files (text + scanned)", "P&ID drawing images", "Cause-Effect table PDFs"]),
        ("OUTPUT", ["List[DocumentChunk]", "GlobalEntityRegistry", "List[str] pid_tags", "List[ExtractedTable]"]),
        ("KEY CLASSES", ["PDFExtractor → TextBlock", "PDFImageExtractor → ExtractedImage", "SemanticChunker → DocumentChunk", "GlobalEntityRegistry → TagEntry", "PIDExtractor, TableExtractor"]),
        ("TECHNOLOGIES", ["PyMuPDF (fitz)", "Tesseract 5.4.0 (PSM 3 + 11)", "OpenCV (cv2)", "camelot / pdfplumber", "regex ISA-5.1 pattern"]),
        ("STATUS", ["COMPLETE"]),
    ]
    slide_phase_impl(prs, 1, "Multimodal Ingestion",
                     "PDF text · Scanned-page OCR (PSM 11 + PSM 3) · Semantic chunking · Global tag registry",
                     code, annot, accent=AMRITA_MAROON)


def slide_phase2_impl(prs):
    code = [
        "# src/extraction/entity_extractor.py",
        "class EntityExtractor:",
        "  def __init__(self, config):",
        "    self.llm = OllamaLLM(model='qwen2.5:14b',",
        "      format='json', temperature=0.1)",
        "",
        "  def _build_chunk_prompt(chunk, registry):",
        "    return (",
        "      f'DOCUMENT CONTEXT\\n'",
        "      f'{registry.as_context_string()}\\n\\n'",
        "      f'SECTION: {chunk.section_title}\\n'",
        "      f'(pages {chunk.page_start}–{chunk.page_end})\\n\\n'",
        "      f'{chunk.text[:5000]}\\n\\n'",
        "      'Return JSON: {\"entities\":[...], \"rules\":[...]}'",
        "    )",
        "",
        "  def extract_from_chunks(chunks, registry):",
        "    all_entities, all_rules = [], []",
        "    for chunk in chunks:            # one call per chunk",
        "      prompt = self._build_chunk_prompt(chunk, registry)",
        "      raw = self.llm.invoke(prompt)",
        "      parsed = self._parse_llm_output(raw)",
        "      # Pydantic v2 validation + null-guard",
        "      for e in parsed.get('entities', []):",
        "        if e.get('tag'):",
        "          all_entities.append(ExtractedEntity(**e))",
        "      for r in parsed.get('rules', []):",
        "        if r.get('rule_id') and r.get('confidence', 0) >= 0.7:",
        "          all_rules.append(ExtractedRule(**r))",
        "    return ExtractionResult(all_entities, all_rules)",
        "",
        "@dataclass",
        "class ExtractedEntity:",
        "  tag: str;  entity_class: str;  subclass: str",
        "  description: str;  confidence: float",
        "",
        "@dataclass",
        "class ExtractedRule:",
        "  rule_id: str;  condition_tag: str",
        "  condition_operator: str;  condition_threshold: float",
        "  action: str;  equipment_tag: str;  confidence: float",
    ]
    annot = [
        ("INPUT", ["List[DocumentChunk]", "GlobalEntityRegistry (tag context)"]),
        ("OUTPUT", ["ExtractionResult", "  ├ List[ExtractedEntity]", "  └ List[ExtractedRule]"]),
        ("KEY CLASSES", ["EntityExtractor", "ExtractionResult", "ExtractedEntity", "ExtractedRule", "DocumentChunk"]),
        ("TECHNOLOGIES", ["Ollama (local LLM runtime)", "Qwen 2.5 14B model", "LangChain OllamaLLM", "Pydantic v2 validation", "JSON structured output"]),
        ("STATUS", ["COMPLETE"]),
    ]
    slide_phase_impl(prs, 2, "LLM Entity Extraction",
                     "Ollama + Qwen 2.5 · Global registry injection · Pydantic v2 validation",
                     code, annot, accent=AMRITA_STEEL)


def slide_phase3_impl(prs):
    code = [
        "# src/linking/cross_modal_linker.py",
        "from rapidfuzz.fuzz import token_sort_ratio",
        "from sentence_transformers import SentenceTransformer",
        "from sklearn.metrics.pairwise import cosine_similarity",
        "",
        "class CrossModalLinker:",
        "  def __init__(self):",
        "    self.model = SentenceTransformer('all-MiniLM-L6-v2')",
        "",
        "  def link(entities, rules, pid_tags):",
        "    canonical: dict[str, List[ExtractedEntity]] = {}",
        "",
        "    # Step 1 — Exact canonical match  O(1) hash",
        "    tag_map = {e.tag.upper(): e for e in entities}",
        "    for pid_tag in pid_tags:",
        "      if pid_tag.upper() in tag_map:",
        "        _merge(canonical, pid_tag, tag_map[pid_tag.upper()])",
        "",
        "    # Step 2 — Fuzzy match  (RapidFuzz token_sort_ratio)",
        "    for a, b in combinations(entities, 2):",
        "      score = token_sort_ratio(a.tag, b.tag) / 100.0",
        "      if score >= 0.85:          # threshold",
        "        findings.append(AuditFinding(TAG_MISMATCH,",
        "          description=f'{a.tag} ~ {b.tag}  score={score:.2f}'))",
        "",
        "    # Step 3 — Embedding cosine similarity",
        "    tags = [e.tag for e in entities]",
        "    embeds = self.model.encode(tags)",
        "    sim_matrix = cosine_similarity(embeds)",
        "    for i, j in combinations(range(len(tags)), 2):",
        "      if sim_matrix[i][j] >= 0.75:   # threshold",
        "        _merge(canonical, tags[i], entities[j])",
        "",
        "    return [LinkedEntity.from_group(g)",
        "            for g in canonical.values()]",
    ]
    annot = [
        ("INPUT", ["List[ExtractedEntity] (3 modalities)", "List[ExtractedRule]", "List[str] pid_tags from Phase 1"]),
        ("OUTPUT", ["List[LinkedEntity]", "  (canonical merged entities)", "TAG_MISMATCH AuditFindings"]),
        ("CASCADE", ["Step 1: exact match  O(1)", "Step 2: RapidFuzz ≥ 0.85", "Step 3: cosine sim ≥ 0.75"]),
        ("TECHNOLOGIES", ["RapidFuzz (fuzzy string)", "sentence-transformers", "all-MiniLM-L6-v2 (80MB)", "sklearn cosine_similarity"]),
        ("CONFIG", ["enable_cross_modal_linking=True", "(ablation flag — can disable)"]),
        ("STATUS", ["COMPLETE"]),
    ]
    slide_phase_impl(prs, 3, "Cross-Modal Entity Linking",
                     "3-step cascade: Exact → RapidFuzz ≥ 85 → all-MiniLM-L6-v2 cosine ≥ 0.75",
                     code, annot, accent=AMRITA_MAROON)


def slide_phase4_impl(prs):
    code = [
        "# src/knowledge/graph_builder.py",
        "import networkx as nx",
        "",
        "_CLASS_COLORS = {",
        "  'Pump': '#4fc3f7',  'Valve': '#81c784',",
        "  'Sensor': '#ffb74d', 'Controller': '#ce93d8',",
        "  'Interlock': '#ef9a9a', 'Alarm': '#fff176',",
        "}",
        "",
        "class KnowledgeGraphBuilder:",
        "  def build(linked_entities, rules) -> EquipmentGraph:",
        "    G = nx.DiGraph()",
        "    # Nodes = canonical equipment tags",
        "    for entity in linked_entities:",
        "      G.add_node(entity.canonical_tag,",
        "        entity_class=entity.entity_class,",
        "        description=entity.description)",
        "    # Edges = control rules (condition → action)",
        "    for rule in rules:",
        "      edge_label = (f'{rule.condition_operator}'",
        "                    f'{rule.condition_threshold}'",
        "                    f'{rule.condition_unit}→{rule.action}')",
        "      G.add_edge(rule.condition_tag,",
        "        rule.equipment_tag, label=edge_label)",
        "    # Semantic edges (sensor → co-located equipment)",
        "    self._add_class_relationships(G, linked_entities)",
        "    return EquipmentGraph(G, G.number_of_nodes(),",
        "                          G.number_of_edges())",
        "",
        "class EquipmentGraph:",
        "  def to_pyvis_html(self, output_path):",
        "    # Embeds vis-network.min.js inline (688 KB)",
        "    # No CDN dependency — works in offline/firewalled env",
        "    html = _make_vis_html(nodes_data, edges_data)",
        "    output_path.write_text(html, encoding='utf-8')",
    ]
    annot = [
        ("INPUT", ["List[LinkedEntity]", "List[ExtractedRule]"]),
        ("OUTPUT", ["EquipmentGraph", "  ├ nx.DiGraph", "  └ vis.js HTML (self-contained)"]),
        ("KEY CLASSES", ["KnowledgeGraphBuilder", "EquipmentGraph", "_make_vis_html()"]),
        ("TECHNOLOGIES", ["NetworkX DiGraph", "vis.js 9.1.9 (inline embed)", "Streamlit st.iframe()", "OpenCV color nodes"]),
        ("DESIGN NOTE", ["vis-network.min.js bundled locally", "avoids corporate CDN block"]),
        ("STATUS", ["COMPLETE"]),
    ]
    slide_phase_impl(prs, 4, "Knowledge Graph Construction",
                     "NetworkX DiGraph · Equipment nodes · Control-rule edges · vis.js inline HTML",
                     code, annot, accent=AMRITA_STEEL)


def slide_phase5_impl(prs):
    code = [
        "# src/ir/rule_builder.py",
        "from pydantic import BaseModel, field_validator",
        "from enum import Enum",
        "",
        "class RuleAction(str, Enum):",
        "  STOP  = 'STOP'",
        "  START = 'START'",
        "  OPEN  = 'OPEN'",
        "  CLOSE = 'CLOSE'",
        "  TRIP  = 'TRIP'",
        "",
        "class Condition(BaseModel):",
        "  sensor_tag: str",
        "  operator:   str   # '>', '<', '>=', '<='",
        "  threshold:  float",
        "  unit:       str",
        "",
        "class ControlRule(BaseModel):",
        "  rule_id:       str",
        "  condition:     Condition",
        "  action:        RuleAction",
        "  equipment_tag: str",
        "  confidence:    float",
        "  needs_review:  bool = False",
        "  iec_clause:    str  = ''",
        "",
        "class RuleBuilder:",
        "  def build(raw_rules) -> List[ControlRule]:",
        "    ir_rules = []",
        "    for r in raw_rules:",
        "      try:",
        "        rule = ControlRule(",
        "          condition=Condition(",
        "            sensor_tag=r.condition_tag,",
        "            operator=r.condition_operator,",
        "            threshold=r.condition_threshold,",
        "            unit=r.condition_unit),",
        "          action=RuleAction[r.action.upper()],",
        "          confidence=r.confidence,",
        "          needs_review=(r.confidence < 0.7))",
        "        ir_rules.append(rule)",
        "      except (ValidationError, KeyError) as e:",
        "        logger.warning(f'Skipped {r.rule_id}: {e}')",
        "    return ir_rules",
    ]
    annot = [
        ("INPUT", ["List[ExtractedRule] (from Phase 2)"]),
        ("OUTPUT", ["List[ControlRule]", "  (Pydantic v2 validated)"]),
        ("KEY CLASSES", ["RuleBuilder", "ControlRule (BaseModel)", "Condition (BaseModel)", "RuleAction (str, Enum)"]),
        ("VALIDATION", ["confidence < 0.7 → needs_review=True", "Unknown action → ValidationError", "Missing tag → skipped + warned"]),
        ("TECHNOLOGIES", ["Pydantic v2 (BaseModel)", "Python Enum (str)"]),
        ("STATUS", ["COMPLETE"]),
    ]
    slide_phase_impl(prs, 5, "Intermediate Representation",
                     "Pydantic v2 ControlRule model · RuleAction enum · Confidence-based review flag",
                     code, annot, accent=AMRITA_MAROON)


def slide_phase6_impl(prs):
    code = [
        "# src/invariants/ + data/invariant_templates/",
        "# 19 templates across 5 JSON category files",
        "",
        "# Template example — pump_hh_shutdown.json:",
        "# {",
        "#   'invariant_id': 'INV-001',",
        "#   'description': 'High-High Pressure Shutdown',",
        "#   'required_entity_class': 'Pump',",
        "#   'required_rule_type': 'SHUTDOWN',",
        "#   'condition_type': 'PRESSURE_HH',",
        "#   'iec_clause': 'IEC 61511-1 §11.4',",
        "#   'severity_if_missing': 'HIGH'",
        "# }",
        "",
        "class SafetyInvariantLibrary:",
        "  def load(templates_dir):",
        "    for f in templates_dir.glob('*.json'):",
        "      self.invariants.extend(json.loads(f.read_text()))",
        "    # Also loads HIGH-severity rules from standards_kb_*.json",
        "    logger.info(f'{len(self.invariants)} invariants loaded')",
        "",
        "  def evaluate_coverage(rules, entities):",
        "    for inv in self.invariants:",
        "      # Find relevant equipment for this invariant",
        "      relevant = [e for e in entities",
        "        if e.entity_class == inv.required_entity_class]",
        "      # Check if any rule covers this invariant",
        "      covered = any(",
        "        r.action.name == inv.required_rule_type",
        "        and any(e.canonical_tag in (r.condition_tag,",
        "                r.equipment_tag) for e in relevant)",
        "        for r in rules)",
        "      yield CoverageResult(inv, covered, relevant)",
        "    # Example: 0/19 → Phase 7 finds 19 OMISSIONS",
    ]
    annot = [
        ("INPUT", ["List[ControlRule] (from Phase 5)", "List[LinkedEntity] (from Phase 3)"]),
        ("OUTPUT", ["List[CoverageResult]", "  (covered: bool per invariant)"]),
        ("TEMPLATES", ["19 IEC 61511 templates", "5 JSON category files:", "  pump / valve / sensor", "  interlock / alarm"]),
        ("IEC CLAUSES", ["§11.4  Shutdown rules", "§11.5  Alarm requirements", "§10.3  Interlock logic", "§9.4   ESD propagation"]),
        ("TECHNOLOGIES", ["JSON file loading", "Python dataclasses", "Standards KB (SQLite)"]),
        ("STATUS", ["COMPLETE"]),
    ]
    slide_phase_impl(prs, 6, "IEC 61511 Invariant Coverage",
                     "19 IEC 61511 safety requirement templates · JSON template library · Coverage gap detection",
                     code, annot, accent=AMRITA_STEEL)


def slide_phase7_impl(prs):
    code = [
        "# src/verification/z3_auditor.py",
        "from z3 import Bool, Solver, Implies, unsat",
        "from itertools import combinations",
        "",
        "class Z3Auditor:",
        "  def audit(rules, coverage_results) -> List[AuditFinding]:",
        "    findings = []",
        "",
        "    # ── Pass 1: OMISSION ─────────────────────────────",
        "    for cov in coverage_results:",
        "      if not cov.covered:",
        "        findings.append(AuditFinding(",
        "          finding_type = FindingType.OMISSION,",
        "          severity     = FindingSeverity[",
        "            cov.invariant.severity_if_missing],",
        "          description  = f'Missing: {cov.invariant.description}',",
        "          iec_clause   = cov.invariant.iec_clause))",
        "",
        "    # ── Pass 2: CONTRADICTION  (Z3 UNSAT) ────────────",
        "    for r1, r2 in combinations(rules, 2):",
        "      if r1.condition.sensor_tag == r2.condition.sensor_tag:",
        "        solver = Solver()",
        "        s = Bool(r1.condition.sensor_tag)",
        "        a1 = Bool(r1.action.name)",
        "        a2 = Bool(r2.action.name)",
        "        solver.add(Implies(s, a1))",
        "        solver.add(Implies(s, a2))",
        "        solver.add(a1 != a2)    # conflict axiom",
        "        if solver.check() == unsat:",
        "          findings.append(AuditFinding(CONTRADICTION))",
        "",
        "    # ── Pass 3: TAG_MISMATCH  (needs_review flag) ────",
        "    for r in rules:",
        "      if r.needs_review:",
        "        findings.append(AuditFinding(",
        "          finding_type = FindingType.TAG_MISMATCH,",
        "          severity     = FindingSeverity.MEDIUM,",
        "          description  = f'Low-confidence rule: {r.rule_id}'))",
        "",
        "    return findings   # HIGH / MEDIUM / LOW",
    ]
    annot = [
        ("INPUT", ["List[ControlRule] (from Phase 5)", "List[CoverageResult] (from Phase 6)"]),
        ("OUTPUT", ["List[AuditFinding]", "  (typed + severity-rated)"]),
        ("3 PASSES", ["OMISSION: uncovered invariants", "CONTRADICTION: Z3 UNSAT proof", "TAG_MISMATCH: needs_review rules"]),
        ("FINDING TYPES", ["FindingType.OMISSION", "FindingType.CONTRADICTION", "FindingType.TAG_MISMATCH"]),
        ("TECHNOLOGIES", ["Microsoft Z3 v4.13", "z3-solver Python binding", "itertools.combinations"]),
        ("STATUS", ["COMPLETE"]),
    ]
    slide_phase_impl(prs, 7, "Z3 Formal Verification",
                     "3-pass Z3 SMT verification: OMISSION · CONTRADICTION (UNSAT) · TAG_MISMATCH",
                     code, annot, accent=AMRITA_MAROON)


def slide_phase8_impl(prs):
    code = [
        "# src/reporting/report_generator.py",
        "from jinja2 import Environment, FileSystemLoader",
        "from dataclasses import dataclass",
        "from datetime import datetime",
        "",
        "@dataclass",
        "class AuditReport:",
        "  input_source:      str",
        "  generated_at:      datetime",
        "  findings:          List[AuditFinding]",
        "  rules:             List[ControlRule]",
        "  invariant_summary: List[dict]",
        "  extraction_stats:  dict",
        "  is_real_data:      bool = False",
        "",
        "class ReportGenerator:",
        "  def __init__(self, templates_dir):",
        "    self.env = Environment(",
        "      loader=FileSystemLoader(templates_dir))",
        "",
        "  def generate(report: AuditReport, output_path: Path):",
        "    template = self.env.get_template(",
        "      'audit_report.html.j2')",
        "    html = template.render(",
        "      report=report,",
        "      findings_by_severity={",
        "        'HIGH':   [f for f in report.findings",
        "                   if f.severity == HIGH],",
        "        'MEDIUM': [f for f in report.findings",
        "                   if f.severity == MEDIUM],",
        "        'LOW':    [f for f in report.findings",
        "                   if f.severity == LOW],",
        "      }",
        "    )",
        "    output_path.write_text(html, encoding='utf-8')",
        "    return output_path",
        "  # Template renders: color-coded findings table,",
        "  # IEC clause links, invariant coverage summary,",
        "  # extraction stats, real-data caution banner",
    ]
    annot = [
        ("INPUT", ["AuditReport dataclass", "  ├ findings (typed + severity)", "  ├ rules (ControlRule)", "  └ extraction_stats (dict)"]),
        ("OUTPUT", ["audit_report.html", "  (Jinja2 rendered, standalone)"]),
        ("REPORT SECTIONS", ["Findings table (color by severity)", "IEC 61511 clause references", "Invariant coverage summary", "Pipeline execution stats", "Real-data caution banner"]),
        ("TECHNOLOGIES", ["Jinja2 templating", "HTML/CSS (Bootstrap-like)", "Python dataclasses"]),
        ("FILES", ["src/reporting/", "templates/audit_report.html.j2"]),
        ("STATUS", ["COMPLETE"]),
    ]
    slide_phase_impl(prs, 8, "Audit Report Generation",
                     "Jinja2 HTML report · Severity-color-coded findings table · IEC 61511 clause references",
                     code, annot, accent=AMRITA_STEEL)


def slide_phase9_impl(prs):
    code = [
        "# src/plc/code_generator.py",
        "# Generates IEC 61131-3 Structured Text (.st)",
        "",
        "class PLCCodeGenerator:",
        "  def generate(rules, output_path, program_name):",
        "    template = self.env.get_template('plc.st.j2')",
        "    code = template.render(",
        "      rules=rules,",
        "      program_name=program_name,",
        "      generated_at=datetime.now())",
        "    output_path.write_text(code, encoding='utf-8')",
        "    return output_path",
        "",
        "# ── Generated Structured Text (plc.st.j2) ────────────",
        "# PROGRAM ControlNarrative",
        "# VAR",
        "#   PT_101 : REAL;  (* Pressure Transmitter *)",
        "#   XV_201 : BOOL;  (* Shutoff Valve        *)",
        "#   P_001  : BOOL;  (* Feed Pump            *)",
        "# END_VAR",
        "#",
        "# (* Rule R0001 — control-narrative.pdf p.4 *)",
        "# IF PT_101 > 50.0 THEN",
        "#   XV_201 := FALSE;   (* CLOSE *)",
        "#   P_001  := FALSE;   (* STOP  *)",
        "# END_IF;",
        "#",
        "# (* AUDIT NOTE [INV-001]:                     *)",
        "# (* OMISSION — No High-High shutdown for PT-101 *)",
        "# (* IEC 61511-1 §11.4   Severity: HIGH        *)",
        "#",
        "# (* WARNING: Draft skeleton only.             *)",
        "# (* Must be reviewed by a qualified SIL engineer *)",
    ]
    annot = [
        ("INPUT", ["List[ControlRule] (from Phase 5)", "List[AuditFinding] (from Phase 7)", "program_name: str"]),
        ("OUTPUT", ["plc_output.st", "  (IEC 61131-3 Structured Text)"]),
        ("ST STRUCTURE", ["PROGRAM block declaration", "VAR section (auto-typed)", "One IF-THEN block per rule", "AUDIT NOTE comments inline", "WARNING banner at end"]),
        ("TECHNOLOGIES", ["Jinja2 templating", "IEC 61131-3 standard", "Python dataclasses"]),
        ("SAFETY NOTE", ["Draft skeleton only", "Requires qualified SIL review", "Not for production use"]),
        ("STATUS", ["COMPLETE"]),
    ]
    slide_phase_impl(prs, 9, "PLC Structured Text Generation",
                     "IEC 61131-3 Structured Text · AUDIT NOTE injection · Draft skeleton for SIL engineer review",
                     code, annot, accent=AMRITA_MAROON)


# ── Standards KB bonus slide ──────────────────────────────────────────────────

def slide_standards_kb_impl(prs):
    code = [
        "# src/standards/  —  Standards Knowledge Base",
        "# SQLite-backed, built from IEC 61511 standard text",
        "",
        "class SafetyRule(TypedDict):",
        "  rule_id:     str       # e.g. 'IEC-61511-11.4.1'",
        "  clause:      str       # e.g. '§11.4.1'",
        "  description: str",
        "  severity:    str       # HIGH / MEDIUM / LOW",
        "  applies_to:  List[str] # entity classes",
        "  keywords:    List[str]",
        "",
        "class StandardsDB:",
        "  def __init__(self, db_path: Path):",
        "    self.conn = sqlite3.connect(str(db_path))",
        "    self._create_tables()",
        "",
        "  def query_rules_for_entity(entity_class, context):",
        "    # Exact class match + keyword similarity",
        "    return self.conn.execute(",
        "      'SELECT * FROM safety_rules WHERE '",
        "      'applies_to LIKE ? AND '",
        "      'severity = \"HIGH\"',",
        "      (f'%{entity_class}%',)).fetchall()",
        "",
        "class StandardsKnowledgeGraph:",
        "  def build_from_standards_db(db):",
        "    # Graph: IEC clause → affected equipment class",
        "    # Used to auto-populate InvariantLibrary",
        "    for rule in db.query_all():",
        "      G.add_node(rule['clause'],",
        "        rule_type='standard',",
        "        severity=rule['severity'])",
        "      for ec in rule['applies_to']:",
        "        G.add_edge(rule['clause'], ec,",
        "          label=rule['description'][:60])",
        "",
        "# Standards DB populated by run_standards_update.py",
        "# (offline LLM extraction — ~3-4 hours on CPU)",
    ]
    annot = [
        ("PURPOSE", ["Extend invariant library with", "rules extracted directly", "from IEC 61511 standard text"]),
        ("KEY CLASSES", ["StandardsDB (SQLite)", "SafetyRule (TypedDict)", "StandardsKnowledgeGraph", "run_standards_update.py"]),
        ("DB SCHEMA", ["safety_rules table:", "  rule_id, clause,", "  description, severity,", "  applies_to, keywords"]),
        ("INTEGRATION", ["HIGH-severity rules → auto-", "added to InvariantLibrary", "(Phase 6) at runtime"]),
        ("TECHNOLOGIES", ["SQLite (stdlib)", "NetworkX DiGraph", "Ollama (offline extraction)"]),
        ("STATUS", ["In Progress"]),
    ]
    slide = blank(prs)
    add_chrome(slide, ACCENT_TEAL)
    add_slide_title(
        slide,
        "Standards Knowledge Base  :  Implementation Detail",
        "SQLite-backed IEC 61511 rule store · Auto-populates InvariantLibrary (Phase 6)"
    )

    CODE_L = Inches(0.3)
    CODE_T = Inches(1.55)
    CODE_W = Inches(7.6)
    CODE_H = Inches(5.55)

    add_rect(slide, CODE_L, CODE_T, CODE_W, CODE_H,
             fill=CODE_BG, line_color=ACCENT_TEAL, radius=True)

    tb, tf = txb(slide,
                 CODE_L + Inches(0.18), CODE_T + Inches(0.12),
                 CODE_W - Inches(0.36), CODE_H - Inches(0.24),
                 wrap=True)
    first = True
    for line in code:
        if first:
            p = tf.paragraphs[0]; first = False
        else:
            p = tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        run = p.add_run()
        run.text = line
        run.font.size = Pt(11.5)
        if _is_comment_line(line):
            run.font.color.rgb = CMT_COLOR; run.font.italic = True
        elif _is_keyword_line(line):
            run.font.color.rgb = KW_COLOR; run.font.bold = True
        elif _is_string_or_deco(line):
            run.font.color.rgb = STR_COLOR
        else:
            run.font.color.rgb = CODE_FG
        _para_spacing(p, before_pt=0.5)

    ANN_L = Inches(8.1)
    ANN_T = Inches(1.55)
    ANN_W = Inches(4.9)
    ANN_H = Inches(5.55)

    add_rect(slide, ANN_L, ANN_T, ANN_W, ANN_H,
             fill=AMRITA_NAVY, radius=True)

    y = ANN_T + Inches(0.15)
    for label, values in annot:
        txb(slide, ANN_L + Inches(0.18), y,
            ANN_W - Inches(0.36), Inches(0.34),
            label, size=Pt(12), bold=True, color=RGBColor(0x5E, 0xE0, 0xD8))
        y += Inches(0.34)
        add_line(slide, ANN_L + Inches(0.18), y,
                 ANN_L + ANN_W - Inches(0.18), y,
                 color=RGBColor(0x3A, 0x5F, 0x9A), w=Pt(0.5))
        y += Inches(0.06)
        for v in values:
            badge_bg = None
            if v.upper() in ("COMPLETE", "COMPLETED"):
                badge_bg = DONE_BADGE_BG
            elif "PROGRESS" in v.upper():
                badge_bg = PROG_BADGE_BG
            if badge_bg:
                add_rect(slide, ANN_L + Inches(0.20), y + Inches(0.03),
                         Inches(1.4), Inches(0.26),
                         fill=badge_bg, radius=True)
                txb(slide, ANN_L + Inches(0.22), y,
                    Inches(1.38), Inches(0.32),
                    v, size=Pt(11), bold=True,
                    color=WHITE, align=PP_ALIGN.CENTER)
            else:
                txb(slide, ANN_L + Inches(0.22), y,
                    ANN_W - Inches(0.44), Inches(0.32),
                    "·  " + v, size=Pt(11), color=ANNOT_VAL, wrap=True)
            y += Inches(0.30)
        y += Inches(0.10)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    prs = new_prs()

    # ── Front matter ──────────────────────────────────────────────────────
    slide_title(prs)
    slide_guide_approval(prs)
    slide_contents_v3(prs)
    slide_intro(prs)
    slide_problem(prs)
    slide_architecture(prs)
    slide_impl_progress(prs)

    # ── Phase 1 ───────────────────────────────────────────────────────────
    slide_section_divider(prs, "Phase 1", "Multimodal Ingestion", [
        "PyMuPDF text extraction  +  Tesseract OCR (PSM 11 + PSM 3 dual pass)",
        "SemanticChunker: heading-boundary grouping with 300-char overlap",
        "GlobalEntityRegistry: regex-first-pass ISA-5.1 tag scan → LLM prompt injection",
    ], color=AMRITA_MAROON)
    slide_phase1_impl(prs)

    # ── Phase 2 ───────────────────────────────────────────────────────────
    slide_section_divider(prs, "Phase 2", "LLM Entity Extraction", [
        "Ollama + Qwen 2.5 14B (local, no API key) — one call per DocumentChunk",
        "Global entity registry injected into every prompt for cross-page context",
        "Pydantic v2 validation: confidence < 0.7 → needs_review flag raised",
    ], color=AMRITA_STEEL)
    slide_phase2_impl(prs)

    # ── Phase 3 ───────────────────────────────────────────────────────────
    slide_section_divider(prs, "Phase 3", "Cross-Modal Entity Linking", [
        "Step 1: O(1) exact canonical match across Control Narrative, C&E Table, P&ID",
        "Step 2: RapidFuzz token_sort_ratio ≥ 85  →  TAG_MISMATCH finding raised",
        "Step 3: all-MiniLM-L6-v2 cosine similarity ≥ 0.75  →  semantic link confirmed",
    ], color=AMRITA_MAROON)
    slide_phase3_impl(prs)

    # ── Phase 4 ───────────────────────────────────────────────────────────
    slide_section_divider(prs, "Phase 4", "Knowledge Graph Construction", [
        "NetworkX DiGraph: nodes = canonical equipment tags, edges = control rules",
        "Semantic edges added: sensors linked to co-located equipment via tag suffix",
        "Self-contained vis.js HTML export (688 KB bundled — no CDN, works offline)",
    ], color=AMRITA_STEEL)
    slide_phase4_impl(prs)

    # ── Phase 5 ───────────────────────────────────────────────────────────
    slide_section_divider(prs, "Phase 5", "Intermediate Representation", [
        "Pydantic v2 ControlRule model: condition (Condition), action (RuleAction enum)",
        "RuleAction enum: STOP / START / OPEN / CLOSE / TRIP — strict validation",
        "confidence < 0.7 → needs_review=True  →  feeds Phase 7 TAG_MISMATCH pass",
    ], color=AMRITA_MAROON)
    slide_phase5_impl(prs)

    # ── Phase 6 ───────────────────────────────────────────────────────────
    slide_section_divider(prs, "Phase 6", "IEC 61511 Invariant Coverage", [
        "19 IEC 61511 safety requirement templates across 5 JSON category files",
        "Each template: required_entity_class, required_rule_type, iec_clause, severity",
        "evaluate_coverage() → CoverageResult per invariant (covered: bool)",
    ], color=AMRITA_STEEL)
    slide_phase6_impl(prs)

    # ── Phase 7 ───────────────────────────────────────────────────────────
    slide_section_divider(prs, "Phase 7", "Z3 Formal Verification", [
        "Pass 1 — OMISSION: uncovered invariants → HIGH/MEDIUM AuditFinding",
        "Pass 2 — CONTRADICTION: Z3 Solver(Implies(cond, a1), a1≠a2) == unsat → HIGH",
        "Pass 3 — TAG_MISMATCH: needs_review=True rules from Phase 5 → MEDIUM",
    ], color=AMRITA_MAROON)
    slide_phase7_impl(prs)

    # ── Phase 8 ───────────────────────────────────────────────────────────
    slide_section_divider(prs, "Phase 8", "Audit Report Generation", [
        "Jinja2 HTML report: color-coded findings table, IEC clause references",
        "AuditReport dataclass: findings, rules, invariant_summary, extraction_stats",
        "is_real_data=True adds a caution banner; safe for real industrial documents",
    ], color=AMRITA_STEEL)
    slide_phase8_impl(prs)

    # ── Phase 9 ───────────────────────────────────────────────────────────
    slide_section_divider(prs, "Phase 9", "PLC Structured Text Generation", [
        "Jinja2 template renders one IF-THEN block per verified ControlRule",
        "AUDIT NOTE comments injected inline for every OMISSION/CONTRADICTION finding",
        "Output: IEC 61131-3 Structured Text (.st) — draft skeleton for SIL review",
    ], color=AMRITA_MAROON)
    slide_phase9_impl(prs)

    # ── Standards KB ──────────────────────────────────────────────────────
    slide_section_divider(prs, "Bonus", "Standards Knowledge Base", [
        "SQLite-backed rule store — rules extracted from IEC 61511 standard text via LLM",
        "HIGH-severity rules automatically promote to SafetyInvariantLibrary (Phase 6)",
        "StandardsKnowledgeGraph: IEC clause → affected equipment class (NetworkX)",
    ], color=ACCENT_TEAL)
    slide_standards_kb_impl(prs)

    # ── Standard algorithms & evaluation ──────────────────────────────────
    slide_section_divider(prs, "§01",
        "Standard Algorithms &\nEvaluation Metrics",
        [
            "Z3 SMT Contradiction Checker — formal proof of rule conflicts",
            "Cross-Modal Entity Linking — 3-step cascade (Exact → Fuzzy → Embedding)",
            "Evaluation on 50-package synthetic benchmark · P / R / F1",
        ],
        color=AMRITA_MAROON)
    slide_algorithm(prs)
    slide_algorithm_linking(prs)
    slide_eval_metrics(prs)

    # ── Tools ─────────────────────────────────────────────────────────────
    slide_section_divider(prs, "§02",
        "Tools and Methods\nfor Implementation",
        [
            "LLM stack: Ollama + Qwen 2.5 · LangChain · Pydantic v2",
            "Formal methods: Z3 v4.13 · 19 IEC 61511 invariant templates",
            "Web: Streamlit 6-page dashboard · FastAPI · SQLite",
        ],
        color=AMRITA_STEEL)
    slide_tools(prs)

    # ── Results ───────────────────────────────────────────────────────────
    slide_section_divider(prs, "§03",
        "Preliminary Verification\nand Results",
        [
            "End-to-end pipeline on PKG-001 (real-world pump pressure loop)",
            "7 findings: 3 HIGH, 3 MEDIUM, 1 LOW — all Z3-proven",
            "Benchmark F1 = 0.918 · Ablation: cross-modal linking +18 pp recall",
        ],
        color=AMRITA_MAROON)
    slide_results_pipeline(prs)
    slide_results_findings(prs)
    slide_results_kg(prs)
    slide_results_benchmark(prs)

    # ── Datasets ──────────────────────────────────────────────────────────
    slide_section_divider(prs, "§04", "Datasets", [
        "50-package synthetic benchmark: narrative + C&E table + P&ID per package",
        "5 injected defect categories aligned to ICS-CERT vulnerability taxonomy",
        "Ground-truth labels: expected finding type, severity, and affected tags",
    ], color=AMRITA_STEEL)
    slide_datasets(prs)

    # ── Closing ───────────────────────────────────────────────────────────
    slide_tech_activities(prs)
    slide_project_plan(prs)
    slide_conclusion(prs)
    slide_references(prs)

    out = "Panel_Review_2_SafetyAuditor_v3.pptx"
    prs.save(out)
    print(f"Saved: {out}  ({len(prs.slides)} slides)")


if __name__ == "__main__":
    main()
