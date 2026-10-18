/* Plotly wrapper: one look for every chart, following the light / dark theme through the CSS variables. */
(function () {
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const PALETTE = ["#2f5fa7", "#2a9d8f", "#d08a2e", "#6b8f4e", "#c0463a", "#7b6fa8", "#5aa0d0", "#6b7280"];   // sea blue, teal, ochre (claims), olive (good), brick (bad), violet, sky, slate
  const MIX = ["#1f4e8c", "#2a9d8f", "#d08a2e", "#c0463a", "#6b8f4e", "#9aa5b1"];                                    // for the parts of a whole: navy, teal, ochre, terracotta, olive, grey
  const FONT = 'Inter, "Segoe UI Variable", "Segoe UI", system-ui, sans-serif';

  const isObj = (x) => x && typeof x === "object" && !Array.isArray(x);
  function deep(a, b) {
    const out = { ...a };
    for (const k of Object.keys(b || {})) out[k] = isObj(a[k]) && isObj(b[k]) ? deep(a[k], b[k]) : b[k];
    return out;
  }
  const rgba = (hex, a) => { const n = parseInt(hex.replace("#", ""), 16); return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`; };

  function layout(extra) {
    const axis = { gridcolor: css("--line"), zeroline: false, linecolor: css("--line"), tickcolor: "rgba(0,0,0,0)", automargin: true, tickfont: { size: 11.5 } };
    return deep({
      paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", colorway: PALETTE, hovermode: "x unified",
      font: { family: FONT, color: css("--muted"), size: 12 }, margin: { l: 48, r: 14, t: 8, b: 34 },
      xaxis: { ...axis }, yaxis: { ...axis },
      legend: { orientation: "h", y: -0.2, x: 0, font: { size: 12 }, bgcolor: "rgba(0,0,0,0)" },
      hoverlabel: { bgcolor: css("--surface"), bordercolor: css("--line"), font: { family: FONT, color: css("--ink"), size: 12.5 } },
    }, extra || {});
  }

  function plot(el, traces, extra) {
    const height = el.clientHeight || 320;
    Plotly.newPlot(el, traces, layout({ height, ...(extra || {}) }), { displayModeBar: false, responsive: true });
  }

  /* trace helpers */
  const line = (x, y, name, color, o = {}) => ({ type: "scatter", mode: o.markers ? "lines+markers" : "lines", x, y, name, line: { color, width: o.width || 2.4, dash: o.dash, shape: "linear" }, marker: { size: 5, color }, connectgaps: false, ...(o.extra || {}) });
  const bar = (x, y, name, color, o = {}) => ({ type: "bar", x, y, name, marker: { color: o.colors || color, cornerradius: 2 }, ...(o.extra || {}) });
  const band = (x, low, high, color, name = "80% range") => ({ type: "scatter", mode: "lines", x: [...x, ...x.slice().reverse()], y: [...high, ...low.slice().reverse()], fill: "toself", fillcolor: rgba(color, 0.16), line: { width: 0 }, hoverinfo: "skip", name, showlegend: false });
  const yTitle = (text) => ({ yaxis: { title: { text, font: { size: 11.5 }, standoff: 6 } } });

  window.Charts = { css, PALETTE, MIX, layout, plot, line, bar, band, rgba, yTitle, deep };
})();
