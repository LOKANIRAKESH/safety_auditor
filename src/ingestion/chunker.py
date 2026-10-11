"""
Semantic Section Chunker — Phase 1 large-document handler.

Converts a flat list of TextBlock objects into DocumentChunk objects, one
chunk per document section.  Sections are detected by heading TextBlocks
(block_type == "heading") from PDFExtractor.

Why section-based rather than fixed-size?
  A fixed 4000-char window may cut a cause-effect rule in half: the CAUSE
  is at the bottom of chunk N and the EFFECT is at the top of chunk N+1.
  The LLM then misses the rule entirely.  Section boundaries are semantically
  safe cut points — an engineer writing a control narrative would never split
  a single alarm rule across two sections.

Large sections (> chunk_max_chars) are split at paragraph breaks (double
newlines) with chunk_overlap_chars overlap so no rule straddles a cut.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.ingestion.pdf_extractor import TextBlock

_PARAGRAPH_SEP = "\n\n"
_FALLBACK_SECTION = "DOCUMENT"


@dataclass
class DocumentChunk:
    """
    A semantically coherent slice of a specification document.

    section_title : heading text that opens this chunk (or "DOCUMENT" for preamble)
    page_start    : first page number covered
    page_end      : last page number covered
    source_doc    : filename of the originating PDF
    text          : full text of this chunk (may include overlap prefix)
    chunk_index   : 0-based position in the chunk sequence for this document
    overlap_prefix: True if this chunk starts with overlap text from previous chunk
    """
    section_title:  str
    page_start:     int
    page_end:       int
    source_doc:     str
    text:           str
    chunk_index:    int
    overlap_prefix: bool = False

    def char_count(self) -> int:
        return len(self.text)

    def __repr__(self) -> str:
        return (
            f"DocumentChunk(#{self.chunk_index} "
            f"'{self.section_title[:40]}' "
            f"pp.{self.page_start}-{self.page_end} "
            f"{self.char_count()}ch)"
        )


class SemanticChunker:
    """
    Groups TextBlock objects into DocumentChunk objects by section boundaries.

    Usage:
        chunker = SemanticChunker(max_chars=5000, overlap_chars=300)
        chunks  = chunker.chunk(text_blocks)
    """

    def __init__(self, max_chars: int = 5000, overlap_chars: int = 300) -> None:
        self.max_chars     = max_chars
        self.overlap_chars = overlap_chars

    # ── Public API ────────────────────────────────────────────────────────────

    def chunk(self, blocks: "List[TextBlock]") -> List[DocumentChunk]:
        """
        Convert a flat list of TextBlock objects into DocumentChunk objects.

        Steps:
          1. Walk blocks; when a heading is found, close the current section
             and open a new one.
          2. Each completed section is passed through _split_if_oversized()
             which adds overlap as needed.
          3. Return the final chunk list with sequential chunk_index values.
        """
        if not blocks:
            return []

        sections = self._group_into_sections(blocks)
        chunks: List[DocumentChunk] = []
        idx = 0

        for title, section_blocks in sections:
            section_chunks = self._split_if_oversized(title, section_blocks)
            for chunk in section_chunks:
                chunk.chunk_index = idx
                chunks.append(chunk)
                idx += 1

        return chunks

    def wrap_single_text(self, text: str, source_doc: str = "", page: int = 1) -> List[DocumentChunk]:
        """
        Convenience: chunk a plain string (e.g. from a table row) that has no
        TextBlock structure.  Returns one or more chunks with page=page.
        """
        if len(text) <= self.max_chars:
            return [DocumentChunk(
                section_title  = "TEXT",
                page_start     = page,
                page_end       = page,
                source_doc     = source_doc,
                text           = text,
                chunk_index    = 0,
                overlap_prefix = False,
            )]
        # Split at paragraph breaks
        split_chunks = self._split_text(
            text          = text,
            section_title = "TEXT",
            page_start    = page,
            page_end      = page,
            source_doc    = source_doc,
        )
        for i, ch in enumerate(split_chunks):
            ch.chunk_index = i
        return split_chunks

    # ── Internals ─────────────────────────────────────────────────────────────

    def _group_into_sections(
        self, blocks: "List[TextBlock]"
    ) -> List[tuple[str, "List[TextBlock]"]]:
        """Group consecutive TextBlocks under their nearest preceding heading."""
        sections: List[tuple[str, "List[TextBlock]"]] = []
        current_title  = _FALLBACK_SECTION
        current_blocks: "List[TextBlock]" = []

        for block in blocks:
            if block.block_type == "heading":
                if current_blocks:
                    sections.append((current_title, current_blocks))
                current_title  = block.text.strip()
                current_blocks = []
            else:
                current_blocks.append(block)

        if current_blocks:
            sections.append((current_title, current_blocks))

        return sections if sections else [(_FALLBACK_SECTION, blocks)]

    def _split_if_oversized(
        self, title: str, blocks: "List[TextBlock]"
    ) -> List[DocumentChunk]:
        """
        Join the section's blocks into text, then split if > max_chars.
        """
        if not blocks:
            return []

        full_text  = _PARAGRAPH_SEP.join(b.text for b in blocks)
        page_start = blocks[0].page
        page_end   = blocks[-1].page
        source_doc = blocks[0].source_doc

        if len(full_text) <= self.max_chars:
            return [DocumentChunk(
                section_title  = title,
                page_start     = page_start,
                page_end       = page_end,
                source_doc     = source_doc,
                text           = full_text,
                chunk_index    = 0,
            )]

        return self._split_text(
            text          = full_text,
            section_title = title,
            page_start    = page_start,
            page_end      = page_end,
            source_doc    = source_doc,
        )

    def _split_text(
        self,
        text:          str,
        section_title: str,
        page_start:    int,
        page_end:      int,
        source_doc:    str,
    ) -> List[DocumentChunk]:
        """
        Split oversized text at paragraph boundaries with overlap.

        Strategy:
          1. Split at _PARAGRAPH_SEP to get natural paragraph breaks.
          2. Greedily accumulate paragraphs until the chunk would exceed max_chars.
          3. Emit the chunk; the next chunk starts with the last overlap_chars
             characters of the previous chunk as a prefix (overlap).
          4. If a single paragraph itself exceeds max_chars (no internal breaks),
             fall back to hard character-level splitting to guarantee max size.
        """
        paragraphs = text.split(_PARAGRAPH_SEP)
        chunks: List[DocumentChunk] = []
        current_paras: List[str]    = []
        overlap_text: str           = ""

        def _emit(is_overlap: bool) -> None:
            chunk_text = (overlap_text + _PARAGRAPH_SEP if overlap_text else "") + _PARAGRAPH_SEP.join(current_paras)
            chunks.append(DocumentChunk(
                section_title  = section_title,
                page_start     = page_start,
                page_end       = page_end,
                source_doc     = source_doc,
                text           = chunk_text.strip(),
                chunk_index    = 0,   # will be set by caller
                overlap_prefix = is_overlap,
            ))

        for para in paragraphs:
            # If the paragraph itself is too long, hard-split it first
            if len(para) > self.max_chars:
                # Emit any pending content first
                if current_paras:
                    _emit(bool(overlap_text))
                    prev = _PARAGRAPH_SEP.join(current_paras)
                    overlap_text  = prev[-self.overlap_chars:] if len(prev) > self.overlap_chars else prev
                    current_paras = []
                # Hard-split the oversized paragraph at word boundaries
                for sub_para in self._hard_split(para):
                    current_paras = [sub_para]
                    _emit(bool(overlap_text))
                    overlap_text  = sub_para[-self.overlap_chars:]
                    current_paras = []
                continue

            candidate = _PARAGRAPH_SEP.join(current_paras + [para])
            if len(candidate) > self.max_chars and current_paras:
                _emit(bool(overlap_text))
                prev_text     = _PARAGRAPH_SEP.join(current_paras)
                overlap_text  = prev_text[-self.overlap_chars:] if len(prev_text) > self.overlap_chars else prev_text
                current_paras = [para]
            else:
                current_paras.append(para)

        if current_paras:
            _emit(bool(overlap_text))

        return chunks

    def _hard_split(self, text: str) -> List[str]:
        """
        Last-resort character-level split for paragraphs with no whitespace breaks.
        Tries to split at spaces; falls back to exact max_chars boundary.
        """
        parts: List[str] = []
        while len(text) > self.max_chars:
            # Find last space within max_chars window
            split_at = text.rfind(" ", 0, self.max_chars)
            if split_at == -1:
                split_at = self.max_chars
            parts.append(text[:split_at].strip())
            text = text[split_at:].strip()
        if text:
            parts.append(text)
        return parts
