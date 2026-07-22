# Bộ bài thực hành RAG

Dự án gồm ba bài thực hành xây dựng hệ thống hỏi đáp tài liệu bằng Gemini:

1. **RAG Foundation** — đọc tài liệu, tạo embedding và trả lời câu hỏi.
2. **Advanced/Graph RAG** — bổ sung multi-query, BM25, Reciprocal Rank Fusion, reranking, mở rộng ngữ cảnh cha và Neo4j.
3. **Enterprise RAG** — bổ sung metadata, phân quyền RBAC, nhật ký kiểm toán, FastAPI và giao diện Streamlit.

Bài 01 tạo `storage/foundation.json`. Bài 02 và Bài 03 dùng lại chỉ mục này, vì vậy luôn hoàn thành Bài 01 trước.

## 1. Cài đặt toàn bộ môi trường

Sao chép mã nguồn và chuyển vào thư mục gốc của dự án:

```powershell
git clone https://github.com/22022658NguyenTienKhoi/RAG_Demo_Labs.git
cd RAG_Demo_Labs
```

Nếu đã tải dự án, hãy mở PowerShell ngay tại thư mục `RAG_Demo_Labs` (thư mục chứa `README.md` và `requirements.txt`). Tất cả lệnh bên dưới đều được chạy từ thư mục này.

### Yêu cầu hệ thống

- Python 3.10 trở lên; khuyến nghị Python 3.11 vì Docker image cũng dùng phiên bản này.
- Docker Desktop có Docker Compose để chạy Neo4j, ChromaDB, PostgreSQL và Redis.
- Một Gemini API key.
- Tùy chọn: Tesseract OCR cùng bộ ngôn ngữ tiếng Việt và tiếng Anh, chỉ cần khi đọc ảnh scan.

Kiểm tra các công cụ chính:

```powershell
python --version
docker --version
docker compose version
```

### Cài các gói Python

Tạo môi trường ảo và cài dependency của dự án:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

`requirements.txt` chỉ chứa dependency chạy ứng dụng: Gemini, xử lý tài liệu, Neo4j, ChromaDB, Pinecone, FastAPI, Streamlit, PostgreSQL và Redis. Không cài sentence-transformers hoặc model reranker riêng.

Để chạy notebook, cài thêm JupyterLab:

```powershell
python -m pip install jupyterlab
```

Nếu PowerShell chặn việc kích hoạt môi trường ảo, thay đổi policy cho tiến trình hiện tại rồi thử lại:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Bạn cũng có thể không kích hoạt môi trường ảo và dùng `.\.venv\Scripts\python.exe` thay cho `python` trong các lệnh phía dưới.

### Cấu hình biến môi trường

Tạo tệp `.env` tại thư mục gốc:

```env
GEMINI_API_KEY=thay-bang-gemini-api-key-cua-ban

NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=thay-bang-mat-khau-it-nhat-8-ky-tu

POSTGRES_PASSWORD=thay-bang-mat-khau-postgres
RAG_VECTOR_BACKEND=chroma
CHROMA_URL=http://localhost:8001

# Khuyến nghị cho tài liệu confidential/restricted; tạo khóa bằng lệnh bên dưới
RAG_ENCRYPTION_KEY=thay-bang-fernet-key
RAG_REQUIRE_ENCRYPTION=true

# Chỉ cần khi chọn RAG_VECTOR_BACKEND=pinecone
PINECONE_API_KEY=thay-bang-pinecone-api-key-cua-ban
PINECONE_INDEX=ten-index-768-chieu-da-ton-tai
```

Tạo Fernet key bằng `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. `GEMINI_API_KEY` là bắt buộc khi tạo chỉ mục và hỏi đáp. Không commit hoặc chia sẻ tệp `.env`.

### Cài và chạy cơ sở dữ liệu

Tải tất cả Docker image cơ sở dữ liệu đã khai báo trong dự án:

```powershell
docker compose pull neo4j chromadb postgres redis
```

Khởi động các dịch vụ dữ liệu:

```powershell
docker compose up -d chromadb neo4j postgres redis
```

| Dịch vụ | Địa chỉ | Mã nguồn hiện tại sử dụng |
|---|---|---|
| Neo4j Browser | `http://localhost:7474` | Có, Bài 02 |
| Neo4j Bolt | `bolt://localhost:7687` | Có, Bài 02 |
| ChromaDB | `http://localhost:8001` | Lưu và truy vấn semantic vector |
| PostgreSQL | Chỉ trong mạng Docker | Metadata catalog và audit trail |
| Redis | Chỉ trong mạng Docker | Cache câu trả lời theo role |
| Pinecone | Dịch vụ cloud | Backend thay thế ChromaDB |

Kiểm tra hoặc dừng các dịch vụ:

```powershell
docker compose ps
docker compose stop neo4j chromadb postgres redis
```

## 2. Chạy Bài 01 — RAG Foundation

Bài 01 đọc tài liệu trong `data/`. Các định dạng được hỗ trợ gồm Markdown, TXT, PDF, DOCX, XLS/XLSX và ảnh. JSON lưu manifest/fallback; ChromaDB là backend local mặc định để lưu và truy vấn vector.

### Bước 1: xem trước cách chia đoạn

Lệnh này không gọi Gemini và không ghi chỉ mục:

```powershell
python 01_rag_foundation/01_chunk_and_index.py --dry-run
```

### Bước 2: tạo chỉ mục dùng chung

```powershell
python 01_rag_foundation/01_chunk_and_index.py --rebuild --backend chroma
```

Quá trình lập chỉ mục gọi Gemini Embedding API nên có thể mất thời gian. Chạy lại với `--rebuild` khi tài liệu hoặc cấu hình chunking thay đổi. Nếu không có `--rebuild`, chương trình sẽ dùng lại chỉ mục hợp lệ và chưa thay đổi.

### Bước 3: đặt câu hỏi

```powershell
python 01_rag_foundation/02_retrieve_and_answer.py --backend chroma --ask "Thong tu nao quy dinh ve hoat dong cho vay?"
```

Chương trình gửi query embedding đến ChromaDB, lấy các đoạn gần nhất rồi yêu cầu Gemini trả lời kèm tên nguồn, trang/sheet, section và mã chunk.

### Chọn vector database

Lệnh lập chỉ mục đã đồng bộ ChromaDB. Có thể đồng bộ lại hoặc chuyển sang Pinecone bằng cùng một collection contract:

ChromaDB:

```powershell
docker compose up -d chromadb
python 01_rag_foundation/03_sync_vector_store.py --backend chroma --collection rag_foundation
```

Pinecone — index được đặt trong `PINECONE_INDEX` phải được tạo sẵn với số chiều bằng `768`:

```powershell
python 01_rag_foundation/03_sync_vector_store.py --backend pinecone --collection rag_foundation
```

## 3. Chạy Bài 02 — Advanced và Graph RAG

Điều kiện trước khi chạy:

- Bài 01 đã tạo `storage/foundation.json`.
- Neo4j đang chạy.
- Các biến `NEO4J_*` đã được cấu hình trong `.env`.

Khởi động Neo4j:

```powershell
docker compose up -d neo4j
```

### Bước 1: xây dựng đồ thị tài liệu

```powershell
python 02_advanced_graph_rag/01_build_neo4j_graph.py
```

Script chỉ tạo lại các node có label `RagLab`, sau đó xây quan hệ `Document -> Section -> Chunk`. Script không tạo lại embedding.

### Bước 2: làm giàu ontology

```powershell
python 02_advanced_graph_rag/04_enrich_ontology.py
```

Script bổ sung Regulation, LegalProvision, Process, Unit, Role và Risk bằng rule-based NER. Thêm `--use-llm` để chạy cả Gemini extraction; các quan hệ gồm `REFERENCES`, `APPLIES_TO`, `REPLACED_BY` và `MENTIONS`.

### Bước 3: chạy demo Hybrid/Graph RAG ngắn

```powershell
python 02_advanced_graph_rag/02_hybrid_graph_query.py --ask "Thong tu nao quy dinh ve hoat dong cho vay?"
```

### Bước 4: chạy pipeline truy xuất đầy đủ

```powershell
python 02_advanced_graph_rag/03_advanced_retrieval_pipeline.py --ask "Dieu kien cho vay la gi?" --top-k 5
```

Pipeline đầy đủ thực hiện multi-query, Gemini dense retrieval, BM25, Reciprocal Rank Fusion, lexical reranking nhẹ, mở rộng bằng Neo4j và mở rộng ngữ cảnh parent-child. Nếu Neo4j không khả dụng, script vẫn tiếp tục bằng Hybrid RAG và thông báo đã bỏ qua graph expansion.

## 4. Chạy Bài 03 — Metadata và Enterprise Chatbot

Điều kiện bắt buộc: Bài 01 đã tạo `storage/foundation.json`. Neo4j là tùy chọn; nếu đã chạy và được nạp dữ liệu ở Bài 02, API có thể mở rộng bằng chứng qua đồ thị.

### Bước 1: tạo metadata catalog

```powershell
python 03_metadata_enterprise_chatbot/01_build_metadata_catalog.py
```

Kết quả là `storage/metadata_catalog.json`, gồm loại tài liệu, đơn vị sở hữu, mức phân loại, ngày hiệu lực, thời hạn lưu trữ và danh sách role được phép truy cập.

### Bước 2: xem ma trận RBAC

```powershell
python 03_metadata_enterprise_chatbot/03_rbac_access_matrix.py
```

Bốn role minh họa gồm `business_user`, `credit_officer`, `compliance` và `internal_auditor`.

### Bước 3: truy vấn bằng CLI có RBAC

```powershell
python 03_metadata_enterprise_chatbot/02_rbac_retrieve_and_answer.py --role internal_auditor --ask "Quy dinh ve hoat dong cho vay?"
```

Tài liệu bị từ chối được đưa vào metadata filter ngay trong truy vấn ChromaDB/Pinecone. Khi có `DATABASE_URL`, audit event được ghi vào PostgreSQL; fallback CLI dùng JSONL và chỉ lưu hash câu hỏi.

### Bước 4: chạy REST API

Để chạy đầy đủ ChromaDB, PostgreSQL, Redis, FastAPI và Streamlit bằng Docker:

```powershell
docker compose up --build
```

API tự đồng bộ ChromaDB và metadata khi khởi động. FastAPI dùng `8000`, ChromaDB dùng `8001`, Streamlit dùng `8501`.

Mở `http://localhost:8000/docs` để thử API bằng Swagger UI.

| Method và endpoint | Chức năng |
|---|---|
| `GET /health` | Kiểm tra trạng thái dịch vụ |
| `POST /ask` | Hỏi đáp chính sách có RBAC |
| `POST /compliance/gap-analysis` | So sánh tài liệu nội bộ và văn bản quy định mà role được phép đọc |
| `POST /compliance/check` | Đánh giá một tài liệu theo yêu cầu kiểm soát |
| `POST /audit/checklist` | Tạo checklist kiểm toán theo rủi ro dựa trên nguồn truy xuất |

### Bước 5: chạy giao diện Streamlit

Giữ API hoạt động. Mở PowerShell thứ hai tại thư mục gốc của dự án, kích hoạt môi trường ảo, cấu hình địa chỉ API local rồi chạy Streamlit:

```powershell
.\.venv\Scripts\Activate.ps1
$env:RAG_API_URL = "http://localhost:8000"
streamlit run 03_metadata_enterprise_chatbot/app.py
```

### Bước 6: tạo Risk Wiki cho Obsidian

```powershell
python 03_metadata_enterprise_chatbot/05_build_risk_wiki.py
```

Mở thư mục `risk_wiki/` như một Obsidian vault để duyệt hồ sơ rủi ro và liên kết văn bản.

### Bước 7: so sánh và đánh giá

RAGAS dùng môi trường đánh giá được pin riêng để không làm nặng hoặc gây xung đột dependency cho API:

```powershell
python -m pip install -r requirements-evaluation.txt
```

Dataset phải là một mảng JSON không rỗng. Mỗi phần tử cần có `question`, `answer`, `contexts` và `ground_truth`:

```json
[
  {
    "question": "Thông tư nào quy định hoạt động cho vay?",
    "answer": "Thông tư 39/2016/TT-NHNN.",
    "contexts": ["Nội dung nguồn đã truy xuất..."],
    "ground_truth": "Thông tư 39/2016/TT-NHNN"
  }
]
```

Chỉ kiểm tra cấu trúc dataset, không gọi model đánh giá:

```powershell
python evaluation/compare_chunking.py
python evaluation/compare_retrieval.py --backend chroma --top-k 5
python 03_metadata_enterprise_chatbot/04_evaluate.py --dataset evaluation/ragas_dataset.json
```

Chạy context precision/recall, faithfulness và answer relevance bằng Gemini judges đã được cấu hình trong script:

```powershell
python 03_metadata_enterprise_chatbot/04_evaluate.py --dataset evaluation/ragas_dataset.json --run
```

Báo cáo được ghi vào `storage/ragas_evaluation_report.json`.

## 5. Chạy notebook

Notebook minh họa tương tác cho cùng các pipeline và có thể dùng thay cho hướng dẫn CLI. Đây không phải các bước bắt buộc bổ sung.

```powershell
jupyter lab
```

Chạy notebook theo thứ tự:

1. `01_rag_foundation/01_rag_foundation.ipynb`
2. `02_advanced_graph_rag/02_advanced_graph_rag.ipynb`
3. `03_metadata_enterprise_chatbot/03_metadata_enterprise_chatbot.ipynb`

Notebook Bài 02 vẫn cần Neo4j cho chức năng đồ thị. Notebook Bài 02 và Bài 03 vẫn cần chỉ mục do Bài 01 tạo.

## Cấu trúc dự án

```text
RAG_Demo_Labs/
|-- data/                              Tài liệu nguồn
|-- evaluation/                        Dataset và script so sánh/evaluation
|-- risk_wiki/                         Obsidian vault được sinh tự động
|-- storage/                           Chỉ mục, metadata, báo cáo và audit log
|-- 01_rag_foundation/                 Đọc tài liệu, lập chỉ mục, retrieval, đồng bộ vector DB
|-- 02_advanced_graph_rag/             Hybrid retrieval và Neo4j Graph RAG
|-- 03_metadata_enterprise_chatbot/    Metadata, RBAC, API, UI và đánh giá
|-- rag_document_processing.py         Đọc PDF, DOCX, bảng tính và ảnh
|-- rag_gemini_runtime.py              Chunking, Gemini, retrieval và citation dùng chung
|-- rag_vector_store.py                ChromaDB/Pinecone upsert và query
|-- rag_enterprise_store.py            PostgreSQL persistence và Redis cache
|-- requirements.txt                   Dependency Python
|-- docker-compose.yml                 Cơ sở dữ liệu và container ứng dụng
`-- Dockerfile                         Image cho API/UI
```

## Xử lý lỗi thường gặp

- **Tiếng Việt hiển thị sai:** chạy `chcp 65001` trước lệnh Python.
- **Chỉ mục đã cũ:** chạy lại `python 01_rag_foundation/01_chunk_and_index.py --rebuild`.
- **Neo4j báo sai mật khẩu:** đảm bảo mật khẩu trong `.env` giống mật khẩu đã dùng khi Neo4j volume được tạo lần đầu.
- **Không kết nối ChromaDB:** kiểm tra `docker compose ps` và `CHROMA_URL=http://localhost:8001` khi chạy Python trên host.
- **Không giải mã được tài liệu:** dùng cùng `RAG_ENCRYPTION_KEY` lúc lập chỉ mục và truy vấn.
- **OCR ảnh thất bại:** cài chương trình Tesseract và các language pack `vie`, `eng`; `pytesseract` chỉ là Python wrapper.

## Các tệp được sinh tự động

| Tệp | Được tạo bởi |
|---|---|
| `storage/foundation.json` | Bài 01 — lập chỉ mục |
| `storage/metadata_catalog.json` | Bài 03 — tạo metadata |
| `storage/audit_log.jsonl` | Truy vấn CLI/API của Bài 03 |
| `storage/ragas_evaluation_report.json` | Đánh giá RAGAS của Bài 03 |
| `storage/chunking_comparison.json` | So sánh Fixed/Semantic/Hierarchical |
| `storage/retrieval_comparison.json` | Precision/recall baseline và Hybrid RAG |
| `risk_wiki/*.md` | Hồ sơ rủi ro liên kết cho Obsidian |
