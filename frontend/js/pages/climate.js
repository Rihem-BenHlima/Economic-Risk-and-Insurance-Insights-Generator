/* Climate and risk: rainfall, heat, floods and drought for Tunis, yearly and by month. */
(function () {
  const { h, fmt, mean, kpi, card, grid, insight, D } = UI;
  const C = Charts;

  Pages.climate = {
    title: "Climate and risk", subtitle: "Rain, heat, floods and drought in Tunis, the weather behind property and motor claims",
    render(view) {
      const a = D.climate.annual, x = a.year, n = x.length - 1, m = D.climate.monthly;
      const wet = a.heavy_rain_days_ge20mm.indexOf(Math.max(...a.heavy_rain_days_ge20mm)), avg = mean(a.rainfall_mm), sign = (v, d = 1) => (v > 0 ? "+" : "") + fmt(v, d);
      const early = mean(a.heat_days_ge35c.slice(0, 10)), recent = mean(a.heat_days_ge35c.slice(-5));
      view.append(insight(`Hot days are becoming more common: Tunis averaged <b>${fmt(early)}</b> days a year at or above 35 °C in ${x[0]}-${x[9]} and <b>${fmt(recent)}</b> in the last five years. Rainfall averages <b>${fmt(avg)} mm</b> but swings between ${fmt(Math.min(...a.rainfall_mm))} and ${fmt(Math.max(...a.rainfall_mm))} mm. The wettest year for flood risk was <b>${x[wet]}</b>, with <b>${a.heavy_rain_days_ge20mm[wet]}</b> days of 20 mm or more.`));
      view.append(grid("g4",
        kpi({ label: `Rainfall ${x[n]}`, value: fmt(a.rainfall_mm[n]), unit: "mm", delta: 100 * (a.rainfall_mm[n] / avg - 1), deltaText: sign(100 * (a.rainfall_mm[n] / avg - 1), 0) + "% vs average", values: a.rainfall_mm.slice(-10), delay: 0 }),
        kpi({ label: `Hot days ${x[n]}`, value: fmt(a.heat_days_ge35c[n]), unit: "days ≥ 35 °C", delta: a.heat_days_ge35c[n] - a.heat_days_ge35c[n - 1], goodUp: false, deltaText: sign(a.heat_days_ge35c[n] - a.heat_days_ge35c[n - 1], 0) + " days", values: a.heat_days_ge35c.slice(-10), delay: 60 }),
        kpi({ label: "Mean temperature", value: fmt(a.temp_mean_c[n], 1), unit: "°C", delta: a.temp_mean_c[n] - a.temp_mean_c[0], goodUp: false, deltaText: sign(a.temp_mean_c[n] - a.temp_mean_c[0]) + " °C since " + x[0], values: a.temp_mean_c.slice(-10), delay: 120 }),
        kpi({ label: "Heaviest day", value: fmt(a.max_daily_rain_mm[n]), unit: "mm", values: a.max_daily_rain_mm.slice(-10), delay: 180 })));
      const c1 = card({ title: "Annual rainfall", sub: "mm, dashed line = average", height: 300 }), c2 = card({ title: "Hot days", sub: "Days at or above 35 °C", height: 300, delay: 60 });
      const c3 = card({ title: "Flood risk", sub: "Days with 20 mm of rain or more; red = the three wettest years", height: 300 }), c4 = card({ title: "Drought", sub: "Longest run of days with under 1 mm of rain", height: 300, delay: 60 });
      const c5 = card({ title: "Rainfall by month and year", sub: "mm: darker = wetter", height: 420 }), c6 = card({ title: "Mean temperature", sub: "°C", height: 420, delay: 60 });
      view.append(grid("g2", c1.el, c2.el), grid("g2", c3.el, c4.el), grid("g-main", c5.el, c6.el));
      C.plot(c1.plot, [C.bar(x, a.rainfall_mm, "Rainfall", C.PALETTE[0])], { shapes: [{ type: "line", xref: "paper", x0: 0, x1: 1, y0: avg, y1: avg, line: { dash: "dash", color: C.css("--muted"), width: 1 } }] });
      C.plot(c2.plot, [C.bar(x, a.heat_days_ge35c, "Hot days", C.PALETTE[2])]);
      const top3 = a.heavy_rain_days_ge20mm.map((v, i) => [v, i]).sort((p, q) => q[0] - p[0]).slice(0, 3).map((p) => p[1]);
      C.plot(c3.plot, [C.bar(x, a.heavy_rain_days_ge20mm, "Days ≥ 20 mm", C.PALETTE[1], { colors: x.map((_, i) => (top3.includes(i) ? C.PALETTE[4] : C.PALETTE[1])) })]);
      C.plot(c4.plot, [C.line(x, a.dry_spell_max_days, "Longest dry spell (days)", "#b45309", { markers: true })]);
      const years = [...new Set(m.month.map((s) => s.slice(0, 4)))], z = years.map((yr) => Array.from({ length: 12 }, (_, i) => { const k = m.month.indexOf(`${yr}-${String(i + 1).padStart(2, "0")}`); return k < 0 ? null : m.rainfall_mm[k]; }));
      C.plot(c5.plot, [{ type: "heatmap", z, x: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], y: years, colorscale: [[0, C.css("--surface-2")], [1, "#4f46e5"]], colorbar: { thickness: 10, len: 0.8 }, hovertemplate: "%{y} %{x}: %{z} mm<extra></extra>" }], { hovermode: "closest", yaxis: { autorange: "reversed", type: "category", dtick: 2 } });
      C.plot(c6.plot, [C.line(x, a.temp_mean_c, "Mean temperature", C.PALETTE[4], { markers: true })], { yaxis: { ticksuffix: " °C" } });
    },
  };
})();
