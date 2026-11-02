import streamlit as st
from flood_ui import load_run_summary, load_test_predictions

summary = load_run_summary()
preds = load_test_predictions()
n_test = summary["test_rows"]
n_flood = int((preds["Actual"] == "Flood").sum())
caught = n_flood - summary["false_negatives"]

st.badge("Practical 10 · Validation, explanation & deployment", icon=":material/verified:", color="primary")
st.title("FloodSense: can AI recognise a flood day?")
st.markdown(
    "This website lets you **use and inspect** an AI system that looks at **7 days of weather and satellite "
    "readings** and decides whether the **last of those days** is a flood day. "
    "It combines three kinds of intelligence: a **deep-learning** model that reads the week as a sequence, "
    "a **machine-learning** model that makes a second opinion, and a set of **transparent rules** that turn "
    "the scores into a clear advisory such as *Low risk* or *Flood warning*."
)

with st.container(horizontal=True):
    st.page_link("app_pages/check_day.py", label="Try it now: check a day", icon=":material/radar:")
    st.page_link("app_pages/results.py", label="See how accurate it is", icon=":material/fact_check:")

st.space("small")
st.subheader("Tested on days it had never seen", icon=":material/insights:")
with st.container(horizontal=True):
    st.metric("Unseen test days", n_test, border=True, help="Days from March–September 2025 kept aside and never used for training or tuning.")
    st.metric("Correct decisions", f"{summary['test_accuracy']:.1%}", border=True, help="Share of the 204 test days where Flood / No Flood was right.")
    st.metric("Floods caught", f"{caught} of {n_flood}", border=True, help="Real flood days the system recognised (recall).")
    st.metric("False alarms", summary["false_positives"], border=True, help="Normal days wrongly flagged as flood days.")
    st.metric("Safety tests passed", f"{summary['input_validation_tests_passed']} / {summary['input_validation_tests_total']}", border=True, help="Bad inputs (missing days, duplicates…) that the system correctly refused.")

st.space("small")
st.subheader("How to use this website", icon=":material/route:")
c1, c2, c3 = st.columns(3)
with c1.container(border=True, height="stretch"):
    st.markdown("##### :material/looks_one: Pick a day")
    st.markdown("Open **Check a day** and choose any date from the dataset, or upload your own 7-day CSV file.")
with c2.container(border=True, height="stretch"):
    st.markdown("##### :material/looks_two: Get the decision")
    st.markdown("Press **Check flood risk**. You get a coloured advisory, the flood score, and whether it was right.")
with c3.container(border=True, height="stretch"):
    st.markdown("##### :material/looks_3: Understand why")
    st.markdown("See which readings and which days pushed the decision, and which safety rules fired.")

st.space("small")
st.subheader("What each page shows", icon=":material/map:")
pages = [
    ("app_pages/check_day.py", "Check a day", ":material/radar:", "Run the full AI system on any 7-day window and get an explained result."),
    ("app_pages/what_if.py", "What-if lab", ":material/tune:", "Move sliders (more rain, wetter soil…) and watch the decision change live."),
    ("app_pages/results.py", "Test results", ":material/fact_check:", "Accuracy, caught floods, false alarms and month-by-month stability on unseen data."),
    ("app_pages/explainability.py", "Why the AI decides", ":material/psychology:", "Which inputs matter most overall, and the exact rules behind each advisory."),
    ("app_pages/safety_tests.py", "Input safety tests", ":material/shield:", "Live tests proving the system refuses broken or incomplete data."),
    ("app_pages/responsible_ai.py", "Responsible AI", ":material/balance:", "Ethics, fairness, bias, limitations, and why this is not a real warning service."),
]
cols = st.columns(3)
for i, (path, title, icon, desc) in enumerate(pages):
    with cols[i % 3].container(border=True, height="stretch"):
        st.page_link(path, label=title, icon=icon)
        st.caption(desc)

st.space("small")
st.warning(
    "This is a classroom project built on an educational dataset. It classifies the **same day** at the end of a "
    "7-day window. It does **not** forecast tomorrow, and it must **never** be used for real emergency decisions.",
    title="Important limitation",
    icon=":material/report:",
)
