"""Initialize persistent services, then start the FastAPI application."""
from __future__ import annotations

import os

from document_catalog import document_metadata
from rag_enterprise_store import save_catalog
from rag_gemini_runtime import STORE_DIR, build_or_load_index
from rag_vector_store import sync_records


def main() -> None:
    records = build_or_load_index("foundation")
    sync_records(records, backend=os.getenv("RAG_VECTOR_BACKEND", "chroma"))
    catalog = {source: document_metadata(source) for source in sorted({record["source"] for record in records})}
    save_catalog(catalog, STORE_DIR / "metadata_catalog.json")
    os.execvp("uvicorn", ["uvicorn", "03_metadata_enterprise_chatbot.api:app", "--host", "0.0.0.0", "--port", "8000"])


if __name__ == "__main__":
    main()
