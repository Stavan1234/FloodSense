import streamlit as st

from flood_ui import (
    LEVELS, actual_label, advisory_banner, cached_explain, drivers, load_data, load_summary, load_system,
    risk_gauge, show_drivers, window_ending,
)

system = load_system()
df = load_data()
summary = load_summary()
c = summary["confusion"]

hero, demo = st.columns([1, 1.15], gap="large", vertical_alignment="center")
with hero:
    st.markdown("# :material/water_drop: FloodSense")
    st.markdown("### Is today a flood day? FloodSense reads a week of weather and satellite data, "
                "gives a clear risk level, and **shows why**.")
    with st.container(horizontal=True):
        if st.button("Check a day", icon=":material/radar:", type="primary"):
            st.switch_page("app_pages/check_day.py")
        if st.button("Try the What-if lab", icon=":material/tune:"):
            st.switch_page("app_pages/what_if.py")

with demo, st.container(border=True):
    latest = df["date"].iloc[-1].date()
    window = window_ending(df, latest)
    result = system.predict_window(window)
    feats, _ = cached_explain(str(latest))
    st.caption(":material/bolt: Live result · latest day in the data")
    advisory_banner(result, actual_label(df, latest))
    g, r = st.columns([1.1, 1], vertical_alignment="center")
    g.plotly_chart(risk_gauge(result["score"], system.thresholds["sys"], height=200), config={"displayModeBar": False})
    with r:
        show_drivers(drivers(feats, window, df, n=2))

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
with st.container(horizontal=True):
    st.metric("Floods caught", f"{c['tp']} of {c['tp'] + c['fn']}", border=True,
              help="Real floods that FloodSense flagged.")
    st.metric("Days judged correctly", f"{summary['metrics']['Accuracy']:.0%}", border=True,
              help="Flood and non-flood days combined.")
    st.metric("False alarms", c["fp"], border=True, help="Days flagged as flood when none happened.")
if st.button("See how far you can trust it", icon=":material/verified_user:", type="tertiary"):
    st.switch_page("app_pages/trust.py")

st.space("small")
st.markdown("**The four risk levels**")
with st.container(horizontal=True):
    for lvl in LEVELS.values():
        st.badge(f"{lvl['label']}: {lvl['action']}", color=lvl["color"], icon=lvl["icon"])
