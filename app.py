"""ASGI entry point used by Vercel (and any ASGI server such as uvicorn).

Vercel loads the top-level ``app`` variable from this file. The website itself
lives in streamlit_app.py.

Run locally with either:
    streamlit run streamlit_app.py
    uvicorn app:app --port 8501
"""
from pathlib import Path

import streamlit as st

app = st.App(str(Path(__file__).resolve().parent / "streamlit_app.py"))
