"""Bài thực hành 03, Giai đoạn 1 — tạo danh mục metadata từ chỉ mục Bài 01.

Điều kiện trước: storage/foundation.json của Bài 01. Bài này không chia đoạn
hoặc tạo embedding Gemini cho tài liệu.
"""
import sys
from pathlib import Path

HERE = Path(globals().get("__file__", Path.cwd())).resolve()
PROJECT_ROOT = next(p for p in (HERE.parent, *HERE.parents, Path.cwd(), Path.cwd() / "RAG_Demo_Labs") if (p / "rag_gemini_runtime.py").exists())
sys.path.insert(0, str(PROJECT_ROOT))

from rag_gemini_runtime import STORE_DIR, load_index
from document_catalog import document_metadata
from rag_enterprise_store import save_catalog


records = load_index("foundation")  # Chỉ mục Bài 01; không chia đoạn/tạo embedding lại.
catalog = {source: document_metadata(source) for source in sorted({r["source"] for r in records})}
STORE_DIR.mkdir(exist_ok=True)
backend = save_catalog(catalog, STORE_DIR / "metadata_catalog.json")
print(f"Đã tạo danh mục metadata cho {len(catalog)} tài liệu từ {len(records)} đoạn; lưu tại {backend}.")
