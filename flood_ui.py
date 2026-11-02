"""Shared loading, explainability and wording helpers for the Practical 10 website.

The prediction itself always goes through ``IntegratedFloodSystem.predict_window``
from ``system_core.py`` (the exact Practical 9 pipeline). The helpers here only add
model-interpretation (occlusion analysis) and plain-language presentation on top.
"""
from pathlib import Path
import json
import warnings

import numpy as np
import pandas as pd
import streamlit as st
import torch

from system_core import IntegratedFloodSystem, ENVIRONMENTAL_FEATURES

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "input_data" / "flood_dataset.csv"
ARTIFACT_DIR = BASE_DIR / "model_artifacts"
RESULT_DIR = BASE_DIR / "practical10_results"
PREDICTIONS_PATH = BASE_DIR / "validation_data_task9_predictions.csv"
COMPONENT_METRICS_PATH = BASE_DIR / "task9_component_metrics.csv"
SAMPLE_CSV_PATH = BASE_DIR / "sample_7_day_input.csv"

# ---------------------------------------------------------------------------
# Plain-language vocabulary
# ---------------------------------------------------------------------------
FRIENDLY_NAMES = {
    "precipitation": "Rainfall",
    "soil_moisture": "Soil moisture",
    "temperature": "Temperature",
    "humidity": "Humidity",
    "pressure": "Air pressure",
    "wind_speed": "Wind speed",
    "evaporation": "Evaporation",
    "water_area_km2": "Water-covered area",
    "water_area_change": "Change in water area",
    "precip_3day_avg": "Rainfall (3-day average)",
    "precip_7day_avg": "Rainfall (7-day average)",
    "temp_3day_avg": "Temperature (3-day average)",
    "soil_3day_avg": "Soil moisture (3-day average)",
    "season": "Time of year (season)",
}

FEATURE_HELP = {
    "precipitation": "How much rain fell that day.",
    "soil_moisture": "How wet the ground is. Wet ground cannot soak up more rain.",
    "temperature": "Air temperature that day.",
    "humidity": "How much moisture is in the air (%).",
    "pressure": "Atmospheric pressure. Low pressure often comes with storms.",
    "wind_speed": "Average wind speed.",
    "evaporation": "How much water evaporated back into the air.",
    "water_area_km2": "Area covered by surface water, measured from satellite (km²).",
    "water_area_change": "How much the water-covered area changed since the previous day (km²).",
    "precip_3day_avg": "Average rainfall over the last 3 days.",
    "precip_7day_avg": "Average rainfall over the last 7 days.",
    "temp_3day_avg": "Average temperature over the last 3 days.",
    "soil_3day_avg": "Average soil moisture over the last 3 days.",
}

# Advisory levels produced by the rule engine, from calmest to most severe.
ADVISORY_STYLE = {
    "LOW RISK": {
        "color": "green", "icon": ":material/check_circle:", "level": 1,
        "headline": "Low risk",
        "meaning": "Nothing unusual. Neither the AI models nor the safety rules found signs of flooding.",
        "action": "No action needed. Keep an eye on the weather as usual.",
    },
    "MONITOR": {
        "color": "blue", "icon": ":material/visibility:", "level": 2,
        "headline": "Monitor",
        "meaning": "The models are calm, but at least one environmental warning sign (rain, wet soil or rising water) is present.",
        "action": "Stay alert and check conditions again later.",
    },
    "FLOOD WATCH": {
        "color": "orange", "icon": ":material/warning:", "level": 3,
        "headline": "Flood watch",
        "meaning": "Flood signs are building up. The flood score is elevated or several warning signs appear together.",
        "action": "Be prepared. In a real system this is when people would get ready to act.",
    },
    "FLOOD WARNING": {
        "color": "red", "icon": ":material/flood:", "level": 4,
        "headline": "Flood warning",
        "meaning": "Both AI models agree that this looks like a flood day, or the combined flood score is very high.",
        "action": "In a real system this would call for action. (This demo is educational only.)",
    },
}

RULES = [
    {"key": "heavy_rain_rule", "feature": "precipitation", "threshold_key": "heavy_rain",
     "name": "Heavy rainfall", "plain": "Today's rainfall is unusually high"},
    {"key": "wet_soil_rule", "feature": "soil_moisture", "threshold_key": "wet_soil",
     "name": "Saturated soil", "plain": "The ground is already very wet"},
    {"key": "rapid_water_rise_rule", "feature": "water_area_change", "threshold_key": "rapid_water_rise",
     "name": "Rapid water rise", "plain": "Water-covered area grew sharply since yesterday"},
]


def pct(x: float) -> str:
    return f"{x:.0%}" if x >= 0.995 or x <= 0.005 else f"{x:.1%}"


# ---------------------------------------------------------------------------
# Cached loaders
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner="Loading the saved AI models…")
def load_system() -> IntegratedFloodSystem:
    with warnings.catch_warnings():
        # Artifacts were pickled with a nearby scikit-learn version; behaviour is identical.
        warnings.simplefilter("ignore")
        return IntegratedFloodSystem(ARTIFACT_DIR)


@st.cache_data(show_spinner=False)
def load_dataset() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_test_predictions() -> pd.DataFrame:
    p = pd.read_csv(PREDICTIONS_PATH)
    p["date"] = pd.to_datetime(p["date"])
    return p


@st.cache_data(show_spinner=False)
def load_component_metrics() -> pd.DataFrame:
    return pd.read_csv(COMPONENT_METRICS_PATH)


@st.cache_data(show_spinner=False)
def load_result_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(RESULT_DIR / name)


@st.cache_data(show_spinner=False)
def load_run_summary() -> dict:
    return json.loads((RESULT_DIR / "task10_run_summary.json").read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_metadata() -> dict:
    return json.loads((ARTIFACT_DIR / "task9_system_metadata.json").read_text(encoding="utf-8"))


def window_ending(df: pd.DataFrame, end_date, days: int = 7) -> pd.DataFrame:
    """Return the `days` consecutive rows ending on `end_date` (inclusive)."""
    idx = int(np.flatnonzero(df["date"].dt.normalize() == pd.Timestamp(end_date).normalize())[0])
    return df.iloc[idx - days + 1: idx + 1].copy()


def actual_label(df: pd.DataFrame, end_date):
    row = df.loc[df["date"].dt.normalize() == pd.Timestamp(end_date).normalize()]
    if row.empty or pd.isna(row.iloc[0]["flood_event"]):
        return None
    return "Flood" if int(row.iloc[0]["flood_event"]) == 1 else "No Flood"


def percentile_of(df: pd.DataFrame, feature: str, value: float) -> float:
    col = pd.to_numeric(df[feature], errors="coerce").dropna()
    return float((col < value).mean())


def typical_wording(p: float) -> str:
    if p >= 0.95: return "extremely high"
    if p >= 0.80: return "high"
    if p >= 0.60: return "above normal"
    if p >= 0.40: return "normal"
    if p >= 0.20: return "below normal"
    return "very low"


# ---------------------------------------------------------------------------
# Model interpretation: occlusion analysis
# ---------------------------------------------------------------------------
# Groups of model inputs that are hidden together. The two day-of-year columns
# describe one idea (season), so they are occluded as a pair.
def feature_groups(system: IntegratedFloodSystem) -> dict[str, list[int]]:
    names = system.feature_names
    groups = {f: [names.index(f)] for f in ENVIRONMENTAL_FEATURES}
    groups["season"] = [names.index("day_of_year_sin"), names.index("day_of_year_cos")]
    return groups


def scale_window(system: IntegratedFloodSystem, raw_window: pd.DataFrame) -> np.ndarray:
    """Validate, engineer and scale exactly as ``predict_window`` does. Returns (7, n_features)."""
    window = system.validate_window(raw_window)
    frame = window[ENVIRONMENTAL_FEATURES].copy()
    doy = window["date"].dt.dayofyear.to_numpy()
    frame["day_of_year_sin"] = np.sin(2 * np.pi * doy / 365.25)
    frame["day_of_year_cos"] = np.cos(2 * np.pi * doy / 365.25)
    frame = frame[system.feature_names]
    return system.scaler.transform(system.imputer.transform(frame)).astype(np.float32)


def score_scaled(system: IntegratedFloodSystem, batch: np.ndarray):
    """Score a batch of scaled windows (n, 7, n_features). Returns LSTM, RF and integrated probabilities."""
    with torch.no_grad():
        logits, emb = system.encoder(torch.from_numpy(batch).to(system.device))
        p_dl = torch.sigmoid(logits).cpu().numpy()
        emb = emb.cpu().numpy()
    p_ml = system.rf.predict_proba(emb)[:, 1]
    return p_dl, p_ml, 0.5 * (p_dl + p_ml)


def explain_window(system: IntegratedFloodSystem, raw_window: pd.DataFrame):
    """Occlusion explanation for one 7-day window.

    Each input (or each day) is replaced by its training-period average (0 after
    standard scaling) and the window is re-scored. The drop in flood probability
    is that input's contribution: positive = pushed towards Flood.
    """
    scaled = scale_window(system, raw_window)
    groups = feature_groups(system)
    batch = [scaled]
    for cols in groups.values():
        x = scaled.copy(); x[:, cols] = 0.0; batch.append(x)
    for d in range(system.window_days):
        x = scaled.copy(); x[d, :] = 0.0; batch.append(x)
    _, _, p = score_scaled(system, np.stack(batch))
    base = p[0]
    n_g = len(groups)
    feat = pd.DataFrame({
        "feature": list(groups.keys()),
        "Input": [FRIENDLY_NAMES[g] for g in groups],
        "Contribution": base - p[1:1 + n_g],
    })
    dates = system.validate_window(raw_window)["date"].dt.strftime("%a %d %b").tolist()
    days = pd.DataFrame({
        "Day": [f"Day {i + 1} · {d}" for i, d in enumerate(dates)],
        "Contribution": base - p[1 + n_g:],
    })
    return float(base), feat, days


@st.cache_data(show_spinner="Measuring which inputs matter most across all 204 unseen test days…")
def global_importance() -> pd.DataFrame:
    """Average occlusion effect over every held-out test window."""
    system = load_system()
    df = load_dataset()
    preds = load_test_predictions()
    groups = feature_groups(system)
    batch = []
    for d in preds["date"]:
        scaled = scale_window(system, window_ending(df, d, system.window_days))
        batch.append(scaled)
        for cols in groups.values():
            x = scaled.copy(); x[:, cols] = 0.0; batch.append(x)
    # One batched call is much faster than scoring each window separately.
    _, _, p = score_scaled(system, np.stack(batch))
    p = p.reshape(len(preds), len(groups) + 1)
    eff = p[:, :1] - p[:, 1:]
    out = pd.DataFrame({
        "feature": list(groups.keys()),
        "Input": [FRIENDLY_NAMES[g] for g in groups],
        "Average impact": np.abs(eff).mean(axis=0),
        "Average push": eff.mean(axis=0),
    })
    return out.sort_values("Average impact", ascending=False).reset_index(drop=True)


def plain_reason(output: dict, feat: pd.DataFrame) -> str:
    """One short paragraph explaining the decision to a non-expert."""
    p = output["integrated_probability"]
    top_up = feat[feat["Contribution"] > 0.01].sort_values("Contribution", ascending=False)["Input"].head(2).tolist()
    top_down = feat[feat["Contribution"] < -0.01].sort_values("Contribution")["Input"].head(2).tolist()
    parts = [f"The combined flood score is **{pct(p)}**."]
    if top_up:
        parts.append("The inputs that pushed the score **up** the most were " + " and ".join(f"**{t.lower()}**" for t in top_up) + ".")
    if top_down:
        parts.append("The inputs that pulled it **down** the most were " + " and ".join(f"**{t.lower()}**" for t in top_down) + ".")
    fired = [r["name"].lower() for r in RULES if output[r["key"]]]
    if fired:
        parts.append("Safety rules triggered: " + ", ".join(fired) + ".")
    else:
        parts.append("None of the three safety rules was triggered.")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Rule-engine transparency and shared result widgets
# ---------------------------------------------------------------------------
def decision_path(system: IntegratedFloodSystem, output: dict) -> list[dict]:
    """Re-trace the rule engine in system_core.predict_window, step by step, in plain words."""
    p, p_dl, p_ml = output["integrated_probability"], output["LSTM_probability"], output["Random_Forest_probability"]
    heavy, wet, rise = output["heavy_rain_rule"], output["wet_soil_rule"], output["rapid_water_rise_rule"]
    watch_cut = max(0.35, system.system_threshold)
    steps = [
        {"advisory": "FLOOD WARNING",
         "question": f"Do both models agree on Flood (LSTM ≥ {pct(system.dl_threshold)} and Random Forest ≥ {pct(system.ml_threshold)}), or is the combined score ≥ 75%?",
         "answer": (p_ml >= system.ml_threshold and p_dl >= system.dl_threshold) or p >= 0.75},
        {"advisory": "FLOOD WATCH",
         "question": f"Is the combined score ≥ {pct(watch_cut)}, or is rapid water rise seen together with heavy rain or wet soil?",
         "answer": p >= watch_cut or (rise and (heavy or wet))},
        {"advisory": "MONITOR",
         "question": "Is at least one environmental safety rule triggered?",
         "answer": heavy or wet or rise},
        {"advisory": "LOW RISK", "question": "Otherwise:", "answer": True},
    ]
    for s in steps:
        if s["answer"]:
            s["chosen"] = True
            break
    return steps


def show_advisory(output: dict, actual: str | None = None) -> None:
    style = ADVISORY_STYLE[output["AI_advisory"]]
    color = style["color"]
    with st.container(border=True):
        top = st.container(horizontal=True, vertical_alignment="center")
        top.markdown(f"## :{color}[{style['icon']} {style['headline']}]")
        top.badge(f"Classified as: {output['integrated_prediction']}",
                  color="red" if output["integrated_prediction"] == "Flood" else "green",
                  icon=":material/flood:" if output["integrated_prediction"] == "Flood" else ":material/sunny:")
        top.badge(f"Day checked: {output['target_date']}", color="gray", icon=":material/calendar_today:")
        st.markdown(f"**What it means:** {style['meaning']}")
        st.markdown(f"**What to do:** {style['action']}")
        level = style["level"]
        st.caption("Advisory scale:  " + "  →  ".join(
            (f"**:{s['color']}[{s['headline']}]**" if s["level"] == level else s["headline"])
            for s in ADVISORY_STYLE.values()))
    if actual is not None:
        right = actual == output["integrated_prediction"]
        if right:
            st.success(f"The dataset records this day as **{actual}**, so the system was **correct**.",
                       icon=":material/task_alt:", title="Was it right? Yes")
        elif actual == "Flood":
            st.error("The dataset records a **flood** on this day, but the system said No Flood. "
                     "This is a **missed flood (false negative)**, the most serious kind of error.",
                     icon=":material/cancel:", title="Was it right? No: missed flood")
        else:
            st.error("The dataset records **no flood** on this day, but the system said Flood. "
                     "This is a **false alarm (false positive)**.",
                     icon=":material/cancel:", title="Was it right? No: false alarm")


def show_scores(system: IntegratedFloodSystem, output: dict) -> None:
    rows = [
        ("Deep learning (LSTM)", output["LSTM_probability"], system.dl_threshold,
         "Reads the 7 days in order, like reading a sentence, and learns patterns over time."),
        ("Machine learning (Random Forest)", output["Random_Forest_probability"], system.ml_threshold,
         "250 decision trees vote, using the summary the LSTM produced."),
        ("Combined flood score", output["integrated_probability"], system.system_threshold,
         "Average of the two. At or above the line means Flood."),
    ]
    for name, value, thr, help_text in rows:
        verdict = "above" if value >= thr else "below"
        st.progress(min(max(value, 0.0), 1.0),
                    text=f"**{name}: {pct(value)}** · {verdict} its Flood line of {pct(thr)}")
        st.caption(help_text)


def contribution_chart(feat: pd.DataFrame, top_n: int = 10):
    import altair as alt
    d = feat.copy()
    d["abs"] = d["Contribution"].abs()
    d = d.sort_values("abs", ascending=False).head(top_n)
    d["Direction"] = np.where(d["Contribution"] >= 0, "Pushed towards Flood", "Pushed towards No Flood")
    d["Points"] = d["Contribution"] * 100
    return (
        alt.Chart(d)
        .mark_bar(cornerRadius=4)
        .encode(
            x=alt.X("Points:Q", title="Change in flood score (percentage points)"),
            y=alt.Y("Input:N", sort=alt.SortField("abs", order="descending"), title=None, axis=alt.Axis(labelLimit=240)),
            color=alt.Color("Direction:N",
                            scale=alt.Scale(domain=["Pushed towards Flood", "Pushed towards No Flood"],
                                            range=["#D93A3A", "#0B6BCB"]),
                            legend=alt.Legend(orient="bottom", title=None)),
            tooltip=["Input", alt.Tooltip("Points:Q", format="+.1f", title="Points")],
        )
        .properties(height=max(220, 30 * len(d)))
    )


def day_chart(days: pd.DataFrame):
    import altair as alt
    d = days.copy()
    d["Points"] = d["Contribution"] * 100
    d["Direction"] = np.where(d["Contribution"] >= 0, "Towards Flood", "Towards No Flood")
    return (
        alt.Chart(d)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("Day:N", sort=None, title=None, axis=alt.Axis(labelAngle=0, labelLimit=120)),
            y=alt.Y("Points:Q", title="Effect on flood score (points)"),
            color=alt.Color("Direction:N", scale=alt.Scale(domain=["Towards Flood", "Towards No Flood"],
                                                           range=["#D93A3A", "#0B6BCB"]),
                            legend=alt.Legend(orient="bottom", title=None)),
            tooltip=["Day", alt.Tooltip("Points:Q", format="+.1f")],
        )
        .properties(height=260)
    )


def rule_rows(system: IntegratedFloodSystem, df: pd.DataFrame, window: pd.DataFrame, output: dict) -> pd.DataFrame:
    last = window.sort_values("date").iloc[-1]
    rows = []
    for r in RULES:
        value = pd.to_numeric(last[r["feature"]], errors="coerce")
        thr = system.rule_thresholds[r["threshold_key"]]
        rows.append({
            "Triggered": bool(output[r["key"]]),
            "Safety rule": r["name"],
            "Plain meaning": r["plain"],
            "Today's value": None if pd.isna(value) else float(value),
            "Trigger level": float(thr),
            "Trigger is higher than": f"{percentile_of(df, r['feature'], thr):.0%} of all days",
        })
    return pd.DataFrame(rows)
