"""Phase 2 — LLM-assisted entity extraction using Ollama."""
from src.extraction.entity_extractor import EntityExtractor
from src.extraction.prompts import build_extraction_prompt

__all__ = ["EntityExtractor", "build_extraction_prompt"]
