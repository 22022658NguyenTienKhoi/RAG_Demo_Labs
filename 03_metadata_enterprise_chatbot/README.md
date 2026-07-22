# Bài thực hành 03 — Metadata và chatbot doanh nghiệp

Bài thực hành 03 sử dụng lại `../storage/foundation.json` từ Bài thực hành 01. Bài này **không** chia đoạn hoặc tạo embedding lại cho tài liệu.

1. Hoàn tất Giai đoạn 1 của Bài thực hành 01: `cd ../01_rag_foundation; python 01_chunk_and_index.py --rebuild`
2. Tạo danh mục metadata: `cd ../03_metadata_enterprise_chatbot; python 01_build_metadata_catalog.py`
3. Chạy truy xuất có lọc RBAC: `python 02_rbac_retrieve_and_answer.py --role internal_auditor --ask "Câu hỏi"`
4. Xem ma trận RBAC ngoại tuyến: `python 03_rbac_access_matrix.py`

Giai đoạn truy vấn áp dụng RBAC trước khi truy xuất và thêm sự kiện kiểm toán vào `../storage/audit_log.jsonl`.

Các vai trò minh họa quyền truy cập khác nhau: `business_user`, `credit_officer`, `compliance` và `internal_auditor`. Danh mục cũng bao gồm loại tài liệu, đơn vị sở hữu, mức phân loại (`public`, `internal`, `confidential`, `restricted`), ngày hiệu lực, thời hạn lưu trữ và các vai trò được phép.
