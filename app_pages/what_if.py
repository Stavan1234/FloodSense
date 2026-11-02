import pandas as pd
import streamlit as st

from flood_ui import LEVELS, advisory_props, ec_push_bars, load_data, load_system, test_period, window_ending
from fs_components import living_advisory

system = load_system()
df = load_data()
test_start, test_end = test_period()

# Each control maps plain labels to real values taken from the dataset (quantiles of every recorded day).
CONTROLS = {
    "rain": ("Rain on the day", "precipitation", ["None", "Light", "Normal", "Heavy", "Very heavy", "Extreme"],
             [0.0, 0.25, 0.5, 0.9, 0.97, 0.995]),
    "soil": ("Soil wetness", "soil_moisture", ["Dry", "Normal", "Damp", "Wet", "Saturated"],
             [0.05, 0.5, 0.75, 0.9, 0.99]),
    "water": ("Water area since yesterday", "water_area_change",
              ["Shrinking fast", "Shrinking", "Stable", "Rising", "Rising fast", "Surging"],
              [0.02, 0.2, 0.5, 0.75, 0.92, 0.99]),
}
WEEK = {"Much drier": 0.25, "Drier": 0.5, "As recorded": 1.0, "Wetter": 2.0, "Much wetter": 3.0}
SCENARIO_DAY = pd.Timestamp("2025-04-18").date()   # each scenario below was checked on this week
PRESETS = {  # name → (advisory it produces, slider settings)
    "Calm day": ("LOW RISK", {"rain": "None", "soil": "Normal", "water": "Stable", "week": "As recorded"}),
    "Soggy ground": ("MONITOR", {"rain": "None", "soil": "Saturated", "water": "Stable", "week": "As recorded"}),
    "Sudden downpour": ("FLOOD WATCH", {"rain": "Heavy", "soil": "Dry", "water": "Shrinking", "week": "Wetter"}),
    "Cloudburst": ("FLOOD WARNING", {"rain": "Extreme", "soil": "Wet", "water": "Rising fast", "week": "Wetter"}),
}


def level_value(key: str, label: str) -> float:
    _, feature, labels, qs = CONTROLS[key]
    return float(df[feature].quantile(qs[labels.index(label)]))


def nearest_label(key: str, value: float) -> str:
    _, feature, labels, _ = CONTROLS[key]
    return min(labels, key=lambda lab: abs(level_value(key, lab) - value))


def reset_to(day) -> None:
    last = window_ending(df, day).iloc[-1]
    for key, (_, feature, _, _) in CONTROLS.items():
        st.session_state[f"wi_{key}"] = nearest_label(key, last[feature])
    st.session_state.wi_week = "As recorded"
    st.session_state.wi_for = day


def apply_preset(name: str) -> None:
    st.session_state.wi_day = st.session_state.wi_for = SCENARIO_DAY
    for key, label in PRESETS[name][1].items():
        st.session_state[f"wi_{key}"] = label


def edited_window(base: pd.DataFrame, rain=None, soil=None, water=None, week=1.0) -> pd.DataFrame:
    """Apply changes to the last day and keep the derived averages consistent."""
    w = base.copy()
    last = w.index[-1]
    w["precipitation"] = w["precipitation"] * week
    if rain is not None: w.loc[last, "precipitation"] = rain
    if soil is not None: w.loc[last, "soil_moisture"] = soil
    if water is not None:
        w.loc[last, "water_area_change"] = water
        w.loc[last, "water_area_km2"] = max(0.0, float(w["water_area_km2"].iloc[-2]) + water)
    w.loc[last, "precip_3day_avg"] = w["precipitation"].iloc[-3:].mean()
    w.loc[last, "precip_7day_avg"] = w["precipitation"].mean()
    w.loc[last, "soil_3day_avg"] = w["soil_moisture"].iloc[-3:].mean()
    return w


st.title("What-if lab", icon=":material/tune:")
st.caption("Change the weather on any day and watch the flood risk respond. One tap shows each risk level.")

st.markdown("**Try a scenario**")
with st.container(horizontal=True):
    for name, (advisory, _) in PRESETS.items():
        st.button(name, icon=LEVELS[advisory]["icon"], on_click=apply_preset, args=(name,),
                  help=f"Gives: {LEVELS[advisory]['label']}")
st.session_state.setdefault("wi_day", SCENARIO_DAY)
day_col, reset_col = st.columns([1, 3], vertical_alignment="bottom")
day = day_col.date_input("Start from the week ending", min_value=test_start, max_value=test_end,
                         format="DD/MM/YYYY", key="wi_day")
if st.session_state.get("wi_for") != day:
    reset_to(day)
reset_col.button("Back to recorded weather", icon=":material/restart_alt:", on_click=reset_to, args=(day,), type="tertiary")

base = window_ending(df, day)
controls, results = st.columns([1, 1.5], gap="large")
with controls, st.container(border=True):
    chosen = {}
    for key, (title, feature, labels, _) in CONTROLS.items():
        label = st.select_slider(title, labels, key=f"wi_{key}")
        chosen[key] = level_value(key, label)
        normal = float(df[feature].median())
        if key != "water" and normal > 0:
            st.caption(f"≈ {chosen[key] / normal:.1f}× a normal day")
    week = WEEK[st.select_slider("Rain over the past week", list(WEEK), key="wi_week")]

after_window = edited_window(base, chosen["rain"], chosen["soil"], chosen["water"], week)
parts = {"Rain on the day": edited_window(base, rain=chosen["rain"]),
         "Soil wetness": edited_window(base, soil=chosen["soil"]),
         "Water area": edited_window(base, water=chosen["water"]),
         "Past week's rain": edited_window(base, week=week)}
before, after, *singles = system.predict_windows([base, after_window, *parts.values()])   # one model call

with results:
    lb, la = LEVELS[before["advisory"]], LEVELS[after["advisory"]]
    living_advisory(**advisory_props(after, df, after_window, None,
                                     f"Your week · recorded week was {lb['label']} at {before['score']:.0%}",
                                     system.thresholds["sys"]), key="whatif_advisory")
    if st.session_state.get("wi_last") not in (None, after["advisory"]):   # only when the advisory just changed
        st.toast(f"Advisory now: {la['label']}", icon=la["icon"])
    st.session_state.wi_last = after["advisory"]

    effect = {k: (r["score"] - before["score"]) * 100 for k, r in zip(parts, singles)}   # each change on its own
    st.markdown("**What moved the risk** · each change on its own")
    st.echarts_chart(ec_push_bars(list(effect), list(effect.values()), "change in flood score (points)"), height=220)
