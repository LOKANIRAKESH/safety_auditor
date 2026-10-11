"""
Global Entity Registry — Phase 1 cross-page context provider.

Performs a fast, LLM-free first pass over ALL text blocks in a document to
build a complete equipment tag inventory.  The registry is then injected into
every LLM chunk prompt so that a rule on page 100 that references PT-101
(defined on page 3) is never processed without that context.

Why this matters for safety-critical documents:
  A control narrative may define "Pump P-001, rated 150 bar" on page 3 and
  reference it only as "P-001" on page 100.  Without the registry the LLM
  sees a bare tag and may hallucinate the entity class — a wrong class skips
  the wrong IEC invariant and a real hazard goes undetected.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from src.ingestion.pdf_extractor import TextBlock

# ISA 5.1 instrument tag pattern — matches PT-101, XV-201A, P-001, ESD-001
_TAG_RE = re.compile(r"\b([A-Z]{1,3}-[0-9]{3,4}[A-Z]?)\b")

# Snippet window around each tag for context (chars)
_SNIPPET_RADIUS = 40


@dataclass
class TagEntry:
    """Single equipment tag seen in the document."""
    tag: str
    first_page: int
    snippet: str       # ≤80-char context excerpt from first occurrence
    source_doc: str


class GlobalEntityRegistry:
    """
    Full-document tag inventory built from raw text blocks (no LLM).

    Build once after PDFExtractor.extract(), then pass to every
    EntityExtractor chunk call via as_context_string().
    """

    def __init__(self) -> None:
        self._entries: Dict[str, TagEntry] = {}

    # ── Construction ──────────────────────────────────────────────────────────

    def build_from_blocks(self, blocks: "List[TextBlock]") -> "GlobalEntityRegistry":
        """
        Scan all text blocks and record the first occurrence of every ISA tag.
        O(total_chars) — typically < 50 ms for a 200-page document.
        """
        for block in blocks:
            upper_text = block.text.upper()  # normalise before regex — catches mixed-case OCR tags
            for match in _TAG_RE.finditer(upper_text):
                tag = match.group(1)  # already uppercase
                if tag in self._entries:
                    continue
                start   = max(0, match.start() - _SNIPPET_RADIUS)
                end     = min(len(block.text), match.end() + _SNIPPET_RADIUS)
                snippet = block.text[start:end].replace("\n", " ").strip()
                self._entries[tag] = TagEntry(
                    tag        = tag,
                    first_page = block.page,
                    snippet    = snippet,
                    source_doc = block.source_doc,
                )
        return self

    def add_tags_from_list(self, tags: List[str], source_doc: str = "pid") -> "GlobalEntityRegistry":
        """
        Merge tags extracted by PIDExtractor (OCR) into the registry.
        These have no page/snippet context so we use page=0 as a sentinel.
        """
        for tag in tags:
            if tag not in self._entries:
                self._entries[tag] = TagEntry(
                    tag        = tag,
                    first_page = 0,
                    snippet    = "(from P&ID / image OCR)",
                    source_doc = source_doc,
                )
        return self

    # ── Query / output ────────────────────────────────────────────────────────

    def all_tags(self) -> List[str]:
        return list(self._entries.keys())

    def size(self) -> int:
        return len(self._entries)

    def as_context_string(self) -> str:
        """
        Compact one-line summary injected at the top of every LLM chunk prompt.

        Format:
          "Equipment tags in this document: PT-101 (p.3), LT-201 (p.3), XV-301 (p.7), ..."

        Kept short deliberately — this string is prepended to EVERY chunk call,
        so it must not dominate the token budget.  Full snippets are available
        via as_detailed_context() when a larger context window allows.
        """
        if not self._entries:
            return "Equipment tags in this document: (none detected)"
        entries_sorted = sorted(
            self._entries.values(), key=lambda e: (e.first_page, e.tag)
        )
        parts = [
            f"{e.tag} (p.{e.first_page})" if e.first_page > 0 else f"{e.tag} (P&ID)"
            for e in entries_sorted
        ]
        return "Equipment tags in this document: " + ", ".join(parts)

    def as_detailed_context(self, max_entries: int = 50) -> str:
        """
        Detailed multi-line context — one line per tag with its snippet.
        Use this for large-context-window models (>= 32k tokens).
        max_entries caps total length for very large documents.
        """
        if not self._entries:
            return "No equipment tags detected in document.\n"
        lines = ["Equipment inventory (from full document scan):"]
        for entry in sorted(self._entries.values(), key=lambda e: (e.first_page, e.tag))[:max_entries]:
            page_str = f"p.{entry.first_page}" if entry.first_page > 0 else "P&ID"
            lines.append(f"  {entry.tag:12s} [{page_str}]  — {entry.snippet}")
        if len(self._entries) > max_entries:
            lines.append(f"  ... and {len(self._entries) - max_entries} more tags")
        return "\n".join(lines) + "\n"

    def __repr__(self) -> str:
        return f"GlobalEntityRegistry({len(self._entries)} tags)"
