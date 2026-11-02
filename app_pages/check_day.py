import pandas as pd
import streamlit as st

from flood_ui import (
    FRIENDLY, SAMPLE_CSV_PATH, actual_label, advisory_banner, cached_explain, day_bars, decision_steps,
    drivers, load_data, load_predictions, load_system, model_scores, risk_gauge, shap_bars, shap_tables,
    show_drivers, test_period, week_chart, window_ending,
)

system = load_system()
df = load_data()
preds = load_predictions()
first_day, last_day = df["date"].iloc[system.window_days - 1].date(), df["date"].iloc[-1].date()
test_start, test_end = test_period()

if "day" in st.query_params:  # deep link, e.g. ?day=2025-05-07
    st.session_state.day = pd.Timestamp(st.query_params["day"]).date()
    del st.query_params["day"]
st.session_state.setdefault("day", test_end)
st.session_state.setdefault("source", "Dataset")

EXAMPLES = {
    "Caught flood": (preds["Actual"] == "Flood") & (preds["Prediction"] == "Flood"),
    "Calm day": (preds["Actual"] == "No Flood") & (preds["Advisory"] == "LOW RISK"),
    "Missed flood": (preds["Actual"] == "Flood") & (preds["Prediction"] == "No Flood"),
    "False alarm": (preds["Actual"] == "No Flood") & (preds["Prediction"] == "Flood"),
}


def use_example():
    choice = st.session_state.example
    if choice:
        rows = preds[EXAMPLES[choice]]
        st.session_state.day = rows["date"].iloc[len(rows) // 2].date()
        st.session_state.source = "Dataset"
    st.session_state.example = None


st.title("Check a day", icon=":material/radar:")
st.caption("Pick a day: FloodSense reads that day and the 6 before it, then tells you the flood risk and why.")

left, right = st.columns([1, 2.3], gap="large")

with left:
    with st.container(border=True):
        source = st.segmented_control("Data", ["Dataset", "My own file"], key="source",
                                      required=True, label_visibility="collapsed")
        window, actual = None, None
        if source == "Dataset":
            day = st.date_input("Day to check", min_value=first_day, max_value=last_day, key="day", format="DD/MM/YYYY")
            st.pills("Try an example", list(EXAMPLES), key="example", on_change=use_example)
            if test_start <= day <= test_end:
                st.badge("Unseen test day", color="green", icon=":material/verified:")
            else:
                st.badge("Training day", color="gray", icon=":material/history:")
            window, actual = window_ending(df, day), actual_label(df, day)
        else:
            uploaded = st.file_uploader("7 consecutive days, one row per day", type="csv")
            st.download_button("Download a template", SAMPLE_CSV_PATH.read_bytes(), "floodsense_template.csv",
                               "text/csv", icon=":material/download:", width="stretch")
            if uploaded is not None:
                try:
                    window = pd.read_csv(uploaded)
                except Exception as exc:
                    st.error(f"Couldn't read that file: {exc}", icon=":material/error:")

with right:
    if window is None:
        st.info("Upload a CSV with 7 consecutive days to see the risk.", icon=":material/upload_file:")
        st.stop()
    try:
        result = system.predict_window(window)
    except Exception as exc:
        st.error(str(exc), title="This data can't be used", icon=":material/block:")
        st.caption("FloodSense refuses incomplete or inconsistent data instead of guessing.")
        st.stop()
    window = system.validate_window(window)
    feats, days = cached_explain(str(day)) if source == "Dataset" else shap_tables(system, window)

    advisory_banner(result, actual)
    g, r = st.columns([1.1, 1], gap="medium", vertical_alignment="center")
    g.plotly_chart(risk_gauge(result["score"], system.thresholds["sys"]), config={"displayModeBar": False})
    with r:
        show_drivers(drivers(feats, window, df))

week_tab, why_tab, how_tab, data_tab = st.tabs(
    [":material/show_chart: The week", ":material/psychology: Why", ":material/account_tree: How it decided",
     ":material/table: Numbers"])
with week_tab:
    st.plotly_chart(week_chart(window, system.rule_levels), config={"displayModeBar": False})
    st.caption("Red dot = the day being checked · dotted line = warning level for that reading")
with why_tab:
    a, b = st.columns([1.4, 1], gap="large")
    a.markdown("**Which readings pushed the risk**")
    a.plotly_chart(shap_bars(feats), config={"displayModeBar": False})
    b.markdown("**Which days mattered**")
    b.plotly_chart(day_bars(days), config={"displayModeBar": False})
    st.caption("Measured with SHAP: each reading's share of the deep-learning model's flood probability.")
with how_tab:
    a, b = st.columns(2, gap="large")
    with a:
        st.markdown("**1 · Two AI models score the week**")
        model_scores(system, result)
    with b:
        st.markdown("**2 · Rules turn scores into an advisory**")
        decision_steps(system, result)
with data_tab:
    table = window[["date"] + list(system.env_features)].rename(columns=FRIENDLY)
    table["date"] = table["date"].dt.strftime("%a %d %b %Y")
    st.dataframe(table, hide_index=True)
