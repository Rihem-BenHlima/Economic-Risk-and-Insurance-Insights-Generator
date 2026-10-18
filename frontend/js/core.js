/* Shared helpers: DOM builder, number formats, icons and the building blocks of every page (cards, KPIs, insights, bars). */
(function () {
  const D = window.DATA;

  function h(tag, props, ...kids) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(props || {})) {
      if (v === false || v == null) continue;
      if (k === "class") e.className = v;
      else if (k === "html") e.innerHTML = v;
      else if (k === "style" && typeof v === "object") Object.assign(e.style, v);
      else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
      else e.setAttribute(k, v === true ? "" : v);
    }
    for (const k of kids.flat(Infinity)) { if (k == null || k === false) continue; e.append(k.nodeType ? k : document.createTextNode(k)); }
    return e;
  }

  const fmt = (n, d = 0) => (n == null || Number.isNaN(n) ? "–" : Number(n).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d }));
  const pct = (n, d = 1) => (n == null || Number.isNaN(n) ? "–" : (n > 0 ? "+" : "") + Number(n).toFixed(d) + "%");
  const last = (a) => { for (let i = a.length - 1; i >= 0; i--) if (a[i] != null) return a[i]; return null; };
  const lastIdx = (a) => { for (let i = a.length - 1; i >= 0; i--) if (a[i] != null) return i; return -1; };
  const cagr = (from, to, years) => (100 * (Math.pow(to / from, 1 / years) - 1));
  const mean = (a) => a.reduce((s, x) => s + x, 0) / a.length;

  const ICONS = {
    overview: '<path d="M4 13h6V4H4v9zm0 7h6v-5H4v5zm10 0h6V11h-6v9zm0-16v5h6V4h-6z"/>',
    forecasts: '<path d="M3 17l6-6 4 4 8-9"/><path d="M15 6h6v6"/>',
    insurance: '<path d="M12 3l8 3v6c0 4.5-3.2 8-8 9-4.8-1-8-4.5-8-9V6l8-3z"/><path d="M9 12l2 2 4-4"/>',
    economy: '<path d="M4 20V10M10 20V4M16 20v-8M22 20H2"/>',
    labour: '<circle cx="9" cy="8" r="3.2"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/><circle cx="17" cy="9" r="2.4"/><path d="M17 14c2.7 0 4.5 2 4.5 5"/>',
    agriculture: '<path d="M12 21v-9"/><path d="M12 12c0-4 3-6.5 7-6.5 0 4-2.7 6.5-7 6.5z"/><path d="M12 15c0-3-2.2-5-5.5-5 0 3 2 5 5.5 5z"/>',
    climate: '<path d="M7 18a4 4 0 010-8 5.5 5.5 0 0110.6-1.2A3.8 3.8 0 0117 18H7z"/><path d="M9 21l1-2M13 21l1-2"/>',
    method: '<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16.5v.01"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    moon: '<path d="M20 14.5A8 8 0 019.5 4a8 8 0 1010.5 10.5z"/>',
    spark: '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3z"/>',
    download: '<path d="M12 4v11M7 11l5 5 5-5M5 20h14"/>',
    chat: '<path d="M21 12a8 8 0 01-11.6 7.1L4 20l1-4.6A8 8 0 1121 12z"/><path d="M8.5 11h7M8.5 14h4"/>',
    history: '<path d="M3 12a9 9 0 109-9 9 9 0 00-6.4 2.6L3 8"/><path d="M3 3v5h5M12 7v5l3 2"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    expand: '<path d="M14 4h6v6M10 20H4v-6M20 4l-7 7M4 20l7-7"/>',
    shrink: '<path d="M20 10h-6V4M4 14h6v6M14 10l7-7M3 21l7-7"/>',
    trash: '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>',
    send: '<path d="M21 3L10 14M21 3l-7 18-4-7-7-4 18-7z"/>',
  };
  const icon = (name, size = 20) => h("span", { html: `<svg viewBox="0 0 24 24" width="${size}" height="${size}" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${ICONS[name] || ""}</svg>`, style: { display: "inline-flex" } });

  function sparkline(values, up = true) {
    const v = values.filter((x) => x != null);
    if (v.length < 2) return h("span");
    const w = 84, hh = 26, min = Math.min(...v), max = Math.max(...v), rng = max - min || 1;
    const pts = v.map((x, i) => [(i / (v.length - 1)) * w, hh - 3 - ((x - min) / rng) * (hh - 8)]);
    const end = pts[pts.length - 1];
    return h("span", { class: "spark", html: `<svg viewBox="0 0 ${w} ${hh}" width="${w}" height="${hh}"><polyline points="${pts.map((p) => p.join(",")).join(" ")}" fill="none" stroke="var(--muted)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" opacity=".75"/><circle cx="${end[0]}" cy="${end[1]}" r="2.8" fill="var(--page)"/></svg>` });
  }

  /* delta: number; goodUp: is an increase good news? unit: '%' or ' pts' */
  function kpi({ label, value, unit, delta, deltaText, goodUp = true, values, delay = 0 }) {
    let chip = null;
    if (delta != null && !Number.isNaN(delta)) {
      const good = delta === 0 ? null : (delta > 0) === goodUp;
      chip = h("span", { class: "delta " + (good === null ? "" : good ? "up" : "down") }, (delta > 0 ? "▲ " : delta < 0 ? "▼ " : "") + (deltaText || pct(delta)));
    } else if (deltaText) chip = h("span", { class: "delta" }, deltaText);
    return h("div", { class: "card kpi", style: { animationDelay: delay + "ms" } },
      h("div", { class: "kpi-label" }, label),
      h("div", { class: "kpi-value" }, value, unit ? h("small", {}, unit) : null),
      h("div", { class: "kpi-foot" }, chip || h("span"), values ? sparkline(values, delta == null || (delta >= 0) === goodUp) : null));
  }

  function card({ title, sub, right, cls = "", delay = 0, height = 320 }) {
    const plot = h("div", { class: "plot", style: { height: height + "px" } });
    const el = h("div", { class: "card " + cls, style: { animationDelay: delay + "ms" } },
      h("div", { class: "card-head" }, h("div", {}, h("h3", {}, title), sub ? h("div", { class: "sub" }, sub) : null), right || null), plot);
    return { el, plot };
  }

  const insight = (html, delay = 0) => h("div", { class: "insight", style: { animationDelay: delay + "ms" } }, h("p", { html }));
  const grid = (cls, ...kids) => h("div", { class: "grid " + cls }, kids);

  /* horizontal bars in plain HTML: rows = [{name, value, label, me}] */
  function bars(rows, max) {
    const m = max || Math.max(...rows.map((r) => r.value));
    return h("div", { class: "bars" }, rows.map((r) => h("div", { class: "bar-row" + (r.me ? " me" : "") },
      h("div", { class: "bar-name" }, r.name), h("div", { class: "bar-track" }, h("div", { class: "bar-fill", style: { width: Math.max(2, (100 * r.value) / m) + "%" } })), h("div", { class: "bar-val" }, r.label))));
  }

  const MODELS = D.meta.models, SERIES = D.meta.series;
  const modelMape = (model) => mean(Object.keys(SERIES).map((s) => D.forecast.metrics[s][model]["MAPE_%"]));

  window.UI = { h, fmt, pct, last, lastIdx, cagr, mean, icon, kpi, card, insight, grid, bars, sparkline, D, MODELS, SERIES, modelMape };
  window.Pages = {};
})();
