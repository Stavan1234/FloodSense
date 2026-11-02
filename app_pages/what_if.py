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
PRESETS = {
    "Cloudburst": {"rain": "Extreme", "soil": "Wet", "water": "Rising fast", "week": "Wetter"},
    "Dry spell": {"rain": "None", "soil": "Dry", "water": "Shrinking", "week": "Much drier"},
    "River swelling": {"rain": "Normal", "soil": "Damp", "water": "Surging", "week": "As recorded"},
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
    for key, label in PRESETS[name].items():
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
st.caption("Change the weather on any day and watch the flood risk respond.")

day = st.columns([1, 3])[0].date_input("Start from the week ending", value=pd.Timestamp("2025-04-18").date(),
                    min_value=test_start, max_value=test_end, format="DD/MM/YYYY")
if st.session_state.get("wi_for") != day:
    reset_to(day)

with st.container(horizontal=True):
    for name, icon in zip(PRESETS, [":material/thunderstorm:", ":material/sunny:", ":material/water:"]):
        st.button(name, icon=icon, on_click=apply_preset, args=(name,))
    st.button("Reset", icon=":material/restart_alt:", on_click=reset_to, args=(day,), type="tertiary")

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

before = system.predict_window(base)
after_window = edited_window(base, chosen["rain"], chosen["soil"], chosen["water"], week)
after = system.predict_window(after_window)

with results:
    lb, la = LEVELS[before["advisory"]], LEVELS[after["advisory"]]
    living_advisory(**advisory_props(after, df, after_window, None,
                                     f"Your week · recorded week was {lb['label']} at {before['score']:.0%}",
                                     system.thresholds["sys"]), key="whatif_advisory")
    if st.session_state.get("wi_last") not in (None, after["advisory"]):   # only when the advisory just changed
        st.toast(f"Advisory now: {la['label']}", icon=la["icon"])
    st.session_state.wi_last = after["advisory"]

    # How much each change moves the risk on its own.
    parts = {"Rain on the day": edited_window(base, rain=chosen["rain"]),
             "Soil wetness": edited_window(base, soil=chosen["soil"]),
             "Water area": edited_window(base, water=chosen["water"]),
             "Past week's rain": edited_window(base, week=week)}
    effect = {k: (system.predict_window(w)["score"] - before["score"]) * 100 for k, w in parts.items()}
    st.markdown("**What moved the risk** · each change on its own")
    st.echarts_chart(ec_push_bars(list(effect), list(effect.values()), "change in flood score (points)"), height=220)
