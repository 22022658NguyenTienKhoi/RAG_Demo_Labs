"""Bài thực hành 02, Giai đoạn 2 — truy xuất lai từ Bài 01 và mở rộng bằng đồ thị Neo4j."""
import argparse
import math
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(globals().get("__file__", Path.cwd())).resolve()
PROJECT_ROOT = next(p for p in (HERE.parent, *HERE.parents, Path.cwd(), Path.cwd() / "RAG_Demo_Labs") if (p / "rag_gemini_runtime.py").exists())
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from neo4j import GraphDatabase
from rag_gemini_runtime import ROOT, infer, load_index, retrieve

def words(text): return re.findall(r"[\wÀ-ỹ]+", text.lower())
def bm25(question, records):
    terms=words(question); n=len(records); df=Counter(t for r in records for t in set(words(r['text']))); avg=sum(len(words(r['text'])) for r in records)/n; result=[]
    for r in records:
        counts=Counter(words(r['text'])); length=sum(counts.values()); score=sum(math.log(1+(n-df[t]+.5)/(df[t]+.5))*counts[t]*2.5/(counts[t]+1.5*(.25+.75*length/avg)) for t in terms if t in counts); result.append((score,r))
    return sorted(result,reverse=True,key=lambda item:item[0])
def rrf(*rankings):
    scores=defaultdict(float); docs={}
    for ranking in rankings:
        for rank,(_,doc) in enumerate(ranking,1): key=(doc['source'],doc['chunk_id']); scores[key]+=1/(60+rank); docs[key]=doc
    return [{**docs[key],'score':score} for key,score in sorted(scores.items(),key=lambda item:item[1],reverse=True)]
def graph_facts(hits):
    load_dotenv(ROOT/'.env'); password=os.getenv('NEO4J_PASSWORD')
    if not password: return "Không dùng Neo4j: thiếu NEO4J_PASSWORD."
    ids=[f"{h['source']}:{h['chunk_id']}" for h in hits]
    try:
        driver=GraphDatabase.driver(os.getenv('NEO4J_URI','bolt://localhost:7687'),auth=(os.getenv('NEO4J_USER','neo4j'),password))
        with driver.session() as session:
            rows=session.run("""UNWIND $ids AS id MATCH (c:RagLab:Chunk {id:id})<-[:CONTAINS]-(s:RagLab:Section)<-[:HAS_SECTION]-(d:RagLab:Document) RETURN d.id AS document, s.name AS section, c.chunk_number AS chunk""",ids=ids).data()
        driver.close(); return "\n".join(f"Đường đi đồ thị: {r['document']} → {r['section']} → đoạn {r['chunk']}" for r in rows) or "Không có node đồ thị tương ứng. Hãy chạy 01_build_neo4j_graph.py."
    except Exception as error: return f"Không thể dùng đồ thị Neo4j: {error}"

parser=argparse.ArgumentParser(description='Hybrid RRF + Graph RAG Neo4j dùng chỉ mục của Bài 01')
parser.add_argument('--ask',required=True)
parser.add_argument('--backend',choices=['chroma','pinecone','json'],default=None)
args=parser.parse_args()
if '?' in args.ask[:-1]:
    raise ValueError("Câu hỏi có '?' thay cho ký tự tiếng Việt. Hãy dùng PowerShell UTF-8 hoặc tiếng Việt không dấu, ví dụ: 'Thong tu nao quy dinh ve hoat dong cho vay cua to chuc tin dung?'.")
records=load_index('foundation')
dense=[(item['score'],item) for item in retrieve(args.ask,records,top_k=len(records),backend=args.backend)]
hits=rrf(dense,bm25(args.ask,records))[:5]
facts=graph_facts(hits)
for h in hits:
    preview=' '.join(h['text'].split())[:180]
    print(f"{h['score']:.3f} | {h['source']} | chunk {h['chunk_id']}\n  {preview}...")
print('\nKết quả duyệt Neo4j:\n',facts)
print('\nCâu trả lời Gemini:\n',infer(args.ask,hits,'Thông tin từ duyệt đồ thị:\n'+facts+'\nChỉ sử dụng bằng chứng truy xuất có trích dẫn.'))
