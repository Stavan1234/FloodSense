import pandas as pd
import streamlit as st

from flood_ui import (
    ADVISORY_STYLE, FEATURE_HELP, FRIENDLY_NAMES, contribution_chart, explain_window,
    load_dataset, load_system, load_test_predictions, pct, show_advisory, window_ending,
)

system = load_system()
df = load_dataset()
preds = load_test_predictions()

st.title("What-if lab", icon=":material/tune:")
st.markdown(
    "Start from a real week, then **change the last day's conditions** with the sliders. "
    "The AI re-runs instantly so you can see **what it is sensitive to**. "
    "This is called *sensitivity analysis* and is a simple way to test whether a model behaves sensibly."
)

c1, c2 = st.columns([1, 2], vertical_alignment="bottom")
day = c1.date_input("Starting week ends on", value=pd.Timestamp("2025-04-18").date(),
                    min_value=preds["date"].min().date(), max_value=preds["date"].max().date(),
                    format="DD/MM/YYYY", help="Only unseen test days are offered here.")
c2.caption("Tip: start from a calm day and add rain and rising water, or start from a flood day and dry it out.")

base_window = window_ending(df, day, system.window_days).reset_index(drop=True)
last = base_window.iloc[-1]
k = str(day)


def bounds(feature):
    col = pd.to_numeric(df[feature], errors="coerce").dropna()
    return float(col.min()), float(col.max())


st.subheader("Change the last day", icon=":material/sliders:")
with st.container(border=True):
    s1, s2 = st.columns(2, gap="large")
    lo, hi = bounds("precipitation")
    rain = s1.slider(f"{FRIENDLY_NAMES['precipitation']} on the last day", lo, hi, float(last["precipitation"]),
                     key=f"rain_{k}", help=FEATURE_HELP["precipitation"], format="%.3f")
    lo, hi = bounds("soil_moisture")
    soil = s2.slider(f"{FRIENDLY_NAMES['soil_moisture']} on the last day", lo, hi, float(last["soil_moisture"]),
                     key=f"soil_{k}", help=FEATURE_HELP["soil_moisture"], format="%.3f")
    lo, hi = bounds("water_area_change")
    change = s1.slider(f"{FRIENDLY_NAMES['water_area_change']} since yesterday (km²)", lo, hi,
                       float(last["water_area_change"]), key=f"chg_{k}", help=FEATURE_HELP["water_area_change"], format="%.0f")
    week_rain = s2.slider("Make the whole week rainier or drier", 0.0, 3.0, 1.0, 0.1, key=f"wk_{k}",
                          help="Multiplies every day's rainfall. 1.0 = unchanged, 2.0 = twice as much rain.",
                          format="%.1f×")
    st.button("Reset sliders", icon=":material/restart_alt:",
              on_click=lambda: [st.session_state.pop(x, None) for x in (f"rain_{k}", f"soil_{k}", f"chg_{k}", f"wk_{k}")])

# Build the edited window and keep the derived rolling averages consistent with the edits.
w = base_window.copy()
w["precipitation"] = w["precipitation"] * week_rain
w.loc[w.index[-1], "precipitation"] = rain
w.loc[w.index[-1], "soil_moisture"] = soil
w.loc[w.index[-1], "water_area_change"] = change
w.loc[w.index[-1], "water_area_km2"] = max(0.0, float(w["water_area_km2"].iloc[-2]) + change)
w.loc[w.index[-1], "precip_3day_avg"] = w["precipitation"].iloc[-3:].mean()
w.loc[w.index[-1], "precip_7day_avg"] = w["precipitation"].mean()
w.loc[w.index[-1], "soil_3day_avg"] = w["soil_moisture"].iloc[-3:].mean()

before = system.predict_window(base_window)
after = system.predict_window(w)

st.subheader("Effect on the decision", icon=":material/compare_arrows:")
b, a = st.columns(2, gap="large")
with b:
    s = ADVISORY_STYLE[before["AI_advisory"]]
    st.markdown("**Original week**")
    st.metric("Flood score", pct(before["integrated_probability"]), border=True)
    st.markdown(f"### :{s['color']}[{s['icon']} {s['headline']}]")
with a:
    s = ADVISORY_STYLE[after["AI_advisory"]]
    st.markdown("**Your edited week**")
    diff = (after["integrated_probability"] - before["integrated_probability"]) * 100
    st.metric("Flood score", pct(after["integrated_probability"]), delta=f"{diff:+.1f} points",
              delta_color="inverse", border=True)
    st.markdown(f"### :{s['color']}[{s['icon']} {s['headline']}]")

if before["AI_advisory"] != after["AI_advisory"]:
    st.info(f"Your changes moved the advisory from **{ADVISORY_STYLE[before['AI_advisory']]['headline']}** "
            f"to **{ADVISORY_STYLE[after['AI_advisory']]['headline']}**.", icon=":material/swap_horiz:")

with st.expander("Full result for the edited week", icon=":material/assignment:"):
    show_advisory(after)
    _, feat, _ = explain_window(system, w)
    st.markdown("**Which readings mattered for the edited week**")
    st.altair_chart(contribution_chart(feat), alt="Contribution of each reading for the edited week")

st.caption(
    "Note: the model learned from an educational dataset, so some reactions may surprise you "
    "(for example, the model leans heavily on *change in water area*). "
    "Spotting such behaviour is exactly why we test and explain AI systems. See *Responsible AI*."
)
