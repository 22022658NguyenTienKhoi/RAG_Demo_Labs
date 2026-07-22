"""Validate and run a RAGAS evaluation for the enterprise RAG dataset."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve(); ROOT = HERE.parents[1]; sys.path.insert(0, str(ROOT))
from rag_core.runtime import STORE_DIR

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
        import os
        from datasets import Dataset
        from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
        from ragas import evaluate
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from ragas.llms import LangchainLLMWrapper
        from ragas.metrics import context_precision, context_recall, faithfulness, answer_relevancy
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
        if not os.getenv("GEMINI_API_KEY"):
            raise RuntimeError("GEMINI_API_KEY is required for the RAGAS judges")
        api_key = os.environ["GEMINI_API_KEY"]
        judge = LangchainLLMWrapper(ChatGoogleGenerativeAI(model=os.getenv("RAGAS_GEMINI_MODEL", "gemini-2.5-flash"), temperature=0, google_api_key=api_key))
        judge_embeddings = LangchainEmbeddingsWrapper(GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", google_api_key=api_key))
        result = evaluate(Dataset.from_list(rows), metrics=[context_precision, context_recall, faithfulness, answer_relevancy], llm=judge, embeddings=judge_embeddings)
        report["scores"] = {key: float(value) for key, value in result.to_pandas().mean(numeric_only=True).to_dict().items()}
        report["status"] = "completed"
    except Exception as error:
        report["status"] = "failed"
        report["error"] = str(error)
        STORE_DIR.mkdir(exist_ok=True)
        (STORE_DIR / "ragas_evaluation_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        raise RuntimeError("RAGAS could not run with the configured Gemini judges; see the report error and retry.") from error

STORE_DIR.mkdir(exist_ok=True)
(STORE_DIR / "ragas_evaluation_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
