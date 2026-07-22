"""Build an Obsidian-compatible linked risk wiki from reviewed corpus evidence."""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = next(path for path in HERE.parents if (path / "rag_gemini_runtime.py").exists())
sys.path.insert(0, str(ROOT))
from rag_gemini_runtime import load_index

WIKI = ROOT / "risk_wiki"
RISK_PATTERNS = {
    "Rủi ro tín dụng": r"rủi ro tín dụng|không trả được nợ|nợ xấu",
    "Rủi ro tuân thủ": r"tuân thủ|vi phạm|không được phép",
    "Rủi ro rửa tiền": r"rửa tiền|tài trợ khủng bố",
    "Rủi ro sử dụng vốn": r"sử dụng vốn sai|mục đích sử dụng vốn|kiểm tra.*sử dụng vốn",
}


def safe_name(name: str) -> str:
    return re.sub(r"[<>:\"/\\|?*]", "-", name)


evidence: dict[str, list[dict]] = defaultdict(list)
for record in load_index("foundation"):
    for risk, pattern in RISK_PATTERNS.items():
        if re.search(pattern, record["text"], re.IGNORECASE):
            evidence[risk].append(record)

WIKI.mkdir(exist_ok=True)
links = []
for risk, hits in evidence.items():
    filename = safe_name(risk)
    links.append(f"- [[{filename}]] — {len(hits)} đoạn bằng chứng")
    sources = sorted({hit["source"] for hit in hits})
    body = [f"# {risk}", "", "## Văn bản liên quan", *[f"- [[{source}]]" for source in sources], "", "## Bằng chứng"]
    for hit in hits[:20]:
        preview = " ".join(hit["text"].split())[:500].rstrip()
        body.extend(["", f"### {hit['source']} · chunk {hit['chunk_id']}", preview])
    (WIKI / f"{filename}.md").write_text("\n".join(body) + "\n", encoding="utf-8")

(WIKI / "Risk Wiki.md").write_text("# Risk Wiki\n\n" + "\n".join(links) + "\n", encoding="utf-8")
print(f"Built {len(links)} linked risk profiles in {WIKI}")
