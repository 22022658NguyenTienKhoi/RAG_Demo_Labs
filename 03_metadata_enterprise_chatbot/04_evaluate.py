"""Validate and run a RAGAS evaluation for the enterprise RAG dataset."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve(); ROOT = next(p for p in HERE.parents if (p / "rag_gemini_runtime.py").exists()); sys.path.insert(0, str(ROOT))
from rag_gemini_runtime import STORE_DIR

parser = argparse.ArgumentParser()
parser.add_argument("--dataset", required=True, help="JSON array: question, answer, contexts, ground_truth")
parser.add_argument("--run", action="store_true", help="Run RAGAS using the LLM/embedding judge configured in the environment")
args = parser.parse_args()
rows = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
required = {"question", "answer", "contexts", "ground_truth"}
if not isinstance(rows, list) or not rows or any(not required <= row.keys() or not isinstance(row["contexts"], list) for row in rows):
    raise ValueError(f"Dataset must be a non-empty JSON array; each row needs {sorted(required)} and a contexts list")

report = {"samples": len(rows), "metrics": ["context_precision", "context_recall", "faithfulness", "answer_relevancy"], "status": "validated"}
if args.run:
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import context_precision, context_recall, faithfulness, answer_relevancy
        result = evaluate(Dataset.from_list(rows), metrics=[context_precision, context_recall, faithfulness, answer_relevancy])
        report["scores"] = {key: float(value) for key, value in result.to_pandas().mean(numeric_only=True).to_dict().items()}
        report["status"] = "completed"
    except Exception as error:
        report["status"] = "failed"
        report["error"] = str(error)
        STORE_DIR.mkdir(exist_ok=True)
        (STORE_DIR / "ragas_evaluation_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        raise RuntimeError("RAGAS could not run. Configure a supported LLM and embedding judge, then retry.") from error

STORE_DIR.mkdir(exist_ok=True)
(STORE_DIR / "ragas_evaluation_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
