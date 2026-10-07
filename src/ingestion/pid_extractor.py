"""Phase 1c — P&ID tag extraction using OpenCV + Tesseract OCR.

Scope: extracts ICS tag strings (e.g. PT-101, P-101, XV-201) and performs
basic ISA 5.1 symbol detection via template matching for partial structural
extraction. Full semantic P&ID parsing is future work (documented in CITATION_TODO.md).
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple
import cv2
import numpy as np
from loguru import logger


# ICS tag pattern: 1-3 uppercase letters, hyphen, 3-4 digits, optional suffix
TAG_PATTERN = re.compile(r"\b([A-Z]{1,3}-[0-9]{3,4}[A-Z]?)\b")

# Symbol classes detectable via contour analysis (no template images required)
SYMBOL_CLASSES = {
    "pump": "circle_with_triangle",
    "valve": "diamond",
    "transmitter": "circle",
    "motor": "circle_large",
}


@dataclass
class DetectedSymbol:
    symbol_class: str
    bbox: Tuple[int, int, int, int]  # (x, y, w, h)
    nearby_tags: List[str] = field(default_factory=list)


@dataclass
class TagExtraction:
    tags: List[str]
    source_doc: str
    page: int = 1
    detected_symbols: List[DetectedSymbol] = field(default_factory=list)
    raw_ocr_text: str = ""


class PIDExtractor:
    """Extracts tag strings and basic structural information from P&ID diagrams."""

    def __init__(self, tesseract_cmd: Optional[str] = None):
        import pytesseract
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        self._pytesseract = pytesseract

    def extract_from_pdf_page(self, pdf_path: Path, page_num: int = 1) -> TagExtraction:
        """Extract tags from a specific page of a PDF (rendered as image)."""
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz
        doc = fitz.open(str(pdf_path))
        page = doc[page_num - 1]
        # Render at 300 DPI for good OCR quality
        mat = fitz.Matrix(300 / 72, 300 / 72)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")
        doc.close()

        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        return self._extract_from_image(img, source_doc=pdf_path.name, page=page_num)

    def extract_from_image(self, image_path: Path) -> TagExtraction:
        """Extract tags from a standalone P&ID image file."""
        img = cv2.imread(str(image_path))
        if img is None:
            raise ValueError(f"Cannot read image: {image_path}")
        return self._extract_from_image(img, source_doc=image_path.name)

    def extract_from_tag_list(self, tag_file: Path) -> TagExtraction:
        """Load tags directly from a plain-text tag list (benchmark corpus format)."""
        text = tag_file.read_text(encoding="utf-8")
        tags = list(set(TAG_PATTERN.findall(text.upper())))
        return TagExtraction(tags=sorted(tags), source_doc=tag_file.name, raw_ocr_text=text)

    def _extract_from_image(self, img: np.ndarray, source_doc: str, page: int = 1) -> TagExtraction:
        preprocessed = self._preprocess(img)

        # OCR with PSM 11 (sparse text, good for diagrams)
        ocr_text = self._pytesseract.image_to_string(
            preprocessed,
            config="--psm 11 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        )

        tags = sorted(set(TAG_PATTERN.findall(ocr_text.upper())))

        # Basic ISA 5.1 symbol detection via contour geometry
        symbols = self._detect_symbols(img, tags)

        logger.info(f"P&ID extraction: {len(tags)} tags, {len(symbols)} symbols from {source_doc} p.{page}")
        return TagExtraction(
            tags=tags,
            source_doc=source_doc,
            page=page,
            detected_symbols=symbols,
            raw_ocr_text=ocr_text,
        )

    @staticmethod
    def _preprocess(img: np.ndarray) -> np.ndarray:
        """Grayscale → denoise → adaptive threshold → slight dilation to connect text."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray, h=10)
        thresh = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
        )
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        dilated = cv2.dilate(thresh, kernel, iterations=1)
        return cv2.bitwise_not(dilated)

    def _detect_symbols(self, img: np.ndarray, known_tags: List[str]) -> List[DetectedSymbol]:
        """
        Detect common ISA 5.1 symbols using contour geometry heuristics.
        Circles → instruments/transmitters; large circles with inscribed shapes → pumps.
        This provides partial structural information without requiring external template images.
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        symbols: List[DetectedSymbol] = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 200 or area > 50000:
                continue

            x, y, w, h = cv2.boundingRect(cnt)
            aspect = w / (h + 1e-6)
            perimeter = cv2.arcLength(cnt, True)
            circularity = 4 * np.pi * area / (perimeter ** 2 + 1e-6)

            if 0.8 <= circularity <= 1.2 and 0.7 <= aspect <= 1.3:
                symbol_class = "transmitter" if area < 2000 else "pump"
            elif circularity < 0.5 and 0.8 <= aspect <= 1.2:
                symbol_class = "valve"
            else:
                continue

            # Find tags near this symbol (within 100px)
            nearby = [t for t in known_tags if self._tag_near_bbox(t, (x, y, w, h), img.shape)]
            symbols.append(DetectedSymbol(
                symbol_class=symbol_class,
                bbox=(x, y, w, h),
                nearby_tags=nearby,
            ))

        return symbols

    @staticmethod
    def _tag_near_bbox(tag: str, bbox: Tuple, img_shape: Tuple) -> bool:
        # Without OCR bounding boxes for each tag, we cannot do precise spatial matching.
        # Return False for now; override if per-word OCR data is available.
        return False
