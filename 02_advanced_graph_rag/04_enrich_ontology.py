"""Enrich Neo4j with rule-based NER and optional Gemini entity extraction."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
from neo4j import GraphDatabase
from rag_core.runtime import GENERATE_MODEL, get_client, load_index

LABELS = {"Regulation", "LegalProvision", "Process", "Unit", "Role", "Risk"}


def rule_entities(text: str) -> list[tuple[str, str]]:
    patterns = {
        "Regulation": r"(?:Thông tư|TT)[ _-]?\d{1,3}[/-]\d{4}(?:[/-]TT-NHNN)?",
        "LegalProvision": r"(?:Điều|Chương)\s+[IVXLCDM0-9]+",
        "Risk": r"(?:rủi ro tín dụng|rủi ro hoạt động|rửa tiền|tài trợ khủng bố|nợ xấu)",
        "Role": r"(?:khách hàng|kiểm toán viên|cán bộ tín dụng|người có thẩm quyền)",
        "Unit": r"(?:Ngân hàng Nhà nước|tổ chức tín dụng|chi nhánh ngân hàng nước ngoài|Kiểm toán nội bộ)",
        "Process": r"(?:thẩm định tín dụng|xét duyệt cấp tín dụng|giám sát sử dụng vốn|cơ cấu lại thời hạn trả nợ|thu hồi nợ)",
    }
    found = []
    for label, pattern in patterns.items():
        found.extend((name.strip(), label) for name in re.findall(pattern, text, re.IGNORECASE))
    return list(dict.fromkeys((name, label) for name, label in found if name))


def llm_entities(text: str) -> list[tuple[str, str]]:
    prompt = f"""Extract named entities from this Vietnamese banking text.
Allowed types: {', '.join(sorted(LABELS))}. Return JSON only as
{{"entities":[{{"name":"...","type":"Risk"}}]}}. Do not invent entities.

TEXT:
{text[:6000]}"""
    response = get_client().models.generate_content(
        model=GENERATE_MODEL,
        contents=prompt,
        config={"temperature": 0, "response_mime_type": "application/json"},
    )
    payload = json.loads(response.text)
    return [
        (item["name"].strip(), item["type"])
        for item in payload.get("entities", [])
        if item.get("name", "").strip() and item.get("type") in LABELS
    ]


def relation_for(text: str) -> str:
    lowered = text.lower()
    if "tham chiếu" in lowered:
        return "REFERENCES"
    if "áp dụng" in lowered:
        return "APPLIES_TO"
    if "thay thế" in lowered:
        return "REPLACED_BY"
    return "MENTIONS"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--use-llm", action="store_true", help="Add Gemini extraction to transparent rule-based NER")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    password = os.getenv("NEO4J_PASSWORD")
    if not password:
        raise RuntimeError("Set NEO4J_PASSWORD before enriching the graph")
    driver = GraphDatabase.driver(os.getenv("NEO4J_URI", "bolt://localhost:7687"), auth=(os.getenv("NEO4J_USER", "neo4j"), password))
    count = 0
    with driver.session() as session:
        for record in load_index("foundation"):
            entities = rule_entities(record["text"])
            if args.use_llm:
                entities = list(dict.fromkeys([*entities, *llm_entities(record["text"])]))
            chunk_id = f"{record['source']}:{record['chunk_id']}"
            relation = relation_for(record["text"])
            for name, label in entities:
                # label and relation are selected only from internal allowlists.
                session.run(
                    f"MERGE (e:RagLab:{label} {{name:$name}}) WITH e MATCH (c:RagLab:Chunk {{id:$id}}) MERGE (c)-[:{relation}]->(e)",
                    name=name,
                    id=chunk_id,
                )
                count += 1
    driver.close()
    print(f"Ontology enriched with {count} entity links across {', '.join(sorted(LABELS))}.")


if __name__ == "__main__":
    main()
