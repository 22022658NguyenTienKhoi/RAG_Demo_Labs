"""Bài thực hành 03, Giai đoạn 1 — tạo danh mục metadata từ chỉ mục Bài 01.

Điều kiện trước: storage/foundation.json của Bài 01. Bài này không chia đoạn
hoặc tạo embedding Gemini cho tài liệu.
"""
import json
import sys
from pathlib import Path

HERE = Path(globals().get("__file__", Path.cwd())).resolve()
PROJECT_ROOT = next(p for p in (HERE.parent, *HERE.parents, Path.cwd(), Path.cwd() / "RAG_Demo_Labs") if (p / "rag_gemini_runtime.py").exists())
sys.path.insert(0, str(PROJECT_ROOT))

from rag_gemini_runtime import STORE_DIR, load_index


def document_metadata(source: str) -> dict:
    shared = {"document_id": Path(source).stem, "source": source, "version": "source-current", "retention_years": 10, "status": "effective", "valid_from": None, "valid_to": None, "replaces": [], "replaced_by": []}
    # Chính sách truy cập được thiết kế đa dạng để minh họa RBAC.
    # Khi vận hành thực tế, các giá trị này đến từ DMS/hệ thống quản lý hồ sơ.
    policy = {
        "TT_02_2023_NHNN.md": {"document_type":"NHNN_circular", "title":"Cơ cấu lại thời hạn trả nợ", "owner_department":"Compliance", "classification":"public", "effective_date":"2023-04-24", "allowed_roles":["business_user","credit_officer","compliance","internal_auditor"]},
        "TT_06_2023_NHNN.md": {"document_type":"NHNN_circular", "title":"Sửa đổi quy định cho vay", "owner_department":"Credit", "classification":"internal", "effective_date":"2023-06-28", "allowed_roles":["credit_officer","compliance","internal_auditor"]},
        "TT_39_2016_NHNN.md": {"document_type":"NHNN_circular", "title":"Hoạt động cho vay", "owner_department":"Credit", "classification":"confidential", "effective_date":"2017-03-15", "allowed_roles":["credit_officer","compliance","internal_auditor"]},
        "chinh_sach_tin_dung.md": {"document_type":"internal_credit_policy", "title":"Chính sách tín dụng nội bộ", "owner_department":"Credit Risk", "classification":"restricted", "effective_date":"see_source_document", "allowed_roles":["compliance","internal_auditor"]},
    }
    metadata = {**shared, **policy[source]}
    # Keep the canonical field requested by the training specification while
    # retaining `classification` for the RBAC implementation.
    metadata["confidentiality"] = metadata["classification"]
    metadata["valid_from"] = metadata["effective_date"] if metadata["effective_date"] != "see_source_document" else None
    return metadata


records = load_index("foundation")  # Chỉ mục Bài 01; không chia đoạn/tạo embedding lại.
catalog = {source: document_metadata(source) for source in sorted({r["source"] for r in records})}
STORE_DIR.mkdir(exist_ok=True)
(STORE_DIR / "metadata_catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Đã tạo danh mục metadata cho {len(catalog)} tài liệu từ {len(records)} đoạn của Bài 01.")
