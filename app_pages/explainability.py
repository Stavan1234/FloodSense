import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from flood_ui import (
    RULES, FRIENDLY_NAMES, global_importance, load_dataset, load_system, load_test_predictions, pct, percentile_of,
)

system = load_system()
df = load_dataset()
preds = load_test_predictions()

st.title("Why the AI decides what it decides", icon=":material/psychology:")
st.markdown(
    "A system that says *Flood* without saying *why* is hard to trust. This page explains the system at three levels: "
    "**what the models rely on overall**, **whether the two models agree**, and **the exact rules** that turn scores into advisories. "
    "For the explanation of a *single* day, use **Check a day**."
)

# ------------------------------------------------------------------ Global importance
st.subheader("1 · What the models rely on overall", icon=":material/leaderboard:")
st.markdown(
    "Technique: **occlusion importance**. For each of the 204 unseen test days we hid one reading at a time "
    "(replaced it with its typical value), re-ran the models and measured how much the flood score moved. "
    "A long bar means the model **depends heavily** on that reading."
)
imp = global_importance()
imp["Impact (points)"] = imp["Average impact"] * 100
top = imp.iloc[0]
chart = alt.Chart(imp).mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4).encode(
    x=alt.X("Impact (points):Q", title="Average change in flood score when hidden (percentage points)"),
    y=alt.Y("Input:N", sort="-x", title=None, axis=alt.Axis(labelLimit=240)),
    color=alt.condition(alt.datum["Impact (points)"] > 10, alt.value("#0B6BCB"), alt.value("#8CB8E6")),
    tooltip=["Input", alt.Tooltip("Impact (points):Q", format=".1f")],
).properties(height=420)
c1, c2 = st.columns([3, 2], gap="large")
c1.altair_chart(chart, alt="Global occlusion importance of each input")
with c2:
    st.metric("Most relied-on reading", top["Input"], f"moves the score by {top['Impact (points)']:.1f} points on average",
              delta_color="off", delta_arrow="off", border=True)
    second = imp.iloc[1]
    st.metric("Second", second["Input"], f"{second['Impact (points)']:.1f} points", delta_color="off", delta_arrow="off", border=True)
    share = imp["Average impact"].iloc[:2].sum() / imp["Average impact"].sum()
    st.markdown(
        f"**Interpretation:** the top two readings account for about **{share:.0%}** of all influence. "
        "The models mostly look at **how fast the water area is changing** and **how much it rained**. "
        "Humidity, wind and evaporation barely matter."
    )
    st.warning("Relying on *change in water area* is partly a warning sign: water spreading on a satellite image "
               "may already *be* the flood, not a cause of it. See **Responsible AI**.", icon=":material/lightbulb:")

# ------------------------------------------------------------------ Agreement
st.subheader("2 · Do the two models agree?", icon=":material/handshake:")
st.markdown(
    "The deep-learning model (LSTM) and the machine-learning model (Random Forest) each give a flood probability. "
    "When they agree, we can be more confident; disagreement points to uncertain days."
)
p = preds.rename(columns={"LSTM probability": "LSTM", "ML probability (RF on LSTM features)": "Random Forest"})
lstm_flood = p["LSTM"] >= system.dl_threshold
rf_flood = p["Random Forest"] >= system.ml_threshold
agree = (lstm_flood == rf_flood).mean()
corr = np.corrcoef(p["LSTM"], p["Random Forest"])[0, 1]
c1, c2 = st.columns([3, 2], gap="large")
with c1:
    sc = alt.Chart(p).mark_circle(size=70, opacity=0.8).encode(
        x=alt.X("LSTM:Q", title="LSTM flood probability", axis=alt.Axis(format="%")),
        y=alt.Y("Random Forest:Q", title="Random Forest flood probability", axis=alt.Axis(format="%")),
        color=alt.Color("Actual:N", title="What really happened",
                        scale=alt.Scale(domain=["Flood", "No Flood"], range=["#D93A3A", "#0B6BCB"]),
                        legend=alt.Legend(orient="bottom")),
        tooltip=[alt.Tooltip("date:T", format="%d %b %Y"), "Actual", alt.Tooltip("LSTM:Q", format=".1%"),
                 alt.Tooltip("Random Forest:Q", format=".1%")],
    ).properties(height=360)
    st.altair_chart(sc.interactive(), alt="Scatter of LSTM vs Random Forest probabilities")
with c2:
    st.metric("Days where both models gave the same verdict", f"{agree:.0%}", border=True)
    st.metric("Correlation between their scores", f"{corr:.2f}", border=True, help="1.0 = they always move together.")
    st.markdown(
        "Most dots sit near the **bottom-left** (both calm) or **top-right** (both alarmed), so the models usually agree. "
        "Red dots in the bottom-left are floods that **both** models missed. Combining two models cannot fix a "
        "blind spot they share, because the Random Forest is built on the LSTM's own summary of the week."
    )

# ------------------------------------------------------------------ Rules
st.subheader("3 · The rule engine is fully transparent", icon=":material/rule:")
st.markdown(
    "The final advisory is **not** a black box. It comes from four IF–THEN rules checked from the most severe "
    "to the calmest (forward chaining). The first rule that matches decides the advisory."
)
watch = max(0.35, system.system_threshold)
st.mermaid_chart(
    f"""
    flowchart TD
        A([7-day readings]) --> B[LSTM score + Random Forest score]
        B --> C{{"Both models say Flood<br/>OR combined score ≥ 75%?"}}
        C -- Yes --> W["FLOOD WARNING"]
        C -- No --> D{{"Combined score ≥ {pct(watch)}<br/>OR rapid water rise + rain/wet soil?"}}
        D -- Yes --> H["FLOOD WATCH"]
        D -- No --> E{{"Any safety rule<br/>triggered?"}}
        E -- Yes --> M["MONITOR"]
        E -- No --> L["LOW RISK"]
        style W fill:#D93A3A,color:#fff,stroke:#D93A3A
        style H fill:#E8820C,color:#fff,stroke:#E8820C
        style M fill:#0B6BCB,color:#fff,stroke:#0B6BCB
        style L fill:#1A9E5C,color:#fff,stroke:#1A9E5C
    """,
    alt="Flowchart of the advisory rules from Flood warning down to Low risk",
)

st.markdown("**The three environmental safety rules** (checked on the last day of the window):")
rows = []
for r in RULES:
    thr = system.rule_thresholds[r["threshold_key"]]
    rows.append({
        "Rule": r["name"],
        "IF…": f"{FRIENDLY_NAMES[r['feature']]} ≥ {thr:,.3g}",
        "Plain meaning": r["plain"],
        "How rare is that?": f"Only {1 - percentile_of(df, r['feature'], thr):.0%} of days reach it",
    })
st.table(pd.DataFrame(rows), hide_index=True, alt="The three environmental safety rules")
st.markdown("**Model thresholds** (the *Flood line* for each model, chosen on a separate validation period, not the test days):")
with st.container(horizontal=True):
    st.metric("LSTM says Flood at", pct(system.dl_threshold), border=True)
    st.metric("Random Forest says Flood at", pct(system.ml_threshold), border=True)
    st.metric("Combined score says Flood at", pct(system.system_threshold), border=True)
st.caption("Rule thresholds were set from training-period data (upper quantiles), so they reflect what is unusual for this region.")
