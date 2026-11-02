from datetime import datetime, timezone

import streamlit as st

from flood_ui import (
    LEVELS, LOCATION, actual_label, advisory_props, cached_explain, drivers, load_data, load_summary,
    load_system, window_ending,
)
from fs_components import count_up_kpis, globe, living_advisory, reason_cards

system = load_system()
df = load_data()
summary = load_summary()
c, m = summary["confusion"], summary["metrics"]

latest = df["date"].iloc[-1].date()
window = window_ending(df, latest)
result = system.predict_window(window)
feats, _ = cached_explain(str(latest))
lvl = LEVELS[result["advisory"]]

hero, earth = st.columns([1, 1.2], gap="large", vertical_alignment="center")
with hero:
    st.markdown("# :material/water_drop: FloodSense")
    st.markdown("### Is today a flood day? FloodSense reads a week of weather and satellite data, "
                "gives a clear risk level, and **shows why**.")
    with st.container(horizontal=True):
        if st.button("Check a day", icon=":material/radar:", type="primary"):
            st.switch_page("app_pages/check_day.py")
        if st.button("Try the What-if lab", icon=":material/tune:"):
            st.switch_page("app_pages/what_if.py")
with earth:
    now = datetime.now(timezone.utc)
    when = datetime(latest.year, latest.month, latest.day, now.hour, now.minute, tzinfo=timezone.utc)
    globe(*LOCATION, color=lvl["hex"], badge=f"{lvl['label']} · {latest:%d %b %Y}",
          when_iso=when.isoformat(), note=f"Monitored point {LOCATION[0]:.0f}°N {LOCATION[1]:.0f}°E · "
          f"daylight shown for {latest:%d %b}, {when:%H:%M} UTC", key="globe")

st.space("small")
card, reasons = st.columns([2.2, 1], gap="large")
with card:
    living_advisory(**advisory_props(result, df, window, actual_label(df, latest), f"Live · latest day in the data · {latest:%d %b %Y}",
                                     system.thresholds["sys"]), key="home_advisory")
with reasons:
    reason_cards(drivers(feats, window, df), key="home_reasons")

st.space("medium")
steps = st.columns(3, gap="medium")
for col, (icon, title, text) in zip(steps, [
    (":material/calendar_month:", "1 · Pick a day", "Any day in the dataset, or upload your own 7 days."),
    (":material/neurology:", "2 · AI reads the week", "Two models score the week; simple rules decide the level."),
    (":material/assignment_turned_in:", "3 · Get the answer", "Risk level, what to do, and the reasons behind it."),
]):
    with col.container(border=True, height="stretch"):
        st.markdown(f"#### {icon} {title}")
        st.caption(text)

st.space("small")
st.markdown("**Tested on 204 days it had never seen**")
count_up_kpis([
    {"label": "Floods caught", "value": c["tp"], "suffix": f" / {c['tp'] + c['fn']}", "color": LEVELS["FLOOD WARNING"]["hex"],
     "help": "Real floods FloodSense flagged"},
    {"label": "Days judged correctly", "value": m["Accuracy"] * 100, "suffix": "%", "color": LEVELS["LOW RISK"]["hex"],
     "help": "Flood and non-flood days combined"},
    {"label": "False alarms", "value": c["fp"], "color": LEVELS["FLOOD WATCH"]["hex"],
     "help": "Flagged as flood when none happened"},
    {"label": "Answer time", "value": 0.1, "decimals": 1, "prefix": "~", "suffix": " s", "color": LEVELS["MONITOR"]["hex"],
     "help": "Prediction plus explanation"},
], key="home_kpis")
if st.button("See how far you can trust it", icon=":material/verified_user:", type="tertiary"):
    st.switch_page("app_pages/trust.py")
