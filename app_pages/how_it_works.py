import streamlit as st

from flood_ui import LEVELS, load_summary, load_system

system = load_system()
summary = load_summary()
H, TREES, DEPTH = system.hidden_size, system.rf.n_estimators, system.rf.max_depth
N_FEAT, DAYS = len(system.feature_names), system.window_days

STYLE = """
<style>
.fs-svg { width: 100%; height: auto; font-family: 'Plus Jakarta Sans', sans-serif; }
.fs-svg text { fill: currentColor; }
.fs-flow { stroke-dasharray: 6 6; animation: fs-march 1.2s linear infinite; }
@keyframes fs-march { to { stroke-dashoffset: -12; } }
.fs-pulse { animation: fs-pulse 2.4s ease-in-out infinite; }
@keyframes fs-pulse { 0%, 100% { opacity: .55; } 50% { opacity: 1; } }
</style>
"""


def box(x, y, w, h, color, title, sub="", sub2=""):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{color}22" stroke="{color}" stroke-width="2"/>'
            f'<text x="{x + w / 2}" y="{y + h / 2 - (12 if sub2 else 6)}" text-anchor="middle" font-size="15" font-weight="700">{title}</text>'
            f'<text x="{x + w / 2}" y="{y + h / 2 + (8 if sub2 else 14)}" text-anchor="middle" font-size="12" opacity=".75">{sub}</text>'
            + (f'<text x="{x + w / 2}" y="{y + h / 2 + 26}" text-anchor="middle" font-size="12" opacity=".75">{sub2}</text>' if sub2 else ""))


def arrow(x1, y1, x2, y2, label="", color="#8C9AAB"):
    lab = (f'<text x="{(x1 + x2) / 2}" y="{min(y1, y2) - 8}" text-anchor="middle" font-size="11" font-weight="600" opacity=".7">{label}</text>'
           if label else "")
    return f'<line class="fs-flow" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="2.5" marker-end="url(#fs-arrow)"/>' + lab


DEFS = ('<defs><marker id="fs-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
        '<path d="M0,0 L10,5 L0,10 z" fill="#8C9AAB"/></marker></defs>')

st.title("How it works", icon=":material/account_tree:")
st.caption("Three kinds of AI, one after another: deep learning reads the week, machine learning scores it, rules decide.")

# ---------------------------------------------------------------- pipeline
blue, green, purple, orange, grey, red = "#0B6BCB", "#1A9E5C", "#7A5AF8", "#E8820C", "#8C9AAB", "#D93A3A"
w, y, h, gap = 132, 40, 92, 62
xs = [10 + i * (w + gap) for i in range(7)]
pipeline = (
    f'<svg class="fs-svg" viewBox="0 0 {xs[-1] + w + 10} 190">{DEFS}'
    + box(xs[0], y, w, h, grey, "7 days", f"{len(system.env_features)} readings each")
    + box(xs[1], y, w, h, grey, "Check & prepare", "fill gaps · scale")
    + box(xs[2], y, w, h, blue, "LSTM", "deep learning", "reads day by day")
    + box(xs[3], y, w, h, green, "Random Forest", "machine learning", f"{TREES} trees")
    + box(xs[4], y, w, h, purple, "Combine", "50 % + 50 %")
    + box(xs[5], y, w, h, orange, "Rules", "4 IF–THEN")
    + box(xs[6], y, w, h, red, "Advisory", "+ reasons")
    + "".join(arrow(xs[i] + w + 4, y + h / 2, xs[i + 1] - 6, y + h / 2, label)
              for i, label in enumerate(["", f"{DAYS}×{N_FEAT}", f"{H} numbers", "P(flood)", "score", ""]))
    + f'<path class="fs-flow" d="M{xs[2] + w / 2},{y + h} C{xs[2] + w / 2},{y + h + 50} {xs[4] + w / 2},{y + h + 50} {xs[4] + w / 2},{y + h + 4}" '
      f'fill="none" stroke="{blue}" stroke-width="2.5" marker-end="url(#fs-arrow)"/>'
    + f'<text x="{(xs[2] + xs[4]) / 2 + w / 2}" y="{y + h + 48}" text-anchor="middle" font-size="11" font-weight="600" opacity=".7">LSTM\'s own P(flood)</text>'
    + "</svg>"
)
st.markdown(STYLE + pipeline, unsafe_allow_html=True)

# ---------------------------------------------------------------- engine cards
cards = st.columns(3, gap="medium")
for col, (icon, title, color, text, stat) in zip(cards, [
    (":material/neurology:", "Deep learning · LSTM", "blue",
     "Reads the 7 days in order, remembering what matters, and compresses the week into a summary.", f"{H}-number summary"),
    (":material/forest:", "Machine learning · Random Forest", "green",
     "Hundreds of decision trees vote on that summary, giving a second opinion.", f"{TREES} trees · depth {DEPTH}"),
    (":material/rule:", "AI reasoning · Rules", "orange",
     "Readable IF–THEN rules turn the scores and warning signs into one of four levels.", "4 rules · checked in order"),
]):
    with col.container(border=True, height="stretch"):
        st.markdown(f"**:{color}[{icon} {title}]**")
        st.caption(text)
        st.badge(stat, color=color)

# ---------------------------------------------------------------- LSTM unrolled
st.subheader("Inside the LSTM", icon=":material/neurology:")
st.caption("One memory cell is reused for every day. Each day it reads that day's readings and updates its memory; "
           "after the last day, the memory is the summary of the week.")
cw, gap, top = 92, 30, 70
cells = ""
for d in range(DAYS):
    x = 20 + d * (cw + gap)
    last = d == DAYS - 1
    label = "Checked day" if last else f"Day −{DAYS - 1 - d}"
    cells += (f'<rect class="fs-pulse" style="animation-delay:{d * 0.25}s" x="{x}" y="{top}" width="{cw}" height="70" rx="12" '
              f'fill="{blue}{"40" if last else "22"}" stroke="{blue}" stroke-width="2"/>'
              f'<text x="{x + cw / 2}" y="{top + 32}" text-anchor="middle" font-size="14" font-weight="700">LSTM</text>'
              f'<text x="{x + cw / 2}" y="{top + 52}" text-anchor="middle" font-size="11" opacity=".75">cell</text>'
              f'<line class="fs-flow" x1="{x + cw / 2}" y1="{top + 140}" x2="{x + cw / 2}" y2="{top + 74}" stroke="{grey}" stroke-width="2" marker-end="url(#fs-arrow)"/>'
              f'<text x="{x + cw / 2}" y="{top + 160}" text-anchor="middle" font-size="12" font-weight="{700 if last else 500}">{label}</text>'
              f'<text x="{x + cw / 2}" y="{top + 176}" text-anchor="middle" font-size="10.5" opacity=".65">{N_FEAT} readings</text>')
    if d < DAYS - 1:
        cells += arrow(x + cw, top + 35, x + cw + gap - 3, top + 35, "memory" if d == 0 else "", blue)
end_x = 20 + DAYS * (cw + gap) - gap
lstm_svg = (
    f'<svg class="fs-svg" viewBox="0 0 1090 260">{DEFS}{cells}'
    + arrow(end_x, top + 35, end_x + 50, top + 35, "", blue)
    + box(end_x + 54, top - 15, 150, 100, purple, "Week summary", f"{H} numbers", "→ Random Forest")
    + "</svg>"
)
st.markdown(STYLE + lstm_svg, unsafe_allow_html=True)

# ---------------------------------------------------------------- rules
st.subheader("The decision rules", icon=":material/rule:")
st.caption("Checked from top to bottom: the first rule that fits decides the level.")
levels = system.rule_levels
signs = (f"Warning signs: heavy rain ≥ {levels['heavy_rain']:.2f}, very wet soil ≥ {levels['wet_soil']:.3f}, "
         f"water rising ≥ {levels['rapid_rise']:.0f} km² in a day (each is unusual for this place: top 10 % of training days).")
for rule_id, advisory, text, _ in system.rules:
    lvl = LEVELS[advisory]
    st.markdown(f"**{rule_id}** &nbsp; IF {text[0].lower() + text[1:]} &nbsp;→&nbsp; :{lvl['color']}[{lvl['icon']} **{lvl['label']}**]")
st.caption(signs)
with st.expander("Model settings", icon=":material/settings:"):
    st.markdown(
        f"- LSTM: 1 layer, {H} hidden units, dropout {system.encoder.dropout.p}; selected config: {summary['lstm_config']}\n"
        f"- Random Forest: {TREES} trees, max depth {DEPTH}, trained on the LSTM's {H}-number summaries\n"
        f"- Flood lines (chosen on validation data): LSTM {system.thresholds['dl']:.2f} · "
        f"Random Forest {system.thresholds['ml']:.2f} · combined {system.thresholds['sys']:.2f}\n"
        f"- Trained on {summary['splits']['train'][0]} → {summary['splits']['train'][1]}; "
        f"tested on {summary['splits']['test'][0]} → {summary['splits']['test'][1]}"
    )
