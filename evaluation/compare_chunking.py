"""Generate a reproducible Fixed/Semantic/Hierarchical chunking comparison."""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rag_document_processing import document_files
from rag_gemini_runtime import DATA_DIR, STORE_DIR, chunk_document


def summarize(strategy: str) -> dict:
    chunks = [chunk for path in document_files(DATA_DIR) for chunk in chunk_document(path, strategy=strategy)]
    lengths = [len(chunk["text"]) for chunk in chunks]
    return {
        "strategy": strategy,
        "chunks": len(chunks),
        "average_characters": round(statistics.mean(lengths), 1),
        "median_characters": round(statistics.median(lengths), 1),
        "max_characters": max(lengths),
        "preserves_parent_metadata": all(bool(chunk.get("parent_id")) for chunk in chunks),
    }


report = {"strategies": [summarize(name) for name in ("fixed", "semantic", "hierarchical")]}
STORE_DIR.mkdir(exist_ok=True)
target = STORE_DIR / "chunking_comparison.json"
target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
