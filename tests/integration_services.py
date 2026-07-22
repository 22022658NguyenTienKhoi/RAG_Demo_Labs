"""Live ChromaDB/PostgreSQL/Redis integration check (no Gemini API call)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from document_catalog import document_metadata
from rag_enterprise_store import append_audit, cache_get, cache_set, database_url, load_catalog, save_catalog
from rag_gemini_runtime import STORE_DIR, load_index
from rag_vector_store import query_records, sync_records

records = load_index("foundation")
sync_records(records, backend="chroma")
source = records[0]["source"]
hits = query_records(records[0]["embedding"], top_k=3, backend="chroma", allowed_sources=[source])
assert hits and {hit["source"] for hit in hits} == {source}, "ChromaDB RBAC-filtered query failed"

catalog = {name: document_metadata(name) for name in sorted({record["source"] for record in records})}
assert save_catalog(catalog, STORE_DIR / "metadata_catalog.json") == "postgresql"
assert load_catalog(STORE_DIR / "metadata_catalog.json").keys() == catalog.keys()

cache_set("rag:integration:test", {"ok": True}, ttl_seconds=60)
assert cache_get("rag:integration:test") == {"ok": True}

entry = {
    "time": datetime.now(timezone.utc).isoformat(),
    "event": "integration_test",
    "role": "internal_auditor",
    "question_hash": "test-hash-no-raw-question",
    "sources": [source],
    "outcome": {"passed": True},
}
assert append_audit(entry, STORE_DIR / "audit_log.jsonl") == "postgresql"

import psycopg
with psycopg.connect(database_url()) as connection, connection.cursor() as cursor:
    cursor.execute("SELECT COUNT(*) FROM audit_events WHERE event_type='integration_test'")
    assert cursor.fetchone()[0] >= 1

print(json.dumps({"chroma_hits": len(hits), "authorized_source": source, "postgresql": "ok", "redis": "ok"}))
