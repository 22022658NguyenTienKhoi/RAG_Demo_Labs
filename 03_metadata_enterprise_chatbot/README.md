# Lab 03 — Metadata và Enterprise RAG Chatbot

Lab này đưa pipeline của hai lab trước vào mô hình ứng dụng doanh nghiệp: có metadata, phân quyền, audit, cache, API và giao diện web.

## Mục tiêu

- Chuẩn hóa metadata tài liệu và thông tin hiệu lực.
- Chặn tài liệu không được phép trước và ngay trong vector retrieval.
- Lưu metadata/audit bằng PostgreSQL và cache theo role bằng Redis.
- Cung cấp FastAPI và Streamlit.
- Thực hành policy lookup, gap analysis, compliance checker và audit checklist.

## Chạy toàn bộ Lab 03

Từ thư mục gốc:

```powershell
docker compose up -d chromadb postgres redis api web
```

- Swagger: `http://localhost:8000/docs`
- Streamlit: `http://localhost:8501`

## Chạy từng bước

```powershell
python 03_metadata_enterprise_chatbot/01_build_metadata_catalog.py
python 03_metadata_enterprise_chatbot/03_rbac_access_matrix.py
python 03_metadata_enterprise_chatbot/02_rbac_retrieve_and_answer.py --backend chroma --role internal_auditor --ask "Quy dinh ve hoat dong cho vay?"
python 03_metadata_enterprise_chatbot/05_build_risk_wiki.py
```

## Thành phần

| Tệp | Vai trò |
|---|---|
| `01_build_metadata_catalog.py` | Tạo metadata catalog |
| `02_rbac_retrieve_and_answer.py` | Demo CLI có RBAC và audit |
| `03_rbac_access_matrix.py` | Hiển thị quyền theo role/tài liệu |
| `04_evaluate.py` | Validation và RAGAS evaluation |
| `05_build_risk_wiki.py` | Sinh Risk Wiki cho Obsidian |
| `api.py` | FastAPI cho bốn use case |
| `app.py` | Giao diện Streamlit |
| `enterprise_store.py` | PostgreSQL persistence và Redis cache |
| `start_api.py` | Khởi tạo index/catalog trước khi chạy API trong Docker |

## Phân quyền minh họa

| Role | Mức dữ liệu tối đa |
|---|---|
| `business_user` | public |
| `credit_officer` | public, internal, confidential |
| `compliance` | public, internal, confidential, restricted |
| `internal_auditor` | public, internal, confidential, restricted |

Audit event không lưu câu hỏi thô; hệ thống chỉ lưu hash và danh sách nguồn đã sử dụng.
