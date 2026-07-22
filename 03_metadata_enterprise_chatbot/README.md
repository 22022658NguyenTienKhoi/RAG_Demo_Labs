# Bài thực hành 03 — Metadata và chatbot doanh nghiệp

Bài thực hành 03 truy vấn ChromaDB/Pinecone và dùng manifest từ Bài 01 cho hybrid retrieval. Bài này **không** tạo embedding tài liệu lại.

1. Hoàn tất Giai đoạn 1 của Bài thực hành 01: `cd ../01_rag_foundation; python 01_chunk_and_index.py --rebuild --backend chroma`
2. Tạo danh mục metadata: `cd ../03_metadata_enterprise_chatbot; python 01_build_metadata_catalog.py`
3. Chạy truy xuất ChromaDB có lọc RBAC: `python 02_rbac_retrieve_and_answer.py --backend chroma --role internal_auditor --ask "Câu hỏi"`
4. Xem ma trận RBAC ngoại tuyến: `python 03_rbac_access_matrix.py`

Giai đoạn truy vấn gửi RBAC source filter vào vector database. Khi chạy Compose, PostgreSQL lưu metadata/audit và Redis cache kết quả theo role; JSON/JSONL chỉ là fallback khi chạy riêng CLI.

Chạy toàn bộ API/UI/dữ liệu bằng `docker compose up --build` tại thư mục gốc. Swagger ở `http://localhost:8000/docs`, Streamlit ở `http://localhost:8501`.

Các vai trò minh họa quyền truy cập khác nhau: `business_user`, `credit_officer`, `compliance` và `internal_auditor`. Danh mục cũng bao gồm loại tài liệu, đơn vị sở hữu, mức phân loại (`public`, `internal`, `confidential`, `restricted`), ngày hiệu lực, thời hạn lưu trữ và các vai trò được phép.
