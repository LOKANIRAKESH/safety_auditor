from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).parent.parent


class PipelineConfig(BaseSettings):
    # LLM
    ollama_host: str = "http://localhost:11434"
    llm_model: str = "qwen2.5"
    llm_fallback_model: str = "llama3"
    extraction_confidence_threshold: float = 0.7
    llm_temperature: float = 0.1
    llm_max_tokens: int = 4096

    # Cross-modal linking (ablation hook: set False to disable)
    enable_cross_modal_linking: bool = True
    fuzzy_match_threshold: int = 85
    embedding_similarity_threshold: float = 0.75
    embedding_borderline_low: float = 0.65
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Paths
    data_dir: Path = BASE_DIR / "data"
    output_dir: Path = BASE_DIR / "output"
    benchmark_dir: Path = BASE_DIR / "benchmark" / "corpus"
    invariants_dir: Path = BASE_DIR / "src" / "invariants" / "templates"
    report_templates_dir: Path = BASE_DIR / "src" / "reporting" / "templates"
    plc_templates_dir: Path = BASE_DIR / "src" / "plc" / "templates"

    # Z3 formal verification
    z3_timeout_ms: int = 5000
    z3_max_depth: int = 10

    # Reporting
    report_format: str = "html"

    # Phase 1 — Semantic chunking for large PDFs
    chunk_max_chars: int = 5000        # max chars per DocumentChunk before splitting
    chunk_overlap_chars: int = 300     # overlap between adjacent oversized chunks

    # Phase 1 — Image extraction thresholds
    pid_ocr_dpi: int = 300             # DPI for rendering scanned pages / P&ID pages
    image_min_size_px: int = 100       # skip images smaller than this (icons/logos)
    pid_candidate_min_px: int = 800    # images wider than this get full P&ID pipeline

    # Tesseract (update path for Windows if needed)
    tesseract_cmd: str = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


config = PipelineConfig()
