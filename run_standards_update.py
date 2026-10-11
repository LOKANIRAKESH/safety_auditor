#!/usr/bin/env python
"""
Standards Knowledge Base CLI Runner
====================================

Usage:
    python run_standards_update.py --help
    python run_standards_update.py seed               # load 20 built-in rules instantly (no LLM)
    python run_standards_update.py download           # fetch all free sources
    python run_standards_update.py extract            # run LLM extraction (slow on CPU)
    python run_standards_update.py graph              # rebuild knowledge graph + visualise
    python run_standards_update.py export             # export invariant template JSON files
    python run_standards_update.py all                # seed + download + extract + graph + export
    python run_standards_update.py stats              # print DB statistics

Options:
    --model MODEL     Ollama model to use for extraction (default: qwen2.5)
    --force           Force re-extraction even if already done
    --source SOURCE   Only process one source_id (e.g. OSHA_PSM_1910_119)

Recommended first-time setup:
    python run_standards_update.py seed               # instant — 20 critical rules loaded
    python run_standards_update.py download           # fetch PDFs (~2 min)
    python run_standards_update.py extract            # run overnight on CPU / fast with GPU
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from loguru import logger

# Ensure repo root is on the path
sys.path.insert(0, str(Path(__file__).parent))

from src.standards.downloader      import StandardsDownloader, FREE_STANDARDS
from src.standards.rule_extractor  import StandardsRuleExtractor
from src.standards.db              import StandardsDB
from src.standards.knowledge_graph import StandardsKnowledgeGraph
from src.standards.seed_rules      import SEED_RULES


def cmd_seed(args) -> None:
    """Immediately load 20 hand-coded critical rules — no LLM, no download needed."""
    db = StandardsDB()
    n  = db.insert_rules(SEED_RULES)
    logger.success(f"Loaded {n} seed rules into knowledge base ({len(SEED_RULES)} total available)")
    db.export_invariant_templates()
    cmd_stats(args)


def cmd_download(args) -> None:
    dl = StandardsDownloader()
    if args.source:
        sources = [s for s in FREE_STANDARDS if s.source_id == args.source]
        if not sources:
            logger.error(f"Unknown source_id: {args.source}")
            logger.info(f"Available: {[s.source_id for s in FREE_STANDARDS]}")
            return
        for src in sources:
            dl.download_one(src, force=args.force)
    else:
        dl.download_all(force=args.force)

    downloaded = dl.list_downloaded()
    logger.success(f"\n{len(downloaded)} standards available in {dl.base_dir}")
    for m in downloaded:
        size_kb = m.get("file_size_bytes", 0) // 1024
        logger.info(f"  [{m['source_id']}] {m['title'][:60]} ({size_kb} KB)")


def cmd_extract(args) -> None:
    dl        = StandardsDownloader()
    extractor = StandardsRuleExtractor(llm_model=args.model)
    db        = StandardsDB()

    meta_list = dl.list_downloaded()
    if not meta_list:
        logger.warning(
            "No downloaded standards found. Run: python run_standards_update.py download"
        )
        return

    if args.source:
        meta_list = [m for m in meta_list if m["source_id"] == args.source]
        if not meta_list:
            logger.error(f"Source not downloaded: {args.source}")
            return

    # Cap chunks for very large documents (NIST SP 800-82 has 700+ chunks).
    # Only SIS-relevant chunks are processed; the rest are filtered by keyword.
    LARGE_DOC_CHUNK_CAP = {
        "NIST_SP800_82": 150,  # 8MB doc — 148 SIS-relevant chunks, skip the rest
    }

    total_rules = 0
    for meta in meta_list:
        source_id    = meta["source_id"]
        standard_ref = meta["standard_ref"]
        local_path   = Path(meta["local_path"])
        filetype     = meta["filetype"]

        if not local_path.exists():
            logger.warning(f"File missing: {local_path} — skipping")
            continue

        if args.force:
            db.clear_source(source_id)

        max_chunks = LARGE_DOC_CHUNK_CAP.get(source_id, 0)
        logger.info(f"\nExtracting: {source_id} ({filetype})"
                    + (f" [capped at {max_chunks} relevant chunks]" if max_chunks else ""))
        try:
            if filetype == "pdf":
                rules = extractor.extract_from_pdf(
                    local_path, source_id, standard_ref, max_chunks=max_chunks
                )
            elif filetype == "html":
                rules = extractor.extract_from_html(local_path, source_id, standard_ref)
            else:
                logger.warning(f"Unknown filetype '{filetype}' for {source_id} — skipping")
                continue
        except Exception as exc:
            logger.error(f"Extraction failed for {source_id}: {exc}")
            continue

        inserted = db.insert_rules(rules)
        total_rules += inserted
        logger.success(f"  {source_id}: {len(rules)} extracted, {inserted} new in DB")

    stats = db.stats()
    logger.success(
        f"\nExtraction complete. "
        f"Total in DB: {stats['total_rules']} rules from {stats['sources']} sources"
    )


def cmd_graph(args) -> None:
    db = StandardsDB()
    rules = db.query_all()
    if not rules:
        logger.warning("Knowledge base is empty — run 'extract' first")
        return

    kg = StandardsKnowledgeGraph()
    kg.add_rules(rules)

    summary = kg.summary()
    logger.success(
        f"Graph: {summary['nodes']} nodes, {summary['edges']} edges, "
        f"{summary['requirements']} requirements"
    )
    logger.info(f"  Standards: {summary['standards']}")
    logger.info(f"  Equipment classes: {summary['equipment']}")
    logger.info(f"  Sensor classes:    {summary['sensors']}")

    from src.config import PipelineConfig
    std_dir = PipelineConfig().data_dir / "standards"
    graphml_path = std_dir / "knowledge_graph.graphml"
    kg.save_graphml(graphml_path)
    logger.info(f"GraphML saved → {graphml_path}")

    png_path = kg.draw(std_dir / "knowledge_graph.png")
    if png_path:
        logger.success(f"Graph visualisation → {png_path}")

    # Check IEC 61511 clause coverage
    required_iec = [
        "IEC 61511 Cl.5", "IEC 61511 Cl.8", "IEC 61511 Cl.9",
        "IEC 61511 Cl.10", "IEC 61511 Cl.11", "IEC 61511 Cl.16",
    ]
    gaps = kg.find_gaps(required_iec)
    if gaps:
        logger.warning(f"IEC 61511 coverage gaps (no rules extracted yet): {gaps}")
    else:
        logger.success("All required IEC 61511 clauses covered")


def cmd_export(args) -> None:
    db = StandardsDB()
    stats = db.stats()
    if stats["total_rules"] == 0:
        logger.warning("Knowledge base is empty — run 'extract' first")
        return

    output_dir = db.export_invariant_templates()
    logger.success(
        f"Exported {stats['total_rules']} rules to invariant templates in {output_dir}"
    )


def cmd_stats(args) -> None:
    db    = StandardsDB()
    stats = db.stats()
    logger.info(f"\nStandards Knowledge Base Statistics")
    logger.info(f"  DB location:   {db.db_path}")
    logger.info(f"  Total rules:   {stats['total_rules']}")
    logger.info(f"  Sources:       {stats['sources']}")
    logger.info(f"\n  By type:")
    for t, count in sorted(stats["by_type"].items()):
        logger.info(f"    {t:<30} {count:>4}")
    logger.info(f"\n  By severity:")
    for s, count in sorted(stats["by_severity"].items()):
        logger.info(f"    {s:<10} {count:>4}")


def main():
    parser = argparse.ArgumentParser(
        description="Standards Knowledge Base CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    for name in ("seed", "download", "extract", "graph", "export", "stats"):
        p = sub.add_parser(name)
        p.add_argument("--force",  action="store_true", help="Force re-run")
        p.add_argument("--source", default="",         help="Filter to one source_id")
        if name in ("extract",):
            p.add_argument("--model", default="qwen2.5", help="Ollama model")

    # 'all' subcommand
    p_all = sub.add_parser("all", help="Run seed → download → extract → graph → export")
    p_all.add_argument("--model",  default="qwen2.5")
    p_all.add_argument("--force",  action="store_true")
    p_all.add_argument("--source", default="")

    args = parser.parse_args()

    if args.cmd == "seed":
        cmd_seed(args)
    elif args.cmd == "download":
        cmd_download(args)
    elif args.cmd == "extract":
        cmd_extract(args)
    elif args.cmd == "graph":
        cmd_graph(args)
    elif args.cmd == "export":
        cmd_export(args)
    elif args.cmd == "stats":
        cmd_stats(args)
    elif args.cmd == "all":
        cmd_seed(args)
        cmd_download(args)
        cmd_extract(args)
        cmd_graph(args)
        cmd_export(args)
        cmd_stats(args)


if __name__ == "__main__":
    main()
