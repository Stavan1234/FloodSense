"""Shared data loading, wording and visual components for the FloodSense website.

Predictions always come from ``IntegratedFloodSystem`` in ``system_core.py``,
which loads the model trained in the notebook. This module only presents them.
"""
from pathlib import Path
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from system_core import ENVIRONMENTAL_FEATURES, IntegratedFloodSystem

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "model_artifacts"
DATA_DIR = BASE_DIR / "site_data"
SAMPLE_CSV_PATH = BASE_DIR / "sample_7_day_input.csv"

# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------
FRIENDLY = {
    "precipitation": "Rainfall",
    "soil_moisture": "Soil wetness",
    "temperature": "Temperature",
    "humidity": "Humidity",
    "pressure": "Air pressure",
    "wind_speed": "Wind speed",
    "evaporation": "Evaporation",
    "water_area_km2": "Water area",
    "water_area_change": "Water-area change",
    "precip_3day_avg": "Rain, last 3 days",
    "precip_7day_avg": "Rain, last 7 days",
    "temp_3day_avg": "Temperature, last 3 days",
    "soil_3day_avg": "Soil wetness, last 3 days",
    "season": "Time of year",
}
HELP = {
    "precipitation": "Rain that fell on the day.",
    "soil_moisture": "How wet the ground is. Wet ground can't soak up more rain.",
    "water_area_km2": "Area covered by surface water, measured by satellite (km²).",
    "water_area_change": "How much the satellite-measured water area grew or shrank since the day before (km²).",
    "precip_3day_avg": "Average rainfall over the last 3 days.",
    "precip_7day_avg": "Average rainfall over the last 7 days.",
    "season": "Where the day falls in the year.",
}

LEVELS = {  # advisory → presentation; colour is never the only signal (icon + label too)
    "LOW RISK": {"label": "Low risk", "color": "green", "hex": "#1A9E5C", "icon": ":material/check_circle:",
                 "meaning": "All clear", "action": "Nothing to do.", "callout": "success"},
    "MONITOR": {"label": "Monitor", "color": "blue", "hex": "#0B6BCB", "icon": ":material/visibility:",
                "meaning": "Something unusual", "action": "Keep an eye on conditions.", "callout": "info"},
    "FLOOD WATCH": {"label": "Flood watch", "color": "orange", "hex": "#E8820C", "icon": ":material/warning:",
                    "meaning": "Flooding possible", "action": "Be ready to act.", "callout": "warning"},
    "FLOOD WARNING": {"label": "Flood warning", "color": "red", "hex": "#D93A3A", "icon": ":material/flood:",
                      "meaning": "Flooding likely", "action": "Act now.", "callout": "error"},
}
TRIGGER_TEXT = {"heavy_rain": "Heavy rain", "wet_soil": "Very wet soil", "rapid_rise": "Water rising fast"}
UP, DOWN, GREY = "#D93A3A", "#0B6BCB", "#8C9AAB"


def pct(x: float) -> str:
    return f"{x:.0%}"


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner="Loading the AI model…")
def load_system() -> IntegratedFloodSystem:
    return IntegratedFloodSystem(MODEL_DIR)


@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "clean_dataset.csv", parse_dates=["date"])


@st.cache_data(show_spinner=False)
def load_predictions() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "test_predictions.csv", parse_dates=["date"])


@st.cache_data(show_spinner=False)
def load_summary() -> dict:
    return json.loads((DATA_DIR / "summary.json").read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / name)


def window_ending(df: pd.DataFrame, day, days: int = 7) -> pd.DataFrame:
    i = int(np.flatnonzero(df["date"].dt.date == pd.Timestamp(day).date())[0])
    return df.iloc[i - days + 1: i + 1].reset_index(drop=True)


def actual_label(df: pd.DataFrame, day) -> str | None:
    row = df.loc[df["date"].dt.date == pd.Timestamp(day).date(), "flood_event"]
    return None if row.empty else ("Flood" if int(row.iloc[0]) == 1 else "No Flood")


def test_period() -> tuple:
    start, end = load_summary()["splits"]["test"]
    return pd.Timestamp(start).date(), pd.Timestamp(end).date()


def wording(df: pd.DataFrame, feature: str, value: float) -> str:
    """Describe a reading relative to every day in the dataset."""
    if feature not in df.columns or pd.isna(value):
        return ""
    p = float((df[feature] < value).mean())
    if p >= 0.95: return "far above usual"
    if p >= 0.80: return "above usual"
    if p >= 0.20: return "about usual"
    if p >= 0.05: return "below usual"
    return "far below usual"


# ---------------------------------------------------------------------------
# Explanations (SHAP, expected gradients) in plain words
# ---------------------------------------------------------------------------
def shap_tables(system: IntegratedFloodSystem, window: pd.DataFrame):
    """Per-reading and per-day SHAP contributions for one window (season = sin + cos)."""
    phi = system.explain(window)                                  # days × features
    per_feature = pd.Series(phi.sum(0), index=system.feature_names)
    season = per_feature[["day_of_year_sin", "day_of_year_cos"]].sum()
    per_feature = per_feature.drop(["day_of_year_sin", "day_of_year_cos"])
    per_feature["season"] = season
    feats = pd.DataFrame({"feature": per_feature.index, "shap": per_feature.values})
    feats["name"] = feats["feature"].map(FRIENDLY)
    feats = feats.reindex(feats["shap"].abs().sort_values(ascending=False).index).reset_index(drop=True)
    dates = window["date"].dt.strftime("%a %d").tolist()
    days = pd.DataFrame({"day": [f"{d}{' ★' if i == len(dates) - 1 else ''}" for i, d in enumerate(dates)],
                         "shap": phi.sum(1)})
    return feats, days


@st.cache_data(show_spinner=False)
def cached_explain(day_key: str) -> tuple:
    df = load_data()
    return shap_tables(load_system(), window_ending(df, day_key))


def drivers(feats: pd.DataFrame, window: pd.DataFrame, df: pd.DataFrame, n: int = 3) -> list[dict]:
    last = window.iloc[-1]
    out = []
    for _, r in feats.head(n).iterrows():
        f = r["feature"]
        desc = wording(df, f, last[f]) if f in window.columns else ""
        out.append({"name": r["name"], "desc": desc, "up": r["shap"] > 0, "points": r["shap"] * 100,
                    "help": HELP.get(f, "")})
    return out


def show_drivers(items: list[dict]) -> None:
    st.markdown("**Top reasons**")
    for d in items:
        arrow, color, effect = ("↑", "red", "raises risk") if d["up"] else ("↓", "blue", "lowers risk")
        desc = f" · {d['desc']}" if d["desc"] else ""
        st.markdown(f":{color}[**{arrow} {d['name']}**]{desc}  \n:gray[{effect} by {abs(d['points']):.0f} points]",
                    help=d["help"] or None)


# ---------------------------------------------------------------------------
# Visual components
# ---------------------------------------------------------------------------
def _style(fig: go.Figure, height: int) -> go.Figure:
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Plus Jakarta Sans, sans-serif"),
                      showlegend=False)
    return fig


def risk_gauge(score: float, flood_line: float, title: str = "Flood score", height: int = 230) -> go.Figure:
    color = LEVELS["FLOOD WARNING"]["hex"] if score >= 0.75 else LEVELS["FLOOD WATCH"]["hex"] if score >= flood_line else LEVELS["LOW RISK"]["hex"]
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=score * 100, number={"suffix": "%", "valueformat": ".0f", "font": {"size": 30, "color": color}},
        title={"text": title, "font": {"size": 14}},
        gauge={"axis": {"range": [0, 100], "ticksuffix": "%", "tickvals": [0, 25, 50, 75, 100]},
               "bar": {"color": color, "thickness": 0.28},
               "steps": [{"range": [0, flood_line * 100], "color": "rgba(26,158,92,0.18)"},
                         {"range": [flood_line * 100, 75], "color": "rgba(232,130,12,0.20)"},
                         {"range": [75, 100], "color": "rgba(217,58,58,0.22)"}],
               "threshold": {"line": {"color": "#7A5AF8", "width": 3}, "thickness": 0.9, "value": flood_line * 100}}))
    return _style(fig, height).update_layout(margin=dict(l=25, r=25, t=50, b=5))


def shap_bars(feats: pd.DataFrame, top: int = 8, height: int = 320) -> go.Figure:
    d = feats.head(top).iloc[::-1]
    fig = go.Figure(go.Bar(
        x=d["shap"] * 100, y=d["name"], orientation="h", marker_color=np.where(d["shap"] > 0, UP, DOWN),
        text=[f"{v:+.0f}" for v in d["shap"] * 100], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}: %{x:+.1f} points<extra></extra>"))
    fig.update_xaxes(title="Push on flood score (points) · red raises, blue lowers", zeroline=True,
                     zerolinecolor=GREY, zerolinewidth=1.5)
    return _style(fig, height)


def day_bars(days: pd.DataFrame, height: int = 260) -> go.Figure:
    fig = go.Figure(go.Bar(x=days["day"], y=days["shap"] * 100, marker_color=np.where(days["shap"] > 0, UP, DOWN),
                           hovertemplate="%{x}: %{y:+.1f} points<extra></extra>"))
    fig.update_yaxes(title="Push (points)", zeroline=True, zerolinecolor=GREY)
    return _style(fig, height)


WEEK_FEATURES = ["precipitation", "soil_moisture", "water_area_km2", "water_area_change"]


def week_chart(window: pd.DataFrame, rule_levels: dict, height: int = 230) -> go.Figure:
    """Four small trend charts for the 7 days; the checked day is highlighted."""
    lines = {"precipitation": rule_levels.get("heavy_rain"), "soil_moisture": rule_levels.get("wet_soil"),
             "water_area_change": rule_levels.get("rapid_rise")}
    fig = make_subplots(rows=1, cols=4, subplot_titles=[FRIENDLY[f] for f in WEEK_FEATURES], horizontal_spacing=0.06)
    x = window["date"].dt.strftime("%a %d")
    for c, f in enumerate(WEEK_FEATURES, start=1):
        y = window[f]
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=DOWN, width=2.5),
                                 fill="tozeroy", fillcolor="rgba(11,107,203,0.10)",
                                 hovertemplate="%{x}: %{y:.3~f}<extra></extra>"), 1, c)
        fig.add_trace(go.Scatter(x=[x.iloc[-1]], y=[y.iloc[-1]], mode="markers",
                                 marker=dict(size=11, color=UP, line=dict(color="white", width=2)),
                                 hovertemplate="Checked day: %{y:.3~f}<extra></extra>"), 1, c)
        if lines.get(f) is not None:
            fig.add_hline(y=lines[f], line=dict(color=LEVELS["FLOOD WATCH"]["hex"], dash="dot", width=1.5), row=1, col=c)
        fig.update_xaxes(showticklabels=False, row=1, col=c)
    fig.update_annotations(font_size=12)
    return _style(fig, height).update_layout(margin=dict(l=10, r=10, t=35, b=5))


# ---------------------------------------------------------------------------
# Result blocks
# ---------------------------------------------------------------------------
def advisory_banner(result: dict, actual: str | None = None) -> None:
    lvl = LEVELS[result["advisory"]]
    callout = getattr(st, lvl["callout"])
    triggers = ", ".join(TRIGGER_TEXT[t] for t in result["triggers"])
    body = f"**{lvl['meaning']}.** {lvl['action']}" + (f"  \nWarning signs: {triggers}" if triggers else "")
    callout(body, title=f"{lvl['label']} · {pd.Timestamp(result['date']):%a %d %b %Y}", icon=lvl["icon"])
    if actual is not None:
        right = actual == result["prediction"]
        if right:
            st.badge(f"Correct · it really was {'a flood' if actual == 'Flood' else 'calm'}", color="green", icon=":material/task_alt:")
        elif actual == "Flood":
            st.badge("Missed · a flood really happened", color="red", icon=":material/cancel:")
        else:
            st.badge("False alarm · no flood happened", color="orange", icon=":material/notifications_off:")


def model_scores(system: IntegratedFloodSystem, result: dict) -> None:
    rows = [("Deep learning (LSTM)", result["p_dl"], system.thresholds["dl"]),
            ("Machine learning (Random Forest)", result["p_ml"], system.thresholds["ml"]),
            ("Combined score", result["score"], system.thresholds["sys"])]
    for name, value, line in rows:
        st.progress(float(np.clip(value, 0, 1)),
                    text=f"**{name}** {pct(value)} · {'above' if value >= line else 'below'} its flood line ({pct(line)})")


def decision_steps(system: IntegratedFloodSystem, result: dict) -> None:
    """Show the four rules, top to bottom, and which one fired."""
    fired = False
    for rule_id, advisory, text, _ in system.rules:
        lvl = LEVELS[advisory]
        if fired:
            st.markdown(f":gray[{rule_id} · {lvl['label']}: not checked]")
        elif rule_id == result["rule"]:
            fired = True
            st.markdown(f":{lvl['color']}[{lvl['icon']} **{rule_id} · {lvl['label']}: fired**]  \n{text}")
        else:
            st.markdown(f":gray[:material/close: {rule_id} · {lvl['label']}: {text}, no]")
