from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from rag_core import vector_store
from rag_core.catalog import document_metadata, is_permitted
from rag_core.security import protect_text, reveal_text


class FakeCollection:
    def __init__(self):
        self.where = None

    def count(self):
        return 2

    def query(self, **kwargs):
        self.where = kwargs["where"]
        return {
            "documents": [["authorized text"]],
            "metadatas": [[{"source": "allowed.md", "chunk_id": 1}]],
            "distances": [[0.2]],
        }


class VectorStoreTests(unittest.TestCase):
    def test_chroma_query_applies_source_filter(self):
        collection = FakeCollection()
        with patch.object(vector_store, "_chroma_collection", return_value=collection):
            hits = vector_store.query_records([0.1, 0.2], backend="chroma", allowed_sources=["allowed.md"])
        self.assertEqual(collection.where, {"source": {"$in": ["allowed.md"]}})
        self.assertEqual(hits[0]["source"], "allowed.md")
        self.assertAlmostEqual(hits[0]["score"], 0.8)

    def test_empty_authorization_does_not_query_backend(self):
        with patch.object(vector_store, "_chroma_collection") as collection:
            self.assertEqual(vector_store.query_records([0.1], backend="chroma", allowed_sources=[]), [])
        collection.assert_not_called()


class SecurityTests(unittest.TestCase):
    def test_sensitive_text_round_trip(self):
        from cryptography.fernet import Fernet

        key = Fernet.generate_key().decode("ascii")
        with patch.dict(os.environ, {"RAG_ENCRYPTION_KEY": key}):
            document, metadata = protect_text("TT_39_2016_NHNN.md", "secret policy")
            self.assertNotIn("secret policy", document)
            self.assertTrue(metadata["encrypted"])
            self.assertEqual(reveal_text(document, metadata), "secret policy")


class RbacTests(unittest.TestCase):
    def test_business_user_cannot_read_confidential_document(self):
        metadata = document_metadata("TT_39_2016_NHNN.md")
        self.assertFalse(is_permitted("business_user", metadata))
        self.assertTrue(is_permitted("internal_auditor", metadata))


class ContextCompressionTests(unittest.TestCase):
    def test_parent_expansion_is_adjacent_and_capped(self):
        import importlib.util
        from pathlib import Path

        spec = importlib.util.spec_from_file_location("advanced", Path("02_advanced_graph_rag/03_advanced_retrieval_pipeline.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        records = [{"source": "a.md", "chunk_id": index, "parent_id": "p", "text": str(index)} for index in range(20)]
        expanded = module.expand_parents([records[10]], records, max_context=4)
        self.assertEqual({item["chunk_id"] for item in expanded}, {9, 10, 11})
        self.assertLessEqual(len(expanded), 4)


if __name__ == "__main__":
    unittest.main()
