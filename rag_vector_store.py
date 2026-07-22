"""Vector-store adapters shared by all RAG labs.

JSON is retained as an explicit teaching/offline fallback.  ChromaDB and
Pinecone are real retrieval backends: both upsert and query embeddings while
preserving citation and authorization metadata.
"""
from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse
from rag_security import protect_text, reveal_text

COLLECTION = "rag_foundation"
BACKENDS = {"json", "chroma", "pinecone"}


def backend_name(value: str | None = None) -> str:
    selected = (value or os.getenv("RAG_VECTOR_BACKEND", "chroma")).lower()
    if selected not in BACKENDS:
        raise ValueError(f"RAG_VECTOR_BACKEND must be one of {sorted(BACKENDS)}")
    return selected


def record_id(record: dict) -> str:
    return f"{record['source']}:{record['chunk_id']}"


def vector_metadata(record: dict) -> dict[str, str | int | float | bool]:
    """Return scalar metadata supported by both ChromaDB and Pinecone."""
    fields = ("source", "chunk_id", "page", "parent_id", "parent_title")
    return {key: value for key in fields if (value := record.get(key)) is not None}


def _chroma_collection(collection: str = COLLECTION):
    import chromadb

    endpoint = urlparse(os.getenv("CHROMA_URL", "http://localhost:8001"))
    client = chromadb.HttpClient(
        host=endpoint.hostname or "localhost",
        port=endpoint.port or (443 if endpoint.scheme == "https" else 8001),
        ssl=endpoint.scheme == "https",
    )
    return client.get_or_create_collection(collection, metadata={"hnsw:space": "cosine"})


def _pinecone_index():
    from dotenv import load_dotenv
    from pinecone import Pinecone

    load_dotenv()
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX")
    if not api_key or not index_name:
        raise RuntimeError("PINECONE_API_KEY and PINECONE_INDEX are required for the Pinecone backend")
    return Pinecone(api_key=api_key).Index(index_name)


def sync_records(records: list[dict], backend: str | None = None, collection: str = COLLECTION) -> int:
    """Upsert a completed index into the selected vector database."""
    selected = backend_name(backend)
    if selected == "json":
        return len(records)
    protected = [protect_text(item["source"], item["text"]) for item in records]
    if selected == "chroma":
        target = _chroma_collection(collection)
        target.upsert(
            ids=[record_id(item) for item in records],
            documents=[document for document, _ in protected],
            embeddings=[item["embedding"] for item in records],
            metadatas=[{**vector_metadata(item), **security} for item, (_, security) in zip(records, protected)],
        )
    else:
        target = _pinecone_index()
        target.upsert(
            vectors=[
                {
                    "id": record_id(item),
                    "values": item["embedding"],
                    "metadata": {**vector_metadata(item), **security, "text": document},
                }
                for item, (document, security) in zip(records, protected)
            ],
            namespace=collection,
        )
    return len(records)


def _normalise_result(metadata: dict[str, Any], document: str | None, score: float) -> dict:
    item = dict(metadata)
    stored_document = document if document is not None else item.pop("text", "")
    item["text"] = reveal_text(stored_document, item)
    item.pop("encrypted_text", None)
    try:
        item["chunk_id"] = int(item["chunk_id"])
    except (KeyError, TypeError, ValueError):
        pass
    item["score"] = float(score)
    item["dense_score"] = float(score)
    return item


def query_records(
    query_embedding: list[float],
    top_k: int = 5,
    backend: str | None = None,
    collection: str = COLLECTION,
    allowed_sources: list[str] | None = None,
) -> list[dict]:
    """Query a vector backend, applying document authorization server-side."""
    selected = backend_name(backend)
    if selected == "json":
        raise ValueError("JSON similarity search is implemented by rag_gemini_runtime.retrieve")
    if allowed_sources == []:
        return []

    if selected == "chroma":
        target = _chroma_collection(collection)
        count = target.count()
        if not count:
            raise RuntimeError(f"ChromaDB collection '{collection}' is empty; run the indexing command first")
        where = {"source": {"$in": allowed_sources}} if allowed_sources is not None else None
        result = target.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, count),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        return [
            _normalise_result(meta or {}, document, 1.0 - float(distance))
            for meta, document, distance in zip(metadatas, documents, distances)
        ]

    where = {"source": {"$in": allowed_sources}} if allowed_sources is not None else None
    query_args = {"vector": query_embedding, "top_k": top_k, "namespace": collection, "include_metadata": True}
    if where is not None:
        query_args["filter"] = where
    result = _pinecone_index().query(**query_args)
    matches = result.matches if hasattr(result, "matches") else result.get("matches", [])
    output = []
    for match in matches:
        metadata = dict(match.metadata if hasattr(match, "metadata") else match.get("metadata", {}))
        score = match.score if hasattr(match, "score") else match.get("score", 0.0)
        output.append(_normalise_result(metadata, metadata.pop("text", ""), score))
    return output
