"""Shortcut so `streamlit run app.py` keeps working.

The website lives in streamlit_app.py (the file Streamlit Community Cloud runs).
"""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).resolve().parent / "streamlit_app.py"))
