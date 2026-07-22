# Bài thực hành 02 — RAG nâng cao và Graph RAG

Bài thực hành 02 sử dụng lại `../storage/foundation.json` do Bài thực hành 01 tạo ra. Bài này **không** chia đoạn hoặc tạo embedding Markdown lần nữa.

1. Hoàn tất Giai đoạn 1 của Bài thực hành 01: `cd ../01_rag_foundation; python 01_chunk_and_index.py --rebuild`
2. Xây dựng Neo4j từ các đoạn đó: `cd ../02_advanced_graph_rag; python 01_build_neo4j_graph.py`
3. Truy vấn Hybrid RRF + Graph RAG: `python 02_hybrid_graph_query.py --ask "Câu hỏi"`
