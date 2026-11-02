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


# ---------------------------------------------------------------------------
# Visual components
# ---------------------------------------------------------------------------
def _style(fig: go.Figure, height: int) -> go.Figure:
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Plus Jakarta Sans, sans-serif"),
                      showlegend=False)
    return fig


# ---------------------------------------------------------------------------
# Result blocks
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Data for the animated components (fs_components.py)
# ---------------------------------------------------------------------------
LOCATION = (19.0, 73.0)   # the single monitored point in the dataset (lat, lon)


def percentile(df: pd.DataFrame, feature: str, value: float) -> float:
    return float((df[feature] < value).mean()) if pd.notna(value) else 0.0


def advisory_props(result: dict, df: pd.DataFrame, window: pd.DataFrame, actual: str | None, eyebrow: str,
                   flood_line: float) -> dict:
    """Arguments for ``living_advisory``: verdict chip, warning-sign chips and rain intensity."""
    verdict = None
    if actual is not None:
        if actual == result["prediction"]:
            verdict = (f"✓ Correct · it really was {'a flood' if actual == 'Flood' else 'calm'}", "#1A9E5C")
        elif actual == "Flood":
            verdict = ("✗ Missed · a flood really happened", "#D93A3A")
        else:
            verdict = ("✗ False alarm · no flood happened", "#E8820C")
    return {"result": result, "levels": LEVELS, "rain": percentile(df, "precipitation", window["precipitation"].iloc[-1]),
            "eyebrow": eyebrow, "flood_line": flood_line, "verdict": verdict, "triggers": [TRIGGER_TEXT[t] for t in result["triggers"]]}


def week_days(window: pd.DataFrame, df: pd.DataFrame) -> list[dict]:
    """One tile per day for ``week_strip``: weather icon level and three mini bars (0–1)."""
    days = []
    for i, row in window.reset_index(drop=True).iterrows():
        rain = percentile(df, "precipitation", row["precipitation"])
        days.append({
            "dow": row["date"].strftime("%a"), "date": row["date"].strftime("%d %b"), "target": i == len(window) - 1,
            "rain_level": int(np.digitize(rain, [0.35, 0.6, 0.8, 0.93])), "rain": rain,
            "soil": percentile(df, "soil_moisture", row["soil_moisture"]),
            "water": percentile(df, "water_area_km2", row["water_area_km2"]),
            "rows": [[f"{row['date']:%a %d %b}", ""]] + [
                [FRIENDLY[f], f"{row[f]:,.3g} ({wording(df, f, row[f])})"]
                for f in ["precipitation", "soil_moisture", "water_area_km2", "water_area_change", "temperature", "humidity"]],
        })
    return days


def engine_trace(system: IntegratedFloodSystem, window: pd.DataFrame, result: dict) -> dict:
    """Everything one day produces inside the engine, for the walkthrough animation."""
    import torch
    w = system.validate_window(window)
    x = system.scale(w)
    with torch.no_grad():
        emb = system.encoder.embed(torch.from_numpy(x)[None]).numpy()[0]
    votes = [int(t.predict_proba(emb[None])[0, 1] >= 0.5) for t in system.rf.estimators_]
    lvl = LEVELS[result["advisory"]]
    fired = [r[0] for r in system.rules].index(result["rule"])
    n_flood = sum(votes)
    captions = [
        f"The week ending {result['date']:%d %b %Y}: 7 days × {x.shape[1]} readings, scaled so 0 means a typical day. "
        "Red cells are above usual, blue below.",
        "The LSTM reads one day at a time and carries a memory forward, so it notices patterns that build up over the week.",
        f"After the last day, its memory is a summary of the whole week: {len(emb)} numbers. "
        f"On its own, the LSTM says {result['p_dl']:.0%} chance of flood.",
        f"The Random Forest's {len(votes)} trees each vote on that summary: {n_flood} say flood. "
        f"Its probability is {result['p_ml']:.0%}.",
        f"Combined score {result['score']:.0%} (flood line {system.thresholds['sys']:.0%}). "
        f"Rules are checked top to bottom: {result['rule']} fires → {lvl['label']}.",
    ]
    return {"grid": np.clip(x, -3, 3).round(2).tolist(), "emb": (emb / (np.abs(emb).max() or 1)).round(3).tolist(),
            "votes": votes, "p_dl": result["p_dl"], "p_ml": result["p_ml"], "score": result["score"],
            "th": system.thresholds, "color": lvl["hex"], "label": lvl["label"], "fired": fired, "captions": captions,
            "rules": [{"id": r[0], "label": LEVELS[r[1]]["label"], "color": LEVELS[r[1]]["hex"]} for r in system.rules]}


# ---------------------------------------------------------------------------
# ECharts specs (animated entrance, themed by Streamlit)
# ---------------------------------------------------------------------------
_ANIM = {"animationDuration": 900, "animationEasing": "cubicOut"}


def ec_push_bars(names: list[str], values: list[float], axis_name: str) -> dict:
    """Horizontal diverging bars: red raises risk, blue lowers it (values in points)."""
    return {**_ANIM, "grid": {"left": 8, "right": 40, "top": 10, "bottom": 30, "containLabel": True},
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
            "xAxis": {"type": "value", "name": axis_name, "nameLocation": "middle", "nameGap": 24},
            "yAxis": {"type": "category", "data": names, "inverse": True, "axisTick": {"show": False}},
            "series": [{"type": "bar", "barWidth": "60%",
                        "label": {"show": True, "position": "right", "formatter": "{c}"},
                        "data": [{"value": round(v, 1), "itemStyle": {"color": UP if v > 0 else DOWN, "borderRadius": 4}}
                                 for v in values]}]}


def ec_day_bars(labels: list[str], values: list[float]) -> dict:
    return {**_ANIM, "grid": {"left": 8, "right": 8, "top": 16, "bottom": 8, "containLabel": True},
            "tooltip": {"trigger": "axis"}, "xAxis": {"type": "category", "data": labels},
            "yAxis": {"type": "value", "name": "points"},
            "series": [{"type": "bar", "barWidth": "55%",
                        "data": [{"value": round(v, 1), "itemStyle": {"color": UP if v > 0 else DOWN, "borderRadius": 4}}
                                 for v in values]}]}


def ec_trends(window: pd.DataFrame, rule_levels: dict) -> dict:
    """Four small line charts for the week, with the warning level as a dashed line."""
    feats = ["precipitation", "soil_moisture", "water_area_km2", "water_area_change"]
    lines = {"precipitation": rule_levels["heavy_rain"], "soil_moisture": rule_levels["wet_soil"],
             "water_area_change": rule_levels["rapid_rise"]}
    x = window["date"].dt.strftime("%a").tolist()
    grids, xs, ys, series, titles = [], [], [], [], []
    for i, f in enumerate(feats):
        left = f"{2 + i * 25}%"
        grids.append({"left": left, "width": "21%", "top": 34, "bottom": 24, "containLabel": True})
        titles.append({"text": FRIENDLY[f], "left": left, "top": 0, "textStyle": {"fontSize": 12}})
        xs.append({"type": "category", "data": x, "gridIndex": i, "axisLabel": {"fontSize": 10}})
        ys.append({"type": "value", "gridIndex": i, "scale": True, "axisLabel": {"fontSize": 10}})
        s = {"type": "line", "xAxisIndex": i, "yAxisIndex": i, "smooth": 0.3, "symbolSize": 6, "data": window[f].round(4).tolist(),
             "lineStyle": {"width": 2.5, "color": DOWN}, "itemStyle": {"color": DOWN},
             "areaStyle": {"opacity": 0.12, "color": DOWN},
             "markPoint": {"symbol": "circle", "symbolSize": 12, "itemStyle": {"color": UP},
                           "data": [{"coord": [len(x) - 1, float(window[f].iloc[-1])]}], "label": {"show": False}}}
        if f in lines:
            s["markLine"] = {"symbol": "none", "silent": True, "label": {"show": False},
                             "lineStyle": {"type": "dashed", "color": LEVELS["FLOOD WATCH"]["hex"]}, "data": [{"yAxis": lines[f]}]}
        series.append(s)
    return {**_ANIM, "title": titles, "grid": grids, "xAxis": xs, "yAxis": ys, "series": series, "tooltip": {"trigger": "axis"}}


def global_style() -> None:
    """Site-wide motion: content fades in, bordered cards lift on hover. Respects reduced motion."""
    st.html("""<style>
    [data-testid="stMainBlockContainer"] > div > [data-testid="stVerticalBlock"] > div {
      animation: fs-rise .5s cubic-bezier(.2,.8,.2,1) both; }
    [data-testid="stMainBlockContainer"] > div > [data-testid="stVerticalBlock"] > div:nth-child(2) { animation-delay: .05s; }
    [data-testid="stMainBlockContainer"] > div > [data-testid="stVerticalBlock"] > div:nth-child(3) { animation-delay: .1s; }
    [data-testid="stMainBlockContainer"] > div > [data-testid="stVerticalBlock"] > div:nth-child(n+4) { animation-delay: .15s; }
    @keyframes fs-rise { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: none; } }
    [data-testid="stVerticalBlockBorderWrapper"] { transition: transform .2s ease, box-shadow .2s ease; }
    [data-testid="stVerticalBlockBorderWrapper"]:hover { transform: translateY(-2px);
      box-shadow: 0 10px 30px -18px rgba(11,107,203,.55); }
    [data-testid="stMetricValue"] { font-variant-numeric: tabular-nums; }
    @media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
    </style>""")
