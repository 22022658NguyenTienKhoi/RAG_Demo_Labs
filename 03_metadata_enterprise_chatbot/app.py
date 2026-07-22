import os
import streamlit as st
import requests

st.set_page_config(page_title="Enterprise RAG", layout="wide")
st.title("Enterprise RAG Chatbot")
role = st.selectbox("Role", ["business_user", "credit_officer", "compliance", "internal_auditor"])
question = st.text_area("Question")
if st.button("Ask") and question.strip():
    url = os.getenv("RAG_API_URL", "http://api:8000") + "/ask"
    response = requests.post(url, json={"question": question, "role": role}, timeout=90)
    response.raise_for_status(); result = response.json()
    st.write(result["answer"]); st.json(result["citations"])
