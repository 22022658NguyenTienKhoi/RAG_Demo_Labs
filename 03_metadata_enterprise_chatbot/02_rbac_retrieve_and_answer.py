import sys
from pathlib import Path
HERE = Path(globals().get("__file__", Path.cwd())).resolve()
PROJECT_ROOT = next(p for p in (HERE.parent, *HERE.parents, Path.cwd(), Path.cwd() / "RAG_Demo_Labs") if (p / "rag_gemini_runtime.py").exists())
sys.path.insert(0, str(PROJECT_ROOT))
import argparse, json
from datetime import datetime
from pathlib import Path
from rag_gemini_runtime import ROOT, STORE_DIR, load_index, retrieve, infer
ROLE_CLEARANCE={
    'business_user': {'public'},
    'credit_officer': {'public','internal','confidential'},
    'compliance': {'public','internal','confidential','restricted'},
    'internal_auditor': {'public','internal','confidential','restricted'},
}
catalog_path = STORE_DIR / 'metadata_catalog.json'
if not catalog_path.exists(): raise RuntimeError('Chưa có danh mục metadata. Hãy chạy 01_build_metadata_catalog.py trước.')
CATALOG = json.loads(catalog_path.read_text(encoding='utf-8'))
if any('classification' not in item or 'allowed_roles' not in item for item in CATALOG.values()):
    raise RuntimeError('Danh mục metadata dùng schema cũ. Hãy chạy lại 01_build_metadata_catalog.py.')
def metadata(r):
    base = CATALOG[r['source']]
    return {**base, 'chunk_id':r['chunk_id']}
parser=argparse.ArgumentParser(description='Giai đoạn 2: truy xuất có lọc RBAC và suy luận Gemini')
parser.add_argument('--ask',required=True); parser.add_argument('--role',choices=ROLE_CLEARANCE,default='internal_auditor'); args=parser.parse_args()
all_records=[{**r,'metadata':metadata(r)} for r in load_index('foundation')]
records=[r for r in all_records if args.role in r['metadata']['allowed_roles'] and r['metadata']['classification'] in ROLE_CLEARANCE[args.role]]
denied=sorted({r['source'] for r in all_records if r not in records})
print(f"Vai trò RBAC: {args.role} | tài liệu được phép: {sorted({r['source'] for r in records})}")
if denied: print(f"RBAC loại trước khi truy xuất: {denied}")
hits=retrieve(args.ask,records,top_k=5); STORE_DIR.mkdir(exist_ok=True)
with (STORE_DIR/'audit_log.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps({'time':datetime.now().isoformat(timespec='seconds'),'role':args.role,'question':args.ask,'sources':[h['source'] for h in hits]},ensure_ascii=False)+'\n')
for h in hits: print(h['metadata'])
print('\nCâu trả lời Gemini:\n',infer(args.ask,hits,f'Vai trò người yêu cầu: {args.role}. Tuân thủ metadata và trích dẫn mọi khẳng định.'))
