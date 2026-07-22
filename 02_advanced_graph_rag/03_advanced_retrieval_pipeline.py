"""Lab 02 complete retrieval pipeline: multi-query, hybrid, reranking and parents."""
from __future__ import annotations

import argparse
import math
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = next(p for p in HERE.parents if (p / "rag_gemini_runtime.py").exists())
sys.path.insert(0, str(ROOT))
from rag_gemini_runtime import infer, load_index, retrieve
from dotenv import load_dotenv
from neo4j import GraphDatabase


def terms(text: str) -> list[str]:
    return re.findall(r"[\wÀ-ỹ]+", text.lower())


def bm25(question: str, records: list[dict]) -> list[tuple[float, dict]]:
    docs = [terms(record["text"]) for record in records]
    df = Counter(term for doc in docs for term in set(doc)); average = sum(map(len, docs)) / max(len(docs), 1)
    scores = []
    for record, doc in zip(records, docs):
        counts = Counter(doc); length = len(doc); score = 0.0
        for term in terms(question):
            if term in counts:
                idf = math.log(1 + (len(records) - df[term] + .5) / (df[term] + .5))
                score += idf * counts[term] * 2.5 / (counts[term] + 1.5 * (.25 + .75 * length / average))
        scores.append((score, record))
    return sorted(scores, key=lambda item: item[0], reverse=True)


def query_variants(question: str) -> list[str]:
    """Deterministic multi-query expansion; safe when generation quota is unavailable."""
    compact = " ".join(terms(question))
    return list(dict.fromkeys([question, compact, f"quy định điều kiện áp dụng {compact}"]))


def rrf(rankings: list[list[tuple[float, dict]]], k: int = 60) -> list[dict]:
    scores: defaultdict[tuple, float] = defaultdict(float); documents = {}
    for ranking in rankings:
        for rank, (_, record) in enumerate(ranking, 1):
            key = (record["source"], record["chunk_id"]); scores[key] += 1 / (k + rank); documents[key] = record
    return [{**documents[key], "score": score} for key, score in sorted(scores.items(), key=lambda pair: pair[1], reverse=True)]


def rerank(question: str, candidates: list[dict]) -> list[dict]:
    """Use a cross-encoder when installed; lexical fallback keeps the lab runnable."""
    try:
        from sentence_transformers import CrossEncoder
        scores = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2").predict([(question, item["text"]) for item in candidates])
        return sorted([{**item, "rerank_score": float(score)} for item, score in zip(candidates, scores)], key=lambda item: item["rerank_score"], reverse=True)
    except ImportError:
        query = set(terms(question))
        return sorted([{**item, "rerank_score": len(query & set(terms(item["text"]))) / max(len(query), 1)} for item in candidates], key=lambda item: item["rerank_score"], reverse=True)


def expand_parents(hits: list[dict], records: list[dict]) -> list[dict]:
    parents = {hit.get("parent_id") for hit in hits}
    siblings = [record for record in records if record.get("parent_id") in parents]
    return list({(item["source"], item["chunk_id"]): item for item in [*hits, *siblings]}.values())


def expand_graph(hits: list[dict], records: list[dict]) -> list[dict]:
    """Add chunks connected to retrieval seeds through the ontology in Neo4j.

    A missing/unavailable graph leaves hybrid RAG usable; it never replaces
    the already retrieved evidence with an unchecked graph result.
    """
    root = Path(__file__).resolve().parents[1]
    load_dotenv(root / ".env")
    password = os.getenv("NEO4J_PASSWORD")
    if not password:
        return hits
    ids = [f"{item['source']}:{item['chunk_id']}" for item in hits]
    try:
        driver = GraphDatabase.driver(os.getenv("NEO4J_URI", "bolt://localhost:7687"), auth=(os.getenv("NEO4J_USER", "neo4j"), password))
        query = """
        MATCH (seed:RagLab:Chunk) WHERE seed.id IN $ids
        MATCH (seed)-[:REFERENCES|APPLIES_TO|REPLACED_BY|MENTIONS]->(entity)
        MATCH (related:RagLab:Chunk)-[:REFERENCES|APPLIES_TO|REPLACED_BY|MENTIONS]->(entity)
        RETURN DISTINCT related.source AS source, related.chunk_number AS chunk_id
        LIMIT 20
        """
        with driver.session() as session:
            rows = session.run(query, ids=ids).data()
        driver.close()
    except Exception as error:
        print(f"Graph expansion unavailable; continuing with hybrid evidence: {error}")
        return hits
    by_id = {(item["source"], item["chunk_id"]): item for item in records}
    connected = [by_id[(row["source"], row["chunk_id"])] for row in rows if (row["source"], row["chunk_id"]) in by_id]
    return list({(item["source"], item["chunk_id"]): item for item in [*hits, *connected]}.values())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ask", required=True); parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args(); records = load_index("foundation")
    rankings = []
    for query in query_variants(args.ask):
        rankings.append([(hit["score"], hit) for hit in retrieve(query, records, top_k=len(records))])
        rankings.append(bm25(query, records))
    hits = rerank(args.ask, rrf(rankings)[:20])
    context = expand_parents(expand_graph(hits[:args.top_k], records), records)
    for item in hits[:args.top_k]: print(f"{item['rerank_score']:.3f} | {item['source']} | {item.get('parent_title', 'N/A')} | chunk {item['chunk_id']}")
    print(infer(args.ask, context, "Use only the retrieved hybrid, graph-connected and parent-child context; cite every claim."))


if __name__ == "__main__": main()
