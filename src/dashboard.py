"""Write dashboard/index.html: a self-contained interactive dashboard (no external libraries).

Usage: python src/dashboard.py   (after analysis.py). Open the file in a browser or serve with GitHub Pages.
"""

from __future__ import annotations

import json

import pandas as pd

from config import BASE, BASKET, LATEST, OUT, PROVINCES, ROOT, SWAPS, WEEKS_PER_YEAR


def build_data() -> dict:
    series = pd.read_csv(OUT / "basket_monthly.csv")
    std = series[series.scenario == "standard"]
    items = pd.read_csv(OUT / "item_changes.csv")
    rank = pd.read_csv(OUT / "province_ranking.csv")
    swaps = pd.read_csv(OUT / "swap_savings.csv")
    geos = PROVINCES + ["Canada"]

    data = {"months": sorted(std.date_key.unique()), "base": BASE, "latest": LATEST, "geos": geos, "by_geo": {}}
    for g in geos:
        s = std[std.geo_name == g].set_index("date_key").weekly_cost
        it = items[(items.geo_name == g) & items["product"].isin(BASKET)].copy()
        it["weekly_change"] = (it.avg_price_latest - it.avg_price_base) * it["product"].map(BASKET)
        it = it.sort_values("weekly_change", ascending=False)
        r = rank[rank.geo_name == g].iloc[0]
        sw = swaps[swaps.geo_name == g]
        data["by_geo"][g] = {
            "series": [round(s.get(m, float("nan")), 2) for m in data["months"]],
            "base_cost": float(r.base_weekly_cost),
            "latest_cost": float(r.latest_weekly_cost),
            "pct_change": float(r["pct_change"]),
            "rank_cost": None if pd.isna(r.rank_most_expensive) else int(r.rank_most_expensive),
            "rank_growth": None if pd.isna(r.rank_fastest_growth) else int(r.rank_fastest_growth),
            "drivers": [{"item": p.split(",")[0], "pct": round(c, 1), "weekly": round(w, 2)}
                        for p, c, w in zip(it["product"], it.pct_chg, it.weekly_change)],
            "swaps": [{"from": o.split(",")[0], "to": s_.split(",")[0], "note": n, "annual": round(a, 0)}
                      for o, s_, n, a in zip(sw.original, sw.substitute, sw.note, sw.annual_saving)],
        }
    data["missing_swaps_note"] = {"Newfoundland and Labrador": "4 L milk is not priced in NL, so that swap is left out."}
    data["weeks"] = WEEKS_PER_YEAR
    data["n_swaps_defined"] = len(SWAPS)
    return data


HTML = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Grocery basket by province, 2021–2024</title>
<style>
:root{--surface:#fcfcfb;--card:#ffffff;--ink:#0b0b0b;--ink2:#52514e;--muted:#8a8984;--grid:#e6e5e1;--line:#d6d5d0;
--s1:#2a78d6;--s2:#b9b8b3;--good:#2a78d6;--bad:#eb6834;--hi:#2a78d6;--lo:#c9d9ef}
@media (prefers-color-scheme:dark){:root{--surface:#1a1a19;--card:#232322;--ink:#f0efec;--ink2:#c3c2b7;--muted:#8f8e88;--grid:#33332f;--line:#44443f;
--s1:#3987e5;--s2:#6b6a64;--good:#3987e5;--bad:#d95926;--hi:#3987e5;--lo:#2c3d55}}
*{box-sizing:border-box}body{margin:0;font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif;background:var(--surface);color:var(--ink)}
main{max-width:1080px;margin:0 auto;padding:24px 20px 48px}h1{font-size:22px;margin:0 0 4px}.sub{color:var(--ink2);margin:0 0 18px}
.controls{display:flex;gap:10px;align-items:center;margin:0 0 18px}select{font:inherit;padding:6px 10px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--ink)}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px}.kpi{background:var(--card);border:1px solid var(--grid);border-radius:10px;padding:14px}
.kpi .v{font-size:26px;font-weight:650;letter-spacing:-.01em}.kpi .l{color:var(--ink2);font-size:12.5px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}.card{background:var(--card);border:1px solid var(--grid);border-radius:10px;padding:14px 16px}
.card.wide{grid-column:1/-1}.card h2{font-size:15px;margin:0 0 2px}.card p.note{color:var(--ink2);margin:0 0 8px;font-size:12.5px}
svg{display:block;width:100%;height:auto;overflow:visible}svg text{fill:var(--ink2);font-size:11px}.axis line,.axis path{stroke:var(--line)}
.gridline{stroke:var(--grid)}.legend{display:flex;gap:14px;font-size:12px;color:var(--ink2);margin:2px 0 6px}.legend i{display:inline-block;width:14px;height:2px;vertical-align:middle;margin-right:5px}
.tip{position:fixed;pointer-events:none;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 10px;font-size:12px;box-shadow:0 4px 14px rgba(0,0,0,.12);display:none;z-index:9}
.tip b{font-size:13px;color:var(--ink)}.tip .r{display:flex;gap:6px;align-items:center;color:var(--ink2)}.tip .r i{width:12px;height:2px;display:inline-block}
details{margin-top:8px;font-size:12.5px;color:var(--ink2)}table{border-collapse:collapse;width:100%;margin-top:6px}td,th{padding:3px 6px;border-bottom:1px solid var(--grid);text-align:right}td:first-child,th:first-child{text-align:left}
footer{margin-top:22px;color:var(--muted);font-size:12px}a{color:var(--s1)}
@media (max-width:760px){.kpis{grid-template-columns:1fr 1fr}.grid{grid-template-columns:1fr}}
</style></head><body><main>
<h1>What a weekly grocery basket costs across Canada</h1>
<p class="sub">24 staples for a two-adult household, priced with Statistics Canada monthly average retail prices (Table 18-10-0245-01), Jan 2017 – Aug 2024. Changes compare summer 2021 with summer 2024 (Jun–Aug averages).</p>
<div class="controls"><label for="geo">Province</label><select id="geo"></select></div>
<div class="kpis">
 <div class="kpi"><div class="v" id="k1"></div><div class="l">weekly basket, Jun–Aug 2024</div></div>
 <div class="kpi"><div class="v" id="k2"></div><div class="l">change since Jun–Aug 2021</div></div>
 <div class="kpi"><div class="v" id="k3"></div><div class="l" id="k3l">rank among 10 provinces (1 = most expensive)</div></div>
 <div class="kpi"><div class="v" id="k4"></div><div class="l">a year saved by the swaps that pay off here</div></div>
</div>
<div class="grid">
 <div class="card wide"><h2>Weekly basket cost, monthly</h2><p class="note">Hover for values. Spikes are mostly meat and produce prices moving month to month.</p>
  <div class="legend"><span><i style="background:var(--s1)"></i><span id="lg1"></span></span><span><i style="background:var(--s2)"></i>Canada</span></div>
  <div id="c1"></div><details><summary>Table</summary><div id="t1"></div></details></div>
 <div class="card"><h2>Increase by province, summer 2021 → summer 2024</h2><p class="note">Same 24 items everywhere. Selected province in blue.</p><div id="c2"></div><details><summary>Table</summary><div id="t2"></div></details></div>
 <div class="card"><h2>What drove the increase</h2><p class="note">Change in weekly cost by item ($ per week). Items to the left got cheaper.</p><div id="c3"></div><details><summary>Table</summary><div id="t3"></div></details></div>
 <div class="card wide"><h2>Cheaper swaps for the same amount of food</h2><p class="note" id="swapnote">Annual saving at Jun–Aug 2024 prices. Orange bars cost more than the original here, so skip them.</p><div id="c4"></div><details><summary>Table</summary><div id="t4"></div></details></div>
</div>
<footer>Source: Statistics Canada, Table 18-10-0245-01, Monthly average retail prices for selected products (Open Government Licence – Canada). Average prices are not a price index: StatCan recommends the CPI for measuring inflation. Code and method: <a href="https://github.com/Lrk777/canada-grocery-basket-inflation">github.com/Lrk777/canada-grocery-basket-inflation</a>.</footer>
</main><div class="tip" id="tip"></div>
<script>
const D = __DATA__;
const $ = s => document.querySelector(s), NS = "http://www.w3.org/2000/svg";
const money = v => "$" + v.toFixed(2), pct = v => (v > 0 ? "+" : "") + v.toFixed(1) + "%";
const el = (t, a = {}, p) => { const e = document.createElementNS(NS, t); for (const k in a) e.setAttribute(k, a[k]); if (p) p.appendChild(e); return e; };
const txt = (p, x, y, s, a = {}) => { const t = el("text", Object.assign({x, y}, a), p); t.textContent = s; return t; };
const tip = $("#tip");
function showTip(ev, title, rows) { tip.replaceChildren(); const b = document.createElement("b"); b.textContent = title; tip.appendChild(b);
  for (const [c, label, val] of rows) { const r = document.createElement("div"); r.className = "r"; const i = document.createElement("i"); i.style.background = c; r.appendChild(i);
    const s = document.createElement("span"); s.textContent = label + ": "; const v = document.createElement("strong"); v.textContent = val; r.append(s, v); tip.appendChild(r); }
  tip.style.display = "block"; const w = tip.offsetWidth; tip.style.left = Math.min(ev.clientX + 14, innerWidth - w - 8) + "px"; tip.style.top = (ev.clientY + 14) + "px"; }
const hideTip = () => tip.style.display = "none";
function table(target, head, rows) { const t = document.createElement("table"); const tr = t.insertRow(); head.forEach(h => { const th = document.createElement("th"); th.textContent = h; tr.appendChild(th); });
  rows.forEach(r => { const row = t.insertRow(); r.forEach(c => { row.insertCell().textContent = c; }); }); $(target).replaceChildren(t); }
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

function lineChart(g) {
  const W = 1000, H = 280, m = {l: 44, r: 90, t: 10, b: 24}, a = D.by_geo[g].series, c = D.by_geo.Canada.series, n = D.months.length;
  const all = a.concat(c).filter(v => !isNaN(v)), lo = Math.floor(Math.min(...all) / 5) * 5, hi = Math.ceil(Math.max(...all) / 5) * 5;
  const x = i => m.l + i * (W - m.l - m.r) / (n - 1), y = v => m.t + (hi - v) * (H - m.t - m.b) / (hi - lo);
  const s = el("svg", {viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Weekly basket cost over time"});
  for (let v = lo; v <= hi; v += 5) { el("line", {x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), class: "gridline"}, s); txt(s, m.l - 6, y(v) + 4, "$" + v, {"text-anchor": "end"}); }
  D.months.forEach((mo, i) => { if (mo.endsWith("-01")) txt(s, x(i), H - 6, mo.slice(0, 4), {"text-anchor": "middle"}); });
  const path = (arr, col, w) => el("path", {d: arr.map((v, i) => (i ? "L" : "M") + x(i) + "," + y(v)).join(""), fill: "none", stroke: col, "stroke-width": w, "stroke-linejoin": "round"}, s);
  if (g !== "Canada") path(c, css("--s2"), 2); path(a, css("--s1"), 2);
  txt(s, x(n - 1) + 6, y(a[n - 1]) + 4, money(a[n - 1]), {style: "fill:var(--ink)"});
  if (g !== "Canada") txt(s, x(n - 1) + 6, y(c[n - 1]) + (c[n - 1] > a[n - 1] ? -6 : 14), "Canada " + money(c[n - 1]));
  const hair = el("line", {y1: m.t, y2: H - m.b, stroke: css("--ink2"), "stroke-width": 1, opacity: 0}, s);
  const hit = el("rect", {x: m.l, y: m.t, width: W - m.l - m.r, height: H - m.t - m.b, fill: "transparent", tabindex: 0}, s);
  hit.addEventListener("pointermove", ev => { const r = s.getBoundingClientRect(), px = (ev.clientX - r.left) * W / r.width;
    const i = Math.max(0, Math.min(n - 1, Math.round((px - m.l) / ((W - m.l - m.r) / (n - 1))))); hair.setAttribute("x1", x(i)); hair.setAttribute("x2", x(i)); hair.setAttribute("opacity", .5);
    const rows = [[css("--s1"), g, money(a[i])]]; if (g !== "Canada") rows.push([css("--s2"), "Canada", money(c[i])]); showTip(ev, D.months[i], rows); });
  hit.addEventListener("pointerleave", () => { hair.setAttribute("opacity", 0); hideTip(); });
  $("#c1").replaceChildren(s); $("#lg1").textContent = g;
  table("#t1", ["Month", g, "Canada"], D.months.map((mo, i) => [mo, money(a[i]), money(c[i])]).filter((_, i) => i % 3 === 0 || i === n - 1));
}

function hbars(target, rows, opts) {
  const W = 480, bh = 18, gap = 6, m = {l: opts.left || 150, r: 64, t: 4, b: 6}, H = m.t + m.b + rows.length * (bh + gap);
  const vals = rows.map(r => r.v), mn = Math.min(0, ...vals), mx = Math.max(0, ...vals);
  const x = v => m.l + (v - mn) * (W - m.l - m.r) / ((mx - mn) || 1);
  const s = el("svg", {viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": opts.label});
  el("line", {x1: x(0), x2: x(0), y1: 0, y2: H, stroke: css("--line")}, s);
  rows.forEach((r, i) => { const yy = m.t + i * (bh + gap), x0 = x(Math.min(0, r.v)), w = Math.max(1, Math.abs(x(r.v) - x(0)));
    txt(s, m.l - 8, yy + bh * .72, r.label, {"text-anchor": "end", style: r.strong ? "fill:var(--ink);font-weight:600" : ""});
    const b = el("rect", {x: x0, y: yy, width: w, height: bh, rx: 3, fill: r.color, tabindex: 0}, s);
    txt(s, r.v >= 0 ? x(r.v) + 5 : x(r.v) - 5, yy + bh * .72, opts.fmt(r.v), {"text-anchor": r.v >= 0 ? "start" : "end"});
    const on = ev => { b.setAttribute("opacity", .8); showTip(ev, r.label, [[r.color, opts.metric, opts.fmt(r.v)]].concat(r.extra || [])); };
    b.addEventListener("pointermove", on); b.addEventListener("focus", ev => on({clientX: b.getBoundingClientRect().right, clientY: b.getBoundingClientRect().top}));
    b.addEventListener("pointerleave", () => { b.setAttribute("opacity", 1); hideTip(); }); b.addEventListener("blur", hideTip); });
  $(target).replaceChildren(s);
}

function render() {
  const g = $("#geo").value, G = D.by_geo[g];
  $("#k1").textContent = money(G.latest_cost); $("#k2").textContent = pct(G.pct_change);
  $("#k3").textContent = G.rank_cost ? G.rank_cost + " of 10" : "—"; $("#k3l").textContent = G.rank_cost ? "rank among 10 provinces (1 = most expensive)" : "national average (not ranked)";
  const good = G.swaps.filter(s => s.annual > 0).reduce((t, s) => t + s.annual, 0); $("#k4").textContent = "$" + Math.round(good);
  lineChart(g);
  const prov = D.geos.filter(p => p !== "Canada").map(p => ({label: p, v: D.by_geo[p].pct_change, color: p === g ? css("--hi") : css("--lo"), strong: p === g,
    extra: [[css("--s2"), "weekly basket, summer 2024", money(D.by_geo[p].latest_cost)]]})).sort((a, b) => b.v - a.v);
  prov.push({label: "Canada (average)", v: D.by_geo.Canada.pct_change, color: g === "Canada" ? css("--hi") : css("--s2"), strong: g === "Canada"});
  hbars("#c2", prov, {left: 170, label: "Percent change by province", metric: "change", fmt: pct});
  table("#t2", ["Province", "Summer 2021", "Summer 2024", "Change"], D.geos.map(p => [p, money(D.by_geo[p].base_cost), money(D.by_geo[p].latest_cost), pct(D.by_geo[p].pct_change)]));
  const dr = G.drivers.map(d => ({label: d.item, v: d.weekly, color: d.weekly >= 0 ? css("--s1") : css("--s2"), extra: [[css("--s2"), "price change", pct(d.pct)]]}));
  hbars("#c3", dr, {left: 150, label: "Contribution to the weekly increase", metric: "weekly cost change", fmt: v => (v < 0 ? "−$" : "+$") + Math.abs(v).toFixed(2)});
  table("#t3", ["Item", "Price change", "$/week change"], G.drivers.map(d => [d.item, pct(d.pct), d.weekly.toFixed(2)]));
  const sw = G.swaps.slice().sort((a, b) => b.annual - a.annual).map(s => ({label: s.from + " → " + s.to, v: s.annual, color: s.annual > 0 ? css("--good") : css("--bad"), extra: [[css("--s2"), "basis", s.note]]}));
  hbars("#c4", sw, {left: 290, label: "Annual saving per swap", metric: "a year", fmt: v => (v < 0 ? "−$" : "$") + Math.abs(Math.round(v))});
  table("#t4", ["Swap", "Basis", "$ a year"], G.swaps.map(s => [s.from + " → " + s.to, s.note, Math.round(s.annual)]));
  $("#swapnote").textContent = "Annual saving at Jun–Aug 2024 prices. Orange bars cost more than the original here, so skip them." + (D.missing_swaps_note[g] ? " " + D.missing_swaps_note[g] : "");
}
D.geos.forEach(g => { const o = document.createElement("option"); o.value = o.textContent = g; $("#geo").appendChild(o); });
$("#geo").value = "Ontario"; $("#geo").addEventListener("change", render); render();
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", render);
</script></body></html>
"""


def main() -> None:
    data = build_data()
    out = ROOT / "dashboard" / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(HTML.replace("__DATA__", json.dumps(data, separators=(",", ":"))), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
