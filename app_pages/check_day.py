import pandas as pd
import streamlit as st

from flood_ui import (
    ENVIRONMENTAL_FEATURES, FEATURE_HELP, FRIENDLY_NAMES, SAMPLE_CSV_PATH,
    actual_label, contribution_chart, day_chart, decision_path, explain_window,
    load_dataset, load_system, load_test_predictions, percentile_of, plain_reason,
    rule_rows, show_advisory, show_scores, typical_wording, window_ending, ADVISORY_STYLE,
)

system = load_system()
df = load_dataset()
preds = load_test_predictions()
test_start, test_end = preds["date"].min().date(), preds["date"].max().date()
data_start = df["date"].iloc[system.window_days - 1].date()
data_end = df["date"].iloc[-1].date()

if "day" not in st.session_state:
    st.session_state.day = test_end
if "source" not in st.session_state:
    st.session_state.source = "Pick a date"


def pick_example(kind: str) -> None:
    p = preds
    if kind == "flood":
        rows = p[(p["Actual"] == "Flood") & (p["Integrated prediction"] == "Flood")]
    elif kind == "missed":
        rows = p[(p["Actual"] == "Flood") & (p["Integrated prediction"] == "No Flood")]
    elif kind == "alarm":
        rows = p[(p["Actual"] == "No Flood") & (p["Integrated prediction"] == "Flood")]
    else:
        rows = p[(p["Actual"] == "No Flood") & (p["AI advisory"] == "LOW RISK")]
    st.session_state.day = rows["date"].iloc[len(rows) // 2].date()
    st.session_state.source = "Pick a date"


st.title("Check a day", icon=":material/radar:")
st.markdown(
    "Choose a day. The system reads that day **plus the 6 days before it** and decides whether the chosen day "
    "is a flood day. Then it explains its reasoning."
)

# ---------------------------------------------------------------- Step 1
st.subheader("Step 1 · Choose the data", icon=":material/looks_one:")
with st.container(border=True):
    source = st.segmented_control(
        "Where should the 7 days of readings come from?",
        ["Pick a date", "Upload my own CSV"],
        required=True, key="source",
    )

    window, actual = None, None
    if source == "Pick a date":
        st.markdown("**Not sure what to pick? Try an example:**")
        with st.container(horizontal=True):
            st.button("A flood the system caught", icon=":material/flood:", on_click=pick_example, args=("flood",))
            st.button("A calm, normal day", icon=":material/sunny:", on_click=pick_example, args=("calm",))
            st.button("A flood it missed", icon=":material/report:", on_click=pick_example, args=("missed",))
            st.button("A false alarm", icon=":material/notifications_off:", on_click=pick_example, args=("alarm",))
        c1, c2 = st.columns([1, 2], vertical_alignment="bottom")
        day = c1.date_input("Day to check", min_value=data_start, max_value=data_end, key="day", format="DD/MM/YYYY")
        is_unseen = test_start <= day <= test_end
        if is_unseen:
            c2.success("This day is in the **unseen test period**: the AI never learned from it.",
                       icon=":material/new_releases:")
        else:
            c2.info(f"This day was part of the training/tuning data. For an honest test, pick a day between "
                    f"{test_start:%d %b %Y} and {test_end:%d %b %Y}.", icon=":material/history:")
        window = window_ending(df, day, system.window_days)
        actual = actual_label(df, day)
    else:
        st.markdown(
            "Upload a CSV with **exactly 7 consecutive days** (one row per day) and the 13 reading columns. "
            "The **last row is the day being checked**. Easiest way: download the template, edit the numbers, upload it."
        )
        st.download_button("Download the template CSV", SAMPLE_CSV_PATH.read_bytes(),
                           file_name="sample_7_day_input.csv", mime="text/csv", icon=":material/download:")
        uploaded = st.file_uploader("Upload your 7-day CSV", type=["csv"])
        with st.expander("Which columns are required?", icon=":material/help:"):
            st.table(pd.DataFrame(
                [{"Column": "date", "Meaning": "Date in YYYY-MM-DD format"}] +
                [{"Column": f, "Meaning": f"{FRIENDLY_NAMES[f]}: {FEATURE_HELP[f]}"} for f in ENVIRONMENTAL_FEATURES]
            ), hide_index=True)
        if uploaded is not None:
            try:
                window = pd.read_csv(uploaded)
            except Exception as exc:
                st.error(f"That file could not be read as a CSV: {exc}", icon=":material/error:")

if window is None:
    st.stop()

# ---------------------------------------------------------------- Step 2
st.subheader("Step 2 · Look at the week's readings", icon=":material/looks_two:")
try:
    clean = system.validate_window(window)
except Exception as exc:
    st.error(f"{exc}", title="This input can't be used", icon=":material/block:")
    st.caption("The system refuses incomplete or inconsistent data instead of guessing. "
               "See the *Input safety tests* page for all the checks.")
    st.stop()

st.caption(f"From **{clean['date'].iloc[0]:%a %d %b %Y}** to **{clean['date'].iloc[-1]:%a %d %b %Y}** "
           "(the last day is the one being checked). Small charts show the 7-day trend; the big number is the last day.")
key_features = ["precipitation", "soil_moisture", "water_area_km2", "water_area_change"]
with st.container(horizontal=True):
    for f in key_features:
        series = clean[f].astype(float)
        last = series.iloc[-1]
        level = typical_wording(percentile_of(df, f, last)) if pd.notna(last) else "missing"
        st.metric(FRIENDLY_NAMES[f], f"{last:,.3g}" if pd.notna(last) else "n/a",
                  delta=f"{level} for this area", delta_color="off", delta_arrow="off",
                  chart_data=series.fillna(0).tolist(), chart_type="area",
                  help=FEATURE_HELP[f], border=True)
with st.expander("See all 13 readings for the 7 days", icon=":material/table:"):
    table = clean[["date"] + ENVIRONMENTAL_FEATURES].rename(columns=FRIENDLY_NAMES)
    table["date"] = table["date"].dt.strftime("%a %d %b %Y")
    st.dataframe(table, hide_index=True, alt="Seven days of environmental readings")
    st.caption("The real Flood/No Flood label is deliberately hidden from the AI.")

# ---------------------------------------------------------------- Step 3
st.subheader("Step 3 · Run the AI system", icon=":material/looks_3:")
signature = (str(clean["date"].iloc[-1].date()), float(clean[ENVIRONMENTAL_FEATURES].sum(numeric_only=True).sum()))
if st.button("Check flood risk", type="primary", icon=":material/play_arrow:", width="stretch"):
    with st.spinner("Running LSTM → Random Forest → rule engine…"):
        output = system.predict_window(window)
        _, feat, days = explain_window(system, window)
    st.session_state.result = {"signature": signature, "output": output, "feat": feat, "days": days}

result = st.session_state.get("result")
if not result or result["signature"] != signature:
    st.caption("Press the button to see the decision and its explanation.")
    st.stop()

output, feat, days = result["output"], result["feat"], result["days"]

st.space("small")
st.header("Result", icon=":material/assignment_turned_in:")
show_advisory(output, actual if source == "Pick a date" else None)

left, right = st.columns([1, 1], gap="large")
with left:
    st.subheader("How sure are the models?", icon=":material/speed:")
    show_scores(system, output)
with right:
    st.subheader("Safety rules (checked on the last day)", icon=":material/rule:")
    rules = rule_rows(system, df, clean, output)
    for _, r in rules.iterrows():
        icon = ":material/error:" if r["Triggered"] else ":material/check_circle:"
        color = "orange" if r["Triggered"] else "green"
        state = "TRIGGERED" if r["Triggered"] else "not triggered"
        today = r["Today's value"]
        value = "missing" if pd.isna(today) else f"{today:,.3g}"
        st.markdown(f":{color}[{icon} **{r['Safety rule']}: {state}**]  \n"
                    f"Checks whether {r['Plain meaning'][0].lower() + r['Plain meaning'][1:]}. "
                    f"Last day: **{value}** · trigger: **{r['Trigger level']:,.3g}** "
                    f":gray[(higher than {r['Trigger is higher than']})]")

st.subheader("Why did it decide this?", icon=":material/psychology:")
st.markdown(plain_reason(output, feat))
c1, c2 = st.columns([3, 2], gap="large")
with c1:
    st.markdown("**Which readings mattered** (top 10)")
    st.altair_chart(contribution_chart(feat), alt="Bar chart of how much each reading changed the flood score")
with c2:
    st.markdown("**Which days mattered**")
    st.altair_chart(day_chart(days), alt="Bar chart of how much each of the 7 days changed the flood score")
with st.expander("How is this explanation calculated?", icon=":material/science:"):
    st.markdown(
        "We use **occlusion analysis**, a standard model-interpretation technique. "
        "For each reading, we replace it with its *typical* (training-average) value for all 7 days, run the "
        "models again, and see how much the flood score changes. If hiding a reading makes the score drop, that "
        "reading was pushing **towards Flood** (red). If the score rises, it was pushing **towards No Flood** (blue). "
        "The same is done for each whole day. Nothing is retrained; we only ask the saved model *what if*."
    )

with st.expander("Step-by-step: how the advisory was chosen", icon=":material/account_tree:", expanded=False):
    for step in decision_path(system, output):
        chosen = step.get("chosen", False)
        name = ADVISORY_STYLE[step["advisory"]]["headline"]
        if chosen:
            st.markdown(f":{ADVISORY_STYLE[step['advisory']]['color']}[:material/arrow_forward: **{step['question']} "
                        f"Yes → {name}**]")
            break
        st.markdown(f":gray[:material/close: {step['question']} No]")
    st.caption("The rules are checked from the most severe to the calmest; the first one that says *yes* wins.")

st.caption(output["task_note"])
