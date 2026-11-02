"""Practical 10 website entry point.

Run with:  streamlit run streamlit_app.py   (app.py wraps this file for Vercel)
"""
import streamlit as st

st.set_page_config(
    page_title="FloodSense · Practical 10",
    page_icon=":material/water_drop:",
    layout="wide",
)

home = st.Page("app_pages/home.py", title="Start here", icon=":material/home:", default=True)
check = st.Page("app_pages/check_day.py", title="Check a day", icon=":material/radar:")
whatif = st.Page("app_pages/what_if.py", title="What-if lab", icon=":material/tune:")
results = st.Page("app_pages/results.py", title="Test results", icon=":material/fact_check:")
explain = st.Page("app_pages/explainability.py", title="Why the AI decides", icon=":material/psychology:")
safety = st.Page("app_pages/safety_tests.py", title="Input safety tests", icon=":material/shield:")
ethics = st.Page("app_pages/responsible_ai.py", title="Responsible AI", icon=":material/balance:")
about = st.Page("app_pages/how_it_works.py", title="How it's built", icon=":material/account_tree:")
viva = st.Page("app_pages/viva.py", title="Glossary & viva", icon=":material/school:")

page = st.navigation(
    {
        "": [home],
        "Use the system": [check, whatif],
        "Validation evidence": [results, explain, safety, ethics],
        "Learn": [about, viva],
    }
)

with st.sidebar:
    st.caption(
        ":material/info: **Educational prototype.** Not an official flood-warning service. "
        "CELBC710 · Computational Intelligence Laboratory · Practical 10"
    )

page.run()
