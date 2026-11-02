import pandas as pd
import streamlit as st

from flood_ui import (
    DATA_DIR, LEVELS, _ANIM, cached_trace, load_data, load_predictions, load_summary, load_system, percentile,
)
from fs_components import count_up_kpis, engine_walkthrough

system = load_system()
summary = load_summary()
df, preds = load_data(), load_predictions()
H, TREES, DEPTH = system.hidden_size, system.ml_model.max_iter, system.ml_model.max_depth
N_IN, N_SEL, DAYS = len(system.lstm_inputs), len(system.selected), system.window_days
N_ALL = DAYS * len(system.ml_daily)
PARAMS = sum(p.numel() for p in system.encoder.parameters())
COMP = summary["components"]
FIG = DATA_DIR / "figures"
blue, green, purple, orange, grey, red = "#0B6BCB", "#1A9E5C", "#7A5AF8", "#E8820C", "#8C9AAB", "#D93A3A"

STYLE = """
<style>
.fs-svg { width: 100%; height: auto; font-family: 'Plus Jakarta Sans', sans-serif; }
.fs-svg text { fill: currentColor; }
.fs-flow { stroke-dasharray: 6 6; animation: fs-march 1.2s linear infinite; }
@keyframes fs-march { to { stroke-dashoffset: -12; } }
.fs-pulse { animation: fs-pulse 2.4s ease-in-out infinite; }
@keyframes fs-pulse { 0%, 100% { opacity: .55; } 50% { opacity: 1; } }
@media (prefers-reduced-motion: reduce) { .fs-flow, .fs-pulse { animation: none; } }
</style>
"""
DEFS = ('<defs><marker id="fs-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
        '<path d="M0,0 L10,5 L0,10 z" fill="#8C9AAB"/></marker></defs>')


def box(x, y, w, h, color, title, sub="", sub2="", size=15):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{color}22" stroke="{color}" stroke-width="2"/>'
            f'<text x="{x + w / 2}" y="{y + h / 2 - (12 if sub2 else 6)}" text-anchor="middle" font-size="{size}" font-weight="700">{title}</text>'
            f'<text x="{x + w / 2}" y="{y + h / 2 + (8 if sub2 else 14)}" text-anchor="middle" font-size="12" opacity=".75">{sub}</text>'
            + (f'<text x="{x + w / 2}" y="{y + h / 2 + 26}" text-anchor="middle" font-size="12" opacity=".75">{sub2}</text>' if sub2 else ""))


def arrow(x1, y1, x2, y2, label="", color=grey):
    lab = (f'<text x="{(x1 + x2) / 2}" y="{min(y1, y2) - 8}" text-anchor="middle" font-size="11" font-weight="600" opacity=".7">{label}</text>'
           if label else "")
    return f'<line class="fs-flow" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="2.5" marker-end="url(#fs-arrow)"/>' + lab


def svg(body: str, width: int, height: int) -> None:
    st.markdown(STYLE + f'<svg class="fs-svg" viewBox="0 0 {width} {height}">{DEFS}{body}</svg>', unsafe_allow_html=True)


def gallery(key: str, figures: dict[str, tuple[str, str]]) -> None:
    """One notebook figure at a time, picked with a segmented control, with a one-line takeaway."""
    choice = st.segmented_control("Evidence from the notebook", list(figures), default=list(figures)[0],
                                  required=True, key=key)
    file, takeaway = figures[choice]
    st.image(str(FIG / file), width="stretch")
    st.caption(f":material/lightbulb: {takeaway}")


def comp(name: str, metric: str) -> float:
    return COMP[name][metric] * 100


# ======================================================================================
st.title("How it works", icon=":material/account_tree:")
st.caption("Three kinds of AI working together: deep learning and machine learning each forecast tomorrow, "
           "their scores are blended, and readable rules decide the advisory.")

CASES = {"A flood it caught": (preds.Actual == "Flood") & (preds.Prediction == "Flood"),
         "A calm day": (preds.Actual == "No Flood") & (preds.Advisory == "LOW RISK"),
         "A flood it missed": (preds.Actual == "Flood") & (preds.Prediction == "No Flood")}
case = st.segmented_control("Follow one real day through the engine", list(CASES), default="A flood it caught",
                            required=True, key="engine_case")
rows = preds[CASES[case]]
day = rows.loc[rows["Combined"].sub(rows["Combined"].median()).abs().idxmin(), "today"].date()
engine_walkthrough(cached_trace(str(day)), key="engine")

st.space("medium")
st.subheader("The big picture", icon=":material/hub:")
svg(box(10, 70, 170, 100, grey, "Last 7 days", "satellite water area", "+ weather")
    + arrow(180, 105, 290, 60, "8 inputs / day", blue) + arrow(180, 135, 290, 180, f"{N_SEL} best readings", green)
    + box(295, 15, 200, 90, blue, "LSTM (DL)", "reads the days in order")
    + box(295, 135, 200, 90, green, "Gradient Boosting (ML)", f"{TREES} small trees")
    + arrow(495, 60, 600, 105, f"{system.w_dl:.0%}", blue) + arrow(495, 180, 600, 135, f"{1 - system.w_dl:.0%}", green)
    + box(605, 70, 160, 100, purple, "Blended score", "P(flood tomorrow)")
    + arrow(765, 120, 830, 120, "", purple) + box(835, 70, 170, 100, orange, "AI rules", "→ one of 4 advisories"),
    1015, 240)
st.caption(f"Why forecast tomorrow? In this dataset a day is labelled *flood* exactly when the satellite sees at least "
           f"{system.flood_line:,.0f} km² of water. Checking *today* would just mean reading that number, so the real, "
           f"useful question is whether the water will cross the line **tomorrow**.")

st.space("small")
st.subheader("Meet the three engines", icon=":material/widgets:")
dl_tab, ml_tab, ai_tab, card_tab = st.tabs([":material/neurology: Deep learning", ":material/forest: Machine learning",
                                            ":material/rule: AI rules", ":material/badge: Model card"])

# ------------------------------------------------------------------------------ deep learning
with dl_tab:
    st.markdown("#### An LSTM reads the week **in order**, like reading a sentence, and remembers what matters.")
    count_up_kpis([
        {"label": "Memory size", "value": H, "suffix": " numbers", "color": blue, "help": "What it carries from day to day"},
        {"label": "Learned weights", "value": PARAMS, "color": purple, "help": "Small on purpose: ~760 training weeks"},
        {"label": "Floods caught alone", "value": comp("LSTM alone (DL)", "Recall"), "suffix": "%", "color": red,
         "help": f"On the {len(preds)} unseen test forecasts"},
        {"label": "Ranking quality", "value": comp("LSTM alone (DL)", "ROC-AUC"), "suffix": "%", "color": green,
         "help": "ROC-AUC: flood-tomorrow days scored above calm ones"},
    ], key="dl_kpis")

    st.markdown("**Unrolled over the week**: one cell, reused every day")
    cw, gap, top = 92, 30, 50
    cells = ""
    for d in range(DAYS):
        x = 20 + d * (cw + gap)
        last = d == DAYS - 1
        label = "Today" if last else f"Day −{DAYS - 1 - d}"
        cells += (f'<rect class="fs-pulse" style="animation-delay:{d * 0.25}s" x="{x}" y="{top}" width="{cw}" height="70" rx="12" '
                  f'fill="{blue}{"40" if last else "22"}" stroke="{blue}" stroke-width="2"/>'
                  f'<text x="{x + cw / 2}" y="{top + 32}" text-anchor="middle" font-size="14" font-weight="700">LSTM</text>'
                  f'<text x="{x + cw / 2}" y="{top + 52}" text-anchor="middle" font-size="11" opacity=".75">cell</text>'
                  f'<line class="fs-flow" x1="{x + cw / 2}" y1="{top + 140}" x2="{x + cw / 2}" y2="{top + 74}" stroke="{grey}" stroke-width="2" marker-end="url(#fs-arrow)"/>'
                  f'<text x="{x + cw / 2}" y="{top + 160}" text-anchor="middle" font-size="12" font-weight="{700 if last else 500}">{label}</text>'
                  f'<text x="{x + cw / 2}" y="{top + 176}" text-anchor="middle" font-size="10.5" opacity=".65">{N_IN} inputs</text>')
        if d < DAYS - 1:
            cells += arrow(x + cw, top + 35, x + cw + gap - 3, top + 35, "memory" if d == 0 else "", blue)
    end_x = 20 + DAYS * (cw + gap) - gap
    svg(cells + arrow(end_x, top + 35, end_x + 50, top + 35, "", blue)
        + box(end_x + 54, top - 15, 150, 100, purple, "Tomorrow", "P(flood)", f"from {H} memory numbers"), 1090, 240)
    st.caption("Its 8 inputs per day: water area, change in water area, days flooded in a row, dry days in a row, "
               "rain, soil moisture and the season (two numbers for the time of year).")

    a, b = st.columns([1, 1.25], gap="large", vertical_alignment="center")
    with a:
        st.markdown("**Inside one cell**: three gates decide what to keep")
        gates = ""
        for i, (name, text, color) in enumerate([("Forget", "drop what no longer matters", red),
                                                  ("Input", "add what today brings", green),
                                                  ("Output", "decide what to pass on", blue)]):
            gx = 60 + i * 170
            gates += (f'<circle class="fs-pulse" style="animation-delay:{i * 0.6}s" cx="{gx + 40}" cy="120" r="28" fill="{color}22" stroke="{color}" stroke-width="2"/>'
                      f'<text x="{gx + 40}" y="125" text-anchor="middle" font-size="16" font-weight="800">σ</text>'
                      f'<text x="{gx + 40}" y="172" text-anchor="middle" font-size="13" font-weight="700">{name}</text>'
                      f'<text x="{gx + 40}" y="189" text-anchor="middle" font-size="10.5" opacity=".7">{text}</text>'
                      f'<line class="fs-flow" x1="{gx + 40}" y1="92" x2="{gx + 40}" y2="58" stroke="{color}" stroke-width="2" marker-end="url(#fs-arrow)"/>')
        svg(f'<rect x="10" y="20" width="560" height="190" rx="18" fill="{blue}10" stroke="{blue}" stroke-width="2"/>'
            f'<line class="fs-flow" x1="20" y1="48" x2="560" y2="48" stroke="{purple}" stroke-width="3" marker-end="url(#fs-arrow)"/>'
            f'<text x="290" y="40" text-anchor="middle" font-size="12" font-weight="700" opacity=".8">long-term memory</text>'
            + gates, 580, 220)
    with b:
        gallery("dl_fig", {
            "Training": ("task7_learning_curves.png",
                         "Several set-ups were tried; the one with the lowest validation loss was kept (early stopping)."),
            "What it looks at": ("task8_shap_heatmap.png",
                                 "SHAP: today's change in water area and the water level drive the LSTM most; rain barely matters."),
            "Inside the memory": ("task8_activations.png",
                                  "Memory units behave differently before a flood, most strongly on the last two days."),
        })

# ------------------------------------------------------------------------------ machine learning
with ml_tab:
    st.markdown(f"#### Gradient Boosting: **{TREES} small trees**, each one fixing the mistakes of the trees before it.")
    count_up_kpis([
        {"label": "Trees in the chain", "value": TREES, "color": green, "help": f"Each only {DEPTH} questions deep"},
        {"label": "Readings it uses", "value": N_SEL, "suffix": f" of {N_ALL}", "color": purple,
         "help": "Picked by mutual information + Random Forest ranking; the count chosen by cross-validation"},
        {"label": "Floods caught alone", "value": comp("Gradient Boosting alone (ML)", "Recall"), "suffix": "%",
         "color": red, "help": f"On the {len(preds)} unseen test forecasts"},
        {"label": "Flood alerts that were real", "value": comp("Gradient Boosting alone (ML)", "Precision"),
         "suffix": "%", "color": blue, "help": "Precision"},
    ], key="ml_kpis")
    trees = ""
    for i in range(5):
        tx, ty = 250 + i * 120, 40
        nodes = [(tx, ty), (tx - 26, ty + 40), (tx + 26, ty + 40), (tx - 40, ty + 80), (tx - 12, ty + 80), (tx + 12, ty + 80), (tx + 40, ty + 80)]
        edges = [(0, 1), (0, 2), (1, 3), (1, 4), (2, 5), (2, 6)]
        trees += "".join(f'<line x1="{nodes[a][0]}" y1="{nodes[a][1]}" x2="{nodes[b][0]}" y2="{nodes[b][1]}" stroke="{green}" stroke-width="2" opacity=".6"/>' for a, b in edges)
        trees += "".join(f'<circle cx="{x}" cy="{y}" r="7" fill="{green}" opacity="{0.9 if k == 0 else 0.55}"/>' for k, (x, y) in enumerate(nodes))
        name = "tree 1" if i == 0 else (f"tree {TREES}" if i == 4 else ("…" if i == 3 else f"tree {i + 1}"))
        trees += f'<text x="{tx}" y="{ty + 115}" text-anchor="middle" font-size="12" font-weight="700" opacity=".8">{name}</text>'
        if i < 4:
            trees += arrow(tx + 46, ty + 40, tx + 72, ty + 40, "errors" if i == 0 else "", orange)
    svg(box(10, 50, 150, 90, purple, f"{N_SEL} readings", "from the last 7 days") + arrow(160, 95, 200, 80) + trees
        + '<text x="490" y="200" text-anchor="middle" font-size="12" opacity=".75">each tree learns what the earlier ones '
          'still got wrong · their outputs are added up</text>'
        + arrow(800, 80, 850, 95) + box(855, 50, 180, 100, green, "Sum → P(flood)", "tomorrow"), 1050, 220)
    st.caption("Its top readings are the water area on each of the last days and the latest change in water area. "
               "Weather alone forecasts badly here (F1 0.23): the floods come from river water, not local rain.")
    gallery("ml_fig", {
        "Why Gradient Boosting": ("task6_model_comparison.png",
                                  "Five models on the same days: Gradient Boosting scored highest, well above the copy-today baseline."),
        "What 'flood' means here": ("task4_label_definition.png",
                                    f"A flood day is exactly a day with ≥ {system.flood_line:,.0f} km² of water, so we forecast tomorrow instead."),
        "Choosing the flood lines": ("task9_thresholds.png",
                                     "The flood lines and the blend were chosen by time-series cross-validation, never on test days."),
    })

# ------------------------------------------------------------------------------ AI rules
with ai_tab:
    st.markdown(f"#### The scores are blended **{system.w_dl:.0%} LSTM + {1 - system.w_dl:.0%} Gradient Boosting**, "
                "then readable **IF → THEN** rules pick one of four levels. The first rule that fits wins.")
    cols = st.columns(4, gap="small")
    for col, (rule_id, advisory, text, _) in zip(cols, system.rules):
        lvl = LEVELS[advisory]
        with col.container(border=True, height="stretch"):
            st.markdown(f":{lvl['color']}[{lvl['icon']} **{rule_id} · {lvl['label']}**]")
            st.caption(f"IF {text[0].lower() + text[1:]}")
            st.badge(lvl["action"], color=lvl["color"])
    st.markdown("**The Monitor warning signs** · rain, soil and rise mean *unusual for this place* (top 10 % of training days)")
    levels = system.rule_levels
    signs = [("Water near the line", "water_area_km2", levels["near_line"],
              f"water area ≥ {levels['near_line']:,.0f} km² (85 % of the flood line)"),
             ("Heavy rain", "precipitation", levels["heavy_rain"], f"rainfall ≥ {levels['heavy_rain']:.2f}"),
             ("Very wet soil", "soil_moisture", levels["wet_soil"], f"soil moisture ≥ {levels['wet_soil']:.3f}"),
             ("Water rising fast", "water_area_change", levels["rapid_rise"], f"water area +{levels['rapid_rise']:,.0f} km² in a day")]
    count_up_kpis([{"label": name, "value": (1 - percentile(df, feat, lvl)) * 100, "suffix": "% of days",
                    "color": orange, "help": rule} for name, feat, lvl, rule in signs], key="sign_kpis")
    st.caption("A day that is already flooded also raises at least a Monitor.")
    gallery("ai_fig", {
        "What each advisory contained": ("task9_integration_results.png",
                                         "On the test months every Flood warning was followed by a flood; no Low risk day was."),
        "Month by month": ("task10_monthly.png",
                           "Accuracy stays high in every test month; recall is weakest in the short December sample."),
    })

# ------------------------------------------------------------------------------ model card
with card_tab:
    st.markdown("#### Everything about the model on one card.")
    names = ["Baseline: tomorrow = today", "LSTM alone (DL)", "Gradient Boosting alone (ML)", "Integrated score (DL+ML)"]
    short = ["Copy today", "LSTM", "Gradient Boosting", "Combined"]
    metrics = ["Accuracy", "Precision", "Recall", "F1"]
    st.echarts_chart({
        **_ANIM, "tooltip": {"trigger": "axis"}, "legend": {"top": 0},
        "grid": {"left": 8, "right": 8, "top": 36, "bottom": 8, "containLabel": True},
        "xAxis": {"type": "category", "data": ["Accuracy", "Alerts that were real", "Floods caught", "F1 (balance)"]},
        "yAxis": {"type": "value", "min": 50, "max": 100, "name": "% on unseen days"},
        "series": [{"type": "bar", "name": s, "itemStyle": {"color": c, "borderRadius": 4},
                    "data": [round(COMP[n][m] * 100, 1) for m in metrics]}
                   for n, s, c in zip(names, short, [grey, blue, green, purple])]}, height=280)
    train, val, test = summary["splits"]["train"], summary["splits"]["validation"], summary["splits"]["test"]
    card = pd.DataFrame([
        ("Task", "Next-day flood forecast: read days t−6 … t, predict whether day t+1 floods"),
        ("Location", f"One satellite-monitored point · {summary['location']}"),
        ("Data", "Daily, 2022–2024 · days with two satellite passes merged (larger water area) · leaky column removed"),
        ("Data split (by date)", f"Train {train[0]} → {train[1]} · Validation {val[0]} → {val[1]} · Test {test[0]} → {test[1]}"),
        ("Deep learning", f"{summary['lstm_config']} · {N_IN} inputs/day · {PARAMS:,} weights · Adam, early stopping"),
        ("Machine learning", f"Gradient Boosting · {TREES} trees · depth {DEPTH} · {N_SEL} of {N_ALL} readings"),
        ("Combination", f"{system.w_dl:.0%} LSTM + {1 - system.w_dl:.0%} Gradient Boosting (time-series cross-validation, F2)"),
        ("Flood lines", f"LSTM {system.thresholds['dl']:.2f} · GB {system.thresholds['ml']:.2f} · "
                        f"combined {system.thresholds['sys']:.2f} · Watch from {system.watch_level:.0%}"),
        ("Explanations", "SHAP in the notebook; on this site, occlusion (swap a reading for a typical value)"),
        ("Known limits", "One location · the label is a satellite water threshold · one day ahead only"),
    ], columns=["", "Details"])
    st.dataframe(card, hide_index=True, width="stretch")
