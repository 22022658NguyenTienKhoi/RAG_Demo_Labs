# Lab 02 — Advanced RAG và Graph RAG

Lab này nâng cấp semantic search của Lab 01 thành pipeline Hybrid RAG và bổ sung mở rộng ngữ cảnh bằng Neo4j.

## Mục tiêu

- Kết hợp vector search và BM25.
- Tạo multi-query và hợp nhất ranking bằng RRF.
- Rerank nhẹ bằng lexical overlap, không tải model riêng.
- Mở rộng chunk lân cận nhưng giới hạn context để giảm noise.
- Mô hình hóa `Document → Section → Chunk` trong Neo4j.
- Trích xuất Regulation, LegalProvision, Process, Unit, Role và Risk.

## Điều kiện

- Lab 01 đã tạo `storage/foundation.json`.
- ChromaDB đã có collection `rag_foundation`.
- `NEO4J_*` đã được cấu hình trong `.env`.

## Thứ tự chạy

```powershell
docker compose up -d chromadb neo4j
python 02_advanced_graph_rag/01_build_neo4j_graph.py
python 02_advanced_graph_rag/04_enrich_ontology.py
python 02_advanced_graph_rag/03_advanced_retrieval_pipeline.py --backend chroma --top-k 5 --ask "Dieu kien cho vay la gi?"
```

Thêm `--use-llm` vào script ontology nếu muốn kết hợp rule-based NER với Gemini extraction.

## Các script

| Tệp | Vai trò |
|---|---|
| `01_build_neo4j_graph.py` | Nạp cấu trúc tài liệu vào Neo4j |
| `02_hybrid_graph_query.py` | Demo ngắn Hybrid RRF và graph facts |
| `03_advanced_retrieval_pipeline.py` | Pipeline multi-query, vector + BM25, RRF, rerank, parent/graph expansion |
| `04_enrich_ontology.py` | Tạo entity và quan hệ ontology |
| `02_advanced_graph_rag.ipynb` | Phiên bản notebook tương tác |

Nếu Neo4j không hoạt động, pipeline vẫn tiếp tục bằng Hybrid RAG.
