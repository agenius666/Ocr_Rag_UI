import streamlit as st
from importlib import import_module

st.set_page_config(page_title="OCR RAG UI", layout="wide")

main_module = import_module("ocr_rag_app.main")
app_runner = getattr(main_module, "run_app", None) or getattr(main_module, "main", None)

if callable(app_runner):
    app_runner()
