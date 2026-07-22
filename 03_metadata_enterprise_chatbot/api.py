"""FastAPI enterprise RAG service with RBAC, grounding checks and audit APIs."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

HERE = Path(__file__).resolve(); ROOT = next(p for p in HERE.parents if (p / "rag_gemini_runtime.py").exists())
sys.path.insert(0, str(ROOT))
from rag_gemini_runtime import STORE_DIR, infer, load_index, retrieve

_pipeline_spec = importlib.util.spec_from_file_location("advanced_pipeline", ROOT / "02_advanced_graph_rag" / "03_advanced_retrieval_pipeline.py")
_pipeline = importlib.util.module_from_spec(_pipeline_spec)
assert _pipeline_spec and _pipeline_spec.loader
_pipeline_spec.loader.exec_module(_pipeline)

app = FastAPI(title="Enterprise RAG Lab", version="2.0")
ROLE_CLEARANCE = {"business_user": {"public"}, "credit_officer": {"public", "internal", "confidential"}, "compliance": {"public", "internal", "confidential", "restricted"}, "internal_auditor": {"public", "internal", "confidential", "restricted"}}

class Question(BaseModel):
    question: str = Field(min_length=3)
    role: str = "internal_auditor"

class GapRequest(Question):
    internal_document: str
    regulatory_document: str

class ChecklistRequest(Question):
    audit_scope: str = Field(min_length=3)

def permitted(role: str) -> list[dict]:
    if role not in ROLE_CLEARANCE:
        raise HTTPException(403, "Unknown role")
    catalog_file = STORE_DIR / "metadata_catalog.json"
    if not catalog_file.exists():
        raise HTTPException(503, "Run 01_build_metadata_catalog.py first")
    catalog = json.loads(catalog_file.read_text(encoding="utf-8")); records = load_index("foundation")
    return [{**record, "metadata": catalog[record["source"]]} for record in records if role in catalog[record["source"]]["allowed_roles"] and catalog[record["source"]]["classification"] in ROLE_CLEARANCE[role]]

def audit(event: str, role: str, question: str, hits: list[dict]) -> None:
    STORE_DIR.mkdir(exist_ok=True)
    entry = {"time": datetime.now(timezone.utc).isoformat(), "event": event, "role": role, "question_hash": hashlib.sha256(question.encode()).hexdigest(), "sources": [hit["source"] for hit in hits]}
    with (STORE_DIR / "audit_log.jsonl").open("a", encoding="utf-8") as log:
        log.write(json.dumps(entry, ensure_ascii=False) + "\n")

def hybrid_graph_retrieve(question: str, records: list[dict]) -> list[dict]:
    """Use the Lab 02 hybrid/RRF/rerank/graph path after the RBAC filter."""
    rankings = []
    for query in _pipeline.query_variants(question):
        rankings.append([(hit["score"], hit) for hit in retrieve(query, records, top_k=len(records))])
        rankings.append(_pipeline.bm25(query, records))
    reranked = _pipeline.rerank(question, _pipeline.rrf(rankings)[:20])[:5]
    return _pipeline.expand_parents(_pipeline.expand_graph(reranked, records), records)

def grounded_answer(question: str, role: str, records: list[dict], purpose: str = "policy_lookup") -> dict:
    hits = hybrid_graph_retrieve(question, records)
    answer = infer(question, hits, f"Requester role: {role}. Task: {purpose}. Mandatory citations and grounded answer only.")
    expected = {f"[SOURCE: {hit['source']}" for hit in hits}
    cited = any(marker in answer for marker in expected)
    confidence = round(sum(max(float(hit.get("score", 0)), 0) for hit in hits) / max(len(hits), 1), 3)
    return {"answer": answer, "hits": hits, "grounding_check": {"passed": cited, "required_citation_found": cited}, "confidence_score": confidence}

@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}

@app.post("/ask")
def ask(payload: Question):
    result = grounded_answer(payload.question, payload.role, permitted(payload.role))
    audit("policy_lookup", payload.role, payload.question, result["hits"])
    return {"answer": result["answer"], "citations": [{"source": h["source"], "chunk_id": h["chunk_id"], "page": h.get("page"), "section": h.get("parent_title")} for h in result["hits"]], "confidence_score": result["confidence_score"], "grounding_check": result["grounding_check"]}

@app.post("/compliance/gap-analysis")
def gap_analysis(payload: GapRequest):
    records = [r for r in permitted(payload.role) if r["source"] in {payload.internal_document, payload.regulatory_document}]
    if {payload.internal_document, payload.regulatory_document} - {r["source"] for r in records}:
        raise HTTPException(403, "One or both requested documents are unavailable to this role")
    question = f"So sánh các điểm khác biệt, nghĩa vụ và khoảng trống giữa {payload.internal_document} và {payload.regulatory_document}. {payload.question}"
    result = grounded_answer(question, payload.role, records, "compliance_gap_analysis")
    audit("compliance_gap_analysis", payload.role, question, result["hits"])
    return {"analysis": result["answer"], "citations": [{"source": h["source"], "chunk_id": h["chunk_id"]} for h in result["hits"]], "grounding_check": result["grounding_check"]}

@app.post("/audit/checklist")
def audit_checklist(payload: ChecklistRequest):
    question = f"Lập checklist kiểm toán theo rủi ro cho phạm vi: {payload.audit_scope}. Yêu cầu bổ sung: {payload.question}"
    result = grounded_answer(question, payload.role, permitted(payload.role), "risk_based_audit_checklist")
    audit("audit_checklist", payload.role, question, result["hits"])
    return {"checklist": result["answer"], "citations": [{"source": h["source"], "chunk_id": h["chunk_id"]} for h in result["hits"]], "grounding_check": result["grounding_check"]}
