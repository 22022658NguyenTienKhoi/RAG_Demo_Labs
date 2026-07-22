import sys
from pathlib import Path
HERE = Path(globals().get("__file__", Path.cwd())).resolve()
PROJECT_ROOT = next(p for p in (HERE.parent, *HERE.parents, Path.cwd(), Path.cwd() / "RAG_Demo_Labs") if (p / "rag_gemini_runtime.py").exists())
sys.path.insert(0, str(PROJECT_ROOT))
from rag_gemini_runtime import load_index, retrieve, infer
import argparse
parser = argparse.ArgumentParser(description="Giai đoạn 2: truy xuất từ chỉ mục hoàn tất và gọi Gemini")
parser.add_argument("--ask", required=True)
args = parser.parse_args()
records = load_index("foundation")
hits = retrieve(args.ask, records, top_k=5)
for h in hits: print(f"{h['score']:.3f} | {h['source']} | chunk {h['chunk_id']}")
print("\nCâu trả lời Gemini:\n", infer(args.ask, hits))
