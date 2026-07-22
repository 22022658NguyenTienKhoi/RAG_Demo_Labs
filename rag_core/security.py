"""Application-level protection for sensitive vector-store document text."""
from __future__ import annotations

import os

from rag_core.catalog import POLICIES

SENSITIVE = {"confidential", "restricted"}


def classification(source: str) -> str:
    return POLICIES.get(source, {}).get("classification", "internal")


def protect_text(source: str, text: str) -> tuple[str, dict[str, str | bool]]:
    level = classification(source)
    key = os.getenv("RAG_ENCRYPTION_KEY")
    if level not in SENSITIVE:
        return text, {"classification": level, "encrypted": False}
    if not key:
        if os.getenv("RAG_REQUIRE_ENCRYPTION", "false").lower() == "true":
            raise RuntimeError("RAG_ENCRYPTION_KEY is required for confidential/restricted documents")
        return text, {"classification": level, "encrypted": False}
    from cryptography.fernet import Fernet

    token = Fernet(key.encode("ascii")).encrypt(text.encode("utf-8")).decode("ascii")
    return "[encrypted document text]", {"classification": level, "encrypted": True, "encrypted_text": token}


def reveal_text(document: str, metadata: dict) -> str:
    if not metadata.get("encrypted"):
        return document
    key = os.getenv("RAG_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("RAG_ENCRYPTION_KEY is required to read an authorized sensitive result")
    from cryptography.fernet import Fernet

    return Fernet(key.encode("ascii")).decrypt(metadata["encrypted_text"].encode("ascii")).decode("utf-8")
