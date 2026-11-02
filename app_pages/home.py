import streamlit as st

from flood_ui import (
    LEVELS, LOCATION, actual_next, advisory_props, cached_explain, cached_predict, drivers, load_data, load_summary,
    load_system, load_predictions, window_ending,
)
from fs_components import count_up_kpis, globe, living_advisory, reason_cards

system = load_system()
df = load_data()
summary = load_summary()
c, m = summary["confusion"], summary["metrics"]
n_test = len(load_predictions())

latest = df["date"].iloc[-1].date()
window = window_ending(df, latest)
result = cached_predict(str(latest))
feats, _ = cached_explain(str(latest))
lvl = LEVELS[result["advisory"]]

hero, earth = st.columns([1, 1.2], gap="large", vertical_alignment="center")
with hero:
    st.markdown("# :material/water_drop: FloodSense")
    st.markdown("### Will it flood tomorrow? FloodSense reads the last 7 days of satellite and weather data, "
                "gives tomorrow's risk level, and **shows why**.")
    with st.container(horizontal=True):
        if st.button("Check a day", icon=":material/radar:", type="primary"):
            st.switch_page("app_pages/check_day.py")
        if st.button("Try the What-if lab", icon=":material/tune:"):
            st.switch_page("app_pages/what_if.py")
with earth:
    globe(LOCATION, lvl["hex"], f"Monitored point · {LOCATION[0]:.2f}°N {LOCATION[1]:.0f}°E · {lvl['label']}",
          hint="drag to spin", key="globe")

st.space("small")
card, reasons = st.columns([2.2, 1], gap="large")
with card:
    living_advisory(**advisory_props(result, df, window, actual_next(df, latest), f"Forecast for {result['for_date']:%A %d %B %Y} · from the latest data",
                                     system.thresholds["sys"]), key="home_advisory")
with reasons:
    reason_cards(drivers(feats, window, df), key="home_reasons")

st.space("medium")
steps = st.columns(3, gap="medium")
for col, (icon, title, text) in zip(steps, [
    (":material/calendar_month:", "1 · Pick a day", "Any day in the dataset as 'today', or upload your own 7 days."),
    (":material/neurology:", "2 · AI reads the week", "An LSTM and Gradient Boosting score tomorrow; simple rules decide the level."),
    (":material/assignment_turned_in:", "3 · Get the answer", "Tomorrow's risk level, what to do, and the reasons behind it."),
]):
    with col.container(border=True, height="stretch"):
        st.markdown(f"#### {icon} {title}")
        st.caption(text)

st.space("small")
st.markdown(f"**Tested on {n_test} forecasts it had never seen** (Jul–Dec 2024)")
count_up_kpis([
    {"label": "Floods caught", "value": c["tp"], "suffix": f" / {c['tp'] + c['fn']}", "color": LEVELS["FLOOD WARNING"]["hex"],
     "help": "Next-day floods FloodSense warned about the day before"},
    {"label": "Days judged correctly", "value": m["Accuracy"] * 100, "decimals": 1, "suffix": "%", "color": LEVELS["LOW RISK"]["hex"],
     "help": f"Flood and non-flood days combined · just copying today scores {summary['baseline_accuracy']:.1%}"},
    {"label": "False alarms", "value": c["fp"], "color": LEVELS["FLOOD WATCH"]["hex"],
     "help": "Flagged as flood when none happened"},
    {"label": "Copy-today baseline", "value": summary["baseline_accuracy"] * 100, "decimals": 1, "suffix": "%",
     "color": LEVELS["MONITOR"]["hex"], "help": "Accuracy of simply saying 'tomorrow = today', the bar to beat"},
], key="home_kpis")
if st.button("See how far you can trust it", icon=":material/verified_user:", type="tertiary"):
    st.switch_page("app_pages/trust.py")
