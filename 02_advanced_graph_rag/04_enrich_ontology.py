"""Add a transparent mini ontology to the Neo4j graph built by Lab 02."""
from __future__ import annotations
import os, re, sys
from pathlib import Path
HERE = Path(__file__).resolve(); ROOT = next(p for p in HERE.parents if (p / "rag_gemini_runtime.py").exists()); sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
from neo4j import GraphDatabase
from rag_gemini_runtime import load_index

def entities(text):
    found = [(item.upper(), "Regulation") for item in re.findall(r"(?:Thông tư|TT)[ _-]?\d{1,3}[/-]\d{4}(?:[/-]TT-NHNN)?", text, re.I)]
    found += [(item.title(), "LegalProvision") for item in re.findall(r"(?:Điều|Chương)\s+[IVXLCDM0-9]+", text, re.I)]
    return list(dict.fromkeys(found))

load_dotenv(ROOT / ".env"); password = os.getenv("NEO4J_PASSWORD")
if not password: raise RuntimeError("Set NEO4J_PASSWORD before enriching the graph.")
driver = GraphDatabase.driver(os.getenv("NEO4J_URI", "bolt://localhost:7687"), auth=(os.getenv("NEO4J_USER", "neo4j"), password))
with driver.session() as session:
    for record in load_index("foundation"):
        chunk_id = f"{record['source']}:{record['chunk_id']}"
        for name, label in entities(record["text"]):
            relation = "REFERENCES" if "tham chiếu" in record["text"].lower() else "APPLIES_TO" if "áp dụng" in record["text"].lower() else "REPLACED_BY" if "thay thế" in record["text"].lower() else "MENTIONS"
            session.run(f"MERGE (e:RagLab:{label} {{name:$name}}) WITH e MATCH (c:RagLab:Chunk {{id:$id}}) MERGE (c)-[:{relation}]->(e)", name=name, id=chunk_id)
driver.close(); print("Ontology enriched: Document, Section, Chunk, Regulation, LegalProvision, REFERENCES/APPLIES_TO/REPLACED_BY.")
