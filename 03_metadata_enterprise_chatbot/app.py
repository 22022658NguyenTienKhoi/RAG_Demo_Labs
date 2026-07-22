"""Streamlit interface for all four enterprise RAG use cases."""
from __future__ import annotations

import os

import requests
import streamlit as st

API = os.getenv("RAG_API_URL", "http://localhost:8000").rstrip("/")
ROLES = ["business_user", "credit_officer", "compliance", "internal_auditor"]
DOCUMENTS = ["TT_02_2023_NHNN.md", "TT_06_2023_NHNN.md", "TT_39_2016_NHNN.md", "chinh_sach_tin_dung.md"]

st.set_page_config(page_title="Enterprise RAG", layout="wide")
st.title("Enterprise RAG Chatbot")
role = st.selectbox("Vai trò", ROLES)


def call(endpoint: str, payload: dict, result_field: str) -> None:
    try:
        response = requests.post(f"{API}{endpoint}", json={**payload, "role": role}, timeout=120)
        if response.status_code >= 400:
            st.error(response.json().get("detail", response.text))
            return
        result = response.json()
        st.markdown(result[result_field])
        st.caption(f"Cache hit: {result.get('cache_hit', False)}")
        st.json({"grounding": result.get("grounding_check"), "citations": result.get("citations", [])})
    except requests.RequestException as error:
        st.error(f"Không thể kết nối API tại {API}: {error}")


lookup, gap, compliance, checklist = st.tabs(["Tra cứu", "Gap analysis", "Compliance checker", "Audit checklist"])

with lookup:
    question = st.text_area("Câu hỏi", key="lookup_question")
    if st.button("Tra cứu") and question.strip():
        call("/ask", {"question": question}, "answer")

with gap:
    internal = st.selectbox("Văn bản nội bộ", DOCUMENTS, index=3)
    regulation = st.selectbox("Văn bản quy định", DOCUMENTS, index=2)
    question = st.text_area("Trọng tâm so sánh", value="Xác định nghĩa vụ chưa được phản ánh đầy đủ.", key="gap_question")
    if st.button("Phân tích khoảng trống"):
        call("/compliance/gap-analysis", {"question": question, "internal_document": internal, "regulatory_document": regulation}, "analysis")

with compliance:
    document = st.selectbox("Tài liệu cần kiểm tra", DOCUMENTS, key="compliance_document")
    requirement = st.text_area("Yêu cầu kiểm soát", key="requirement")
    question = st.text_area("Ghi chú", value="Đánh giá đầy đủ và nêu phần còn thiếu.", key="compliance_question")
    if st.button("Kiểm tra tuân thủ") and requirement.strip():
        call("/compliance/check", {"question": question, "document": document, "requirement": requirement}, "assessment")

with checklist:
    scope = st.text_input("Phạm vi kiểm toán")
    question = st.text_area("Yêu cầu bổ sung", value="Ưu tiên rủi ro cao và dẫn nguồn cho từng thủ tục.", key="checklist_question")
    if st.button("Tạo checklist") and scope.strip():
        call("/audit/checklist", {"question": question, "audit_scope": scope}, "checklist")
