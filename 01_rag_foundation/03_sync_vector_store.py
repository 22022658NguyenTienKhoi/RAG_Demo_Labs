"""Upsert the Lab 01 index into a queryable ChromaDB or Pinecone backend."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve(); ROOT = next(p for p in HERE.parents if (p / "rag_gemini_runtime.py").exists())
sys.path.insert(0, str(ROOT))
from rag_gemini_runtime import load_index
from rag_vector_store import sync_records

def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--backend", choices=["chroma", "pinecone"], required=True)
    parser.add_argument("--collection", default="rag_foundation")
    args = parser.parse_args(); records = load_index("foundation")
    count = sync_records(records, backend=args.backend, collection=args.collection)
    print(f"Synced {count} queryable vectors to {args.backend}/{args.collection}.")

if __name__ == "__main__": main()
