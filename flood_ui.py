"""Shared data loading, wording and visual helpers for the FloodSense website.

Forecasts always come from ``IntegratedFloodSystem`` in ``system_core.py``, which loads the
model trained in the notebook. The task: from the last 7 days, forecast a flood TOMORROW.
"""
from pathlib import Path
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from system_core import IntegratedFloodSystem

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "model_artifacts"
DATA_DIR = BASE_DIR / "site_data"
SAMPLE_CSV_PATH = BASE_DIR / "sample_7_day_input.csv"
LOCATION = (26.25, 68.0)          # the monitored point

# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------
FRIENDLY = {
    "precipitation": "Rainfall", "soil_moisture": "Soil wetness", "temperature": "Temperature", "humidity": "Humidity",
    "pressure": "Air pressure", "wind_speed": "Wind speed", "evaporation": "Evaporation", "water_area_km2": "Water area",
    "water_area_change": "Water-area change", "precip_3day_avg": "Rain, last 3 days", "precip_7day_avg": "Rain, last 7 days",
    "temp_3day_avg": "Temperature, last 3 days", "soil_3day_avg": "Soil wetness, last 3 days", "season": "Time of year",
    "day_of_year_sin": "Season (sin)", "day_of_year_cos": "Season (cos)", "flood_streak": "Days already flooded",
    "dry_streak": "Days since water dropped",
}
HELP = {
    "precipitation": "Rain that fell on the day.",
    "soil_moisture": "How wet the ground is. Wet ground can't soak up more rain.",
    "water_area_km2": "Area covered by surface water, measured by satellite (km²). Above the flood line it counts as a flood.",
    "water_area_change": "How much the satellite-measured water area grew or shrank since the day before (km²).",
    "precip_3day_avg": "Average rainfall over the last 3 days.",
    "precip_7day_avg": "Average rainfall over the last 7 days.",
}

LEVELS = {  # advisory → presentation; colour is never the only signal (icon + label too)
    "LOW RISK": {"label": "Low risk", "color": "green", "hex": "#1A9E5C", "icon": ":material/check_circle:",
                 "meaning": "No flood expected tomorrow", "action": "Nothing to do."},
    "MONITOR": {"label": "Monitor", "color": "blue", "hex": "#0B6BCB", "icon": ":material/visibility:",
                "meaning": "No flood expected, but something to watch", "action": "Check again tomorrow."},
    "FLOOD WATCH": {"label": "Flood watch", "color": "orange", "hex": "#E8820C", "icon": ":material/warning:",
                    "meaning": "Flooding possible tomorrow", "action": "Be ready to act."},
    "FLOOD WARNING": {"label": "Flood warning", "color": "red", "hex": "#D93A3A", "icon": ":material/flood:",
                      "meaning": "Flood expected tomorrow", "action": "Act now."},
}
TRIGGER_TEXT = {"flooded_today": "Flooded today", "near_line": "Water close to the flood line", "heavy_rain": "Heavy rain",
                "wet_soil": "Very wet soil", "rapid_rise": "Water rising fast"}
UP, DOWN, GREY = "#D93A3A", "#0B6BCB", "#8C9AAB"


def pct(x: float) -> str:
    return f"{x:.0%}"


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "clean_dataset.csv", parse_dates=["date"])


@st.cache_data(show_spinner=False)
def load_predictions() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "test_predictions.csv", parse_dates=["today", "for"])


@st.cache_data(show_spinner=False)
def load_summary() -> dict:
    return json.loads((DATA_DIR / "summary.json").read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / name)


def _engine_version() -> tuple:
    """Changes whenever the engine code or model files change, so the cached model is rebuilt."""
    import system_core
    files = [Path(system_core.__file__), *sorted(MODEL_DIR.glob("*"))]
    return tuple(f.stat().st_mtime_ns for f in files)


@st.cache_resource(show_spinner="Loading the AI model…", max_entries=1)
def _load_system(version: tuple) -> IntegratedFloodSystem:
    df = load_data()
    train_end = pd.Timestamp(load_summary()["splits"]["train"][1])
    typical = df[df["date"] <= train_end].median(numeric_only=True).to_dict()      # training medians, for explanations
    return IntegratedFloodSystem(MODEL_DIR, typical=typical)


def load_system() -> IntegratedFloodSystem:
    return _load_system(_engine_version())


def window_ending(df: pd.DataFrame, day, days: int = 7) -> pd.DataFrame:
    i = int(np.flatnonzero(df["date"].dt.date == pd.Timestamp(day).date())[0])
    return df.iloc[i - days + 1: i + 1].reset_index(drop=True)


def actual_next(df: pd.DataFrame, day) -> str | None:
    """What really happened the day after ``day`` (None if outside the data)."""
    nxt = pd.Timestamp(day).date() + pd.Timedelta(days=1)
    row = df.loc[df["date"].dt.date == nxt, "flood_event"]
    return None if row.empty else ("Flood" if int(row.iloc[0]) == 1 else "No Flood")


def test_period() -> tuple:
    """First and last 'today' of the unseen test forecasts."""
    p = load_predictions()
    return p["today"].min().date(), p["today"].max().date()


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


def percentile(df: pd.DataFrame, feature: str, value: float) -> float:
    return float((df[feature] < value).mean()) if pd.notna(value) else 0.0


# ---------------------------------------------------------------------------
# Forecasts and explanations
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False, max_entries=512)
def cached_predict(day_key: str) -> dict:
    return load_system().predict_window(window_ending(load_data(), day_key))


def impact_tables(system: IntegratedFloodSystem, window: pd.DataFrame):
    """How much each reading and each day moved tomorrow's score (occlusion, in probability units)."""
    _, readings, days = system.explain(window)
    feats = pd.DataFrame({"feature": list(readings), "impact": list(readings.values())})
    feats["name"] = feats["feature"].map(FRIENDLY)
    feats = feats.reindex(feats["impact"].abs().sort_values(ascending=False).index).reset_index(drop=True)
    labels = [d.strftime("%a %d") for d in pd.to_datetime(window["date"])]
    labels[-1] += " (today)"
    return feats, pd.DataFrame({"day": labels, "impact": days})


@st.cache_data(show_spinner=False, max_entries=512)
def cached_explain(day_key: str) -> tuple:
    return impact_tables(load_system(), window_ending(load_data(), day_key))


def drivers(feats: pd.DataFrame, window: pd.DataFrame, df: pd.DataFrame, n: int = 3) -> list[dict]:
    last, line = window.iloc[-1], load_system().flood_line
    strong = feats[feats["impact"].abs() >= 0.005]          # skip pushes under half a point: noise, not a reason
    out = []
    for _, r in (strong if len(strong) else feats).head(n).iterrows():
        f = r["feature"]
        if f == "water_area_km2":
            desc = f"today {last[f]:,.0f} km² · flood line {line:,.0f}"
        elif f == "water_area_change":
            desc = f"today {last[f]:+,.0f} km² since yesterday"
        else:
            desc = f"today {wording(df, f, last[f])}" if f in window.columns else ""
        out.append({"name": r["name"], "desc": desc, "up": r["impact"] > 0, "points": r["impact"] * 100,
                    "help": HELP.get(f, "")})
    return out


def advisory_props(result: dict, df: pd.DataFrame, window: pd.DataFrame, actual: str | None, eyebrow: str,
                   flood_line: float) -> dict:
    """Arguments for ``living_advisory``: verdict chip, warning-sign chips and rain intensity."""
    verdict = None
    if actual is not None:
        if actual == result["prediction"]:
            verdict = (f"✓ Correct · {'a flood came' if actual == 'Flood' else 'no flood came'}", "#1A9E5C")
        elif actual == "Flood":
            verdict = ("✗ Missed · a flood came next day", "#D93A3A")
        else:
            verdict = ("✗ False alarm · no flood came", "#E8820C")
    return {"result": result, "levels": LEVELS, "rain": percentile(df, "precipitation", window["precipitation"].iloc[-1]),
            "eyebrow": eyebrow, "flood_line": flood_line, "verdict": verdict, "triggers": [TRIGGER_TEXT[t] for t in result["triggers"]]}


# ---------------------------------------------------------------------------
# Result blocks
# ---------------------------------------------------------------------------
def model_scores(system: IntegratedFloodSystem, result: dict) -> None:
    rows = [("Deep learning (LSTM)", result["p_dl"], system.thresholds["dl"]),
            (f"Machine learning ({system.ml_name})", result["p_ml"], system.thresholds["ml"]),
            (f"Combined ({system.w_dl:.0%} LSTM + {1 - system.w_dl:.0%} ML)", result["score"], system.thresholds["sys"])]
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
def week_days(window: pd.DataFrame, df: pd.DataFrame, flood_line: float) -> list[dict]:
    """One tile per day for ``week_strip``: weather icon level and three mini bars (0–1)."""
    days = []
    for i, row in window.reset_index(drop=True).iterrows():
        rain = percentile(df, "precipitation", row["precipitation"])
        flooded = row["water_area_km2"] >= flood_line
        days.append({
            "dow": row["date"].strftime("%a"), "date": row["date"].strftime("%d %b"), "target": i == len(window) - 1,
            "rain_level": int(np.digitize(rain, [0.35, 0.6, 0.8, 0.93])), "rain": rain,
            "soil": percentile(df, "soil_moisture", row["soil_moisture"]),
            "water": min(1.0, row["water_area_km2"] / (1.6 * flood_line)),
            "rows": [[f"{row['date']:%a %d %b}", "flooded" if flooded else "dry"]] + [
                [FRIENDLY[f], f"{row[f]:,.3g} ({wording(df, f, row[f])})"]
                for f in ["water_area_km2", "water_area_change", "precipitation", "soil_moisture", "temperature", "humidity"]],
        })
    return days


@st.cache_data(show_spinner=False, max_entries=64)
def cached_trace(day_key: str) -> dict:
    return engine_trace(load_system(), window_ending(load_data(), day_key), cached_predict(day_key))


def engine_trace(system: IntegratedFloodSystem, window: pd.DataFrame, result: dict) -> dict:
    """Everything one forecast produces inside the engine, for the walkthrough animation."""
    import torch
    frame = system.frame(system.validate_window(window))
    x = system.seq_scaler.transform(system.seq_imputer.transform(frame[system.lstm_inputs])).astype(np.float32)
    with torch.no_grad():
        emb = system.encoder.embed(torch.from_numpy(x)[None]).numpy()[0]
    X = pd.DataFrame([system.flat(frame)])[system.selected]
    stages = [float(p[0, 1]) for p in system.ml_model.staged_predict_proba(X)]
    votes = [int(p >= system.thresholds["ml"]) for p in stages]
    lvl = LEVELS[result["advisory"]]
    fired = [r[0] for r in system.rules].index(result["rule"])
    captions = [
        f"The 7 days up to {result['date']:%d %b %Y}: {x.shape[1]} inputs per day (water, its change, flood counters, rain, soil, season), "
        "scaled so 0 means a typical day. Red = above usual, blue = below.",
        "The LSTM reads one day at a time and carries a memory forward, so it notices water building up or draining away.",
        f"After today, its memory summarises the week in {len(emb)} numbers. On its own, the LSTM gives "
        f"{result['p_dl']:.0%} chance of a flood tomorrow.",
        f"Separately, {system.ml_name} adds up {len(stages)} small trees over the {len(system.selected)} most useful window "
        f"features, each correcting the last. Its answer: {result['p_ml']:.0%}.",
        f"Combined {system.w_dl:.0%} LSTM + {1 - system.w_dl:.0%} ML = {result['score']:.0%} (flood line "
        f"{system.thresholds['sys']:.0%}). Rules checked top to bottom: {result['rule']} → {lvl['label']} for {result['for_date']:%d %b}.",
    ]
    return {"grid": np.clip(x, -3, 3).round(2).tolist(), "emb": (emb / (np.abs(emb).max() or 1)).round(3).tolist(),
            "votes": votes, "p_dl": result["p_dl"], "p_ml": result["p_ml"], "score": result["score"],
            "th": system.thresholds, "color": lvl["hex"], "label": lvl["label"], "fired": fired, "captions": captions,
            "rules": [{"id": r[0], "label": LEVELS[r[1]]["label"], "color": LEVELS[r[1]]["hex"]} for r in system.rules]}


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
_ANIM = {"animationDuration": 900, "animationEasing": "cubicOut"}


def _style(fig: go.Figure, height: int) -> go.Figure:
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Plus Jakarta Sans, sans-serif"), showlegend=False)
    return fig


def ec_push_bars(names: list[str], values: list[float], axis_name: str) -> dict:
    """Horizontal diverging bars: red raises tomorrow's risk, blue lowers it (values in points)."""
    return {**_ANIM, "grid": {"left": 24, "right": 40, "top": 10, "bottom": 30, "containLabel": True},
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
            "xAxis": {"type": "value", "name": axis_name, "nameLocation": "middle", "nameGap": 24},
            "yAxis": {"type": "category", "data": names, "inverse": True, "axisTick": {"show": False},
                      "axisLine": {"onZero": False}, "axisLabel": {"margin": 12}},
            "series": [{"type": "bar", "barWidth": "60%", "label": {"show": True, "position": "right", "formatter": "{c}"},
                        "data": [{"value": round(v, 1), "itemStyle": {"color": UP if v > 0 else DOWN, "borderRadius": 4}}
                                 for v in values]}]}


def ec_day_bars(labels: list[str], values: list[float]) -> dict:
    return {**_ANIM, "grid": {"left": 8, "right": 8, "top": 16, "bottom": 8, "containLabel": True},
            "tooltip": {"trigger": "axis"}, "xAxis": {"type": "category", "data": labels, "axisLabel": {"fontSize": 10}},
            "yAxis": {"type": "value", "name": "points"},
            "series": [{"type": "bar", "barWidth": "55%",
                        "data": [{"value": round(v, 1), "itemStyle": {"color": UP if v > 0 else DOWN, "borderRadius": 4}}
                                 for v in values]}]}


def ec_trends(window: pd.DataFrame, rule_levels: dict, flood_line: float) -> dict:
    """Four small line charts for the week; dashed lines = warning levels (red one = the flood line)."""
    feats = ["water_area_km2", "water_area_change", "precipitation", "soil_moisture"]
    lines = {"water_area_km2": (flood_line, UP), "water_area_change": (rule_levels["rapid_rise"], LEVELS["FLOOD WATCH"]["hex"]),
             "precipitation": (rule_levels["heavy_rain"], LEVELS["FLOOD WATCH"]["hex"]),
             "soil_moisture": (rule_levels["wet_soil"], LEVELS["FLOOD WATCH"]["hex"])}
    x = window["date"].dt.strftime("%a").tolist()
    grids, xs, ys, series, titles = [], [], [], [], []
    for i, f in enumerate(feats):
        left = f"{2 + i * 25}%"
        grids.append({"left": left, "width": "21%", "top": 34, "bottom": 24, "containLabel": True})
        titles.append({"text": FRIENDLY[f], "left": left, "top": 0, "textStyle": {"fontSize": 12}})
        xs.append({"type": "category", "data": x, "gridIndex": i, "axisLabel": {"fontSize": 10}})
        ys.append({"type": "value", "gridIndex": i, "scale": True, "axisLabel": {"fontSize": 10}})
        level, color = lines[f]
        series.append({"type": "line", "xAxisIndex": i, "yAxisIndex": i, "smooth": 0.3, "symbolSize": 6,
                       "data": window[f].round(4).tolist(), "lineStyle": {"width": 2.5, "color": DOWN}, "itemStyle": {"color": DOWN},
                       "areaStyle": {"opacity": 0.12, "color": DOWN},
                       "markPoint": {"symbol": "circle", "symbolSize": 12, "itemStyle": {"color": UP},
                                     "data": [{"coord": [len(x) - 1, float(window[f].iloc[-1])]}], "label": {"show": False}},
                       "markLine": {"symbol": "none", "silent": True, "label": {"show": False},
                                    "lineStyle": {"type": "dashed", "color": color}, "data": [{"yAxis": level}]}})
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
