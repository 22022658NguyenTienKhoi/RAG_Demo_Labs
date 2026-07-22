"""Kiểm tra RBAC ngoại tuyến: minh họa vai trò nào được tìm kiếm tài liệu nào."""
import json
import sys
from pathlib import Path

HERE = Path(globals().get("__file__", Path.cwd())).resolve()
PROJECT_ROOT = HERE.parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from rag_core.runtime import STORE_DIR

CLEARANCE={
    'business_user': {'public'},
    'credit_officer': {'public','internal','confidential'},
    'compliance': {'public','internal','confidential','restricted'},
    'internal_auditor': {'public','internal','confidential','restricted'},
}
catalog_path=STORE_DIR/'metadata_catalog.json'
if not catalog_path.exists(): raise RuntimeError('Hãy chạy 01_build_metadata_catalog.py trước.')
catalog=json.loads(catalog_path.read_text(encoding='utf-8'))
if any('classification' not in item or 'allowed_roles' not in item for item in catalog.values()):
    raise RuntimeError('Danh mục metadata dùng schema cũ. Hãy chạy lại 01_build_metadata_catalog.py.')
print('Ma trận quyền truy cập RBAC (CHO PHÉP / TỪ CHỐI):')
for role, levels in CLEARANCE.items():
    print(f'\n{role}:')
    for source, meta in catalog.items():
        allowed=role in meta['allowed_roles'] and meta['classification'] in levels
        reason='vai trò và mức phân loại cho phép truy cập' if allowed else f"bị chặn: classification={meta['classification']}, allowed_roles={meta['allowed_roles']}"
        print(f"  {'CHO PHÉP' if allowed else 'TỪ CHỐI'} | {source} | {reason}")
