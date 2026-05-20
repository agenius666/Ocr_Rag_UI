import streamlit as st

st.set_page_config(page_title="OCR RAG UI", layout="wide")

from ocr_rag_app.main import run_app


run_app()
