import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from flood_ui import (
    ADVISORY_STYLE, RESULT_DIR, load_component_metrics, load_result_csv, load_system, load_test_predictions,
)

system = load_system()
preds = load_test_predictions()
actual = (preds["Actual"] == "Flood").astype(int).to_numpy()
pred = (preds["Integrated prediction"] == "Flood").astype(int).to_numpy()
tp = int(((actual == 1) & (pred == 1)).sum())
fn = int(((actual == 1) & (pred == 0)).sum())
fp = int(((actual == 0) & (pred == 1)).sum())
tn = int(((actual == 0) & (pred == 0)).sum())
n = len(preds)

st.title("Test results", icon=":material/fact_check:")
st.markdown(
    f"To check the system honestly, the last **{n} days** of the data "
    f"(**{preds['date'].min():%d %b %Y} – {preds['date'].max():%d %b %Y}**) were **kept aside**. "
    "The models never learned from them and no setting was tuned on them. "
    "Below is how the complete system (LSTM + Random Forest + rules) performed on those unseen days."
)

st.subheader("The scorecard", icon=":material/scoreboard:")
with st.container(horizontal=True):
    st.metric("Correct decisions (accuracy)", f"{(tp + tn) / n:.1%}", border=True,
              help="Out of every 100 days, how many got the right Flood / No Flood answer.")
    st.metric("Floods caught (recall)", f"{tp / (tp + fn):.1%}", border=True,
              help="Of all real flood days, the share the system recognised. Higher = fewer missed floods.")
    st.metric("Trust in a flood alert (precision)", f"{tp / (tp + fp):.1%}", border=True,
              help="When the system says Flood, how often it is really a flood.")
    st.metric("Balanced accuracy", f"{0.5 * (tp / (tp + fn) + tn / (tn + fp)):.1%}", border=True,
              help="Average of how well it does on flood days and on normal days, so the bigger class can't hide mistakes.")
    st.metric("F1-score", f"{2 * tp / (2 * tp + fp + fn):.3f}", border=True,
              help="One number that balances catching floods and avoiding false alarms (1.0 is perfect).")

st.markdown(
    f"**In plain words:** out of **{tp + fn} real flood days**, the system caught **{tp}** and missed **{fn}**. "
    f"Out of **{tn + fp} normal days**, it correctly stayed calm on **{tn}** and raised **{fp}** false alarms."
)

st.subheader("Where were the mistakes? (confusion matrix)", icon=":material/grid_view:")
left, right = st.columns([1, 1], gap="large")
with left:
    g1, g2 = st.columns(2)
    with g1.container(border=True):
        st.markdown(f":green[:material/task_alt: **Floods caught**]")
        st.markdown(f"## {tp}")
        st.caption("Real flood, said Flood (true positive)")
    with g2.container(border=True):
        st.markdown(f":red[:material/report: **Floods missed**]")
        st.markdown(f"## {fn}")
        st.caption("Real flood, said No Flood (false negative). The most dangerous error.")
    with g1.container(border=True):
        st.markdown(f":orange[:material/notifications_off: **False alarms**]")
        st.markdown(f"## {fp}")
        st.caption("Normal day, said Flood (false positive). Costly, erodes trust.")
    with g2.container(border=True):
        st.markdown(f":green[:material/check_circle: **Correctly calm**]")
        st.markdown(f"## {tn}")
        st.caption("Normal day, said No Flood (true negative)")
with right:
    cm = pd.DataFrame({
        "Real answer": ["Flood", "Flood", "No Flood", "No Flood"],
        "System said": ["Flood", "No Flood", "Flood", "No Flood"],
        "Days": [tp, fn, fp, tn],
    })
    base = alt.Chart(cm).encode(
        x=alt.X("System said:N", sort=["Flood", "No Flood"], axis=alt.Axis(orient="top", labelAngle=0)),
        y=alt.Y("Real answer:N", sort=["Flood", "No Flood"]),
    )
    heat = base.mark_rect(cornerRadius=8).encode(
        color=alt.Color("Days:Q", scale=alt.Scale(scheme="blues"), legend=None), tooltip=["Real answer", "System said", "Days"])
    text = base.mark_text(fontSize=28, fontWeight="bold").encode(
        text="Days:Q", color=alt.condition(alt.datum.Days > 60, alt.value("white"), alt.value("#0F2235")))
    st.altair_chart((heat + text).properties(height=300), alt="Confusion matrix of real vs predicted labels")

st.subheader("Flood score over the whole test period", icon=":material/timeline:")
st.caption("Each dot is one day. Red dots are days that really flooded. The dashed line is the Flood threshold: "
           "dots above it were called Flood. Red dots below the line are missed floods; blue dots above it are false alarms.")
tl = preds[["date", "Actual", "Integrated probability", "AI advisory"]].copy()
tl["Flood score"] = tl["Integrated probability"]
points = alt.Chart(tl).mark_circle(size=60, opacity=0.85).encode(
    x=alt.X("date:T", title=None),
    y=alt.Y("Flood score:Q", axis=alt.Axis(format="%"), scale=alt.Scale(domain=[0, 1])),
    color=alt.Color("Actual:N", title="What really happened",
                    scale=alt.Scale(domain=["Flood", "No Flood"], range=["#D93A3A", "#0B6BCB"]),
                    legend=alt.Legend(orient="bottom")),
    tooltip=[alt.Tooltip("date:T", format="%d %b %Y"), "Actual", alt.Tooltip("Flood score:Q", format=".1%"), "AI advisory"],
)
rule = alt.Chart(pd.DataFrame({"y": [system.system_threshold]})).mark_rule(strokeDash=[6, 4], color="#8C9AAB").encode(y="y:Q")
st.altair_chart((points + rule).properties(height=320).interactive(bind_y=False),
                alt="Daily integrated flood probability across the test period")

c1, c2 = st.columns(2, gap="large")
with c1:
    st.subheader("Does it work every month?", icon=":material/calendar_month:")
    st.caption("A basic stability check: performance should not collapse in any single month.")
    monthly = load_result_csv("task10_monthly_stability_check.csv")
    m = monthly.melt(id_vars=["Month"], value_vars=["Accuracy", "Flood recall"], var_name="Measure", value_name="Score")
    st.altair_chart(
        alt.Chart(m).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
            x=alt.X("Month:N", title=None, axis=alt.Axis(labelAngle=0)),
            xOffset="Measure:N",
            y=alt.Y("Score:Q", axis=alt.Axis(format="%"), scale=alt.Scale(domain=[0, 1])),
            color=alt.Color("Measure:N", legend=alt.Legend(orient="bottom", title=None)),
            tooltip=["Month", "Measure", alt.Tooltip("Score:Q", format=".1%")],
        ).properties(height=280),
        alt="Monthly accuracy and flood recall")
    worst = monthly.loc[monthly["Flood recall"].idxmin()]
    st.caption(f"Weakest month: **{worst['Month']}**, where only {worst['Flood recall']:.0%} of floods were caught.")
with c2:
    st.subheader("How often each advisory was issued", icon=":material/campaign:")
    st.caption("Across the 204 test days. Watches and warnings are what a user would see as alerts.")
    adv = load_result_csv("task10_advisory_counts.csv")
    adv["Advisory"] = adv["AI advisory"].map(lambda a: ADVISORY_STYLE[a]["headline"])
    order = [s["headline"] for s in ADVISORY_STYLE.values()]
    st.altair_chart(
        alt.Chart(adv).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            x=alt.X("Advisory:N", sort=order, title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Test cases:Q", title="Days"),
            color=alt.Color("Advisory:N", sort=order, legend=None,
                            scale=alt.Scale(domain=order, range=["#1A9E5C", "#0B6BCB", "#E8820C", "#D93A3A"])),
            tooltip=["Advisory", "Test cases"],
        ).properties(height=280),
        alt="Number of test days per advisory level")

st.subheader("Is combining models worth it?", icon=":material/join:")
st.markdown(
    "Each part of the system was scored separately on the same unseen days. "
    "**ROC-AUC** measures how well a model *ranks* flood days above normal days, regardless of the threshold "
    "(1.0 = perfect, 0.5 = coin toss)."
)
comp = load_component_metrics()
comp = comp.rename(columns={"Threshold (selected on validation)": "Flood line"})
st.dataframe(
    comp, hide_index=True, alt="Metrics for each component of the system",
    column_config={
        "Component": st.column_config.TextColumn(width="large"),
        "Flood line": st.column_config.NumberColumn(format="%.2f", help="Probability at which this part says Flood. Chosen on a separate validation period."),
        **{c: st.column_config.ProgressColumn(c, min_value=0, max_value=1, format="percent")
           for c in ["Accuracy", "Balanced accuracy", "Precision (Flood)", "Recall (Flood)", "F1-score (Flood)"]},
        "ROC-AUC": st.column_config.NumberColumn(format="%.3f"),
    },
)
st.caption(
    "Reading the table: all parts land close together (about 89–90% accuracy). The Random Forest catches slightly more floods; "
    "the combined score ranks days slightly better than the LSTM alone. The rule-based advisory keeps the same accuracy "
    "while adding a readable explanation, which is the main value of the AI layer."
)

st.subheader("Look at every mistake", icon=":material/search:")
errors = load_result_csv("task10_misclassified_cases.csv")
kind = st.segmented_control("Show", ["All mistakes", "Missed floods", "False alarms"], default="All mistakes", required=True)
if kind == "Missed floods":
    errors = errors[errors["Error type"].str.startswith("False negative")]
elif kind == "False alarms":
    errors = errors[errors["Error type"].str.startswith("False positive")]
st.dataframe(
    errors[["date", "Error type", "Actual", "Integrated prediction", "Integrated probability", "AI advisory", "Rule explanation"]],
    hide_index=True, alt="Table of misclassified test days",
    column_config={"Integrated probability": st.column_config.ProgressColumn("Flood score", min_value=0, max_value=1, format="percent")},
)
st.caption("Most missed floods had low scores from both models and no rule triggered, so they looked like normal days "
           "in the readings. Open *Check a day* with one of these dates to see its explanation.")

with st.expander("Download the evidence files generated by the notebook", icon=":material/download:"):
    files = sorted(p for p in RESULT_DIR.iterdir() if p.suffix in {".csv", ".json"})
    with st.container(horizontal=True):
        for p in files:
            st.download_button(p.name, p.read_bytes(), file_name=p.name, icon=":material/description:", key=f"dl_{p.name}")
    st.image(str(RESULT_DIR / "task10_confusion_matrix.png"), caption="Notebook figure: confusion matrix", width=420)
