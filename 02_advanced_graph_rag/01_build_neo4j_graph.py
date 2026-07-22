"""Bài thực hành 02, Giai đoạn 1 — xây Neo4j từ chỉ mục đoạn có sẵn của Bài 01.

Điều kiện trước: chạy ../01_rag_foundation/01_chunk_and_index.py --rebuild.
Script này không tạo embedding Gemini. Nó đọc storage/foundation.json.
"""
import argparse
import os
import re
import sys
from pathlib import Path

HERE = Path(globals().get("__file__", Path.cwd())).resolve()
PROJECT_ROOT = HERE.parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from neo4j import GraphDatabase
from rag_core.runtime import ROOT, load_index


def section_name(text: str) -> str:
    """Use the first legal/Markdown heading as a transparent graph section."""
    match = re.search(r"^(?:#{1,6}\s+|Điều\s+|Chương\s+)(.+)$", text, re.MULTILINE)
    return match.group(0).strip()[:240] if match else "Nội dung chung"


def main() -> None:
    load_dotenv(ROOT / ".env")
    password = os.getenv("NEO4J_PASSWORD")
    if not password:
        raise RuntimeError("Hãy đặt NEO4J_PASSWORD trong RAG_Demo_Labs/.env trước khi xây đồ thị.")
    records = load_index("foundation")  # Lab 01 output; no chunking/embedding here.
    driver = GraphDatabase.driver(os.getenv("NEO4J_URI", "bolt://localhost:7687"), auth=(os.getenv("NEO4J_USER", "neo4j"), password))
    with driver.session() as session:
        # Chỉ xóa node do bài thực hành này tạo, không đụng đến đồ thị Neo4j khác.
        session.run("MATCH (n:RagLab) DETACH DELETE n")
        for record in records:
            document_id = record["source"]
            chunk_id = f"{document_id}:{record['chunk_id']}"
            section = section_name(record["text"])
            session.run("""
                MERGE (d:RagLab:Document {id:$document_id})
                MERGE (s:RagLab:Section {id:$section_id, name:$section})
                MERGE (d)-[:HAS_SECTION]->(s)
                MERGE (c:RagLab:Chunk {id:$chunk_id})
                SET c.text=$text, c.source=$document_id, c.chunk_number=$chunk_number
                MERGE (s)-[:CONTAINS]->(c)
            """, document_id=document_id, section_id=f"{document_id}:{section}", section=section,
                 chunk_id=chunk_id, text=record["text"], chunk_number=record["chunk_id"])
    driver.close()
    print(f"Đã xây đồ thị Neo4j từ {len(records)} đoạn của Bài 01; không tạo embedding lại.")


if __name__ == "__main__":
    argparse.ArgumentParser(description="Xây đồ thị Neo4j từ chỉ mục nền tảng hoàn tất của Bài 01.").parse_args()
    main()
