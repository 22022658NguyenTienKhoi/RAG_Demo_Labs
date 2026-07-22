"""Canonical document metadata and RBAC policy for the workshop corpus."""
from __future__ import annotations

from pathlib import Path

ROLE_CLEARANCE = {
    "business_user": {"public"},
    "credit_officer": {"public", "internal", "confidential"},
    "compliance": {"public", "internal", "confidential", "restricted"},
    "internal_auditor": {"public", "internal", "confidential", "restricted"},
}

POLICIES = {
    "TT_02_2023_NHNN.md": {"document_type": "NHNN_circular", "title": "Cơ cấu lại thời hạn trả nợ", "owner_department": "Compliance", "classification": "public", "effective_date": "2023-04-24", "allowed_roles": list(ROLE_CLEARANCE)},
    "TT_06_2023_NHNN.md": {"document_type": "NHNN_circular", "title": "Sửa đổi quy định cho vay", "owner_department": "Credit", "classification": "internal", "effective_date": "2023-06-28", "allowed_roles": ["credit_officer", "compliance", "internal_auditor"]},
    "TT_39_2016_NHNN.md": {"document_type": "NHNN_circular", "title": "Hoạt động cho vay", "owner_department": "Credit", "classification": "confidential", "effective_date": "2017-03-15", "allowed_roles": ["credit_officer", "compliance", "internal_auditor"]},
    "chinh_sach_tin_dung.md": {"document_type": "internal_credit_policy", "title": "Chính sách tín dụng nội bộ", "owner_department": "Credit Risk", "classification": "restricted", "effective_date": None, "allowed_roles": ["compliance", "internal_auditor"]},
}


def document_metadata(source: str) -> dict:
    if source not in POLICIES:
        raise KeyError(f"No reviewed metadata policy exists for {source}")
    policy = POLICIES[source]
    effective = policy["effective_date"]
    return {
        "document_id": Path(source).stem,
        "source": source,
        "version": "source-current",
        "retention_years": 10,
        "status": "effective",
        "valid_from": effective,
        "valid_to": None,
        "replaces": [],
        "replaced_by": [],
        **policy,
        "confidentiality": policy["classification"],
    }


def is_permitted(role: str, metadata: dict) -> bool:
    return (
        role in ROLE_CLEARANCE
        and role in metadata.get("allowed_roles", [])
        and metadata.get("classification") in ROLE_CLEARANCE[role]
    )
