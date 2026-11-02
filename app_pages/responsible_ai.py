import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from flood_ui import load_dataset, load_result_csv, load_system, load_test_predictions, pct

system = load_system()
df = load_dataset()
preds = load_test_predictions()

st.title("Responsible AI: ethics, fairness and limits", icon=":material/balance:")
st.markdown(
    "Good accuracy is not enough. A flood system affects people's safety, so we must ask: "
    "**who is hurt by its mistakes, whom might it treat unfairly, can its data be trusted, and who is accountable?**"
)

STATUS_COLOR = {"PASS": "green", "REVIEW": "orange", "NO": "red", "NOT DONE": "red"}

st.subheader("Responsible-AI checklist", icon=":material/checklist:")
checks = load_result_csv("task10_responsible_ai_checks.csv")
for _, r in checks.iterrows():
    with st.container(border=True, horizontal=True, vertical_alignment="center"):
        st.badge(r["Status"], color=STATUS_COLOR.get(r["Status"], "gray"), width=110)
        st.markdown(f"**{r['Check']}**  \n:gray[{r['Note']}]")

# ------------------------------------------------------------------ error trade-off
st.subheader("1 · Safety: not all mistakes are equal", icon=":material/crisis_alert:")
c1, c2 = st.columns(2, gap="large")
with c1.container(border=True, height="stretch"):
    st.markdown(":red[:material/report: **Missed flood (false negative)**]")
    st.markdown("People are not warned and may be in danger. **This is the most harmful error.**")
with c2.container(border=True, height="stretch"):
    st.markdown(":orange[:material/notifications_off: **False alarm (false positive)**]")
    st.markdown("Unneeded worry and cost. Too many false alarms make people **ignore real warnings** (the *cry-wolf* effect).")

st.markdown(
    "Moving the *Flood line* trades one error for the other. Drag the slider to see the trade-off on the 204 test days."
)
thr = st.slider("Flood line (combined score needed to say Flood)", 0.05, 0.95, float(round(system.system_threshold, 2)), 0.01,
                format="%.2f", help=f"The system uses {system.system_threshold:.2f}, chosen on a separate validation period.")
prob = preds["Integrated probability"].to_numpy()
act = (preds["Actual"] == "Flood").to_numpy()
fn = int((act & (prob < thr)).sum()); fp = int((~act & (prob >= thr)).sum())
with st.container(horizontal=True):
    st.metric("Missed floods", fn, delta=fn - int((act & (prob < system.system_threshold)).sum()), delta_color="inverse", border=True)
    st.metric("False alarms", fp, delta=fp - int((~act & (prob >= system.system_threshold)).sum()), delta_color="inverse", border=True)
    st.metric("Accuracy", f"{1 - (fn + fp) / len(act):.1%}", border=True)

grid = np.round(np.arange(0.05, 0.96, 0.01), 2)
curve = pd.DataFrame({
    "Flood line": np.repeat(grid, 2),
    "Error": ["Missed floods", "False alarms"] * len(grid),
    "Days": [v for t in grid for v in (int((act & (prob < t)).sum()), int((~act & (prob >= t)).sum()))],
})
lines = alt.Chart(curve).mark_line(strokeWidth=3).encode(
    x=alt.X("Flood line:Q"), y=alt.Y("Days:Q"),
    color=alt.Color("Error:N", scale=alt.Scale(domain=["Missed floods", "False alarms"], range=["#D93A3A", "#E8820C"]),
                    legend=alt.Legend(orient="bottom", title=None)))
now = alt.Chart(pd.DataFrame({"x": [thr]})).mark_rule(strokeDash=[5, 4], color="#8C9AAB").encode(x="x:Q")
st.altair_chart((lines + now).properties(height=260), alt="Missed floods and false alarms as the flood threshold changes")
st.caption(
    "Ethical choice: a real flood service would usually accept more false alarms to miss fewer floods, decided together "
    "with emergency experts and the community. **Note:** this slider is for learning only. Picking the threshold "
    "by looking at test results would be cheating (it leaks test information), which is why the real threshold was fixed beforehand."
)

# ------------------------------------------------------------------ fairness
st.subheader("2 · Fairness: who could be treated unequally?", icon=":material/diversity_3:")
monthly = load_result_csv("task10_monthly_stability_check.csv")
worst = monthly.loc[monthly["Flood recall"].idxmin()]
best = monthly.loc[monthly["Flood recall"].idxmax()]
locs = df[["latitude", "longitude"]].drop_duplicates()
c1, c2, c3 = st.columns(3, gap="medium")
with c1.container(border=True, height="stretch"):
    st.markdown("**Over time**")
    st.markdown(f"Floods caught ranged from **{worst['Flood recall']:.0%}** ({worst['Month']}) to "
                f"**{best['Flood recall']:.0%}** ({best['Month']}). People flooded in a weak month get worse protection.")
with c2.container(border=True, height="stretch"):
    st.markdown("**Across places**")
    st.markdown(f"All data comes from **{len(locs)} location** ({locs.iloc[0]['latitude']}°N, {locs.iloc[0]['longitude']}°E). "
                "Using the model for other towns, rivers or terrain would be **unfair and unreliable** for them.")
with c3.container(border=True, height="stretch"):
    st.markdown("**Across people**")
    st.markdown("The data has **no information about people** (income, housing, disability). So we **cannot** measure "
                "whether vulnerable groups are protected equally. A real system must check this.")

# ------------------------------------------------------------------ bias in data
st.subheader("3 · Bias and quality problems in the data", icon=":material/dataset:")
rate = df.assign(Month=df["date"].dt.month).groupby("Month")["flood_event"].mean().reset_index()
rate["Month name"] = pd.to_datetime(rate["Month"], format="%m").dt.strftime("%b")
c1, c2 = st.columns([3, 2], gap="large")
with c1:
    st.markdown("**Share of days labelled *Flood*, by calendar month**")
    st.altair_chart(
        alt.Chart(rate).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3, color="#0B6BCB").encode(
            x=alt.X("Month name:N", sort=None, title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("flood_event:Q", title="Flood days", axis=alt.Axis(format="%"), scale=alt.Scale(domain=[0, 1])),
            tooltip=["Month name", alt.Tooltip("flood_event:Q", format=".0%", title="Flood days")],
        ).properties(height=250),
        alt="Share of flood days per calendar month")
with c2:
    st.markdown(
        f"About **{df['flood_event'].mean():.0%}** of days are labelled *Flood* in **every** month. "
        "Real floods in western India cluster in the **June–September monsoon**. This flat pattern suggests the labels "
        "are **simulated or noisy**, so the model may learn patterns that do not exist in reality."
    )
st.markdown(
    "- **Possible target proxy:** *change in water area* is the model's most relied-on reading. Water spreading on a "
    "satellite image may *be* the flood itself, so the model may be partly **detecting** floods rather than **predicting** them.\n"
    "- **Same-day only:** the last day of the window is the day classified, so this is **not** an early-warning forecast.\n"
    "- **Data errors seen:** a `water_area_pct_change` column holds the text *invalid*, a `month` column disagrees with the "
    "date, and a few values are missing. These were not used as model inputs, but they lower trust in the source."
)
water = load_result_csv("task10_water_area_label_diagnostic.csv")
with st.expander("Water-area diagnostic from the notebook", icon=":material/water:"):
    st.dataframe(water.round(1), hide_index=True, alt="Water area statistics by class")
    st.caption("Typical water-covered area is about the same on flood and normal days. The influence comes from its "
               "day-to-day *change*, which is why that feature needs expert review.")

# ------------------------------------------------------------------ ethics
st.subheader("4 · Ethical principles applied", icon=":material/gavel:")
principles = [
    (":material/visibility:", "Transparency", "Every decision shows its scores, triggered rules and an occlusion explanation."),
    (":material/person:", "Human in the loop", "Advisories support people; they never trigger actions automatically."),
    (":material/lock:", "Privacy", "Only environmental readings are used; no personal data is collected or stored."),
    (":material/verified:", "Honest reporting", "Missed floods and false alarms are shown openly, not hidden behind accuracy."),
    (":material/do_not_disturb_on:", "Clear limits", "Stated everywhere: educational, same-day, single location, not for emergencies."),
    (":material/history_edu:", "Accountability", "Fixed saved models, thresholds and feature order make every result reproducible and auditable."),
]
cols = st.columns(3)
for i, (icon, title, text) in enumerate(principles):
    with cols[i % 3].container(border=True, height="stretch"):
        st.markdown(f"**{icon} {title}**")
        st.caption(text)

st.subheader("5 · What would be needed before real-world use", icon=":material/rocket_launch:")
readiness = load_result_csv("task10_deployment_readiness.csv")
c1, c2 = st.columns(2, gap="large")
with c1:
    st.markdown("**Deployment readiness (from the notebook)**")
    for _, r in readiness.iterrows():
        color = STATUS_COLOR.get(r["Status"], "gray")
        icon = ":material/check_circle:" if r["Status"] == "PASS" else ":material/cancel:"
        st.markdown(f":{color}[{icon}] {r['Deployment check']}: **:{color}[{r['Status']}]**")
with c2:
    st.markdown("**Still required**")
    st.markdown(
        "1. Real, verified flood records from official agencies\n"
        "2. Testing on other locations and years (external validation)\n"
        "3. A true forecasting set-up (predict *tomorrow*, not today)\n"
        "4. Probability calibration and expert-chosen alert thresholds\n"
        "5. Fairness review with affected communities\n"
        "6. Monitoring for data drift after deployment"
    )
