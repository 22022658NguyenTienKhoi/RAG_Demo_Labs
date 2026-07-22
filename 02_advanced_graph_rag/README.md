# Bài thực hành 02 — RAG nâng cao và Graph RAG

Bài thực hành 02 dùng ChromaDB/Pinecone cho semantic search và manifest `../storage/foundation.json` cho BM25, parent expansion và Neo4j. Bài này **không** tạo embedding tài liệu lần nữa.

1. Hoàn tất Giai đoạn 1 của Bài thực hành 01: `cd ../01_rag_foundation; python 01_chunk_and_index.py --rebuild --backend chroma`
2. Xây dựng Neo4j từ các đoạn đó: `cd ../02_advanced_graph_rag; python 01_build_neo4j_graph.py`
3. Truy vấn Hybrid RRF + Graph RAG: `python 02_hybrid_graph_query.py --ask "Câu hỏi"`
4. Chạy pipeline đầy đủ: `python 03_advanced_retrieval_pipeline.py --backend chroma --ask "Câu hỏi"`

Pipeline dùng multi-query, vector search, BM25, RRF và lexical reranking nhẹ; không cần sentence-transformers.
