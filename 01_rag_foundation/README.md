# Bài thực hành 01 — Nền tảng RAG

Chạy ChromaDB trước bằng `docker compose up -d chromadb` tại thư mục gốc.

1. Chia đoạn, tạo embedding và upsert ChromaDB: `python 01_chunk_and_index.py --rebuild --backend chroma`
2. Truy vấn ChromaDB và trả lời: `python 02_retrieve_and_answer.py --backend chroma --ask "Câu hỏi"`

Dùng `--backend pinecone` để thực hành cloud hoặc `--backend json` làm fallback ngoại tuyến rõ ràng.
