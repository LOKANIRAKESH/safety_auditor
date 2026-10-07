"""Loads safety invariant templates from JSON files."""
from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict, Any
from loguru import logger


class InvariantLoader:
    """Loads all invariant templates from a directory of JSON files."""

    def load_all(self, templates_dir: Path) -> List[Dict[str, Any]]:
        templates_dir = Path(templates_dir)
        all_invariants: List[Dict[str, Any]] = []

        json_files = sorted(templates_dir.glob("*.json"))
        if not json_files:
            logger.warning(f"No invariant template JSON files found in {templates_dir}")
            return []

        for json_file in json_files:
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
                invariants = data.get("invariants", [])
                for inv in invariants:
                    inv["_source_file"] = json_file.name
                all_invariants.extend(invariants)
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Failed to load {json_file}: {e}")

        logger.info(f"Loaded {len(all_invariants)} invariant templates from {len(json_files)} files")
        return all_invariants
