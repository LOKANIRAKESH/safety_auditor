"""Phase 1a — PDF text extraction using PyMuPDF."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
try:
    import pymupdf as fitz  # PyMuPDF >= 1.24 preferred import
except ImportError:
    import fitz  # fallback for older versions
from loguru import logger


@dataclass
class TextBlock:
    text: str
    page: int
    bbox: tuple[float, float, float, float]  # (x0, y0, x1, y1)
    source_doc: str
    block_type: str = "text"  # text | heading | paragraph


class PDFExtractor:
    """Extracts structured text blocks from PDF documents with page provenance."""

    MIN_BLOCK_LEN = 10  # discard noise fragments shorter than this

    def extract(self, pdf_path: Path) -> List[TextBlock]:
        """Return all text blocks from pdf_path, ordered by page and vertical position."""
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        blocks: List[TextBlock] = []
        doc = fitz.open(str(pdf_path))

        for page_num, page in enumerate(doc, start=1):
            raw_blocks = page.get_text("blocks")  # list of (x0,y0,x1,y1,text,block_no,block_type)
            for b in raw_blocks:
                x0, y0, x1, y1, text, _, block_type_code = b
                text = text.strip()
                if len(text) < self.MIN_BLOCK_LEN:
                    continue
                block_type = "heading" if self._is_heading(text, y0) else "text"
                blocks.append(TextBlock(
                    text=text,
                    page=page_num,
                    bbox=(x0, y0, x1, y1),
                    source_doc=pdf_path.name,
                    block_type=block_type,
                ))

        doc.close()
        logger.info(f"Extracted {len(blocks)} text blocks from {pdf_path.name}")
        return blocks

    def extract_full_text(self, pdf_path: Path) -> str:
        """Return the entire document as a single string (for LLM context)."""
        blocks = self.extract(pdf_path)
        return "\n\n".join(b.text for b in blocks)

    @staticmethod
    def _is_heading(text: str, y_pos: float) -> bool:
        """Heuristic: all-caps short lines or numbered section headings are headings."""
        stripped = text.strip()
        if len(stripped) < 80 and stripped.isupper():
            return True
        import re
        if re.match(r"^\d+(\.\d+)*\s+[A-Z]", stripped):
            return True
        return False
