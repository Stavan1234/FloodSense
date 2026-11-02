import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from flood_ui import DOWN, FRIENDLY, GREY, LEVELS, UP, _ANIM, _style, ec_day_bars, load_csv, load_predictions, load_summary, load_system
from fs_components import count_up_kpis

system = load_system()
preds = load_predictions()
summary = load_summary()
c, m = summary["confusion"], summary["metrics"]

OUTCOMES = {  # name → (colour, marker symbol); symbol differs too, so colour is not the only cue
    "Caught flood": (UP, "square"),
    "Missed flood": (UP, "square-open"),
    "False alarm": ("#E8820C", "diamond"),
    "Correct calm day": ("#B9D4EE", "square"),
}
preds["Outcome"] = np.select(
    [(preds.Actual == "Flood") & (preds.Prediction == "Flood"), (preds.Actual == "Flood"), (preds.Prediction == "Flood")],
    ["Caught flood", "Missed flood", "False alarm"], "Correct calm day")

st.title("Can I trust it?", icon=":material/verified_user:")
st.caption(f"Every number here comes from {len(preds)} days the AI never saw during training "
           f"({preds['date'].min():%d %b} – {preds['date'].max():%d %b %Y}).")

acc_tab, time_tab, look_tab, safe_tab, limit_tab = st.tabs(
    [":material/grid_view: Accuracy", ":material/timeline: Over time", ":material/visibility: What it looks at",
     ":material/shield: Safety checks", ":material/report: Limits"])

with acc_tab:
    st.markdown(f"#### It caught **{c['tp']} of {c['tp'] + c['fn']}** floods, with **{c['fp']}** false alarms.")
    count_up_kpis([
        {"label": "Days judged correctly", "value": m["Accuracy"] * 100, "suffix": "%", "color": LEVELS["LOW RISK"]["hex"],
         "help": "Accuracy: share of all days right"},
        {"label": "Floods caught", "value": m["Recall"] * 100, "suffix": "%", "color": LEVELS["FLOOD WARNING"]["hex"],
         "help": "Recall: share of real floods flagged"},
        {"label": "Flood alerts that were real", "value": m["Precision"] * 100, "suffix": "%", "color": LEVELS["MONITOR"]["hex"],
         "help": "Precision: alerts where a flood really happened"},
    ], key="trust_kpis")
    d = preds.copy()
    d["week"] = ((d["date"] - d["date"].min()).dt.days + d["date"].min().day_of_week) // 7
    d["weekday"] = d["date"].dt.day_of_week
    fig = go.Figure()
    for name, (color, symbol) in OUTCOMES.items():
        part = d[d.Outcome == name]
        fig.add_trace(go.Scatter(
            x=part["week"], y=part["weekday"], mode="markers", name=f"{name} ({len(part)})",
            marker=dict(size=15, symbol=symbol.replace("-open", ""),   # hollow look, but still clickable
                        color="rgba(217,58,58,0.12)" if "open" in symbol else color,
                        line=dict(width=2.5 if "open" in symbol else 0, color=color)),
            customdata=part["date"].dt.strftime("%Y-%m-%d"),
            hovertemplate="%{customdata}<br>" + name + "<extra></extra>"))
    months = d.groupby(d["date"].dt.to_period("M"))["week"].min()
    fig.update_xaxes(tickvals=months.values, ticktext=[p.strftime("%b") for p in months.index], showgrid=False)
    fig.update_yaxes(tickvals=list(range(7)), ticktext=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                     autorange="reversed", showgrid=False)
    fig = _style(fig, 300).update_layout(showlegend=True, legend=dict(orientation="h", y=-0.15), dragmode=False)
    st.caption("Each square is one day. **Click a day** to open it in Check a day.")
    event = st.plotly_chart(fig, on_select="rerun", selection_mode="points", key="calendar",
                            config={"displayModeBar": False})
    points = event.selection.points if event and event.selection else []
    if points:
        st.session_state.day = pd.Timestamp(points[0]["customdata"]).date()
        st.session_state.source = "Dataset"
        st.switch_page("app_pages/check_day.py")

with time_tab:
    monthly = load_csv("monthly_performance.csv")
    weakest = monthly.loc[monthly["Recall"].idxmin()]
    st.markdown(f"#### Steady across the season; weakest in **{pd.Period(weakest['month']):%B}** "
                f"({weakest['Recall']:.0%} of floods caught).")
    dates = preds["date"].dt.strftime("%Y-%m-%d").tolist()
    marks = []
    for name in ["Caught flood", "Missed flood", "False alarm"]:
        color, symbol = OUTCOMES[name]
        part = preds[preds.Outcome == name]
        marks.append({"type": "scatter", "name": name, "symbolSize": 10,
                      "symbol": {"square": "rect", "square-open": "emptyRect", "diamond": "diamond"}[symbol],
                      "itemStyle": {"color": color},
                      "data": [[dt, round(v * 100, 1)] for dt, v in zip(part["date"].dt.strftime("%Y-%m-%d"), part["Combined"])]})
    st.echarts_chart({
        **_ANIM, "tooltip": {"trigger": "axis"}, "legend": {"top": 0},
        "grid": {"left": 8, "right": 16, "top": 40, "bottom": 50, "containLabel": True},
        "xAxis": {"type": "time"}, "yAxis": {"type": "value", "name": "Flood score %", "min": 0, "max": 100},
        "dataZoom": [{"type": "inside"}, {"type": "slider", "height": 18, "bottom": 8}],
        "series": [{"type": "line", "name": "Flood score", "showSymbol": False, "lineStyle": {"width": 1.2, "color": GREY},
                    "areaStyle": {"opacity": 0.08}, "data": [[dt, round(v * 100, 1)] for dt, v in zip(dates, preds["Combined"])],
                    "markLine": {"symbol": "none", "silent": True, "lineStyle": {"type": "dashed", "color": "#7A5AF8"},
                                 "label": {"formatter": "flood line"}, "data": [{"yAxis": system.thresholds["sys"] * 100}]}}]
                  + marks}, height=340)
    names = [pd.Period(p).strftime("%b") for p in monthly["month"]]
    st.echarts_chart({
        **_ANIM, "tooltip": {"trigger": "axis"}, "legend": {"top": 0},
        "grid": {"left": 8, "right": 8, "top": 36, "bottom": 8, "containLabel": True},
        "xAxis": {"type": "category", "data": names}, "yAxis": {"type": "value", "max": 100, "name": "%"},
        "series": [{"type": "bar", "name": "Floods caught", "itemStyle": {"color": UP, "borderRadius": 4},
                    "data": (monthly["Recall"] * 100).round(0).tolist()},
                   {"type": "bar", "name": "Alerts that were real", "itemStyle": {"color": DOWN, "borderRadius": 4},
                    "data": (monthly["Precision"] * 100).round(0).tolist()}]}, height=260)

with look_tab:
    feats = load_csv("shap_features.csv").set_index("feature")["mean_abs_shap"]
    feats["season"] = feats.pop("day_of_year_sin") + feats.pop("day_of_year_cos")
    feats = feats.sort_values(ascending=False)
    top2 = [FRIENDLY[f] for f in feats.index[:2]]
    st.markdown(f"#### Most decisions are driven by **{top2[0].lower()}** and **{top2[1].lower()}**.")
    a, b = st.columns([1.5, 1], gap="large")
    with a:
        st.echarts_chart({
            **_ANIM, "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
            "grid": {"left": 8, "right": 30, "top": 8, "bottom": 30, "containLabel": True},
            "xAxis": {"type": "value", "name": "average push (points) · SHAP", "nameLocation": "middle", "nameGap": 24},
            "yAxis": {"type": "category", "inverse": True, "data": [FRIENDLY[f] for f in feats.index], "axisTick": {"show": False}},
            "series": [{"type": "bar", "barWidth": "60%", "data": [
                {"value": round(v * 100, 1), "itemStyle": {"color": UP if i < 2 else GREY, "borderRadius": 4}}
                for i, v in enumerate(feats.values)]}]}, height=420)
    with b:
        days = load_csv("shap_days.csv")
        st.markdown("**Which day of the week matters**")
        st.echarts_chart(ec_day_bars(days["day"].str.replace("Day ", "").tolist(), (days["mean_abs_shap"] * 100).tolist()),
                         height=280)
        st.caption("The checked day itself carries most of the weight; earlier days add context.")

with safe_tab:
    tests = load_csv("robustness_tests.csv")
    passed = int((tests["Result"] == "PASS").sum())
    st.markdown(f"#### It refuses broken input instead of guessing: **{passed} of {len(tests)}** checks passed.")
    cols = st.columns(2, gap="medium")
    for i, t in tests.reset_index(drop=True).iterrows():
        ok = t["Result"] == "PASS"
        with cols[i % 2].container(border=True):
            st.markdown(f"{':green[:material/check_circle:]' if ok else ':red[:material/cancel:]'} **{t['Test']}**  \n"
                        f":gray[{t['Outcome']}]")

with limit_tab:
    st.markdown("#### A strong classroom prototype, **not** a real warning service.")
    cards = [
        (":material/today:", "Same day, not tomorrow", "It judges the last day of the week it reads. It does not forecast."),
        (":material/location_on:", "One place only", "All data comes from a single point (19°N, 73°E). Other places may behave differently."),
        (":material/label_off:", "Labels look simulated", "About 35 % of days are floods in every month, with no monsoon peak."),
        (":material/water:", "Water area may be the flood", "Its top clue is satellite water-area change, which may show a flood already happening."),
    ]
    cols = st.columns(2, gap="medium")
    for i, (icon, title, text) in enumerate(cards):
        with cols[i % 2].container(border=True, height="stretch"):
            st.markdown(f"**{icon} {title}**")
            st.caption(text)
