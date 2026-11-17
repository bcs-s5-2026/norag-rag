// Metrics tab: numbers from /api/metrics drawn as small SVG charts in the app's own colours.
(() => {
  const NS = "http://www.w3.org/2000/svg";
  const GREEN = "#27664e", LIGHT = "#64a17c", GREY = "#c9d3cb", RED = "#b4543a", AMBER = "#c79a3b";
  const $ = (id) => document.getElementById(id);
  const fmt = (v, unit = "") => (v === null || v === undefined ? "–" : v.toLocaleString() + unit);
  function el(tag, attrs = {}, text) {
    const e = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
    if (text !== undefined) e.textContent = text;
    return e;
  }
  function html(tag, text, cls) {
    const e = document.createElement(tag);
    if (text !== undefined) e.textContent = text;
    if (cls) e.className = cls;
    return e;
  }
  function chartBox(title, note) {
    const box = html("div", undefined, "metric-chart");
    box.append(html("h3", title));
    if (note) box.append(html("p", note, "hint"));
    return box;
  }
  function empty(box) { box.append(html("p", "Nothing to show yet.", "hint")); return box; }

  function donut(m) {
    const q = m.questions;
    const parts = [["Answered", q.answered, GREEN], ["Abstained", q.abstained, AMBER], ["Failed or rejected", q.errors + q.invalid, RED]];
    const total = parts.reduce((s, p) => s + p[1], 0);
    const box = chartBox("How questions ended", "An abstention means the documents did not contain the answer.");
    if (!total) return empty(box);
    const svg = el("svg", { viewBox: "0 0 360 170", role: "img", "aria-label": "Question outcomes" });
    let angle = -Math.PI / 2;
    const r = 62, cx = 85, cy = 85;
    for (const [, value, colour] of parts) {
      if (!value) continue;
      const sweep = (value / total) * Math.PI * 2;
      if (value === total) svg.append(el("circle", { cx, cy, r, fill: "none", stroke: colour, "stroke-width": 26 }));
      else {
        const a = [cx + r * Math.cos(angle), cy + r * Math.sin(angle)];
        const b = [cx + r * Math.cos(angle + sweep), cy + r * Math.sin(angle + sweep)];
        svg.append(el("path", { d: `M${a} A${r},${r} 0 ${sweep > Math.PI ? 1 : 0} 1 ${b}`, fill: "none", stroke: colour, "stroke-width": 26 }));
      }
      angle += sweep;
    }
    svg.append(el("text", { x: cx, y: cy + 6, "text-anchor": "middle", "font-size": 22, "font-weight": 700, fill: "#24342e" }, total));
    parts.forEach(([name, value, colour], i) => {
      svg.append(el("rect", { x: 180, y: 38 + i * 32, width: 12, height: 12, rx: 3, fill: colour }));
      svg.append(el("text", { x: 200, y: 49 + i * 32, "font-size": 13, fill: "#24342e" }, `${name}: ${value} (${Math.round((value / total) * 100)}%)`));
    });
    box.append(svg);
    return box;
  }

  function hbars(title, note, entries, unit) {
    const box = chartBox(title, note);
    if (!entries.length) return empty(box);
    const max = Math.max(...entries.map((e) => e[1] || 0), 1);
    const h = 28 * entries.length + 8;
    const svg = el("svg", { viewBox: `0 0 520 ${h}`, role: "img", "aria-label": title });
    entries.forEach(([name, value], i) => {
      const y = 4 + i * 28, w = Math.max(2, (value / max) * 290);
      svg.append(el("text", { x: 0, y: y + 15, "font-size": 12, fill: "#24342e" }, name));
      svg.append(el("rect", { x: 110, y: y + 3, width: w, height: 14, rx: 3, fill: LIGHT }));
      svg.append(el("text", { x: 116 + w, y: y + 15, "font-size": 12, fill: "#527d61" }, fmt(value) + unit));
    });
    box.append(svg);
    return box;
  }

  function columns(title, note, labels, values, colours) {
    const box = chartBox(title, note);
    if (!values.length) return empty(box);
    const max = Math.max(...values, 1), W = 520, H = 190, base = 150, slot = Math.min(40, (W - 40) / values.length);
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": title });
    svg.append(el("line", { x1: 30, y1: base, x2: W, y2: base, stroke: GREY }));
    svg.append(el("text", { x: 0, y: 14, "font-size": 11, fill: "#527d61" }, fmt(Math.round(max))));
    values.forEach((v, i) => {
      const h = (v / max) * (base - 20), x = 36 + i * slot;
      svg.append(el("rect", { x, y: base - h, width: slot * 0.7, height: h, rx: 2, fill: colours ? colours[i] : GREEN }));
      if (labels && (values.length <= 14 || i % Math.ceil(values.length / 10) === 0))
        svg.append(el("text", { x: x + slot * 0.35, y: base + 16, "text-anchor": "middle", "font-size": 10, fill: "#527d61" }, labels[i]));
    });
    box.append(svg);
    return box;
  }

  function render(m) {
    const root = $("metrics-body");
    root.replaceChildren();
    root.append(html("p", m.since
      ? `Computed from ${m.traces} saved traces since ${m.since.slice(0, 10)}. Traces hold counts, timings and costs, never text.`
      : "No traces yet. Ask a question first.", "hint"));
    const q = m.questions;
    const cards = html("div", undefined, "metric-cards");
    for (const [label, value] of [
      ["questions", fmt(q.total)], ["median latency", fmt(m.latency_ms.p50, " ms")], ["slowest 5% (p95)", fmt(m.latency_ms.p95, " ms")],
      ["model calls", fmt(m.llm.calls)], ["tokens in / out", `${fmt(m.llm.input_tokens)} / ${fmt(m.llm.output_tokens)}`],
      ["total cost (USD)", fmt(m.llm.cost_usd)], ["cost per question (USD)", fmt(m.llm.per_question_usd)],
      ["emails / phones hidden", fmt(m.redactions)], ["concept graphs built", `${m.graph_builds.built}${m.graph_builds.partial ? ` (+${m.graph_builds.partial} partial)` : ""}`],
      ["graph unavailable → fallback", fmt(m.graph_unavailable)]]) {
      const c = html("div", undefined, "metric-card");
      c.append(html("b", value), html("span", label));
      cards.append(c);
    }
    root.append(cards);
    const grid = html("div", undefined, "metric-grid");
    grid.append(
      donut(m),
      hbars("Search methods used", "How many questions ticked each method.", Object.entries(m.retrievers), ""),
      hbars("Time per step", "Average milliseconds. The model call and dense search dominate.", Object.entries(m.steps_ms), " ms"),
      columns("Questions per day", "Last 14 days with activity.", Object.keys(m.questions_per_day).map((d) => d.slice(5)), Object.values(m.questions_per_day)),
      columns("Latency of the latest questions (ms)", "Oldest to newest; red bars are failed or rejected questions.",
        (m.recent || []).map((_, i) => String(i + 1)), (m.recent || []).map((r) => r.duration_ms),
        (m.recent || []).map((r) => (r.outcome === "answered" ? GREEN : r.outcome === "abstained" ? AMBER : RED))));
    root.append(grid);
  }

  async function load() {
    try {
      const response = await fetch("/api/metrics");
      render(await response.json());
    } catch (error) {
      $("metrics-body").replaceChildren(html("p", error.message, "error"));
    }
  }
  document.querySelector('[data-tab="metrics-view"]').addEventListener("click", load);
  if (location.pathname === "/metrics") { showTab("metrics-view"); load(); }
})();
