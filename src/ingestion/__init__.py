"""Phase 1 — Document Ingestion: text, tables, images, chunking, entity registry."""
from src.ingestion.pdf_extractor import PDFExtractor, TextBlock
from src.ingestion.table_extractor import TableExtractor, ExtractedTable
from src.ingestion.pid_extractor import PIDExtractor, TagExtraction
from src.ingestion.entity_registry import GlobalEntityRegistry, TagEntry
from src.ingestion.chunker import SemanticChunker, DocumentChunk
from src.ingestion.image_extractor import PDFImageExtractor, ExtractedImage

__all__ = [
    "PDFExtractor",       "TextBlock",
    "TableExtractor",     "ExtractedTable",
    "PIDExtractor",       "TagExtraction",
    "GlobalEntityRegistry","TagEntry",
    "SemanticChunker",    "DocumentChunk",
    "PDFImageExtractor",  "ExtractedImage",
]
