import pandas as pd
import streamlit as st

from flood_ui import (
    FRIENDLY, LEVELS, SAMPLE_CSV_PATH, actual_next, advisory_props, cached_explain, cached_predict, decision_steps,
    drivers, ec_day_bars, ec_push_bars, ec_trends, impact_tables, load_data, load_predictions, load_system,
    model_scores, test_period, week_days, window_ending,
)
from fs_components import living_advisory, reason_cards, week_strip

system = load_system()
df = load_data()
preds = load_predictions()
first_day, last_day = df["date"].iloc[system.window_days - 1].date(), df["date"].iloc[-1].date()
test_start, test_end = test_period()

if "day" in st.query_params:  # deep link, e.g. ?day=2024-08-20
    st.session_state.day = pd.Timestamp(st.query_params["day"]).date()
    del st.query_params["day"]
st.session_state.setdefault("day", test_end)
st.session_state.setdefault("source", "Dataset")

EXAMPLES = {  # one tap shows each risk level, plus the two kinds of mistake
    "Low risk": preds["Advisory"] == "LOW RISK",
    "Monitor": preds["Advisory"] == "MONITOR",
    "Flood watch": preds["Advisory"] == "FLOOD WATCH",
    "Flood warning": preds["Advisory"] == "FLOOD WARNING",
    "Missed flood": (preds["Actual"] == "Flood") & (preds["Prediction"] == "No Flood"),
    "False alarm": (preds["Actual"] == "No Flood") & (preds["Prediction"] == "Flood"),
}
EXAMPLES = {k: v for k, v in EXAMPLES.items() if v.any()}


def use_example():
    choice = st.session_state.example
    if choice:
        rows = preds[EXAMPLES[choice]]
        st.session_state.day = rows["today"].iloc[len(rows) // 2].date()
        st.session_state.source = "Dataset"
    st.session_state.example = None


st.title("Check a day", icon=":material/radar:")
st.caption("Pick a day: FloodSense reads that day and the 6 before it, then forecasts whether **the next day** floods, and why.")

left, right = st.columns([1, 2.6], gap="large")
with left:
    with st.container(border=True):
        source = st.segmented_control("Data", ["Dataset", "My own file"], key="source", required=True,
                                      label_visibility="collapsed")
        window, actual = None, None
        if source == "Dataset":
            day = st.date_input("Today is", min_value=first_day, max_value=last_day, key="day", format="DD/MM/YYYY")
            st.pills("Jump to an example", list(EXAMPLES), key="example", on_change=use_example)
            if test_start <= day <= test_end:
                st.badge("Unseen test period", color="green", icon=":material/verified:")
            else:
                st.badge("Training period", color="gray", icon=":material/history:")
            window, actual = window_ending(df, day), actual_next(df, day)
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
        st.info("Upload a CSV with 7 consecutive days to get tomorrow's forecast.", icon=":material/upload_file:")
        st.stop()
    try:
        result = cached_predict(str(day)) if source == "Dataset" else system.predict_window(window)
    except Exception as exc:
        st.error(str(exc), title="This data can't be used", icon=":material/block:")
        st.caption("FloodSense refuses incomplete or inconsistent data instead of guessing.")
        st.stop()
    window = system.validate_window(window)
    feats, days = cached_explain(str(day)) if source == "Dataset" else impact_tables(system, window)
    living_advisory(**advisory_props(result, df, window, actual,
                                     f"Forecast for {result['for_date']:%A %d %B %Y}",
                                     system.thresholds["sys"]), key="advisory")

reason_col, week_col = st.columns([1, 2.6], gap="large")
with reason_col:
    reason_cards(drivers(feats, window, df), title="Why · biggest pushes", key="reasons")
with week_col:
    st.markdown("**The 7 days the AI read**")
    week_strip(week_days(window, df, system.flood_line), LEVELS[result["advisory"]]["hex"], key="week")

why_tab, how_tab, trend_tab, data_tab = st.tabs(
    [":material/psychology: Why", ":material/account_tree: How it decided", ":material/show_chart: Trends",
     ":material/table: Numbers"])
with why_tab:
    a, b = st.columns([1.4, 1], gap="large")
    with a:
        st.markdown("**Which readings pushed tomorrow's risk**")
        top = feats.head(8)
        st.echarts_chart(ec_push_bars(top["name"].tolist(), (top["impact"] * 100).tolist(),
                                      "points · red raises, blue lowers"), height=320)
    with b:
        st.markdown("**Which days mattered**")
        st.echarts_chart(ec_day_bars(days["day"].tolist(), (days["impact"] * 100).tolist()), height=280)
    st.caption("Each bar: how much tomorrow's combined score changes if that reading (or day) is replaced by a typical value.")
with how_tab:
    a, b = st.columns(2, gap="large")
    with a:
        st.markdown("**1 · Two AI models score tomorrow**")
        model_scores(system, result)
    with b:
        st.markdown("**2 · Rules turn the score into an advisory**")
        decision_steps(system, result)
with trend_tab:
    st.echarts_chart(ec_trends(window, system.rule_levels, system.flood_line), height=260)
    st.caption(f"Red dot = today · red dashed line = the flood line ({system.flood_line:.0f} km² of water) · "
               "orange dashed = warning levels")
with data_tab:
    table = window[["date"] + list(system.env_features)].rename(columns=FRIENDLY)
    table["date"] = table["date"].dt.strftime("%a %d %b %Y")
    st.dataframe(table, hide_index=True)
