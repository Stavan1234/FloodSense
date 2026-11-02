"""Animated FloodSense components (Streamlit custom components v2, inline HTML/CSS/JS).

Every animation is driven by real model output: rain from the day's rainfall, water
level from the flood score, mood from the advisory level. All of them respect the
visitor's "reduce motion" setting and pause when scrolled out of view.
"""
import streamlit as st

# Shared icon paths (24×24 viewBox) for the four advisory levels.
ICONS = {
    "LOW RISK": '<path d="M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4z"/>',
    "MONITOR": '<path d="M12 4.5C7 4.5 2.7 7.6 1 12c1.7 4.4 6 7.5 11 7.5s9.3-3.1 11-7.5c-1.7-4.4-6-7.5-11-7.5zm0 12.5a5 5 0 1 1 0-10 5 5 0 0 1 0 10zm0-8a3 3 0 1 0 0 6 3 3 0 0 0 0-6z"/>',
    "FLOOD WATCH": '<path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/>',
    "FLOOD WARNING": '<path d="M2 16c2.2 0 2.2-1.5 4.4-1.5S8.6 16 10.8 16s2.2-1.5 4.4-1.5S17.4 16 19.6 16 21.8 14.5 22 14.5V17c-2.2 0-2.2 1.5-4.4 1.5S15.4 17 13.2 17s-2.2 1.5-4.4 1.5S6.6 17 4.4 17 2.2 18.5 2 18.5zm0 4c2.2 0 2.2-1.5 4.4-1.5S8.6 20 10.8 20s2.2-1.5 4.4-1.5S17.4 20 19.6 20s2.2-1.5 2.4-1.5V21c-2.2 0-2.2 1.5-4.4 1.5S15.4 21 13.2 21s-2.2 1.5-4.4 1.5S6.6 21 4.4 21 2.2 22.5 2 22.5zM12 3l7 6h-2v4H7V9H5z"/>',
}

# =====================================================================================
# 1 · Living advisory card
# =====================================================================================
_ADVISORY_HTML = """
<div class="card">
  <canvas class="scene"></canvas>
  <div class="content">
    <div class="main">
      <div class="eyebrow"></div>
      <div class="level"><svg class="icon" viewBox="0 0 24 24"></svg><span class="label"></span></div>
      <div class="action"></div>
      <div class="chips"></div>
    </div>
    <div class="ring">
      <svg viewBox="0 0 120 120">
        <circle class="track" cx="60" cy="60" r="50"/>
        <circle class="mark" cx="60" cy="60" r="50"/>
        <circle class="arc" cx="60" cy="60" r="50"/>
      </svg>
      <div class="score"><div class="num"><b>0</b><small>%</small></div><span>flood score</span></div>
    </div>
  </div>
  <div class="ladder"></div>
</div>
"""

_ADVISORY_CSS = """
:host { display: block; }
.card { position: relative; overflow: hidden; border-radius: 18px; min-height: 230px;
  background: var(--st-secondary-background-color); color: var(--st-text-color);
  border: 1px solid color-mix(in srgb, var(--lvl) 45%, transparent);
  box-shadow: 0 0 0 0 var(--lvl); transition: border-color .6s, box-shadow .6s;
  font-family: var(--st-font, sans-serif); }
.card.glow { animation: glow 2.8s ease-in-out infinite; }
@keyframes glow { 0%,100% { box-shadow: 0 0 0 0 color-mix(in srgb, var(--lvl) 0%, transparent); }
                  50% { box-shadow: 0 0 28px 2px color-mix(in srgb, var(--lvl) 45%, transparent); } }
.scene { position: absolute; inset: 0; width: 100%; height: 100%; }
.main { text-shadow: 0 0 12px var(--st-secondary-background-color), 0 0 4px var(--st-secondary-background-color); }
.content { position: relative; display: flex; gap: 18px; align-items: center; justify-content: space-between;
  padding: 22px 26px 8px; }
.eyebrow { font-size: .8rem; letter-spacing: .08em; text-transform: uppercase; opacity: .75; font-weight: 600; }
.level { display: flex; align-items: center; gap: 12px; margin: 6px 0 4px; }
.icon { width: 40px; height: 40px; fill: var(--lvl); flex: none;
  filter: drop-shadow(0 2px 8px color-mix(in srgb, var(--lvl) 50%, transparent)); }
.label { font-size: 2.3rem; font-weight: 800; line-height: 1.05; color: var(--lvl); transition: color .6s; }
.action { font-size: 1.05rem; font-weight: 600; margin-bottom: 10px; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip { font-size: .78rem; font-weight: 600; padding: 4px 10px; border-radius: 999px;
  background: color-mix(in srgb, var(--c) 16%, transparent); color: var(--c);
  border: 1px solid color-mix(in srgb, var(--c) 35%, transparent); }
.ring { position: relative; width: 150px; height: 150px; flex: none; }
.ring svg { width: 100%; height: 100%; transform: rotate(-90deg); }
.track { fill: none; stroke: color-mix(in srgb, var(--st-text-color) 12%, transparent); stroke-width: 10; }
.arc { fill: none; stroke: var(--lvl); stroke-width: 10; stroke-linecap: round; stroke-dasharray: 314.16;
  transition: stroke .6s; filter: drop-shadow(0 0 6px color-mix(in srgb, var(--lvl) 60%, transparent)); }
.mark { fill: none; stroke: #7A5AF8; stroke-width: 14; stroke-dasharray: 2.2 312; }
.score { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.num { display: flex; align-items: baseline; gap: 1px; }
.score b { font-size: 2.4rem; font-weight: 800; font-variant-numeric: tabular-nums; line-height: 1; }
.score small { font-size: 1rem; font-weight: 700; }
.score span { font-size: .72rem; opacity: .7; margin-top: 2px; text-transform: uppercase; letter-spacing: .06em; }
.ladder { position: relative; display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; padding: 10px 26px 18px; }
.step { font-size: .72rem; font-weight: 600; text-align: center; opacity: .45; transition: opacity .4s; }
.step i { display: block; height: 6px; border-radius: 6px; margin-bottom: 5px; background: var(--c);
  opacity: .35; transition: opacity .4s, transform .4s; }
.step.on { opacity: 1; } .step.on i { opacity: 1; transform: scaleY(1.6); }
@media (max-width: 640px) {
  .content { flex-direction: column-reverse; align-items: flex-start; padding: 18px; }
  .label { font-size: 1.8rem; } .ring { width: 120px; height: 120px; align-self: center; }
  .ladder { padding: 8px 18px 14px; } }
"""

_ADVISORY_JS = """
const STATE = new WeakMap();
const lerp = (a, b, t) => a + (b - a) * t;
const hex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));

function init(root) {
  const s = { root, canvas: root.querySelector(".scene"), t: 0, raf: 0, visible: true,
    cur: { rain: 0, clouds: 0, water: 0.15, wave: 0.3, wind: 0, tint: [26, 158, 92], score: 0 },
    target: null, drops: [], clouds: [] };
  s.ctx = s.canvas.getContext("2d");
  s.reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  for (let i = 0; i < 320; i++) s.drops.push({ x: Math.random(), y: Math.random(), v: 0.6 + Math.random() * 0.8, l: 0.5 + Math.random() });
  for (let i = 0; i < 6; i++) s.clouds.push({ x: Math.random(), y: 0.05 + Math.random() * 0.3, r: 0.12 + Math.random() * 0.12, v: 0.00004 + Math.random() * 0.00008 });
  s.resize = () => { const r = s.canvas.getBoundingClientRect(), d = window.devicePixelRatio || 1;
    s.w = r.width; s.h = r.height; s.canvas.width = r.width * d; s.canvas.height = r.height * d; s.ctx.setTransform(d, 0, 0, d, 0, 0); };
  s.ro = new ResizeObserver(() => { s.resize(); if (s.reduce) draw(s); }); s.ro.observe(s.canvas);
  s.io = new IntersectionObserver(([e]) => { s.visible = e.isIntersecting; if (s.visible && !s.reduce) loop(s); });
  s.io.observe(s.canvas);
  s.resize();
  return s;
}

function draw(s) {
  const { ctx, w, h, cur } = s; if (!w) return;
  ctx.clearRect(0, 0, w, h);
  const [r, g, b] = cur.tint.map(Math.round);
  const sky = ctx.createLinearGradient(0, 0, 0, h);
  sky.addColorStop(0, `rgba(${r},${g},${b},${0.10 + cur.clouds * 0.16})`); sky.addColorStop(1, `rgba(${r},${g},${b},0.02)`);
  ctx.fillStyle = sky; ctx.fillRect(0, 0, w, h);
  for (const c of s.clouds) {                       // soft drifting clouds
    const cx = ((c.x + s.t * c.v * 60) % 1.3 - 0.15) * w, cy = c.y * h, rad = c.r * w;
    const grd = ctx.createRadialGradient(cx, cy, 0, cx, cy, rad);
    grd.addColorStop(0, `rgba(140,154,171,${0.30 * cur.clouds})`); grd.addColorStop(1, "rgba(140,154,171,0)");
    ctx.fillStyle = grd; ctx.beginPath(); ctx.ellipse(cx, cy, rad, rad * 0.45, 0, 0, Math.PI * 2); ctx.fill();
  }
  const n = Math.round(cur.rain);                   // rain, slanted by wind
  ctx.strokeStyle = "rgba(77,163,255,0.40)"; ctx.lineWidth = 1.2; ctx.beginPath();
  for (let i = 0; i < n; i++) {
    const d = s.drops[i]; const x = d.x * (w + 80) - 40, y = d.y * h, len = 8 + d.l * 10;
    ctx.moveTo(x, y); ctx.lineTo(x - cur.wind * len, y + len);
  }
  ctx.stroke();
  const level = h * (1 - cur.water);                // water surface: two moving waves
  for (const [amp, speed, alpha, phase] of [[1, 1, 0.16, 0], [0.7, 1.6, 0.24, 2]]) {
    ctx.beginPath(); ctx.moveTo(0, h);
    for (let x = 0; x <= w; x += 6) {
      ctx.lineTo(x, level + Math.sin(x / 38 + s.t * 0.035 * speed + phase) * 5 * cur.wave * amp
                       + Math.sin(x / 91 - s.t * 0.02 * speed) * 3 * cur.wave * amp);
    }
    ctx.lineTo(w, h); ctx.closePath();
    const wg = ctx.createLinearGradient(0, level, 0, h);
    wg.addColorStop(0, `rgba(11,107,203,${alpha})`); wg.addColorStop(1, `rgba(11,107,203,${alpha * 0.4})`);
    ctx.fillStyle = wg; ctx.fill();
  }
}

function step(s) {
  const tg = s.target, k = s.reduce ? 1 : 0.04;
  for (const key of ["rain", "clouds", "water", "wave", "wind"]) s.cur[key] = lerp(s.cur[key], tg[key], k);
  s.cur.tint = s.cur.tint.map((v, i) => lerp(v, tg.tint[i], k));
  s.cur.score = lerp(s.cur.score, tg.score, s.reduce ? 1 : 0.06);
  s.scoreEl.textContent = Math.round(s.cur.score * 100);
  s.arc.style.strokeDashoffset = 314.16 * (1 - s.cur.score);
  for (const d of s.drops) { d.y += 0.012 * d.v * (0.6 + s.cur.rain / 200); if (d.y > 1) { d.y = -0.1; d.x = Math.random(); } }
  s.t += 1;
}

function loop(s) {
  cancelAnimationFrame(s.raf);
  const tick = () => { if (!s.visible) return; step(s); draw(s); s.raf = requestAnimationFrame(tick); };
  s.raf = requestAnimationFrame(tick);
}

export default function (component) {
  const { data, parentElement } = component;
  let s = STATE.get(parentElement);
  if (!s) { s = init(parentElement); STATE.set(parentElement, s); }
  const root = parentElement;
  s.scoreEl = root.querySelector(".score b"); s.arc = root.querySelector(".arc");
  const card = root.querySelector(".card");
  card.style.setProperty("--lvl", data.color);
  card.classList.toggle("glow", data.level >= 2 && !s.reduce);
  root.querySelector(".eyebrow").textContent = data.eyebrow;
  root.querySelector(".label").textContent = data.label;
  root.querySelector(".action").textContent = data.action;
  root.querySelector(".icon").innerHTML = data.icon;
  root.querySelector(".mark").style.strokeDashoffset = -314.16 * data.flood_line;
  root.querySelector(".chips").innerHTML = data.chips.map((c) => `<span class="chip" style="--c:${c.color}">${c.text}</span>`).join("");
  root.querySelector(".ladder").innerHTML = data.ladder.map((l, i) =>
    `<div class="step ${i === data.level ? "on" : ""}" style="--c:${l.color}"><i></i>${l.label}</div>`).join("");
  const L = data.level, rainBase = [0, 18, 80, 150][L];
  s.target = { rain: Math.min(240, rainBase + data.rain * 70 * (L >= 1)), clouds: [0.12, 0.55, 0.8, 1][L],
    water: 0.10 + data.score * 0.32, wave: [0.35, 0.6, 1.0, 1.6][L], wind: [0, 0.15, 0.3, 0.55][L],
    tint: hex(data.color), score: data.score };
  if (s.reduce) { step(s); draw(s); } else loop(s);
  return () => { cancelAnimationFrame(s.raf); s.ro.disconnect(); s.io.disconnect(); STATE.delete(parentElement); };
}
"""

_ADVISORY = st.components.v2.component("fs_living_advisory", html=_ADVISORY_HTML, css=_ADVISORY_CSS, js=_ADVISORY_JS)


def living_advisory(result: dict, levels: dict, flood_line: float, rain: float, eyebrow: str,
                    verdict: tuple[str, str] | None = None, triggers: list[str] | None = None, key: str | None = None):
    """Full-width animated advisory. `rain` is 0–1 (how rainy the day is relative to the data)."""
    order = list(levels)
    lvl = levels[result["advisory"]]
    chips = [{"text": text, "color": color} for text, color in ([verdict] if verdict else [])]
    chips += [{"text": t, "color": "#E8820C"} for t in (triggers or [])]
    _ADVISORY(key=key, data={
        "level": order.index(result["advisory"]), "label": lvl["label"], "color": lvl["hex"],
        "action": f"{lvl['meaning']}. {lvl['action']}", "eyebrow": eyebrow, "icon": ICONS[result["advisory"]],
        "score": float(result["score"]), "flood_line": float(flood_line), "rain": float(rain), "chips": chips,
        "ladder": [{"label": v["label"], "color": v["hex"]} for v in levels.values()],
    })


# =====================================================================================
# 2 · Week strip (7 days, revealed left → right the way the LSTM reads them)
# =====================================================================================
_WEEK_HTML = '<div class="strip"></div><div class="detail"></div>'
_WEEK_CSS = """
.strip { display: grid; grid-template-columns: repeat(7, 1fr); gap: 8px; font-family: var(--st-font, sans-serif); color: var(--st-text-color); }
.day { position: relative; border-radius: 14px; padding: 10px 6px 10px; text-align: center; cursor: pointer;
  background: var(--st-secondary-background-color); border: 1px solid var(--st-border-color);
  opacity: 0; transform: translateY(10px); animation: in .5s ease forwards; transition: transform .2s, border-color .2s; }
.day:hover { transform: translateY(-3px); border-color: var(--st-primary-color); }
.day.sel { border-color: var(--st-primary-color); box-shadow: 0 0 0 2px color-mix(in srgb, var(--st-primary-color) 35%, transparent); }
.day.target { background: color-mix(in srgb, var(--lvl) 12%, var(--st-secondary-background-color)); border-color: var(--lvl); }
.day::after { content: ""; position: absolute; inset: 0; border-radius: 14px; pointer-events: none;
  background: linear-gradient(120deg, transparent 30%, color-mix(in srgb, var(--st-primary-color) 30%, transparent), transparent 70%);
  opacity: 0; animation: scan .7s ease forwards; animation-delay: inherit; }
@keyframes in { to { opacity: 1; transform: none; } }
@keyframes scan { 0% { opacity: 0; } 40% { opacity: 1; } 100% { opacity: 0; } }
.dow { font-size: .72rem; font-weight: 700; letter-spacing: .05em; text-transform: uppercase; opacity: .7; }
.date { font-size: .78rem; opacity: .6; }
.wx { width: 38px; height: 38px; margin: 6px auto 4px; display: block; }
.bars { display: flex; gap: 4px; justify-content: center; margin-top: 4px; }
.bar { width: 6px; height: 26px; border-radius: 4px; background: color-mix(in srgb, var(--st-text-color) 10%, transparent);
  display: flex; align-items: flex-end; overflow: hidden; }
.bar i { display: block; width: 100%; border-radius: 4px; background: var(--c); height: 0; animation: grow .8s ease forwards; animation-delay: inherit; }
@keyframes grow { from { height: 0; } to { height: var(--h); } }
.tag { margin-top: 6px; font-size: .66rem; font-weight: 700; color: var(--lvl); text-transform: uppercase; }
.legend { grid-column: 1 / -1; display: flex; gap: 14px; justify-content: center; font-size: .72rem; opacity: .7; margin-top: 2px; }
.legend span::before { content: ""; display: inline-block; width: 8px; height: 8px; border-radius: 2px; margin-right: 5px; background: var(--c); }
.detail { margin-top: 10px; font-family: var(--st-font, sans-serif); color: var(--st-text-color); }
.detail .box { border-radius: 12px; padding: 10px 14px; background: var(--st-secondary-background-color);
  border: 1px solid var(--st-border-color); display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 4px 16px;
  font-size: .82rem; animation: in .3s ease forwards; opacity: 0; }
.detail b { font-weight: 700; }
@media (max-width: 640px) { .strip { gap: 4px; } .wx { width: 28px; height: 28px; } .date { display: none; } }
@media (prefers-reduced-motion: reduce) { .day, .detail .box { animation: none; opacity: 1; transform: none; }
  .day::after { display: none; } .bar i { animation: none; height: var(--h); } }
"""
_WEEK_JS = """
const SUN = '<circle cx="24" cy="24" r="9" fill="#F5B301"/><g stroke="#F5B301" stroke-width="3" stroke-linecap="round"><path d="M24 4v5M24 39v5M4 24h5M39 24h5M9.9 9.9l3.5 3.5M34.6 34.6l3.5 3.5M9.9 38.1l3.5-3.5M34.6 13.4l3.5-3.5"/></g>';
const CLOUD = (c) => `<path d="M14 36h21a8 8 0 0 0 0-16 11 11 0 0 0-21-2 9 9 0 0 0 0 18z" fill="${c}"/>`;
const RAIN = (n) => Array.from({length: n}, (_, i) => `<path d="M${15 + i * 7} 38l-3 7" stroke="#4DA3FF" stroke-width="2.5" stroke-linecap="round"/>`).join("");
const ICON = [SUN, '<g transform="translate(-6,-6) scale(.6)">' + SUN + '</g>' + CLOUD("#B8C4D0"), CLOUD("#A3B1C2"), CLOUD("#8C9AAB") + RAIN(3), CLOUD("#6B7A8C") + RAIN(5)];

export default function (component) {
  const { data, parentElement, setStateValue } = component;
  const strip = parentElement.querySelector(".strip"), detail = parentElement.querySelector(".detail");
  const sig = JSON.stringify(data.days.map((d) => d.date));
  const sel = (i) => {
    strip.querySelectorAll(".day").forEach((el, j) => el.classList.toggle("sel", j === i));
    const d = data.days[i];
    detail.innerHTML = `<div class="box">${d.rows.map(([k, v]) => `<div>${k}: <b>${v}</b></div>`).join("")}</div>`;
  };
  if (strip.dataset.sig !== sig) {
    strip.dataset.sig = sig;
    strip.style.setProperty("--lvl", data.color);
    strip.innerHTML = data.days.map((d, i) => `
      <div class="day ${d.target ? "target" : ""}" style="animation-delay:${i * 0.12}s">
        <div class="dow">${d.dow}</div><div class="date">${d.date}</div>
        <svg class="wx" viewBox="0 0 48 48">${ICON[d.rain_level]}</svg>
        <div class="bars">
          <div class="bar" title="Rain"><i style="--c:#4DA3FF;--h:${d.rain * 100}%"></i></div>
          <div class="bar" title="Soil wetness"><i style="--c:#A0703C;--h:${d.soil * 100}%"></i></div>
          <div class="bar" title="Water area"><i style="--c:#0B6BCB;--h:${d.water * 100}%"></i></div>
        </div>
        ${d.target ? '<div class="tag">Checked</div>' : ""}
      </div>`).join("") +
      '<div class="legend"><span style="--c:#4DA3FF">Rain</span><span style="--c:#A0703C">Soil wetness</span><span style="--c:#0B6BCB">Water area</span><span>tap a day for details</span></div>';
    detail.innerHTML = "";
  }
  strip.querySelectorAll(".day").forEach((el, i) => { el.onclick = () => sel(i); });
}
"""
_WEEK = st.components.v2.component("fs_week_strip", html=_WEEK_HTML, css=_WEEK_CSS, js=_WEEK_JS)


def week_strip(days: list[dict], color: str, key: str | None = None):
    _WEEK(key=key, data={"days": days, "color": color})


# =====================================================================================
# 3 · Reason cards (animated bars) and count-up KPIs
# =====================================================================================
_REASONS_HTML = '<div class="list"></div>'
_REASONS_CSS = """
.list { display: flex; flex-direction: column; gap: 10px; font-family: var(--st-font, sans-serif); color: var(--st-text-color); }
.r { border-radius: 14px; padding: 10px 14px; background: var(--st-secondary-background-color); border: 1px solid var(--st-border-color);
  opacity: 0; transform: translateX(8px); animation: in .45s ease forwards; }
@keyframes in { to { opacity: 1; transform: none; } }
.top { display: flex; justify-content: space-between; gap: 10px; align-items: baseline; }
.name { font-weight: 700; } .name b { color: var(--c); margin-right: 4px; }
.pts { font-size: .8rem; font-weight: 700; color: var(--c); font-variant-numeric: tabular-nums; white-space: nowrap; }
.desc { font-size: .8rem; opacity: .7; margin: 2px 0 6px; }
.track { height: 6px; border-radius: 6px; background: color-mix(in srgb, var(--st-text-color) 10%, transparent); overflow: hidden; }
.fill { height: 100%; width: 0; border-radius: 6px; background: var(--c); transition: width .9s cubic-bezier(.2,.8,.2,1); }
.title { font-size: .8rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; opacity: .7; }
@media (prefers-reduced-motion: reduce) { .r { animation: none; opacity: 1; transform: none; } .fill { transition: none; } }
"""
_REASONS_JS = """
export default function (component) {
  const { data, parentElement } = component;
  const list = parentElement.querySelector(".list");
  const max = Math.max(...data.items.map((d) => Math.abs(d.points)), 1);
  list.innerHTML = `<div class="title">${data.title}</div>` + data.items.map((d, i) => `
    <div class="r" style="--c:${d.up ? "#D93A3A" : "#0B6BCB"};animation-delay:${0.1 + i * 0.12}s">
      <div class="top"><div class="name"><b>${d.up ? "↑" : "↓"}</b>${d.name}</div><div class="pts">${d.up ? "raises" : "lowers"} risk ${Math.abs(d.points).toFixed(0)} pts</div></div>
      <div class="desc">${d.desc || "&nbsp;"}</div>
      <div class="track"><div class="fill" data-w="${(Math.abs(d.points) / max) * 100}"></div></div>
    </div>`).join("");
  requestAnimationFrame(() => requestAnimationFrame(() =>
    list.querySelectorAll(".fill").forEach((f) => { f.style.width = f.dataset.w + "%"; })));
}
"""
_REASONS = st.components.v2.component("fs_reasons", html=_REASONS_HTML, css=_REASONS_CSS, js=_REASONS_JS)


def reason_cards(items: list[dict], title: str = "Top reasons", key: str | None = None):
    _REASONS(key=key, data={"items": items, "title": title})


_KPI_HTML = '<div class="row"></div>'
_KPI_CSS = """
.row { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; font-family: var(--st-font, sans-serif); color: var(--st-text-color); }
.k { border-radius: 16px; padding: 16px 18px; background: var(--st-secondary-background-color); border: 1px solid var(--st-border-color);
  transition: transform .2s, border-color .2s; }
.k:hover { transform: translateY(-3px); border-color: var(--c); }
.v { font-size: 2.1rem; font-weight: 800; font-variant-numeric: tabular-nums; color: var(--c); line-height: 1.1; }
.l { font-size: .85rem; font-weight: 600; } .h { font-size: .75rem; opacity: .65; margin-top: 2px; }
"""
_KPI_JS = """
export default function (component) {
  const { data, parentElement } = component;
  const row = parentElement.querySelector(".row");
  row.innerHTML = data.items.map((d) => `<div class="k" style="--c:${d.color}"><div class="v" data-to="${d.value}">0</div>
    <div class="l">${d.label}</div><div class="h">${d.help}</div></div>`).join("");
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const fmt = (el, x) => { const d = data.items[[...row.children].indexOf(el.parentElement)];
    el.textContent = (d.prefix || "") + (d.decimals ? x.toFixed(d.decimals) : Math.round(x)) + (d.suffix || ""); };
  const run = () => row.querySelectorAll(".v").forEach((el) => {
    const to = parseFloat(el.dataset.to); if (reduce) return fmt(el, to);
    const t0 = performance.now(); const tick = (now) => { const p = Math.min(1, (now - t0) / 1100);
      fmt(el, to * (1 - Math.pow(1 - p, 3))); if (p < 1) requestAnimationFrame(tick); }; requestAnimationFrame(tick); });
  const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { run(); io.disconnect(); } });
  io.observe(row);
  return () => io.disconnect();
}
"""
_KPI = st.components.v2.component("fs_kpis", html=_KPI_HTML, css=_KPI_CSS, js=_KPI_JS)


def count_up_kpis(items: list[dict], key: str | None = None):
    """items: label, value, help, color and optional prefix/suffix/decimals."""
    _KPI(key=key, data={"items": items})


# =====================================================================================
# 4 · Engine walkthrough: one real day travels through every stage
# =====================================================================================
_ENGINE_HTML = """
<div class="wrap">
  <div class="controls">
    <button class="play" type="button">▶ Play</button>
    <button class="prev" type="button" aria-label="Previous step">‹</button>
    <button class="next" type="button" aria-label="Next step">›</button>
    <div class="dots"></div>
  </div>
  <div class="stages"></div>
  <div class="caption"></div>
</div>
"""
_ENGINE_CSS = """
.wrap { font-family: var(--st-font, sans-serif); color: var(--st-text-color); }
.controls { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
button { font: inherit; font-weight: 700; border-radius: 10px; padding: 6px 14px; cursor: pointer;
  border: 1px solid var(--st-border-color); background: var(--st-secondary-background-color); color: var(--st-text-color); }
button.play { background: var(--st-primary-color); color: #fff; border-color: transparent; }
.dots { display: flex; gap: 6px; margin-left: 6px; }
.dots i { width: 22px; height: 6px; border-radius: 6px; background: color-mix(in srgb, var(--st-text-color) 15%, transparent); transition: background .3s; }
.dots i.on { background: var(--st-primary-color); }
.stages { display: grid; grid-template-columns: 1.1fr 1fr 1fr 1fr 1.2fr; gap: 10px; align-items: stretch; }
.stage { position: relative; border-radius: 16px; padding: 12px; border: 1px solid var(--st-border-color);
  background: var(--st-secondary-background-color); opacity: .45; transition: opacity .4s, border-color .4s, box-shadow .4s, transform .4s; }
.stage.done { opacity: 1; }
.stage.active { opacity: 1; border-color: var(--c); transform: translateY(-3px);
  box-shadow: 0 8px 28px -10px color-mix(in srgb, var(--c) 70%, transparent); }
.stage:not(:last-child)::after { content: "›"; position: absolute; right: -10px; top: 46%; font-size: 1.4rem; font-weight: 800; opacity: .5; }
.t { font-size: .72rem; font-weight: 800; letter-spacing: .07em; text-transform: uppercase; color: var(--c); }
.n { font-size: .95rem; font-weight: 700; margin: 2px 0 8px; }
.small { font-size: .72rem; opacity: .7; margin-top: 6px; }
.grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; }
.grid i { aspect-ratio: 1.6; border-radius: 2px; background: var(--bg); opacity: 0; transition: opacity .25s; }
.stage.on .grid i { opacity: 1; }
.cells { display: flex; gap: 4px; align-items: center; margin: 10px 0; }
.cells i { flex: 1; aspect-ratio: 1; border-radius: 8px; border: 2px solid var(--c); background: transparent; transition: background .3s; }
.cells i.lit { background: color-mix(in srgb, var(--c) 60%, transparent); }
.mem { height: 6px; border-radius: 6px; background: color-mix(in srgb, var(--st-text-color) 10%, transparent); overflow: hidden; }
.mem b { display: block; height: 100%; width: 0; background: var(--c); transition: width .25s; }
.emb { display: flex; gap: 2px; align-items: center; height: 70px; }
.emb i { flex: 1; border-radius: 2px; background: var(--c); height: 0; transition: height .5s; }
.trees { display: grid; grid-template-columns: repeat(25, 1fr); gap: 2px; }
.trees i { aspect-ratio: 1; border-radius: 50%; background: color-mix(in srgb, var(--st-text-color) 12%, transparent); transition: background .2s; }
.bars div { font-size: .75rem; margin-top: 6px; display: flex; justify-content: space-between; }
.bars .bt { position: relative; height: 8px; border-radius: 6px; background: color-mix(in srgb, var(--st-text-color) 10%, transparent); margin-top: 3px; }
.bars .bt b { position: absolute; inset: 0 auto 0 0; width: 0; border-radius: 6px; background: var(--b); transition: width .7s cubic-bezier(.2,.8,.2,1); }
.bars .bt s { position: absolute; top: -3px; bottom: -3px; width: 2px; background: #7A5AF8; }
.rules { margin-top: 8px; display: flex; flex-direction: column; gap: 3px; font-size: .74rem; }
.rules span { padding: 3px 8px; border-radius: 8px; opacity: .45; transition: all .3s; }
.rules span.fired { opacity: 1; font-weight: 800; color: #fff; background: var(--r); }
.verdict { margin-top: 8px; font-weight: 800; color: var(--r); font-size: 1rem; opacity: 0; transition: opacity .4s; }
.stage.active .verdict, .stage.done .verdict { opacity: 1; }
.caption { margin-top: 12px; border-radius: 12px; padding: 10px 14px; font-size: .9rem; line-height: 1.45;
  background: color-mix(in srgb, var(--st-primary-color) 10%, transparent); border-left: 4px solid var(--st-primary-color); min-height: 44px; }
@media (max-width: 900px) { .stages { grid-template-columns: 1fr 1fr; } .stage::after { display: none; } }
"""
_ENGINE_JS = """
const STATE = new WeakMap();
const col = (v) => { const t = Math.max(-1, Math.min(1, v / 2.5));
  return t >= 0 ? `rgba(217,58,58,${0.15 + t * 0.85})` : `rgba(11,107,203,${0.15 - t * 0.85})`; };

function build(root, d) {
  const stg = root.querySelector(".stages");
  const C = ["#8C9AAB", "#0B6BCB", "#7A5AF8", "#1A9E5C", d.color];
  const grid = d.grid[0].map((_, f) => d.grid.map((day, i) =>
    `<i style="--bg:${col(day[f])};transition-delay:${i * 60}ms"></i>`).join("")).join("");
  const bars = [["LSTM", d.p_dl, d.th.dl, "#0B6BCB"], ["Forest", d.p_ml, d.th.ml, "#1A9E5C"], ["Combined", d.score, d.th.sys, d.color]]
    .map(([k, v, th, c]) => `<div><span>${k}</span><b>${Math.round(v * 100)}%</b></div>` +
      `<div class="bt" style="--b:${c}"><b data-w="${v * 100}"></b><s style="left:${th * 100}%"></s></div>`).join("");
  stg.innerHTML = `
   <div class="stage" style="--c:${C[0]}"><div class="t">1 · Input</div><div class="n">7 days × ${d.grid[0].length} readings</div>
     <div class="grid">${grid}</div><div class="small">red = above usual · blue = below</div></div>
   <div class="stage" style="--c:${C[1]}"><div class="t">2 · Deep learning</div><div class="n">LSTM reads day by day</div>
     <div class="cells">${d.grid.map(() => "<i></i>").join("")}</div><div class="mem"><b></b></div>
     <div class="small">memory builds up →</div></div>
   <div class="stage" style="--c:${C[2]}"><div class="t">3 · Summary</div><div class="n">${d.emb.length} numbers</div>
     <div class="emb">${d.emb.map((v) => `<i data-h="${8 + Math.abs(v) * 92}"></i>`).join("")}</div>
     <div class="small">the week, compressed</div></div>
   <div class="stage" style="--c:${C[3]}"><div class="t">4 · Machine learning</div><div class="n">${d.votes.length} trees vote</div>
     <div class="trees">${d.votes.map(() => "<i></i>").join("")}</div>
     <div class="small"><b class="vcount">0</b> vote flood</div></div>
   <div class="stage" style="--c:${C[4]};--r:${d.color}"><div class="t">5 · Decide</div><div class="n">Combine + rules</div>
     <div class="bars">${bars}</div>
     <div class="rules">${d.rules.map((r, i) => `<span data-i="${i}" style="--r:${r.color}">${r.id} → ${r.label}</span>`).join("")}</div>
     <div class="verdict">${d.label}</div></div>`;
  root.querySelector(".dots").innerHTML = C.map(() => "<i></i>").join("");
}

function show(s, k, animate) {
  const root = s.root, d = s.data, stages = [...root.querySelectorAll(".stage")];
  s.k = k; (s.timeouts || []).forEach(clearTimeout); s.timeouts = [];
  const later = (fn, ms) => { if (animate) s.timeouts.push(setTimeout(fn, ms)); else fn(); };
  stages.forEach((el, i) => { el.classList.toggle("active", i === k); el.classList.toggle("done", i < k); el.classList.toggle("on", i <= k); });
  root.querySelectorAll(".dots i").forEach((el, i) => el.classList.toggle("on", i <= k));
  root.querySelector(".caption").textContent = d.captions[k];
  const cells = [...root.querySelectorAll(".cells i")], mem = root.querySelector(".mem b");
  cells.forEach((c) => c.classList.remove("lit")); mem.style.width = "0";
  if (k >= 1) cells.forEach((c, i) => later(() => { c.classList.add("lit"); mem.style.width = ((i + 1) / cells.length * 100) + "%"; }, i * 220));
  root.querySelectorAll(".emb i").forEach((b, i) => { b.style.transitionDelay = (animate ? i * 15 : 0) + "ms"; b.style.height = k >= 2 ? b.dataset.h + "%" : "0"; });
  const trees = [...root.querySelectorAll(".trees i")], vc = root.querySelector(".vcount"); let count = 0;
  trees.forEach((t) => { t.style.background = ""; }); vc.textContent = "0";
  if (k >= 3) trees.forEach((t, i) => later(() => { t.style.background = d.votes[i] ? "#D93A3A" : "#0B6BCB";
    if (d.votes[i]) count++; vc.textContent = `${count} of ${d.votes.length}`; }, i * 6));
  root.querySelectorAll(".bars .bt b").forEach((b) => { b.style.width = k >= 4 ? b.dataset.w + "%" : "0"; });
  root.querySelectorAll(".rules span").forEach((r) => r.classList.remove("fired"));
  if (k >= 4) later(() => root.querySelectorAll(".rules span")[d.fired].classList.add("fired"), 700);
}

function play(s) {
  clearInterval(s.timer); show(s, 0, true); let k = 0;
  s.timer = setInterval(() => { k++; if (k > 4) return clearInterval(s.timer); show(s, k, true); }, 2400);
}

export default function (component) {
  const { data, parentElement } = component;
  let s = STATE.get(parentElement);
  if (!s) { s = { root: parentElement }; STATE.set(parentElement, s); }
  s.data = data;
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const sig = JSON.stringify([data.label, data.score, data.captions[0]]);
  if (s.sig !== sig) {
    s.sig = sig; clearInterval(s.timer); build(parentElement, data);
    if (reduce) show(s, 4, false);
    else {
      show(s, 0, false); if (s.io) s.io.disconnect();
      s.io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { play(s); s.io.disconnect(); } });
      s.io.observe(parentElement.querySelector(".stages"));
    }
  }
  parentElement.querySelector(".play").onclick = () => play(s);
  parentElement.querySelector(".prev").onclick = () => { clearInterval(s.timer); show(s, Math.max(0, (s.k ?? 0) - 1), true); };
  parentElement.querySelector(".next").onclick = () => { clearInterval(s.timer); show(s, Math.min(4, (s.k ?? 0) + 1), true); };
  return () => { clearInterval(s.timer); if (s.io) s.io.disconnect(); STATE.delete(parentElement); };
}
"""
_ENGINE = st.components.v2.component("fs_engine", html=_ENGINE_HTML, css=_ENGINE_CSS, js=_ENGINE_JS)


def engine_walkthrough(trace: dict, key: str | None = None):
    _ENGINE(key=key, data=trace)


# =====================================================================================
# 5 · Globe: NASA imagery, day/night for the chosen date, pulsing advisory marker
# =====================================================================================
_GLOBE_HTML = """
<div class="fs-globe">
  <div class="fs-map"></div>
  <div class="fs-badge"><i></i><span></span></div>
  <div class="fs-note"></div>
</div>
"""
_GLOBE_CSS = """
.fs-globe { position: relative; height: 420px; border-radius: 20px; overflow: hidden;
  background: radial-gradient(circle at 50% 45%, #0d2747 0%, #050b16 70%); }
.fs-map { position: absolute; inset: 0; }
.fs-badge { position: absolute; left: 14px; top: 14px; z-index: 2; display: flex; align-items: center; gap: 8px; padding: 6px 12px;
  border-radius: 999px; background: rgba(5, 11, 22, .72); color: #fff; font: 700 .8rem var(--st-font, sans-serif);
  backdrop-filter: blur(6px); border: 1px solid rgba(255,255,255,.12); }
.fs-badge i { width: 10px; height: 10px; border-radius: 50%; background: var(--lvl); box-shadow: 0 0 10px var(--lvl); }
.fs-note { position: absolute; left: 16px; top: 52px; right: 60px; z-index: 2; text-shadow: 0 1px 4px #000; color: rgba(255,255,255,.78); font: 500 .72rem var(--st-font, sans-serif); }
.fs-pin { width: 16px; height: 16px; border-radius: 50%; background: var(--lvl); border: 2px solid #fff; position: relative; }
.fs-pin::before, .fs-pin::after { content: ""; position: absolute; inset: -2px; border-radius: 50%; border: 2px solid var(--lvl);
  animation: fs-ping 2.2s ease-out infinite; }
.fs-pin::after { animation-delay: 1.1s; }
@keyframes fs-ping { from { transform: scale(1); opacity: .9; } to { transform: scale(4.2); opacity: 0; } }
@media (prefers-reduced-motion: reduce) { .fs-pin::before, .fs-pin::after { animation: none; } }
"""
_GLOBE_JS = """
const ML = "https://unpkg.com/maplibre-gl@5.6.0/dist/maplibre-gl.js";
const MLCSS = "https://unpkg.com/maplibre-gl@5.6.0/dist/maplibre-gl.css";
const GIBS = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best";
const STATE = new WeakMap();

function loadLib() {
  if (window.maplibregl) return Promise.resolve(window.maplibregl);
  if (!window.__fsMaplibre) {
    window.__fsMaplibre = new Promise((resolve, reject) => {
      const css = document.createElement("link"); css.rel = "stylesheet"; css.href = MLCSS; document.head.appendChild(css);
      const s = document.createElement("script"); s.src = ML; s.onload = () => resolve(window.maplibregl); s.onerror = reject;
      document.head.appendChild(s);
    });
  }
  return window.__fsMaplibre;
}

function nightPolygon(date) {          // day/night line from the sun's declination and hour angle
  const rad = Math.PI / 180, doy = (date - Date.UTC(date.getUTCFullYear(), 0, 0)) / 864e5;
  const decl = -23.44 * Math.cos(2 * Math.PI / 365 * (doy + 10));
  const sunLon = (12 - (date.getUTCHours() + date.getUTCMinutes() / 60)) * 15;
  const pts = [];
  for (let lon = -180; lon <= 180; lon += 2) pts.push([lon, Math.atan(-Math.cos((lon - sunLon) * rad) / Math.tan(decl * rad)) / rad]);
  const pole = decl > 0 ? -90 : 90;
  return { type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [[[-180, pole], ...pts, [180, pole], [-180, pole]]] } };
}

export default function (component) {
  const { data, parentElement } = component;
  const box = parentElement.querySelector(".fs-globe");
  box.style.setProperty("--lvl", data.color);
  parentElement.querySelector(".fs-badge span").textContent = data.badge;
  parentElement.querySelector(".fs-note").textContent = data.note;
  const when = new Date(data.when);
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let s = STATE.get(parentElement);
  if (s) {
    if (s.map && s.map.getSource("night")) s.map.getSource("night").setData(nightPolygon(when));
    return () => { if (s.map) s.map.remove(); STATE.delete(parentElement); };
  }
  s = {}; STATE.set(parentElement, s);
  loadLib().then((maplibregl) => {
    const map = new maplibregl.Map({
      container: parentElement.querySelector(".fs-map"), attributionControl: { compact: true },
      center: [data.lon - 70, data.lat - 5], zoom: 1.1, scrollZoom: false,
      style: { version: 8, projection: { type: "globe" },
        sky: { "atmosphere-blend": ["interpolate", ["linear"], ["zoom"], 0, 1, 5, 1, 7, 0] },
        sources: {
          day: { type: "raster", tileSize: 256, maxzoom: 8, attribution: "Imagery: NASA GIBS Blue Marble",
                 tiles: [GIBS + "/BlueMarble_NextGeneration/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg"] },
          night: { type: "geojson", data: nightPolygon(when) } },
        layers: [ { id: "space", type: "background", paint: { "background-color": "#050b16" } },
                  { id: "day", type: "raster", source: "day" },
                  { id: "night", type: "fill", source: "night", paint: { "fill-color": "#020611", "fill-opacity": 0.55 } } ] },
    });
    s.map = map;
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    const pin = document.createElement("div"); pin.className = "fs-pin";
    new maplibregl.Marker({ element: pin }).setLngLat([data.lon, data.lat]).addTo(map);
    map.on("load", () => {
      if (reduce) return map.jumpTo({ center: [data.lon, data.lat], zoom: 3.6 });
      map.easeTo({ center: [data.lon - 20, data.lat], zoom: 1.6, duration: 2600, easing: (t) => t });
      setTimeout(() => map.flyTo({ center: [data.lon, data.lat], zoom: 3.6, speed: 0.55, curve: 1.6 }), 2700);
    });
  }).catch(() => { parentElement.querySelector(".fs-note").textContent = "The map couldn't load (no internet?)."; });
  return () => { if (s.map) s.map.remove(); STATE.delete(parentElement); };
}
"""
_GLOBE = st.components.v2.component("fs_globe", html=_GLOBE_HTML, css=_GLOBE_CSS, js=_GLOBE_JS, isolate_styles=False)


def globe(lat: float, lon: float, color: str, badge: str, when_iso: str, note: str, key: str | None = None):
    _GLOBE(key=key, data={"lat": lat, "lon": lon, "color": color, "badge": badge, "when": when_iso, "note": note})
