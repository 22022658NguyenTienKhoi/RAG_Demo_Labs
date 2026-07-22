"""Optionally mirror the Lab 01 JSON index to ChromaDB or Pinecone."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve(); ROOT = next(p for p in HERE.parents if (p / "rag_gemini_runtime.py").exists())
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
from rag_gemini_runtime import STORE_DIR, load_index

def ids(records): return [f"{item['source']}:{item['chunk_id']}" for item in records]
def metadata(item): return {key: str(value) for key, value in item.items() if key in {"source", "chunk_id", "page", "parent_id", "parent_title"}}

def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--backend", choices=["chroma", "pinecone"], required=True)
    parser.add_argument("--collection", default="rag_foundation")
    parser.add_argument("--chroma-url", default=os.getenv("CHROMA_URL", "http://localhost:8000"), help="Docker ChromaDB endpoint")
    args = parser.parse_args(); records = load_index("foundation")
    if args.backend == "chroma":
        import chromadb
        from urllib.parse import urlparse
        endpoint = urlparse(args.chroma_url)
        client = chromadb.HttpClient(host=endpoint.hostname or "localhost", port=endpoint.port or 8000, ssl=endpoint.scheme == "https")
        collection = client.get_or_create_collection(args.collection)
        collection.upsert(ids=ids(records), documents=[item["text"] for item in records], embeddings=[item["embedding"] for item in records], metadatas=[metadata(item) for item in records])
    else:
        from pinecone import Pinecone
        load_dotenv(ROOT / ".env"); api_key = os.getenv("PINECONE_API_KEY"); index_name = os.getenv("PINECONE_INDEX")
        if not api_key or not index_name: raise RuntimeError("Set PINECONE_API_KEY and PINECONE_INDEX in .env")
        index = Pinecone(api_key=api_key).Index(index_name)
        index.upsert(vectors=[{"id": key, "values": item["embedding"], "metadata": {**metadata(item), "text": item["text"]}} for key, item in zip(ids(records), records)], namespace=args.collection)
    print(f"Synced {len(records)} vectors to {args.backend}/{args.collection}.")

if __name__ == "__main__": main()
