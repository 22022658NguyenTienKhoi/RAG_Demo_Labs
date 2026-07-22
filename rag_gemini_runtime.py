"""Thành phần chạy RAG Gemini dùng chung cho ba bài thực hành.

Lập chỉ mục tệp Markdown cục bộ bằng embedding Gemini và lưu vector ở dạng
JSON. API key được đọc từ `.env` của thư mục này và không bao giờ được in ra.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import unicodedata
import time
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from rag_document_processing import document_files, extract_document, normalize_vietnamese
from rag_vector_store import backend_name, query_records

# PowerShell hosts can still expose a legacy code page; Vietnamese CLI output
# must not make otherwise valid ingestion/retrieval commands fail.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
STORE_DIR = ROOT / "storage"
EMBED_MODEL = "gemini-embedding-2"
GENERATE_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")

# Một client dùng chung để tránh tạo lại kết nối không cần thiết.
_client_instance: genai.Client | None = None


def get_client() -> genai.Client:
    global _client_instance
    if _client_instance is not None:
        return _client_instance

    load_dotenv(ROOT / ".env")
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("Thiếu GEMINI_API_KEY. Hãy thêm khóa vào RAG_Demo_Labs/.env.")
    
    retry_config = types.HttpRetryOptions(
        attempts=6,
        initial_delay=2.0,
        http_status_codes=[408, 429, 500, 502, 503, 504]
    )
    
    _client_instance = genai.Client(
        api_key=key,
        http_options=types.HttpOptions(retry_options=retry_config)
    )
    return _client_instance


def markdown_files() -> list[Path]:
    """Backward-compatible name for all supported corpus files."""
    return document_files(DATA_DIR)


def clean(text: str) -> str:
    return normalize_vietnamese(text.replace("\r\n", "\n"))


def chunk_markdown(path: Path, chunk_size: int = 1400, overlap: int = 220) -> list[dict]:
    """Chia đoạn theo cấu trúc, ưu tiên ranh giới heading Markdown/Điều."""
    text = clean(path.read_text(encoding="utf-8"))
    parts = re.split(r"(?=^#{1,6}\s|^Điều\s+\d+|^Chương\s+[IVXLCDM0-9]+)", text, flags=re.MULTILINE)
    chunks, current = [], ""
    for part in (p.strip() for p in parts if p.strip()):
        if current and len(current) + len(part) + 2 > chunk_size:
            chunks.append(current)
            current = current[-overlap:] + "\n" + part
        else:
            current = (current + "\n\n" + part).strip()
    if current:
        chunks.append(current)
    # Tách các phần quá dài nhưng vẫn giữ ngữ cảnh lân cận.
    output = []
    for block in chunks:
        output.extend(block[i:i + chunk_size] for i in range(0, len(block), chunk_size - overlap))
    return [{"text": piece, "source": path.name, "chunk_id": i} for i, piece in enumerate(output)]


def chunk_document(path: Path, chunk_size: int = 1400, overlap: int = 220, strategy: str = "hierarchical") -> list[dict]:
    """Chunk all supported file types and preserve page/sheet and parent metadata."""
    if strategy not in {"fixed", "semantic", "hierarchical"}:
        raise ValueError("strategy must be fixed, semantic, or hierarchical")
    output: list[dict] = []
    for unit in extract_document(path):
        text = clean(unit["text"])
        if not text:
            continue
        # Headings/Articles define legal parents; semantic mode uses paragraphs.
        # Keep this Unicode-aware expression separate from the legacy line below
        # so Vietnamese Điều/Chương titles are recognized reliably.
        legal_boundary = r"(?=^#{1,6}\s|^Điều\s+\d+|^Chương\s+[IVXLCDM0-9]+)"
        boundary = r"(?=^#{1,6}\s|^Äiá»u\s+\d+|^ChÆ°Æ¡ng\s+[IVXLCDM0-9]+)" if strategy == "hierarchical" else r"\n\n+"
        if strategy == "hierarchical":
            boundary = legal_boundary
        parent = "Ná»™i dung chung"
        parent = "Nội dung chung"
        current = ""
        for part in (p.strip() for p in re.split(boundary, text, flags=re.MULTILINE) if p.strip()):
            if strategy == "hierarchical" and re.match(r"(?:#{1,6}\s+|Điều\s+|Chương\s+).+", part):
                parent = part.splitlines()[0][:240]
            if strategy == "hierarchical" and re.match(r"(?:#{1,6}\s+|Äiá»u\s+|ChÆ°Æ¡ng\s+).+", part):
                parent = part.splitlines()[0][:240]
            # Semantic/hierarchical boundaries are preferred, but no record may
            # exceed the configured context budget when a legal section is long.
            pieces = [part] if len(part) <= chunk_size and strategy != "fixed" else [part[i:i + chunk_size] for i in range(0, len(part), max(1, chunk_size - overlap))]
            for piece in pieces:
                if current and len(current) + len(piece) + 2 > chunk_size:
                    output.append({"text": current, "source": path.name, "page": unit["page"], "parent_id": f"{path.name}:{parent}", "parent_title": parent})
                    carry = min(overlap, max(0, chunk_size - len(piece) - 1))
                    current = (current[-carry:] + "\n" + piece).strip() if carry else piece
                else:
                    current = (current + "\n\n" + piece).strip()
        if current:
            output.append({"text": current, "source": path.name, "page": unit["page"], "parent_id": f"{path.name}:{parent}", "parent_title": parent})
    return [{**record, "chunk_id": i} for i, record in enumerate(output)]


def corpus_fingerprint(strategy: str = "hierarchical", chunk_size: int = 1400, overlap: int = 220) -> str:
    """Content-based fingerprint that is stable across host and containers."""
    digest = hashlib.sha256()
    for path in markdown_files():
        digest.update(path.name.encode("utf-8"))
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    digest.update(f"strategy={strategy}|chunk_size={chunk_size}|overlap={overlap}|chunker_v=3".encode())
    return digest.hexdigest()


def _valid_records(saved: dict) -> bool:
    expected_sources = {path.name for path in markdown_files()}
    indexed_sources = {record.get("source") for record in saved.get("records", [])}
    return indexed_sources == expected_sources and all(
        {"page", "parent_id", "parent_title", "embedding"} <= record.keys()
        for record in saved.get("records", [])
    )


def _migrate_legacy_fingerprint(saved: dict, target: Path, fingerprint: str) -> bool:
    """One-time migration from the old host-mtime fingerprint format."""
    if saved.get("fingerprint_scheme") or not _valid_records(saved):
        return False
    saved["fingerprint"] = fingerprint
    saved["fingerprint_scheme"] = "content-sha256-v1"
    target.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
    return True


def embed(client: genai.Client, texts: list[str], task_type: str) -> list[list[float]]:
    """Tạo embedding một đoạn cho mỗi yêu cầu và kiểm tra ánh xạ 1:1.

    Một số tổ hợp model/API Gemini trả về một vector cho yêu cầu dạng danh sách
    (coi danh sách là một nội dung nhiều phần). Gửi riêng từng đoạn ngăn việc
    ghi âm thầm một chỉ mục thiếu dữ liệu.
    """
    vectors = []
    for position, text in enumerate(texts, 1):
        response = client.models.embed_content(
            model=EMBED_MODEL,
            contents=text,
            config=types.EmbedContentConfig(task_type=task_type, output_dimensionality=768),
        )
        if len(response.embeddings) != 1:
            raise RuntimeError(f"Gemini trả về {len(response.embeddings)} embedding cho một đoạn; chỉ mục không được lưu.")
        vectors.append(response.embeddings[0].values)
        if position < len(texts):
            time.sleep(0.25)  # điều tiết nhẹ cho Gemini API công khai
        if len(texts) > 1 and (position % 25 == 0 or position == len(texts)):
            print(f"  Đã tạo embedding {position}/{len(texts)} đoạn")
    if len(vectors) != len(texts):
        raise RuntimeError(f"Số embedding không khớp: {len(vectors)} vector cho {len(texts)} đoạn.")
    return vectors


def build_or_load_index(name: str, force: bool = False, strategy: str = "hierarchical") -> list[dict]:
    """Xây dựng chỉ mục embedding một lần, tái sử dụng cho đến khi `.md` thay đổi hoặc có `--rebuild`."""
    STORE_DIR.mkdir(exist_ok=True)
    target = STORE_DIR / f"{name}.json"
    fingerprint = corpus_fingerprint(strategy=strategy)
    if target.exists() and not force:
        saved = json.loads(target.read_text(encoding="utf-8"))
        if _valid_records(saved) and (
            saved.get("fingerprint") == fingerprint or _migrate_legacy_fingerprint(saved, target, fingerprint)
        ):
            return saved["records"]
    chunks_by_source = {path.name: chunk_document(path, strategy=strategy) for path in markdown_files()}
    docs = [chunk for chunks in chunks_by_source.values() for chunk in chunks]
    if not docs:
        raise RuntimeError(f"Không tìm thấy tài liệu Markdown trong {DATA_DIR}")
    print("Kế hoạch chia đoạn trước khi tạo embedding Gemini:")
    for source, chunks in chunks_by_source.items():
        print(f"  - {source}: {len(chunks)} chunks")
    print(f"  Tổng cộng: {len(docs)} đoạn")
    client = get_client()
    vectors = embed(client, [d["text"] for d in docs], "RETRIEVAL_DOCUMENT")
    if len(vectors) != len(docs):
        raise RuntimeError("Từ chối lưu chỉ mục vector không đầy đủ.")
    records = [{**doc, "embedding": vector} for doc, vector in zip(docs, vectors)]
    target.write_text(json.dumps({"fingerprint": fingerprint, "fingerprint_scheme": "content-sha256-v1", "created_at": datetime.now(timezone.utc).isoformat(), "records": records}, ensure_ascii=False), encoding="utf-8")
    return records


def load_index(name: str) -> list[dict]:
    """Chỉ nạp chỉ mục hoàn tất; giai đoạn truy vấn không được chia đoạn/tạo embedding tài liệu."""
    target = STORE_DIR / f"{name}.json"
    if not target.exists():
        raise RuntimeError(f"Chỉ mục '{name}' chưa tồn tại. Hãy chạy script chia đoạn và lập chỉ mục trước.")
    saved = json.loads(target.read_text(encoding="utf-8"))
    fingerprint = corpus_fingerprint()
    if not _valid_records(saved) or not (
        saved.get("fingerprint") == fingerprint or _migrate_legacy_fingerprint(saved, target, fingerprint)
    ):
        raise RuntimeError("Tài liệu đã thay đổi hoặc chỉ mục chưa đầy đủ. Hãy chạy script lập chỉ mục với --rebuild.")
    return saved["records"]


def cosine(a: list[float], b: list[float]) -> float:
    den = math.sqrt(sum(x*x for x in a)) * math.sqrt(sum(y*y for y in b))
    return sum(x*y for x, y in zip(a, b)) / den if den else 0.0


def normalized_tokens(text: str) -> set[str]:
    """Match unaccented Vietnamese queries against accented legal documents."""
    text = text.lower().replace("đ", "d")
    text = "".join(char for char in unicodedata.normalize("NFD", text) if unicodedata.category(char) != "Mn")
    return set(re.findall(r"[a-z0-9_]+", text))


def retrieve(
    question: str,
    records: list[dict] | None = None,
    top_k: int = 5,
    backend: str | None = None,
    allowed_sources: list[str] | None = None,
) -> list[dict]:
    """Retrieve from ChromaDB/Pinecone, or explicitly use local JSON search.

    ``allowed_sources`` is forwarded to the vector database as a metadata
    filter, ensuring forbidden documents are never returned by semantic search.
    """
    # Assign client to a variable instead of passing a temporary call
    client = get_client()
    query = embed(client, [question], "RETRIEVAL_QUERY")[0]
    selected = backend_name(backend)
    if selected != "json":
        return query_records(query, top_k=top_k, backend=selected, allowed_sources=allowed_sources)
    if records is None:
        records = load_index("foundation")
    if allowed_sources is not None:
        allowed = set(allowed_sources)
        records = [record for record in records if record["source"] in allowed]
    query_terms = normalized_tokens(question)
    ranked = []
    for record in records:
        dense = cosine(query, record["embedding"])
        lexical = len(query_terms & normalized_tokens(record["text"])) / max(len(query_terms), 1)
        # Preserve semantic Gemini recall and boost exact legal names/terms.
        ranked.append({**record, "score": dense + 0.25 * lexical, "dense_score": dense, "lexical_score": lexical})
    ranked.sort(key=lambda record: record["score"], reverse=True)
    return ranked[:top_k]


def context_with_citations(hits: list[dict]) -> str:
    return "\n\n".join(
        f"[SOURCE: {h['source']} | page/sheet {h.get('page', 'N/A')} | "
        f"section {h.get('parent_title', 'N/A')} | chunk {h['chunk_id']}]\n{h['text']}"
        for h in hits
    )


def infer(question: str, hits: list[dict], extra_rules: str = "") -> str:
    prompt = f"""Bạn là trợ lý tra cứu tài liệu ngân hàng. Chỉ trả lời bằng NGỮ CẢNH.
Nếu bằng chứng không đủ, hãy nói chính xác: Không tìm thấy thông tin liên quan trong cơ sở dữ liệu hiện có.
Mỗi ý chính phải có citation [SOURCE: filename | chunk n]. Không bịa nguồn, không dùng kiến thức ngoài ngữ cảnh.
{extra_rules}

NGỮ CẢNH:
{context_with_citations(hits)}

CÂU HỎI: {question}
TRẢ LỜI:"""
    # Assign client to a variable before making the call
    client = get_client()
    response = client.models.generate_content(
        model=GENERATE_MODEL, contents=prompt,
        config=types.GenerateContentConfig(temperature=0.0, max_output_tokens=900),
    )
    return response.text
