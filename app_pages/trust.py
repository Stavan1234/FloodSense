import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from flood_ui import DOWN, FRIENDLY, GREY, UP, _style, load_csv, load_predictions, load_summary, load_system

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
    with st.container(horizontal=True):
        st.metric("Days judged correctly", f"{m['Accuracy']:.0%}", border=True, help="Accuracy: share of all days right.")
        st.metric("Floods caught", f"{m['Recall']:.0%}", border=True, help="Recall: share of real floods flagged.")
        st.metric("Flood alerts that were real", f"{m['Precision']:.0%}", border=True,
                  help="Precision: share of flood alerts where a flood really happened.")
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
    fig = go.Figure(go.Scatter(x=preds["date"], y=preds["Combined"] * 100, mode="lines", line=dict(color=GREY, width=1.2),
                               hovertemplate="%{x|%d %b}: %{y:.0f}%<extra></extra>", name="Flood score"))
    for name in ["Caught flood", "Missed flood", "False alarm"]:
        color, symbol = OUTCOMES[name]
        part = preds[preds.Outcome == name]
        fig.add_trace(go.Scatter(x=part["date"], y=part["Combined"] * 100, mode="markers", name=name,
                                 marker=dict(size=9, color=color, symbol=symbol, line=dict(width=2, color=color)),
                                 hovertemplate="%{x|%d %b}: %{y:.0f}%<extra>" + name + "</extra>"))
    fig.add_hline(y=system.thresholds["sys"] * 100, line=dict(color="#7A5AF8", dash="dash"),
                  annotation_text="flood line", annotation_position="top left")
    fig.update_yaxes(title="Flood score (%)", range=[-3, 103])
    st.plotly_chart(_style(fig, 320).update_layout(showlegend=True, legend=dict(orientation="h", y=1.12)),
                    config={"displayModeBar": False})
    bars = go.Figure([go.Bar(x=[pd.Period(p).strftime("%b") for p in monthly["month"]], y=monthly["Recall"] * 100,
                             name="Floods caught", marker_color=UP),
                      go.Bar(x=[pd.Period(p).strftime("%b") for p in monthly["month"]], y=monthly["Precision"] * 100,
                             name="Alerts that were real", marker_color=DOWN)])
    bars.update_yaxes(title="%", range=[0, 105])
    st.plotly_chart(_style(bars, 240).update_layout(showlegend=True, legend=dict(orientation="h", y=1.15), barmode="group"),
                    config={"displayModeBar": False})

with look_tab:
    feats = load_csv("shap_features.csv").set_index("feature")["mean_abs_shap"]
    feats["season"] = feats.pop("day_of_year_sin") + feats.pop("day_of_year_cos")
    feats = feats.sort_values()
    top2 = [FRIENDLY[f] for f in feats.index[::-1][:2]]
    st.markdown(f"#### Most decisions are driven by **{top2[0].lower()}** and **{top2[1].lower()}**.")
    fig = go.Figure(go.Bar(x=feats.values * 100, y=[FRIENDLY[f] for f in feats.index], orientation="h",
                           marker_color=[UP if i >= len(feats) - 2 else GREY for i in range(len(feats))],
                           hovertemplate="%{y}: %{x:.1f} points on average<extra></extra>"))
    fig.update_xaxes(title="Average push on the flood score (points) · SHAP")
    a, b = st.columns([1.5, 1], gap="large")
    a.plotly_chart(_style(fig, 400), config={"displayModeBar": False})
    days = load_csv("shap_days.csv")
    fig = go.Figure(go.Bar(x=days["day"].str.replace("Day ", ""), y=days["mean_abs_shap"] * 100,
                           marker_color=[DOWN] * (len(days) - 1) + [UP]))
    fig.update_yaxes(title="Average push (points)")
    with b:
        st.markdown("**Which day of the week matters**")
        st.plotly_chart(_style(fig, 260), config={"displayModeBar": False})
        st.caption("The checked day itself carries most of the weight; earlier days add context.")

with safe_tab:
    tests = load_csv("robustness_tests.csv")
    passed = int((tests["Result"] == "PASS").sum())
    st.markdown(f"#### It refuses broken input instead of guessing: **{passed} of {len(tests)}** checks passed.")
    for _, t in tests.iterrows():
        ok = t["Result"] == "PASS"
        st.markdown(f"{':green[:material/check_circle:]' if ok else ':red[:material/cancel:]'} **{t['Test']}** "
                    f":gray[· {t['Outcome']}]")

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
