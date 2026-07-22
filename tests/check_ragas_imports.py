"""Verify the pinned optional RAGAS/Gemini adapter imports."""
from ragas import evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

assert all((evaluate, LangchainEmbeddingsWrapper, LangchainLLMWrapper, ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings))
print("pinned RAGAS adapters: ok")
