"""
PDF Image Extractor — Phase 1 embedded-image and scanned-page handler.

Handles three cases that PDFExtractor.extract() silently ignores:

  Case 1 — Scanned page:
    Some pages have no text layer at all (< 30 chars) but contain a full-page
    raster image (e.g. a scanned P&ID drawing).  We render the page at
    config.pid_ocr_dpi DPI and run the full PIDExtractor pipeline on it.

  Case 2 — Large embedded image (PID_CANDIDATE):
    An image embedded in a text-PDF page with width >= config.pid_candidate_min_px.
    These are almost always engineering diagrams.  We extract the raw image bytes
    and run PIDExtractor on them.

  Case 3 — Medium embedded image (FIGURE):
    Embedded images 100–800 px wide — process flow icons, block diagrams, alarm
    annunciator maps.  We run Tesseract PSM 6 (uniform block of text) to capture
    any numeric thresholds or tag labels printed on the figure.

  Case 4 — Small image (ICON):
    < config.image_min_size_px in either dimension — logos, decorative borders.
    Skipped entirely; no OCR performed.

All results carry full provenance: source_doc, page, image_class, bbox,
extracted_tags, raw_ocr_text so every downstream finding can be traced
back to the exact page and image.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

import numpy as np
from loguru import logger

if TYPE_CHECKING:
    from src.ingestion.pid_extractor import PIDExtractor
    from src.config import PipelineConfig

# ISA 5.1 tag pattern — same as GlobalEntityRegistry and PIDExtractor
_TAG_RE = re.compile(r"\b([A-Z]{1,3}-[0-9]{3,4}[A-Z]?)\b")

# Image classification constants
IMAGE_ICON    = "ICON"          # too small to contain useful data
IMAGE_FIGURE  = "FIGURE"        # medium: text OCR (PSM 6)
IMAGE_PID     = "PID_CANDIDATE" # large: full P&ID pipeline
IMAGE_SCANNED = "SCANNED_PAGE"  # no text layer: render entire page

# Minimum text chars below which a page is considered scanned/image-only
_SCANNED_PAGE_TEXT_THRESHOLD = 30


@dataclass
class ExtractedImage:
    """
    A single image extracted from a PDF, with OCR results and provenance.

    Fields
    ------
    image_class   : one of IMAGE_ICON / IMAGE_FIGURE / IMAGE_PID / IMAGE_SCANNED
    page          : 1-based page number in the source PDF
    source_doc    : filename of the originating PDF
    extracted_tags: ISA instrument tags found in this image (may be empty for ICON)
    raw_ocr_text  : tag-focused OCR output (PSM 11 + whitelist, for P&ID diagrams)
    full_text_ocr : full prose OCR output (PSM 3, no whitelist) — populated only for
                    SCANNED_PAGE images; used to create TextBlocks for LLM extraction
    width, height : pixel dimensions of the image
    bbox          : (x0, y0, x1, y1) bounding box on the PDF page in pt units
                    (0, 0, 0, 0) for scanned-page renders
    """
    image_class:    str
    page:           int
    source_doc:     str
    extracted_tags: List[str]
    raw_ocr_text:   str
    width:          int
    height:         int
    bbox:           tuple = field(default_factory=lambda: (0, 0, 0, 0))
    full_text_ocr:  str = ""


class PDFImageExtractor:
    """
    Walks every page of a PDF and extracts all meaningful image content.

    Usage:
        extractor = PDFImageExtractor()
        images    = extractor.extract_from_pdf(pdf_path, pid_extractor, config)
        all_tags  = [t for img in images for t in img.extracted_tags]
    """

    def extract_from_pdf(
        self,
        pdf_path:      Path,
        pid_extractor: "PIDExtractor",
        config:        "PipelineConfig",
    ) -> List[ExtractedImage]:
        """
        Main entry point.  Returns one ExtractedImage per processed image/page.
        ICON images are filtered out and not returned.
        """
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz

        pdf_path  = Path(pdf_path)
        doc       = fitz.open(str(pdf_path))
        results:  List[ExtractedImage] = []

        for page_num, page in enumerate(doc, start=1):
            page_results = self._process_page(
                doc, page, page_num, pdf_path.name, pid_extractor, config
            )
            results.extend(page_results)

        doc.close()

        n_pid     = sum(1 for r in results if r.image_class == IMAGE_PID)
        n_fig     = sum(1 for r in results if r.image_class == IMAGE_FIGURE)
        n_scanned = sum(1 for r in results if r.image_class == IMAGE_SCANNED)
        n_tags    = sum(len(r.extracted_tags) for r in results)
        logger.info(
            f"Image extraction [{pdf_path.name}]: "
            f"{n_pid} P&ID, {n_fig} figure, {n_scanned} scanned-page | "
            f"{n_tags} tags total"
        )
        return results

    # ── Per-page logic ────────────────────────────────────────────────────────

    def _process_page(
        self,
        doc,
        page,
        page_num:      int,
        source_doc:    str,
        pid_extractor: "PIDExtractor",
        config:        "PipelineConfig",
    ) -> List[ExtractedImage]:
        results: List[ExtractedImage] = []

        try:
            import pymupdf as fitz
        except ImportError:
            import fitz

        page_text = page.get_text().strip()
        image_list = page.get_images(full=True)

        # Case 1: scanned page (almost no text, but has images)
        if len(page_text) < _SCANNED_PAGE_TEXT_THRESHOLD and image_list:
            result = self._ocr_full_page(
                page, page_num, source_doc, pid_extractor, config
            )
            if result:
                results.append(result)
            return results

        # Case 2+3+4: text page with embedded images
        for img_info in image_list:
            xref = img_info[0]
            try:
                result = self._process_embedded_image(
                    doc, xref, page, page_num, source_doc, pid_extractor, config
                )
                if result:  # None means ICON — skip
                    results.append(result)
            except Exception as exc:
                logger.warning(
                    f"Image xref {xref} on p.{page_num} of {source_doc}: {exc}"
                )

        return results

    def _ocr_full_page(
        self,
        page,
        page_num:      int,
        source_doc:    str,
        pid_extractor: "PIDExtractor",
        config:        "PipelineConfig",
    ) -> Optional[ExtractedImage]:
        """Render the entire page as a raster and OCR it.

        Two OCR passes:
          Pass 1 (P&ID):  PSM 11 + char whitelist → ISA instrument tags
          Pass 2 (text):  PSM 3 + no whitelist    → full prose text for LLM
        """
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz

        dpi = getattr(config, "pid_ocr_dpi", 300)
        scale = dpi / 72.0
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")

        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        import cv2
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if img is None:
            return None

        # Pass 1: P&ID tag extraction (PSM 11 + whitelist)
        extraction = pid_extractor._extract_from_image(
            img, source_doc=source_doc, page=page_num
        )

        # Pass 2: full-text OCR (PSM 3, no whitelist) — for LLM ingestion
        full_text = ""
        try:
            import pytesseract
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # Light denoise only — preserve text crispness
            denoised = cv2.fastNlMeansDenoising(gray, h=10)
            full_text = pytesseract.image_to_string(
                denoised,
                config="--psm 3 --oem 3"
            ).strip()
        except Exception as exc:
            logger.debug(f"Full-text OCR failed p.{page_num} [{source_doc}]: {exc}")

        h, w = img.shape[:2]
        logger.debug(
            f"Scanned page p.{page_num} [{source_doc}]: "
            f"{len(extraction.tags)} tags, {w}×{h}px, "
            f"full_text={len(full_text)} chars"
        )
        return ExtractedImage(
            image_class    = IMAGE_SCANNED,
            page           = page_num,
            source_doc     = source_doc,
            extracted_tags = extraction.tags,
            raw_ocr_text   = extraction.raw_ocr_text,
            full_text_ocr  = full_text,
            width          = w,
            height         = h,
            bbox           = (0, 0, 0, 0),
        )

    def _process_embedded_image(
        self,
        doc,
        xref:          int,
        page,
        page_num:      int,
        source_doc:    str,
        pid_extractor: "PIDExtractor",
        config:        "PipelineConfig",
    ) -> Optional[ExtractedImage]:
        """Extract, classify, and OCR one embedded image by its xref."""
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz

        pix = fitz.Pixmap(doc, xref)
        # Convert CMYK (n=4, alpha=0), CMYK+alpha (n=5), or RGBA (n=4, alpha=1)
        # to plain RGB so OpenCV can decode the PNG correctly.
        # pix.n > 3 catches: RGBA (4), CMYK (4), CMYK+alpha (5).
        if pix.n > 3:
            pix = fitz.Pixmap(fitz.csRGB, pix)

        w, h = pix.width, pix.height
        img_bytes = pix.tobytes("png")

        # Get bounding box on the page
        bbox = self._get_image_bbox(page, xref)

        # --- Classify ---
        min_px     = getattr(config, "image_min_size_px",    100)
        pid_min_px = getattr(config, "pid_candidate_min_px", 800)

        if w < min_px or h < min_px:
            return None  # ICON — skip

        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        import cv2
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if img is None:
            return None

        if w >= pid_min_px:
            # Full P&ID pipeline
            extraction = pid_extractor._extract_from_image(
                img, source_doc=source_doc, page=page_num
            )
            image_class = IMAGE_PID
            tags        = extraction.tags
            ocr_text    = extraction.raw_ocr_text
            logger.debug(
                f"P&ID image p.{page_num} [{source_doc}] {w}×{h}px: {len(tags)} tags"
            )
        else:
            # FIGURE: simple text OCR (PSM 6 — uniform block of text)
            tags, ocr_text = self._ocr_figure(img, source_doc, page_num)
            image_class = IMAGE_FIGURE
            logger.debug(
                f"Figure image p.{page_num} [{source_doc}] {w}×{h}px: {len(tags)} tags"
            )

        return ExtractedImage(
            image_class    = image_class,
            page           = page_num,
            source_doc     = source_doc,
            extracted_tags = tags,
            raw_ocr_text   = ocr_text,
            width          = w,
            height         = h,
            bbox           = bbox,
        )

    # ── OCR helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _ocr_figure(img, source_doc: str, page: int):
        """
        PSM 6 (assume uniform block of text) OCR for medium embedded figures.
        Returns (tags, raw_ocr_text).
        """
        import pytesseract
        import cv2

        gray    = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, bw   = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        ocr_raw = pytesseract.image_to_string(
            bw,
            config="--psm 6 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_. "
        )
        tags = sorted(set(_TAG_RE.findall(ocr_raw.upper())))
        return tags, ocr_raw

    @staticmethod
    def _get_image_bbox(page, xref: int) -> tuple:
        """Return (x0,y0,x1,y1) bounding box of image xref on the page (in pt)."""
        try:
            for item in page.get_image_rects(xref, transform=False):
                if item:
                    r = item[0] if isinstance(item, (list, tuple)) else item
                    return (r.x0, r.y0, r.x1, r.y1)
        except Exception:
            pass
        return (0, 0, 0, 0)
