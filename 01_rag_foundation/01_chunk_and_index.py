import sys
from pathlib import Path
HERE = Path(globals().get("__file__", Path.cwd())).resolve()
PROJECT_ROOT = next(p for p in (HERE.parent, *HERE.parents, Path.cwd(), Path.cwd() / "RAG_Demo_Labs") if (p / "rag_gemini_runtime.py").exists())
sys.path.insert(0, str(PROJECT_ROOT))
from rag_gemini_runtime import build_or_load_index, chunk_document, markdown_files
import argparse
parser = argparse.ArgumentParser(description="Giai đoạn 1: chia Markdown và tạo chỉ mục embedding Gemini")
parser.add_argument("--rebuild", action="store_true")
parser.add_argument("--dry-run", action="store_true", help="Hiển thị nguồn/số đoạn mà không gọi Gemini")
args = parser.parse_args()
if args.dry_run:
    plan = {path.name: len(chunk_document(path)) for path in markdown_files()}
    print("Kế hoạch chia đoạn:", plan, "| tổng:", sum(plan.values()))
    raise SystemExit(0)
records = build_or_load_index("foundation", force=args.rebuild)
print(f"Đã lập chỉ mục {len(records)} đoạn vào storage/foundation.json")
print("Nguồn:", sorted({r['source'] for r in records}))
