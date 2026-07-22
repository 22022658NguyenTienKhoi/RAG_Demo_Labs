# Bộ 3 bài thực hành xây dựng hệ thống RAG

Dự án hướng dẫn xây dựng một hệ thống hỏi đáp tài liệu bằng Gemini theo ba cấp độ, từ RAG cơ bản đến chatbot doanh nghiệp có phân quyền và kiểm toán.

| Bài thực hành | Nội dung chính | Kết quả đầu ra |
|---|---|---|
| **Lab 01 — RAG Foundation** | Xử lý tài liệu, chunking, embedding, ChromaDB/Pinecone, citation | Pipeline RAG cơ bản trả lời có dẫn nguồn |
| **Lab 02 — Advanced & Graph RAG** | Hybrid Search, multi-query, RRF, reranking nhẹ, parent-child, Neo4j | Pipeline truy xuất nâng cao và mở rộng bằng đồ thị |
| **Lab 03 — Enterprise RAG** | Metadata, RBAC, audit log, PostgreSQL, Redis, FastAPI, Streamlit | Chatbot doanh nghiệp với bốn use case nghiệp vụ |

Ba lab dùng chung dữ liệu và chỉ mục. Hãy hoàn thành theo thứ tự **Lab 01 → Lab 02 → Lab 03**.

## 1. Kiến trúc học tập

```text
Tài liệu trong data/
        |
        v
Lab 01: parse -> chunk -> Gemini embedding -> ChromaDB/Pinecone
        |
        v
Lab 02: vector search + BM25 -> RRF -> rerank -> parent/graph expansion
        |
        v
Lab 03: metadata/RBAC -> FastAPI -> PostgreSQL audit + Redis cache -> Streamlit
```

Mã dùng chung nằm trong `rag_core/` để tránh sao chép giữa ba lab:

- `document_processing.py`: đọc PDF, DOCX, Excel, Markdown, TXT và ảnh OCR.
- `runtime.py`: chunking, Gemini embedding/generation, citation và JSON fallback.
- `vector_store.py`: upsert/query ChromaDB và Pinecone.
- `catalog.py`: metadata và chính sách truy cập của corpus minh họa.
- `security.py`: mã hóa nội dung nhạy cảm trước khi lưu vào vector database.

## 2. Chuẩn bị môi trường

### Yêu cầu

- Python 3.10 trở lên; khuyến nghị Python 3.11.
- Docker Desktop và Docker Compose.
- Gemini API key.
- Tùy chọn: Tesseract OCR với language pack `vie` và `eng` nếu xử lý ảnh scan.

Sao chép dự án:

```powershell
git clone https://github.com/22022658NguyenTienKhoi/RAG_Demo_Labs.git
cd RAG_Demo_Labs
```

Tất cả lệnh trong tài liệu này được chạy từ thư mục chứa `README.md` và `docker-compose.yml`.

### Tạo tệp `.env`

```env
GEMINI_API_KEY=thay-bang-api-key-cua-ban
GEMINI_MODEL=gemini-flash-lite-latest

RAG_VECTOR_BACKEND=chroma
CHROMA_URL=http://localhost:8001

NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=thay-bang-mat-khau-it-nhat-8-ky-tu

POSTGRES_PASSWORD=thay-bang-mat-khau-postgres

# Khuyến nghị khi index tài liệu confidential/restricted
RAG_ENCRYPTION_KEY=thay-bang-fernet-key
RAG_REQUIRE_ENCRYPTION=true

# Chỉ cần khi dùng Pinecone
PINECONE_API_KEY=
PINECONE_INDEX=
```

Tạo Fernet key:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Không commit, in hoặc chia sẻ `.env`. Tệp này đã được loại khỏi Git và Docker build context.

## 3. Cách chạy nhanh bằng Docker

Đây là cách đơn giản nhất để chạy hệ thống hoàn chỉnh:

```powershell
docker compose up --build
```

Khi khởi động, API sẽ:

1. Đọc và chia tài liệu nếu chưa có chỉ mục hợp lệ.
2. Tạo Gemini embedding.
3. Upsert vector vào ChromaDB.
4. Khởi tạo metadata catalog trong PostgreSQL.
5. Khởi động FastAPI và Streamlit.

| Dịch vụ | Địa chỉ |
|---|---|
| Streamlit | `http://localhost:8501` |
| FastAPI Swagger | `http://localhost:8000/docs` |
| FastAPI health | `http://localhost:8000/health` |
| ChromaDB | `http://localhost:8001` |
| Neo4j Browser | `http://localhost:7474` |

Kiểm tra trạng thái:

```powershell
docker compose ps
```

Dừng hệ thống mà không xóa dữ liệu:

```powershell
docker compose stop
```

## 4. Chạy từng lab để học theo từng bước

Nếu muốn quan sát rõ từng giai đoạn, hãy chạy thủ công theo hướng dẫn dưới đây.

### Cài dependency Python

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Nếu PowerShell chặn activate script:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### Lab 01 — RAG Foundation

Mục tiêu:

- Đọc tài liệu nhiều định dạng và chuẩn hóa tiếng Việt.
- So sánh fixed, semantic và hierarchical chunking.
- Tạo Gemini embedding một lần.
- Lưu và truy vấn vector bằng ChromaDB hoặc Pinecone.
- Sinh câu trả lời chỉ từ context và bắt buộc citation.

Khởi động ChromaDB:

```powershell
docker compose up -d chromadb
```

Xem trước số chunk mà không gọi Gemini:

```powershell
python 01_rag_foundation/01_chunk_and_index.py --dry-run
```

Tạo chỉ mục và upsert ChromaDB:

```powershell
python 01_rag_foundation/01_chunk_and_index.py --rebuild --backend chroma
```

Đặt câu hỏi:

```powershell
python 01_rag_foundation/02_retrieve_and_answer.py --backend chroma --ask "Thong tu nao quy dinh ve hoat dong cho vay?"
```

Pinecone dùng cùng giao diện:

```powershell
python 01_rag_foundation/03_sync_vector_store.py --backend pinecone --collection rag_foundation
python 01_rag_foundation/02_retrieve_and_answer.py --backend pinecone --ask "Dieu kien cho vay la gi?"
```

`--backend json` là fallback minh bạch cho mục đích học tập/offline; ChromaDB là backend local mặc định.

Xem thêm: [Hướng dẫn Lab 01](01_rag_foundation/README.md).

### Lab 02 — Advanced & Graph RAG

Điều kiện: Lab 01 đã tạo `storage/foundation.json` và vector collection.

Mục tiêu:

- Kết hợp semantic search và BM25.
- Tạo nhiều biến thể truy vấn.
- Hợp nhất ranking bằng Reciprocal Rank Fusion.
- Rerank nhẹ, không cần sentence-transformers.
- Chỉ lấy chunk lân cận cần thiết để nén context.
- Mở rộng bằng quan hệ trong Neo4j.

Khởi động Neo4j:

```powershell
docker compose up -d neo4j
```

Xây cấu trúc `Document → Section → Chunk`:

```powershell
python 02_advanced_graph_rag/01_build_neo4j_graph.py
```

Làm giàu ontology bằng rule-based NER:

```powershell
python 02_advanced_graph_rag/04_enrich_ontology.py
```

Thêm Gemini entity extraction nếu muốn minh họa LLM extraction:

```powershell
python 02_advanced_graph_rag/04_enrich_ontology.py --use-llm
```

Chạy pipeline đầy đủ:

```powershell
python 02_advanced_graph_rag/03_advanced_retrieval_pipeline.py --backend chroma --top-k 5 --ask "Dieu kien cho vay la gi?"
```

Nếu Neo4j không khả dụng, pipeline vẫn chạy Hybrid RAG và thông báo đã bỏ qua graph expansion.

Xem thêm: [Hướng dẫn Lab 02](02_advanced_graph_rag/README.md).

### Lab 03 — Enterprise RAG

Điều kiện: Lab 01 đã hoàn tất; Neo4j từ Lab 02 là tùy chọn.

Mục tiêu:

- Chuẩn hóa metadata và temporal metadata.
- Lọc quyền trước và ngay trong vector retrieval.
- Ghi audit trail vào PostgreSQL.
- Cache câu trả lời theo role bằng Redis.
- Cung cấp REST API và giao diện Streamlit.
- Thực hành bốn use case nghiệp vụ.

Tạo metadata catalog:

```powershell
python 03_metadata_enterprise_chatbot/01_build_metadata_catalog.py
```

Xem ma trận quyền:

```powershell
python 03_metadata_enterprise_chatbot/03_rbac_access_matrix.py
```

Thử RBAC bằng CLI:

```powershell
python 03_metadata_enterprise_chatbot/02_rbac_retrieve_and_answer.py --backend chroma --role internal_auditor --ask "Quy dinh ve hoat dong cho vay?"
```

Chạy API và UI thuận tiện nhất bằng:

```powershell
docker compose up -d api web postgres redis chromadb
```

Các endpoint chính:

| Endpoint | Use case |
|---|---|
| `POST /ask` | Tra cứu quy định có RBAC |
| `POST /compliance/gap-analysis` | So sánh văn bản nội bộ với quy định |
| `POST /compliance/check` | Kiểm tra một tài liệu theo yêu cầu kiểm soát |
| `POST /audit/checklist` | Sinh checklist kiểm toán theo rủi ro |

Tạo Risk Wiki có thể mở bằng Obsidian:

```powershell
python 03_metadata_enterprise_chatbot/05_build_risk_wiki.py
```

Xem thêm: [Hướng dẫn Lab 03](03_metadata_enterprise_chatbot/README.md).

## 5. Đánh giá chất lượng

So sánh ba chiến lược chunking:

```powershell
python evaluation/compare_chunking.py
```

So sánh precision/recall giữa baseline và Hybrid RAG:

```powershell
python evaluation/compare_retrieval.py --backend chroma --top-k 5
```

RAGAS được tách khỏi runtime để không làm nặng API. Cài dependency đánh giá đã pin:

```powershell
python -m pip install -r requirements-evaluation.txt
```

Kiểm tra dataset:

```powershell
python 03_metadata_enterprise_chatbot/04_evaluate.py --dataset evaluation/ragas_dataset.json
```

Chạy context precision, context recall, faithfulness và answer relevancy bằng Gemini judge:

```powershell
python 03_metadata_enterprise_chatbot/04_evaluate.py --dataset evaluation/ragas_dataset.json --run
```

## 6. Notebook

Notebook là cách tương tác thay thế cho CLI, không phải bước bắt buộc bổ sung:

1. `01_rag_foundation/01_rag_foundation.ipynb`
2. `02_advanced_graph_rag/02_advanced_graph_rag.ipynb`
3. `03_metadata_enterprise_chatbot/03_metadata_enterprise_chatbot.ipynb`

Cài JupyterLab nếu cần:

```powershell
python -m pip install jupyterlab
jupyter lab
```

## 7. Cấu trúc thư mục

```text
RAG_Demo_Labs/
|-- 01_rag_foundation/                 Lab 01: ingest, chunk, index, basic RAG
|-- 02_advanced_graph_rag/             Lab 02: Hybrid RAG và Graph RAG
|-- 03_metadata_enterprise_chatbot/    Lab 03: metadata, RBAC, API, UI, persistence
|-- rag_core/                          Thành phần dùng chung của ba lab
|-- data/                              Tài liệu đầu vào
|-- storage/                           Manifest, catalog, audit và báo cáo sinh ra
|-- evaluation/                        Dataset và script đánh giá
|-- risk_wiki/                         Obsidian-compatible risk profiles
|-- tests/                             Unit test và integration test
|-- docker-compose.yml                 Toàn bộ dịch vụ local
|-- requirements.txt                   Dependency runtime
`-- requirements-evaluation.txt        Dependency RAGAS tùy chọn
```

## 8. Bảo mật và phân quyền

- `.env` không được đưa vào Git hoặc Docker image.
- `confidential` và `restricted` có thể được mã hóa bằng Fernet trước khi lưu text vào vector database.
- RBAC source filter được gửi vào ChromaDB/Pinecone, không chỉ lọc sau retrieval.
- Audit log chỉ lưu hash câu hỏi, không lưu nội dung câu hỏi thô.
- Redis cache key bao gồm role và tập tài liệu được phép đọc.
- Đây là lab đào tạo; production vẫn cần secret manager, TLS, network policy và quản lý khóa tập trung.

## 9. Xử lý lỗi thường gặp

- **ChromaDB không kết nối:** kiểm tra `docker compose ps` và `CHROMA_URL=http://localhost:8001` khi chạy Python trên host.
- **Chỉ mục cũ:** chạy lại Lab 01 với `--rebuild`.
- **Neo4j sai mật khẩu:** mật khẩu trong `.env` phải giống mật khẩu dùng khi volume được tạo lần đầu.
- **Không giải mã được tài liệu:** dùng cùng `RAG_ENCRYPTION_KEY` khi index và query.
- **PowerShell hiển thị sai tiếng Việt:** chạy `chcp 65001` trước lệnh Python.
- **OCR thất bại:** cài Tesseract cùng language pack `vie` và `eng`.
- **Cổng bận:** FastAPI dùng `8000`, ChromaDB dùng `8001`, Streamlit dùng `8501`.

## 10. Kiểm thử

Unit test:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

Integration test cần ChromaDB, PostgreSQL và Redis đang chạy:

```powershell
docker compose run --rm --no-deps api python tests/integration_services.py
```
