import numpy as np
import pandas as pd
import streamlit as st

from flood_ui import LEVELS, advisory_props, ec_push_bars, load_data, load_system, test_period, window_ending
from fs_components import living_advisory

system = load_system()
df = load_data()
test_start, test_end = test_period()
LINE = system.flood_line

# Plain labels → real values. Water is relative to the flood line; rain and soil are quantiles of every recorded day.
WATER = {"Very low": 0.1, "Low": 0.35, "Normal": 0.6, "Near the line": 0.9, "Just above the line": 1.1,
         "Far above the line": 1.6}
TREND = {"Falling": np.linspace(1.5, 1.08, 6), "As recorded": None, "Rising": np.linspace(0.55, 0.92, 6)}
RAIN = {"None": 0.0, "Normal": 0.5, "Heavy": 0.9, "Extreme": 0.995}
SOIL = {"Dry": 0.05, "Normal": 0.5, "Wet": 0.9, "Saturated": 0.99}
CONTROLS = {  # key → (title, options)
    "water": ("Water area today", WATER),
    "trend": ("Water over the past 6 days", TREND),
    "rain": ("Rain today", RAIN),
    "soil": ("Soil wetness today", SOIL),
}
SCENARIO_DAY = pd.Timestamp("2024-07-19").date()   # each scenario below was checked on this week
PRESETS = {  # name → (advisory it produces, slider settings)
    "Dry and receding": ("LOW RISK", {"water": "Low", "trend": "Falling", "rain": "None", "soil": "Dry"}),
    "Water near the line": ("MONITOR", {"water": "Near the line", "trend": "As recorded", "rain": "Normal", "soil": "Normal"}),
    "Water rising toward the line": ("FLOOD WATCH", {"water": "Near the line", "trend": "Rising", "rain": "Normal", "soil": "Normal"}),
    "River over the line": ("FLOOD WARNING", {"water": "Far above the line", "trend": "Rising", "rain": "Heavy", "soil": "Wet"}),
}


def quantile(feature: str, q: float) -> float:
    return float(df[feature].quantile(q))


def recorded_labels(day) -> dict:
    """Slider positions closest to what was actually recorded on that day."""
    last = window_ending(df, day).iloc[-1]
    near = lambda options, value: min(options, key=lambda k: abs(options[k] - value))
    return {"water": near(WATER, last["water_area_km2"] / LINE), "trend": "As recorded",
            "rain": min(RAIN, key=lambda k: abs(quantile("precipitation", RAIN[k]) - last["precipitation"])),
            "soil": min(SOIL, key=lambda k: abs(quantile("soil_moisture", SOIL[k]) - last["soil_moisture"]))}


def reset_to(day) -> None:
    st.session_state.wi_rec = recorded_labels(day)
    for key, label in st.session_state.wi_rec.items():
        st.session_state[f"wi_{key}"] = label
    st.session_state.wi_for = day


def apply_preset(name: str) -> None:
    st.session_state.wi_day = SCENARIO_DAY
    reset_to(SCENARIO_DAY)
    for key, label in PRESETS[name][1].items():
        st.session_state[f"wi_{key}"] = label


def edited_window(base: pd.DataFrame, water=None, trend=None, rain=None, soil=None) -> pd.DataFrame:
    """Apply changes to the week and keep the derived columns (change, averages) consistent."""
    w = base.copy().reset_index(drop=True)
    last = w.index[-1]
    if water is not None:
        w.loc[last, "water_area_km2"] = WATER[water] * LINE
    if trend is not None and TREND[trend] is not None:
        w.loc[:last - 1, "water_area_km2"] = TREND[trend] * w.loc[last, "water_area_km2"]
    w.loc[1:, "water_area_change"] = w["water_area_km2"].diff().iloc[1:]
    if rain is not None: w.loc[last, "precipitation"] = quantile("precipitation", RAIN[rain])
    if soil is not None: w.loc[last, "soil_moisture"] = quantile("soil_moisture", SOIL[soil])
    w.loc[last, "precip_3day_avg"] = w["precipitation"].iloc[-3:].mean()
    w.loc[last, "precip_7day_avg"] = w["precipitation"].mean()
    w.loc[last, "soil_3day_avg"] = w["soil_moisture"].iloc[-3:].mean()
    return w


st.title("What-if lab", icon=":material/tune:")
st.caption("Change today's water and weather, and watch tomorrow's flood risk respond. One tap shows each risk level.")

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
reset_col.button("Back to recorded data", icon=":material/restart_alt:", on_click=reset_to, args=(day,), type="tertiary")

base = window_ending(df, day)
controls, results = st.columns([1, 1.5], gap="large")
with controls, st.container(border=True):
    chosen = {}
    for key, (title, options) in CONTROLS.items():
        label = st.select_slider(title, list(options), key=f"wi_{key}")
        chosen[key] = None if label == st.session_state.wi_rec[key] else label   # untouched → keep the real reading
        if key == "water":
            value = base["water_area_km2"].iloc[-1] if chosen[key] is None else WATER[label] * LINE
            st.caption(f"≈ {value:,.0f} km² · flood line {LINE:,.0f} km²")
    st.caption("Untouched sliders keep the real reading of that day.")

after_window = edited_window(base, **chosen)
parts = {"Water area today": edited_window(base, water=chosen["water"]),
         "Water over the week": edited_window(base, trend=chosen["trend"]),
         "Rain today": edited_window(base, rain=chosen["rain"]),
         "Soil wetness": edited_window(base, soil=chosen["soil"])}
before, after, *singles = system.predict_windows([base, after_window, *parts.values()])   # one model call

with results:
    lb, la = LEVELS[before["advisory"]], LEVELS[after["advisory"]]
    living_advisory(**advisory_props(after, df, after_window, None,
                                     f"Your scenario · forecast for {after['for_date']:%d %b %Y} · "
                                     f"recorded data gave {lb['label']} at {before['score']:.0%}",
                                     system.thresholds["sys"]), key="whatif_advisory")
    if st.session_state.get("wi_last") not in (None, after["advisory"]):   # only when the advisory just changed
        st.toast(f"Advisory now: {la['label']}", icon=la["icon"])
    st.session_state.wi_last = after["advisory"]

    effect = {k: (r["score"] - before["score"]) * 100 for k, r in zip(parts, singles)}   # each change on its own
    st.markdown("**What moved the risk** · each change on its own")
    st.echarts_chart(ec_push_bars(list(effect), list(effect.values()), "change in flood score (points)"), height=220)
    st.caption("Here floods come from river water spreading over the plain, so the water area moves the risk far "
               "more than a single day's rain. Rain and wet soil still raise a Monitor flag.")
