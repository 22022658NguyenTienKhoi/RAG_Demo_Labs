# Bộ bài thực hành RAG

Dự án gồm ba bài thực hành xây dựng hệ thống hỏi đáp tài liệu bằng Gemini:

1. **RAG Foundation** — đọc tài liệu, tạo embedding và trả lời câu hỏi.
2. **Advanced/Graph RAG** — bổ sung multi-query, BM25, Reciprocal Rank Fusion, reranking, mở rộng ngữ cảnh cha và Neo4j.
3. **Enterprise RAG** — bổ sung metadata, phân quyền RBAC, nhật ký kiểm toán, FastAPI và giao diện Streamlit.

Bài 01 tạo `storage/foundation.json`. Bài 02 và Bài 03 dùng lại chỉ mục này, vì vậy luôn hoàn thành Bài 01 trước.

## 1. Cài đặt toàn bộ môi trường

Chạy tất cả lệnh từ thư mục gốc của dự án:

```powershell
cd C:\Users\HP\Downloads\RAG_Demo_Labs
```

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

`requirements.txt` bao gồm thư viện cho Gemini, xử lý tài liệu, Neo4j, ChromaDB, Pinecone, FastAPI, Streamlit, RAGAS, PostgreSQL và Redis.

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

# Tùy chọn: chỉ dùng khi đồng bộ sang Pinecone ở Bài 01
PINECONE_API_KEY=thay-bang-pinecone-api-key-cua-ban
PINECONE_INDEX=ten-index-768-chieu-da-ton-tai
```

`GEMINI_API_KEY` là bắt buộc khi tạo chỉ mục và hỏi đáp. Các biến `NEO4J_*` chỉ bắt buộc với chức năng đồ thị của Bài 02. Không commit hoặc chia sẻ tệp `.env`.

### Cài và chạy cơ sở dữ liệu

Tải tất cả Docker image cơ sở dữ liệu đã khai báo trong dự án:

```powershell
docker compose pull neo4j chromadb postgres redis
```

Chỉ khởi động dịch vụ khi bài thực hành cần đến:

```powershell
# Bắt buộc cho chức năng đồ thị của Bài 02
docker compose up -d neo4j

# Tùy chọn: lưu thêm một bản sao chỉ mục của Bài 01
docker compose up -d chromadb

# Dành cho phần mở rộng sau này; mã nguồn hiện tại chưa truy vấn hai dịch vụ này
docker compose up -d postgres redis
```

| Dịch vụ | Địa chỉ | Mã nguồn hiện tại sử dụng |
|---|---|---|
| Neo4j Browser | `http://localhost:7474` | Có, Bài 02 |
| Neo4j Bolt | `bolt://localhost:7687` | Có, Bài 02 |
| ChromaDB | `http://localhost:8000` | Tùy chọn ở Bài 01 |
| PostgreSQL | Chỉ trong mạng Docker | Chưa; dành cho phần mở rộng |
| Redis | Chỉ trong mạng Docker | Chưa; dành cho phần mở rộng |
| Pinecone | Dịch vụ cloud | Tùy chọn ở Bài 01 |

ChromaDB và FastAPI cùng dùng cổng `8000` trên máy host. Hãy dừng ChromaDB trước khi chạy API trên cổng mặc định:

```powershell
docker compose stop chromadb
```

Kiểm tra hoặc dừng các dịch vụ:

```powershell
docker compose ps
docker compose stop neo4j chromadb postgres redis
```

## 2. Chạy Bài 01 — RAG Foundation

Bài 01 đọc tài liệu trong `data/`. Các định dạng được hỗ trợ gồm Markdown, TXT, PDF, DOCX, XLS/XLSX và ảnh. Kết quả là chỉ mục vector Gemini dùng chung tại `storage/foundation.json`.

### Bước 1: xem trước cách chia đoạn

Lệnh này không gọi Gemini và không ghi chỉ mục:

```powershell
python 01_rag_foundation/01_chunk_and_index.py --dry-run
```

### Bước 2: tạo chỉ mục dùng chung

```powershell
python 01_rag_foundation/01_chunk_and_index.py --rebuild
```

Quá trình lập chỉ mục gọi Gemini Embedding API nên có thể mất thời gian. Chạy lại với `--rebuild` khi tài liệu hoặc cấu hình chunking thay đổi. Nếu không có `--rebuild`, chương trình sẽ dùng lại chỉ mục hợp lệ và chưa thay đổi.

### Bước 3: đặt câu hỏi

```powershell
python 01_rag_foundation/02_retrieve_and_answer.py --ask "Thong tu nao quy dinh ve hoat dong cho vay?"
```

Chương trình tìm các đoạn liên quan nhất rồi yêu cầu Gemini trả lời kèm tên nguồn, trang/sheet, section và mã chunk.

### Tùy chọn: sao chép chỉ mục sang vector database

Các bài thực hành vẫn dùng `storage/foundation.json`. Những lệnh dưới đây chỉ tạo thêm một bản sao trong vector database.

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

Script bổ sung entity văn bản pháp lý và điều khoản, cùng các quan hệ `REFERENCES`, `APPLIES_TO`, `REPLACED_BY` hoặc `MENTIONS`.

### Bước 3: chạy demo Hybrid/Graph RAG ngắn

```powershell
python 02_advanced_graph_rag/02_hybrid_graph_query.py --ask "Thong tu nao quy dinh ve hoat dong cho vay?"
```

### Bước 4: chạy pipeline truy xuất đầy đủ

```powershell
python 02_advanced_graph_rag/03_advanced_retrieval_pipeline.py --ask "Dieu kien cho vay la gi?" --top-k 5
```

Pipeline đầy đủ thực hiện multi-query, Gemini dense retrieval, BM25, Reciprocal Rank Fusion, cross-encoder reranking, mở rộng bằng Neo4j và mở rộng ngữ cảnh parent-child. Lần chạy cross-encoder đầu tiên có thể cần tải model. Nếu Neo4j không khả dụng, script vẫn tiếp tục bằng Hybrid RAG và thông báo đã bỏ qua graph expansion.

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

Tài liệu bị từ chối được loại bỏ trước bước retrieval. Mỗi truy vấn sẽ ghi thêm một event vào `storage/audit_log.jsonl`.

### Bước 4: chạy REST API

Đảm bảo ChromaDB đã dừng vì cả hai cùng dùng cổng `8000`, sau đó chạy FastAPI:

```powershell
docker compose stop chromadb
uvicorn 03_metadata_enterprise_chatbot.api:app --reload --port 8000
```

Mở `http://localhost:8000/docs` để thử API bằng Swagger UI.

| Method và endpoint | Chức năng |
|---|---|
| `GET /health` | Kiểm tra trạng thái dịch vụ |
| `POST /ask` | Hỏi đáp chính sách có RBAC |
| `POST /compliance/gap-analysis` | So sánh tài liệu nội bộ và văn bản quy định mà role được phép đọc |
| `POST /audit/checklist` | Tạo checklist kiểm toán theo rủi ro dựa trên nguồn truy xuất |

### Bước 5: chạy giao diện Streamlit

Giữ API hoạt động. Mở PowerShell thứ hai, kích hoạt môi trường ảo, cấu hình địa chỉ API local rồi chạy Streamlit:

```powershell
cd C:\Users\HP\Downloads\RAG_Demo_Labs
.\.venv\Scripts\Activate.ps1
$env:RAG_API_URL = "http://localhost:8000"
streamlit run 03_metadata_enterprise_chatbot/app.py
```

### Tùy chọn: đánh giá bằng RAGAS

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
python 03_metadata_enterprise_chatbot/04_evaluate.py --dataset evaluation.json
```

Sau khi cấu hình LLM và embedding provider được phiên bản RAGAS đang cài hỗ trợ, chạy các metric:

```powershell
python 03_metadata_enterprise_chatbot/04_evaluate.py --dataset evaluation.json --run
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
|-- storage/                           Chỉ mục, metadata, báo cáo và audit log
|-- 01_rag_foundation/                 Đọc tài liệu, lập chỉ mục, retrieval, đồng bộ vector DB
|-- 02_advanced_graph_rag/             Hybrid retrieval và Neo4j Graph RAG
|-- 03_metadata_enterprise_chatbot/    Metadata, RBAC, API, UI và đánh giá
|-- rag_document_processing.py         Đọc PDF, DOCX, bảng tính và ảnh
|-- rag_gemini_runtime.py              Chunking, Gemini, retrieval và citation dùng chung
|-- requirements.txt                   Dependency Python
|-- docker-compose.yml                 Cơ sở dữ liệu và container ứng dụng
`-- Dockerfile                         Image cho API/UI
```

## Xử lý lỗi thường gặp

- **Tiếng Việt hiển thị sai:** chạy `chcp 65001` trước lệnh Python.
- **Chỉ mục đã cũ:** chạy lại `python 01_rag_foundation/01_chunk_and_index.py --rebuild`.
- **Neo4j báo sai mật khẩu:** đảm bảo mật khẩu trong `.env` giống mật khẩu đã dùng khi Neo4j volume được tạo lần đầu.
- **Cổng 8000 đang được sử dụng:** dừng ChromaDB trước khi chạy FastAPI, hoặc dùng cổng API khác và cập nhật `RAG_API_URL`.
- **OCR ảnh thất bại:** cài chương trình Tesseract và các language pack `vie`, `eng`; `pytesseract` chỉ là Python wrapper.
- **Không tải được reranker:** lần tải cross-encoder model đầu tiên cần Internet. Nếu thiếu gói `sentence-transformers`, chương trình dùng lexical reranking dự phòng.

## Các tệp được sinh tự động

| Tệp | Được tạo bởi |
|---|---|
| `storage/foundation.json` | Bài 01 — lập chỉ mục |
| `storage/metadata_catalog.json` | Bài 03 — tạo metadata |
| `storage/audit_log.jsonl` | Truy vấn CLI/API của Bài 03 |
| `storage/ragas_evaluation_report.json` | Đánh giá RAGAS của Bài 03 |

