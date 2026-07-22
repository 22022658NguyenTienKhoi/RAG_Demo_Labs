"""Compare baseline vector retrieval with the advanced hybrid pipeline."""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rag_core.runtime import STORE_DIR, load_index, retrieve

spec = importlib.util.spec_from_file_location("advanced", ROOT / "02_advanced_graph_rag" / "03_advanced_retrieval_pipeline.py")
advanced = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(advanced)


def metrics(hits: list[dict], relevant: set[str]) -> dict:
    returned = [hit["source"] for hit in hits]
    relevant_hits = sum(source in relevant for source in returned)
    return {
        "precision_at_k": relevant_hits / max(len(returned), 1),
        "recall_at_k": len(set(returned) & relevant) / max(len(relevant), 1),
    }


parser = argparse.ArgumentParser()
parser.add_argument("--dataset", default=str(ROOT / "evaluation" / "retrieval_dataset.json"))
parser.add_argument("--backend", choices=["chroma", "pinecone", "json"], default=None)
parser.add_argument("--top-k", type=int, default=5)
args = parser.parse_args()

rows = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
records = load_index("foundation")
results = []
for row in rows:
    relevant = set(row["relevant_sources"])
    baseline = retrieve(row["question"], records, top_k=args.top_k, backend=args.backend)
    hybrid = advanced.hybrid_retrieve(row["question"], records, top_k=args.top_k, backend=args.backend)
    results.append({"question": row["question"], "baseline": metrics(baseline, relevant), "hybrid": metrics(hybrid, relevant)})

summary = {
    name: {
        metric: sum(row[name][metric] for row in results) / len(results)
        for metric in ("precision_at_k", "recall_at_k")
    }
    for name in ("baseline", "hybrid")
}
report = {"top_k": args.top_k, "backend": args.backend or "environment-default", "summary": summary, "samples": results}
STORE_DIR.mkdir(exist_ok=True)
(STORE_DIR / "retrieval_comparison.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
