"""FloodSense website entry point.

Run with:  streamlit run streamlit_app.py
"""
import streamlit as st

st.set_page_config(page_title="FloodSense", page_icon=":material/water_drop:", layout="wide")

from flood_ui import global_style  # noqa: E402  (after set_page_config)
from fs_components import ambient_background  # noqa: E402

global_style()
ambient_background()

page = st.navigation(
    [
        st.Page("app_pages/home.py", title="Home", icon=":material/home:", default=True),
        st.Page("app_pages/check_day.py", title="Check a day", icon=":material/radar:"),
        st.Page("app_pages/what_if.py", title="What-if lab", icon=":material/tune:"),
        st.Page("app_pages/how_it_works.py", title="How it works", icon=":material/account_tree:"),
        st.Page("app_pages/trust.py", title="Can I trust it?", icon=":material/verified_user:"),
    ],
    position="top",
)
page.run()

st.divider()
st.caption(":material/info: Educational prototype, not an official flood-warning service.")
