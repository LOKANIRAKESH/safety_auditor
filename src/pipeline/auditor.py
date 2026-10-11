"""
Main Pipeline Orchestrator — SafetyAuditor
==========================================

This module wires together all 9 phases of the neuro-symbolic safety audit.
It is the only module that knows the full pipeline sequence; each phase module
is independent and unaware of the phases that come before or after it.

THE 9-PHASE SEQUENCE
  Phase 1  Ingestion           PDF text + table extraction + P&ID tag OCR
  Phase 2  LLM Extraction      Ollama (Qwen 2.5) → equipment entities + control rules
  Phase 3  Cross-Modal Linking  Exact → Fuzzy → Embedding cascade across 3 modalities
  Phase 4  Knowledge Graph     NetworkX DiGraph + PyVis interactive HTML export
  Phase 5  IR Construction     ExtractedRule → ControlRule (Pydantic v2 validated)
  Phase 6  Invariant Coverage  19 IEC 61511 templates → coverage evaluation
  Phase 7  Z3 Verification     OMISSION / CONTRADICTION / TAG_MISMATCH passes
  Phase 8  Audit Report        Jinja2 HTML report + statistics summary
  Phase 9  PLC Sketch          IEC 61131-3 Structured Text (.st) code generation
  Post:    DB Persist          SQLite audit_store.db via AuditRepository

WHY THIS STRUCTURE?
  Separating phases into independent modules means:
  - Each phase can be tested in isolation (no LLM needed for Z3 tests)
  - The ablation study (Phase 3 ON vs OFF) is a single config flag
  - The baseline comparison (no Phase 6/7) is just skipping those phases
  - Research iteration: improve one phase without touching the others
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from loguru import logger
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from src.config import PipelineConfig
from src.ingestion import PDFExtractor, TableExtractor, PIDExtractor
from src.ingestion.entity_registry import GlobalEntityRegistry
from src.ingestion.chunker import SemanticChunker
from src.ingestion.image_extractor import PDFImageExtractor, IMAGE_SCANNED
from src.ingestion.pdf_extractor import TextBlock
from src.extraction import EntityExtractor
from src.linking import CrossModalLinker
from src.knowledge import KnowledgeGraphBuilder
from src.ir import RuleBuilder
from src.invariants import SafetyInvariantLibrary
from src.verification import Z3Auditor
from src.reporting import ReportGenerator, AuditReport
from src.plc import PLCCodeGenerator
from src.verification.finding_model import AuditFinding
from db import init_db, get_session, AuditRepository


@dataclass
class AuditRunResult:
    """
    Return value of SafetyAuditor.run().

    Callers (CLI, Streamlit UI, test suite) receive this object and never
    interact with intermediate pipeline objects directly.

    Fields:
        total_findings:  Total number of safety findings produced.
        high/medium/low_count: Breakdown by severity for the UI summary card.
        report_path:     Path to the generated HTML audit report.
        plc_output_path: Path to the generated .st PLC Structured Text file.
        graph_html_path: Path to the interactive PyVis knowledge graph HTML.
        findings:        Full list of AuditFinding objects (for the UI findings page).
        run_id:          SQLite run ID, e.g. "run-20261007-143022-a9f3b1".
                         None if DB persist failed (non-fatal).
    """
    total_findings: int
    high_count: int
    medium_count: int
    low_count: int
    report_path: Path
    plc_output_path: Path
    graph_html_path: Optional[Path] = None
    graph_node_count: int = 0
    graph_edge_count: int = 0
    findings: List[AuditFinding] = field(default_factory=list)
    run_id: Optional[str] = None


class SafetyAuditor:
    """
    Orchestrates the full neuro-symbolic safety auditing pipeline.

    One instance is created per application lifetime (CLI command or Streamlit
    session). The instance holds the config; call run() once per specification
    document to audit.

    The DB is initialised in __init__ so that the Streamlit "Audit History"
    page can query it even before the first run() call.
    """

    def __init__(self, config: PipelineConfig):
        self.config = config
        # Ensure output directory exists before any phase writes to it
        config.output_dir.mkdir(parents=True, exist_ok=True)
        # Initialise the SQLite audit store (creates tables if they don't exist)
        init_db()

    def run(self, input_path: Path, output_dir: Path, is_real_data: bool = False) -> AuditRunResult:
        """
        Run the full 9-phase pipeline on one specification package.

        Args:
            input_path:   Path to a single PDF or a directory containing
                          multiple PDFs + optional P&ID image files.
            output_dir:   Directory where all artefacts will be written
                          (report, PLC .st file, knowledge graph HTML).
            is_real_data: True when auditing a real industrial specification
                          (vs. a benchmark package). Controls a flag in the
                          HTML report that adds a caution banner.

        Returns:
            AuditRunResult with finding counts, output paths, and run_id.
        """
        input_path = Path(input_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(), transient=True
        ) as progress:

            # ═══════════════════════════════════════════════════════════════
            # PHASE 1 — INGESTION
            # ═══════════════════════════════════════════════════════════════
            # Extract raw content from all PDFs in the specification package:
            #   text_blocks: list of TextBlock objects (paragraph + page number)
            #   tables:      list of TableData objects (rows/cols + source PDF)
            #   pid_tags:    list of ISA tag strings from P&ID image OCR
            # The _phase1_ingest helper handles both single-PDF and directory inputs.
            task = progress.add_task("Phase 1: Ingesting documents...", total=None)
            chunks, tables, pid_tags, registry = self._phase1_ingest(input_path)
            progress.remove_task(task)
            logger.info(
                f"Phase 1 complete: {len(chunks)} chunks, {len(tables)} tables, "
                f"{len(pid_tags)} P&ID tags, registry={registry.size()} tags"
            )

            # ═══════════════════════════════════════════════════════════════
            # PHASE 2 — LLM EXTRACTION
            # ═══════════════════════════════════════════════════════════════
            # Send semantic chunks (not raw text blocks) to Ollama (Qwen 2.5).
            # The GlobalEntityRegistry is prepended to every chunk prompt so the
            # LLM always has the full equipment tag inventory in context —
            # this solves the cross-page reference problem (page 100 knows page 3).
            task = progress.add_task(f"Phase 2: Extracting entities via {self.config.llm_model}...", total=None)
            extractor = EntityExtractor(self.config)
            extraction_result = extractor.extract_from_chunks(
                chunks, registry=registry, source_modality="narrative"
            )
            for table in tables:
                table_result = extractor.extract_from_table(table, source_modality="table")
                extraction_result.entities.extend(table_result.entities)
                extraction_result.rules.extend(table_result.rules)
                extraction_result.low_confidence_count += table_result.low_confidence_count
                extraction_result.extraction_errors.extend(table_result.extraction_errors)
            progress.remove_task(task)
            logger.info(f"Phase 2 complete: {len(extraction_result.entities)} entities, {len(extraction_result.rules)} raw rules")

            # ═══════════════════════════════════════════════════════════════
            # PHASE 3 — CROSS-MODAL ENTITY LINKING
            # ═══════════════════════════════════════════════════════════════
            # The same physical equipment appears with different tag spellings
            # across the three source modalities:
            #   narrative:  "pump P-101"
            #   C&E table:  "P101"
            #   P&ID image: "P-101A"  (OCR artefact)
            # The 3-step cascade resolves all spellings to one canonical tag:
            #   Step 1: Exact match           (fast path — most tags agree)
            #   Step 2: Fuzzy Levenshtein     (handles OCR noise, P-101 vs P101)
            #   Step 3: Sentence-transformer  (handles semantic paraphrases)
            # If ENABLE_CROSS_MODAL_LINKING=false (ablation mode), entities are
            # returned as-is without merging (sets an upper bound on noise).
            task = progress.add_task("Phase 3: Cross-modal entity linking...", total=None)
            linker = CrossModalLinker(self.config)
            linked_entities, linked_rules_raw = linker.link(
                extraction_result.entities, extraction_result.rules, pid_tags=pid_tags
            )
            progress.remove_task(task)

            # ═══════════════════════════════════════════════════════════════
            # PHASE 4 — KNOWLEDGE GRAPH
            # ═══════════════════════════════════════════════════════════════
            # Build a NetworkX DiGraph where:
            #   nodes = canonical equipment/sensor entities (from Phase 3)
            #   edges = control relationships extracted by the LLM (from Phase 2)
            # The graph is:
            #   a) stored in memory for Phase 6 coverage evaluation
            #   b) exported as a self-contained PyVis HTML for the UI
            #   c) persisted to the SQLite DB (nodes + edges tables)
            task = progress.add_task("Phase 4: Building knowledge graph...", total=None)
            kg_builder = KnowledgeGraphBuilder()
            graph = kg_builder.build(linked_entities, linked_rules_raw)
            graph_html = output_dir / "knowledge_graph.html"
            graph.to_pyvis_html(graph_html)
            progress.remove_task(task)

            # ═══════════════════════════════════════════════════════════════
            # PHASE 5 — CONTROL RULE IR CONSTRUCTION
            # ═══════════════════════════════════════════════════════════════
            # Convert loosely-typed ExtractedRule dicts into strongly-typed
            # ControlRule Pydantic models:
            #   ControlRule.condition = Condition(sensor_tag, operator, threshold, unit)
            #   ControlRule.action    = RuleAction enum (STOP / START / OPEN / CLOSE)
            #   ControlRule.confidence = float 0.0–1.0 (from LLM output)
            # Rules below EXTRACTION_CONFIDENCE_THRESHOLD are kept but flagged
            # as `needs_review=True` and `ambiguity_note` is populated.
            # The IR is the stable interface between the LLM world (Phases 2–4)
            # and the formal world (Phase 6–7).
            task = progress.add_task("Phase 5: Building rule IR...", total=None)
            rule_builder = RuleBuilder()
            ir_rules = rule_builder.build(linked_rules_raw)
            progress.remove_task(task)
            logger.info(f"Phase 5 complete: {len(ir_rules)} IR rules")

            # ═══════════════════════════════════════════════════════════════
            # PHASE 6 — SAFETY INVARIANT COVERAGE EVALUATION
            # ═══════════════════════════════════════════════════════════════
            # The SafetyInvariantLibrary holds 19 IEC 61511 invariant templates
            # (JSON files in src/invariants/templates/).
            # evaluate_coverage() checks each applicable invariant against the
            # rule set and entity set:
            #   is_covered = True  → at least one ControlRule satisfies this invariant
            #   is_covered = False → OMISSION candidate for Phase 7
            # Each invariant specifies which entity classes it applies to
            # (e.g. "Pump" → requires a pressure high-high shutdown rule).
            # Invariants for entity classes not present in this spec are skipped.
            task = progress.add_task("Phase 6: Evaluating safety invariant coverage...", total=None)
            library = SafetyInvariantLibrary(self.config).load()
            coverage_results = library.evaluate_coverage(ir_rules, linked_entities)
            invariant_summary = library.summary_table()
            progress.remove_task(task)

            # ═══════════════════════════════════════════════════════════════
            # PHASE 7 — Z3 FORMAL VERIFICATION
            # ═══════════════════════════════════════════════════════════════
            # Z3Auditor runs three independent verification passes:
            #
            #   Pass 1 OMISSION:      For every uncovered invariant from Phase 6,
            #                         report a safety gap (no Z3 formula needed —
            #                         absence of coverage is sufficient evidence).
            #                         MX (mutual exclusion) invariants are only
            #                         reported when conflicting commands exist.
            #
            #   Pass 2 CONTRADICTION: For every (STOP, START) rule pair that acts
            #                         on the same equipment with the same sensor,
            #                         build Z3 formulas and check satisfiability.
            #                         UNSAT = the two rules cannot both be true
            #                         simultaneously → CONTRADICTION finding.
            #
            #   Pass 3 TAG_MISMATCH:  Rules flagged `needs_review=True` in Phase 5
            #                         are reported as MEDIUM findings for engineer
            #                         review (no Z3 required).
            task = progress.add_task("Phase 7: Z3 formal verification...", total=None)
            z3_auditor = Z3Auditor(self.config)
            findings = z3_auditor.audit(ir_rules, coverage_results)
            progress.remove_task(task)

            # ═══════════════════════════════════════════════════════════════
            # PHASE 8 — AUDIT REPORT GENERATION
            # ═══════════════════════════════════════════════════════════════
            # Build an AuditReport dataclass with all pipeline statistics and
            # findings, then render it to HTML via Jinja2.
            # extraction_stats is the "pipeline provenance" section of the report —
            # it lets the process safety engineer trace every number back to its source.
            task = progress.add_task("Phase 8: Generating audit report...", total=None)
            extraction_stats = {
                "Semantic chunks processed": len(chunks),
                "Tables extracted": len(tables),
                "P&ID tags extracted": len(pid_tags),
                "Registry size (unique tags)": registry.size(),
                "Raw entities": len(extraction_result.entities),
                "Raw rules": len(extraction_result.rules),
                "Linked entities (canonical)": len(linked_entities),
                "IR rules (verified-confidence)": len(ir_rules),
                "Flagged for engineer review": extraction_result.low_confidence_count,
                "Invariants checked": len(coverage_results),
                "Cross-modal linking enabled": self.config.enable_cross_modal_linking,
                "LLM model used": self.config.llm_model,
            }
            report = AuditReport(
                input_source=str(input_path),
                generated_at=datetime.now(),
                findings=findings,
                rules=ir_rules,
                invariant_summary=invariant_summary,
                extraction_stats=extraction_stats,
                is_real_data=is_real_data,
            )
            report_gen = ReportGenerator(self.config)
            report_path = report_gen.generate(report, output_dir / "audit_report.html")
            progress.remove_task(task)

            # ═══════════════════════════════════════════════════════════════
            # PHASE 9 — PLC STRUCTURED TEXT GENERATION
            # ═══════════════════════════════════════════════════════════════
            # Generate a IEC 61131-3 Structured Text (.st) file from the
            # validated ControlRule IR. This is a "sketch" — it preserves the
            # intent of every extracted rule in machine-readable PLC syntax
            # but is not a deployable program (it does not include SCADA I/O
            # addressing, hardware declarations, or safety PLC libraries).
            #
            # The sketch is the "after" deliverable: the engineer has the audit
            # findings (Phase 8) to fix, and the PLC sketch to see what the
            # verified rules look like in code form.
            task = progress.add_task("Phase 9: Generating PLC Structured Text...", total=None)
            plc_gen = PLCCodeGenerator(self.config)
            plc_output = plc_gen.generate(
                ir_rules,
                output_path=output_dir / "plc_output.st",
                program_name=f"AUDIT_{input_path.stem.upper()[:16]}",
            )
            progress.remove_task(task)

        from src.verification.finding_model import FindingSeverity

        # ═══════════════════════════════════════════════════════════════════
        # PERSIST TO SQLITE (non-fatal — if DB fails, the audit still succeeds)
        # ═══════════════════════════════════════════════════════════════════
        # Every completed run is stored in output/audit_store.db.
        # This populates the "Audit History" page in the Streamlit UI and
        # enables cross-run analysis (trend charts, aggregate finding counts).
        # If the DB write fails (e.g. disk full, concurrent write conflict),
        # we log a warning and return run_id=None — the HTML report was already
        # written and is the primary deliverable.
        run_id = None
        try:
            with get_session() as session:
                repo = AuditRepository(session)
                db_run = repo.save_run(
                    input_source=str(input_path),
                    findings=findings,
                    llm_model=self.config.llm_model,
                    cross_modal_linking=self.config.enable_cross_modal_linking,
                    total_rules=len(ir_rules),
                    total_entities=len(linked_entities),
                    invariants_checked=len(coverage_results),
                    report_path=str(report_path),
                    plc_path=str(plc_output.output_path),
                    graph=graph.graph,
                )
                run_id = db_run.run_id
                logger.info(f"Audit persisted to DB as {run_id}")
        except Exception as e:
            logger.warning(f"DB persist failed (non-fatal): {e}")

        return AuditRunResult(
            total_findings=len(findings),
            high_count=sum(1 for f in findings if f.severity == FindingSeverity.HIGH),
            medium_count=sum(1 for f in findings if f.severity == FindingSeverity.MEDIUM),
            low_count=sum(1 for f in findings if f.severity == FindingSeverity.LOW),
            report_path=report_path,
            plc_output_path=plc_output.output_path,
            graph_html_path=graph_html,
            graph_node_count=graph.node_count,
            graph_edge_count=graph.edge_count,
            findings=findings,
            run_id=run_id,
        )

    def _phase1_ingest(self, input_path: Path):
        """
        Extract raw content from all documents in the specification package.

        Returns:
            chunks   : List[DocumentChunk]       — semantically chunked text for Phase 2
            tables   : List[ExtractedTable]      — C&E tables for Phase 2 table extraction
            pid_tags : List[str]                 — deduplicated ISA tags from images/OCR
            registry : GlobalEntityRegistry     — full-document tag inventory for cross-page context

        Three mechanisms are applied:

        1. GLOBAL ENTITY REGISTRY
           Fast regex first-pass over all text blocks → builds {tag: (page, snippet)} map.
           Injected into every LLM prompt chunk so rules on late pages can resolve
           equipment tags first defined on early pages.

        2. SEMANTIC CHUNKING
           PDFExtractor.extract() returns flat TextBlock list.
           SemanticChunker groups them into DocumentChunk objects at section-heading
           boundaries, then splits oversized sections with overlap.  One LLM call per
           chunk (not one per page) — safe cut points, no rules split across chunks.

        3. IMAGE EXTRACTION
           PDFImageExtractor scans every page for:
             - Scanned pages (image-only, < 30 chars text): full-page OCR at config.pid_ocr_dpi DPI
             - Large embedded images (>= config.pid_candidate_min_px wide): full P&ID pipeline
             - Medium embedded images (100–800 px): Tesseract PSM 6 for text labels
           All extracted ISA tags are merged into pid_tags and registry.
        """
        pdf_extractor   = PDFExtractor()
        table_extractor = TableExtractor()
        pid_extractor   = PIDExtractor(tesseract_cmd=self.config.tesseract_cmd)
        img_extractor   = PDFImageExtractor()
        chunker         = SemanticChunker(
            max_chars    = self.config.chunk_max_chars,
            overlap_chars= self.config.chunk_overlap_chars,
        )

        all_text_blocks = []
        tables          = []
        pid_tags        = []

        # ── Collect PDFs ──────────────────────────────────────────────────────
        if input_path.is_file() and input_path.suffix.lower() == ".pdf":
            pdfs = [input_path]
        elif input_path.is_dir():
            pdfs = list(input_path.glob("**/*.pdf"))
        else:
            pdfs = []

        # ── Per-PDF extraction ────────────────────────────────────────────────
        for pdf in pdfs:
            try:
                # Text and table extraction (existing)
                blocks = pdf_extractor.extract(pdf)
                all_text_blocks.extend(blocks)
                tables.extend(table_extractor.extract(pdf))

                # Image extraction (new): scanned pages + embedded images
                images = img_extractor.extract_from_pdf(pdf, pid_extractor, self.config)
                for img in images:
                    pid_tags.extend(img.extracted_tags)
                    # For scanned pages: add full-text OCR as a TextBlock so
                    # the LLM can extract entities and rules from prose content.
                    if img.image_class == IMAGE_SCANNED and img.full_text_ocr:
                        all_text_blocks.append(TextBlock(
                            text=img.full_text_ocr,
                            page=img.page,
                            bbox=(0.0, 0.0, 0.0, 0.0),
                            source_doc=pdf.name,
                            block_type="paragraph",
                        ))

            except Exception as e:
                logger.warning(f"Extraction failed for {pdf}: {e}")

        # ── Directory-level P&ID sources (existing, kept) ────────────────────
        # These supplement the embedded-image pipeline for benchmark packages
        # that ship pre-extracted tag lists or standalone PNG diagrams.
        if input_path.is_dir():
            for tag_file in input_path.glob("*pid_tags*.txt"):
                extraction = pid_extractor.extract_from_tag_list(tag_file)
                pid_tags.extend(extraction.tags)
            for img_file in list(input_path.glob("*.png")) + list(input_path.glob("*.jpg")):
                try:
                    extraction = pid_extractor.extract_from_image(img_file)
                    pid_tags.extend(extraction.tags)
                except Exception as e:
                    logger.warning(f"Image extraction failed for {img_file.name}: {e}")

        # ── Mechanism 1: Global Entity Registry ───────────────────────────────
        registry = GlobalEntityRegistry().build_from_blocks(all_text_blocks)
        # Merge P&ID-sourced tags into the registry (page=0 sentinel)
        registry.add_tags_from_list(list(set(pid_tags)), source_doc="pid_ocr")

        # ── Mechanism 2: Semantic chunking ────────────────────────────────────
        chunks = chunker.chunk(all_text_blocks)

        # ── Deduplicate pid_tags ──────────────────────────────────────────────
        pid_tags = list(set(pid_tags))

        logger.info(
            f"_phase1_ingest: {len(all_text_blocks)} blocks → {len(chunks)} chunks | "
            f"{len(tables)} tables | {len(pid_tags)} P&ID tags | "
            f"registry={registry.size()} tags"
        )
        return chunks, tables, pid_tags, registry
