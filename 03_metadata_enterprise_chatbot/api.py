"""Enterprise RAG API: vector search, RBAC, PostgreSQL audit and Redis cache."""
from __future__ import annotations

import hashlib
import importlib.util
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

HERE = Path(__file__).resolve()
ROOT = next(path for path in HERE.parents if (path / "rag_gemini_runtime.py").exists())
sys.path.insert(0, str(ROOT))

from document_catalog import ROLE_CLEARANCE, is_permitted
from rag_enterprise_store import append_audit, cache_get, cache_set, load_catalog, service_health
from rag_gemini_runtime import STORE_DIR, infer, load_index

_pipeline_spec = importlib.util.spec_from_file_location(
    "advanced_pipeline", ROOT / "02_advanced_graph_rag" / "03_advanced_retrieval_pipeline.py"
)
_pipeline = importlib.util.module_from_spec(_pipeline_spec)
assert _pipeline_spec and _pipeline_spec.loader
_pipeline_spec.loader.exec_module(_pipeline)

app = FastAPI(title="Enterprise RAG Lab", version="3.0")


class Question(BaseModel):
    question: str = Field(min_length=3)
    role: str = "internal_auditor"


class GapRequest(Question):
    internal_document: str
    regulatory_document: str


class ComplianceRequest(Question):
    document: str
    requirement: str = Field(min_length=3)


class ChecklistRequest(Question):
    audit_scope: str = Field(min_length=3)


def permitted(role: str) -> list[dict]:
    if role not in ROLE_CLEARANCE:
        raise HTTPException(403, "Unknown role")
    try:
        catalog = load_catalog(STORE_DIR / "metadata_catalog.json")
        records = load_index("foundation")
    except RuntimeError as error:
        raise HTTPException(503, str(error)) from error
    return [
        {**record, "metadata": catalog[record["source"]]}
        for record in records
        if record["source"] in catalog and is_permitted(role, catalog[record["source"]])
    ]


def audit(event: str, role: str, question: str, hits: list[dict], outcome: dict | None = None) -> None:
    entry = {
        "time": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "role": role,
        "question_hash": hashlib.sha256(question.encode("utf-8")).hexdigest(),
        "sources": sorted({hit["source"] for hit in hits}),
        "outcome": outcome or {},
    }
    append_audit(entry, STORE_DIR / "audit_log.jsonl")


def hybrid_graph_retrieve(question: str, records: list[dict]) -> list[dict]:
    """Apply RBAC in the vector query, then hybrid/rerank/graph expansion."""
    allowed_sources = sorted({record["source"] for record in records})
    reranked = _pipeline.hybrid_retrieve(
        question,
        records,
        top_k=5,
        backend=os.getenv("RAG_VECTOR_BACKEND", "chroma"),
        allowed_sources=allowed_sources,
    )
    return _pipeline.expand_parents(_pipeline.expand_graph(reranked, records), records)


def grounded_answer(question: str, role: str, records: list[dict], purpose: str = "policy_lookup") -> dict:
    sources = sorted({record["source"] for record in records})
    cache_material = "|".join([purpose, role, question, *sources, os.getenv("RAG_VECTOR_BACKEND", "chroma")])
    cache_key = "rag:answer:" + hashlib.sha256(cache_material.encode("utf-8")).hexdigest()
    try:
        cached = cache_get(cache_key)
    except Exception:
        cached = None
    if cached is not None:
        cached["cache_hit"] = True
        return cached

    hits = hybrid_graph_retrieve(question, records)
    answer = infer(question, hits, f"Requester role: {role}. Task: {purpose}. Mandatory citations and grounded answer only.")
    expected = {f"[SOURCE: {hit['source']}" for hit in hits}
    cited = any(marker in answer for marker in expected)
    dense_scores = [max(float(hit.get("dense_score", 0)), 0) for hit in hits]
    confidence = round(sum(dense_scores) / max(len(dense_scores), 1), 3)
    safe_hits = [{key: value for key, value in hit.items() if key != "embedding"} for hit in hits]
    result = {
        "answer": answer,
        "hits": safe_hits,
        "grounding_check": {"passed": cited, "required_citation_found": cited},
        "confidence_score": confidence,
        "cache_hit": False,
    }
    try:
        cache_set(cache_key, result)
    except Exception:
        pass
    return result


def citations(hits: list[dict]) -> list[dict]:
    return [
        {"source": hit["source"], "chunk_id": hit["chunk_id"], "page": hit.get("page"), "section": hit.get("parent_title")}
        for hit in hits
    ]


@app.get("/health")
def health():
    return {
        "status": "ok",
        "time": datetime.now(timezone.utc).isoformat(),
        "vector_backend": os.getenv("RAG_VECTOR_BACKEND", "chroma"),
        "services": service_health(),
    }


@app.post("/ask")
def ask(payload: Question):
    result = grounded_answer(payload.question, payload.role, permitted(payload.role))
    audit("policy_lookup", payload.role, payload.question, result["hits"], result["grounding_check"])
    return {"answer": result["answer"], "citations": citations(result["hits"]), "confidence_score": result["confidence_score"], "grounding_check": result["grounding_check"], "cache_hit": result["cache_hit"]}


@app.post("/compliance/gap-analysis")
def gap_analysis(payload: GapRequest):
    records = [record for record in permitted(payload.role) if record["source"] in {payload.internal_document, payload.regulatory_document}]
    if {payload.internal_document, payload.regulatory_document} - {record["source"] for record in records}:
        raise HTTPException(403, "One or both requested documents are unavailable to this role")
    question = f"So sánh nghĩa vụ và khoảng trống giữa {payload.internal_document} và {payload.regulatory_document}. {payload.question}"
    result = grounded_answer(question, payload.role, records, "compliance_gap_analysis")
    audit("compliance_gap_analysis", payload.role, question, result["hits"], result["grounding_check"])
    return {"analysis": result["answer"], "citations": citations(result["hits"]), "grounding_check": result["grounding_check"], "cache_hit": result["cache_hit"]}


@app.post("/compliance/check")
def compliance_check(payload: ComplianceRequest):
    records = [record for record in permitted(payload.role) if record["source"] == payload.document]
    if not records:
        raise HTTPException(403, "The requested document is unavailable to this role")
    question = f"Đánh giá tài liệu {payload.document} đối với yêu cầu sau: {payload.requirement}. {payload.question}. Kết luận COMPLIANT, PARTIAL hoặc NON_COMPLIANT và nêu bằng chứng."
    result = grounded_answer(question, payload.role, records, "compliance_checker")
    audit("compliance_checker", payload.role, question, result["hits"], result["grounding_check"])
    return {"assessment": result["answer"], "citations": citations(result["hits"]), "grounding_check": result["grounding_check"], "cache_hit": result["cache_hit"]}


@app.post("/audit/checklist")
def audit_checklist(payload: ChecklistRequest):
    question = f"Lập checklist kiểm toán theo rủi ro cho phạm vi: {payload.audit_scope}. Yêu cầu bổ sung: {payload.question}"
    result = grounded_answer(question, payload.role, permitted(payload.role), "risk_based_audit_checklist")
    audit("audit_checklist", payload.role, question, result["hits"], result["grounding_check"])
    return {"checklist": result["answer"], "citations": citations(result["hits"]), "grounding_check": result["grounding_check"], "cache_hit": result["cache_hit"]}
