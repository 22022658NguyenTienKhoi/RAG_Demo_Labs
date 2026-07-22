"""PostgreSQL persistence and Redis caching with local workshop fallbacks."""
from __future__ import annotations

import json
import os
from pathlib import Path


def database_url() -> str | None:
    return os.getenv("DATABASE_URL")


def redis_url() -> str | None:
    return os.getenv("REDIS_URL")


def initialize_database() -> bool:
    url = database_url()
    if not url:
        return False
    import psycopg

    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_catalog (
                source TEXT PRIMARY KEY,
                metadata JSONB NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                id BIGSERIAL PRIMARY KEY,
                occurred_at TIMESTAMPTZ NOT NULL,
                event_type TEXT NOT NULL,
                role_name TEXT NOT NULL,
                question_hash TEXT NOT NULL,
                sources JSONB NOT NULL,
                outcome JSONB NOT NULL DEFAULT '{}'::jsonb
            )
        """)
    return True


def save_catalog(catalog: dict[str, dict], fallback_path: Path) -> str:
    fallback_path.parent.mkdir(exist_ok=True)
    fallback_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    if not initialize_database():
        return "json"
    import psycopg
    from psycopg.types.json import Jsonb

    with psycopg.connect(database_url()) as connection, connection.cursor() as cursor:
        for source, metadata in catalog.items():
            cursor.execute(
                """INSERT INTO document_catalog(source, metadata) VALUES (%s, %s)
                   ON CONFLICT(source) DO UPDATE SET metadata=EXCLUDED.metadata, updated_at=NOW()""",
                (source, Jsonb(metadata)),
            )
    return "postgresql"


def load_catalog(fallback_path: Path) -> dict[str, dict]:
    if database_url():
        initialize_database()
        import psycopg

        with psycopg.connect(database_url()) as connection, connection.cursor() as cursor:
            cursor.execute("SELECT source, metadata FROM document_catalog ORDER BY source")
            rows = cursor.fetchall()
        if rows:
            return {source: metadata for source, metadata in rows}
    if not fallback_path.exists():
        raise RuntimeError("Metadata catalog is missing; run 01_build_metadata_catalog.py")
    return json.loads(fallback_path.read_text(encoding="utf-8"))


def append_audit(entry: dict, fallback_path: Path) -> str:
    """Persist a privacy-preserving event; raw questions are never stored."""
    if database_url():
        initialize_database()
        import psycopg
        from psycopg.types.json import Jsonb

        with psycopg.connect(database_url()) as connection, connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO audit_events
                   (occurred_at, event_type, role_name, question_hash, sources, outcome)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (entry["time"], entry["event"], entry["role"], entry["question_hash"],
                 Jsonb(entry.get("sources", [])), Jsonb(entry.get("outcome", {}))),
            )
        return "postgresql"
    fallback_path.parent.mkdir(exist_ok=True)
    with fallback_path.open("a", encoding="utf-8") as log:
        log.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return "jsonl"


def cache_get(key: str) -> dict | None:
    if not redis_url():
        return None
    import redis

    value = redis.from_url(redis_url(), decode_responses=True).get(key)
    return json.loads(value) if value else None


def cache_set(key: str, value: dict, ttl_seconds: int = 300) -> None:
    if not redis_url():
        return
    import redis

    redis.from_url(redis_url(), decode_responses=True).setex(key, ttl_seconds, json.dumps(value, ensure_ascii=False))


def service_health() -> dict[str, str]:
    status = {"postgresql": "not_configured", "redis": "not_configured"}
    if database_url():
        try:
            initialize_database()
            status["postgresql"] = "ok"
        except Exception as error:
            status["postgresql"] = f"error: {error}"
    if redis_url():
        try:
            import redis
            redis.from_url(redis_url()).ping()
            status["redis"] = "ok"
        except Exception as error:
            status["redis"] = f"error: {error}"
    return status
