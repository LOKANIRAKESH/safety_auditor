"""Phase 1b — Table extraction from PDFs using pdfplumber and Camelot."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import pandas as pd
from loguru import logger


@dataclass
class ExtractedTable:
    dataframe: pd.DataFrame
    page: int
    source_doc: str
    extraction_method: str  # "camelot" or "pdfplumber"
    table_index: int = 0


class TableExtractor:
    """Extracts tables from PDF — tries Camelot (lattice) first, falls back to pdfplumber."""

    def extract(self, pdf_path: Path) -> List[ExtractedTable]:
        pdf_path = Path(pdf_path)
        results: List[ExtractedTable] = []

        # Try Camelot lattice mode first (best for bordered C&E tables)
        try:
            results = self._extract_camelot(pdf_path)
            if results:
                logger.info(f"Camelot extracted {len(results)} tables from {pdf_path.name}")
                return results
        except Exception as e:
            logger.warning(f"Camelot failed for {pdf_path.name}: {e}. Falling back to pdfplumber.")

        # Fallback: pdfplumber
        results = self._extract_pdfplumber(pdf_path)
        logger.info(f"pdfplumber extracted {len(results)} tables from {pdf_path.name}")
        return results

    def _extract_camelot(self, pdf_path: Path) -> List[ExtractedTable]:
        import camelot
        tables = camelot.read_pdf(str(pdf_path), pages="all", flavor="lattice")
        results = []
        for i, t in enumerate(tables):
            df = t.df
            if df.empty or df.shape[0] < 2:
                continue
            # Promote first row to header
            df.columns = df.iloc[0].str.strip()
            df = df.iloc[1:].reset_index(drop=True)
            df.columns = [str(c).strip() for c in df.columns]
            results.append(ExtractedTable(
                dataframe=df,
                page=t.page,
                source_doc=pdf_path.name,
                extraction_method="camelot",
                table_index=i,
            ))
        return results

    def _extract_pdfplumber(self, pdf_path: Path) -> List[ExtractedTable]:
        import pdfplumber
        results = []
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables()
                for i, raw_table in enumerate(tables):
                    if not raw_table or len(raw_table) < 2:
                        continue
                    headers = [str(h).strip() if h else f"col_{j}" for j, h in enumerate(raw_table[0])]
                    rows = [[str(c).strip() if c else "" for c in row] for row in raw_table[1:]]
                    df = pd.DataFrame(rows, columns=headers)
                    results.append(ExtractedTable(
                        dataframe=df,
                        page=page_num,
                        source_doc=pdf_path.name,
                        extraction_method="pdfplumber",
                        table_index=i,
                    ))
        return results

    @staticmethod
    def is_cause_effect_table(df: pd.DataFrame) -> bool:
        """Heuristic: a C&E table has columns containing 'cause', 'effect', 'action', or 'tag'."""
        col_text = " ".join(str(c).lower() for c in df.columns)
        keywords = ["cause", "effect", "action", "trip", "alarm", "condition", "tag", "interlock"]
        return any(k in col_text for k in keywords)
