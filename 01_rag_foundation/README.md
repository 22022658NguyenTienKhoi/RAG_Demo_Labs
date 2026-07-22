# Lab 01 — RAG Foundation

Lab này xây dựng pipeline RAG tối thiểu nhưng hoàn chỉnh: **tài liệu → chunk → embedding → vector search → câu trả lời có citation**.

## Mục tiêu

- Đọc Markdown, TXT, PDF, DOCX, XLS/XLSX và ảnh OCR.
- Giữ metadata nguồn, trang/sheet, section cha và chunk ID.
- Thực hành fixed, semantic và hierarchical chunking.
- Lưu và truy vấn embedding bằng ChromaDB hoặc Pinecone.
- Chỉ trả lời bằng bằng chứng đã truy xuất.

## Thứ tự chạy

Chạy từ thư mục gốc dự án:

```powershell
docker compose up -d chromadb
python 01_rag_foundation/01_chunk_and_index.py --dry-run
python 01_rag_foundation/01_chunk_and_index.py --rebuild --backend chroma
python 01_rag_foundation/02_retrieve_and_answer.py --backend chroma --ask "Thong tu nao quy dinh ve hoat dong cho vay?"
```

## Các script

| Tệp | Vai trò |
|---|---|
| `01_chunk_and_index.py` | Chia tài liệu, tạo Gemini embedding và upsert vector database |
| `02_retrieve_and_answer.py` | Query vector, dựng context và sinh câu trả lời có citation |
| `03_sync_vector_store.py` | Đồng bộ manifest hiện có sang ChromaDB hoặc Pinecone |
| `01_rag_foundation.ipynb` | Phiên bản notebook tương tác |

## Đầu ra

- `storage/foundation.json`: manifest/fallback chứa chunk, metadata và embedding.
- ChromaDB collection `rag_foundation`, hoặc namespace tương ứng trên Pinecone.

Lab 02 và Lab 03 tái sử dụng đầu ra này; không tạo embedding tài liệu lại.
