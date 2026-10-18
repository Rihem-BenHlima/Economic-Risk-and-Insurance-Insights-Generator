/* Forecast explorer: pick a series and a model; history, backtest, forecast with its 80% range, scores of all models, horizon accuracy and a CSV download. */
(function () {
  const { h, fmt, pct, cagr, icon, card, grid, insight, bars, D, SERIES, MODELS } = UI;
  const C = Charts;
  const state = { series: "premiums_total", model: "ensemble", backtest: true, band: true, others: false };

  function seg(items, current, onPick) {
    return h("div", { class: "seg" }, Object.entries(items).map(([k, v]) => h("button", { class: k === current ? "on" : "", onclick: () => onPick(k) }, v)));
  }

  function csv() {
    const rows = [["series", "model", "year", "forecast_MTND", "low_80", "high_80"]];
    for (const m of Object.keys(MODELS)) for (const r of D.forecast.forecasts[m][state.series]) rows.push([state.series, m, r.year, r.value, r.low, r.high]);
    const a = h("a", { href: URL.createObjectURL(new Blob([rows.map((r) => r.join(",")).join("\n")], { type: "text/csv" })), download: `forecast_${state.series}.csv` });
    document.body.append(a); a.click(); a.remove();
  }

  Pages.forecasts = {
    title: "Forecasts", subtitle: "Pick a series and a model, and see what it expects for the next three years",
    render(view) {
      const hist = D.forecast.history[state.series], f = D.forecast.forecasts[state.model][state.series], bt = D.forecast.backtest[state.model][state.series];
      const y0 = hist.year[hist.year.length - 1], v0 = hist.value[hist.value.length - 1];
      const rerender = () => { view.replaceChildren(); Pages.forecasts.render(view); };

      view.append(h("div", { class: "controls" },
        h("div", {}, h("div", { class: "ctl-label" }, "Series"), seg(SERIES, state.series, (k) => { state.series = k; rerender(); })),
        h("div", {}, h("div", { class: "ctl-label" }, "Model"), seg(MODELS, state.model, (k) => { state.model = k; rerender(); })),
        h("div", {}, h("div", { class: "ctl-label" }, "Show"),
          h("div", { style: { display: "flex", gap: "16px", padding: "8px 0" } },
            ...[["backtest", "Backtest"], ["band", "80% range"], ["others", "Other models"]].map(([k, label]) =>
              h("label", { class: "toggle" }, h("input", { type: "checkbox", ...(state[k] ? { checked: true } : {}), onchange: (e) => { state[k] = e.target.checked; rerender(); } }), label))))));

      const mape = D.forecast.metrics[state.series][state.model]["MAPE_%"];
      view.append(insight(`<b>${MODELS[state.model]}</b> expects <b>${SERIES[state.series].toLowerCase()}</b> of <b>${fmt(f[2].value)} M.TND</b> in ${f[2].year}, about <b>${pct(cagr(v0, f[2].value, 3))} a year</b> from ${fmt(v0)} in ${y0}. The 80% range for ${f[2].year} is ${fmt(f[2].low)} to ${fmt(f[2].high)}. On past years this model missed this series by <b>${fmt(mape, 1)}%</b> on average.`));

      const main = card({ title: `${SERIES[state.series]}: ${MODELS[state.model]}`, sub: "M.TND. Dots = what the model predicted one year ahead, using only earlier years", height: 440,
        right: h("button", { class: "btn", onclick: csv }, icon("download", 16), "Download CSV") });
      view.append(main.el);
      const traces = [C.line(hist.year, hist.value, "Actual", C.css("--ink"), { width: 2.2, markers: true })];
      if (state.others) for (const m of Object.keys(MODELS)) if (m !== state.model) {
        const g = D.forecast.forecasts[m][state.series];
        traces.push(C.line([y0, ...g.map((r) => r.year)], [v0, ...g.map((r) => r.value)], MODELS[m], C.rgba("#6b7280", 0.8), { width: 1.4, dash: "dot" }));
      }
      if (state.backtest) traces.push({ type: "scatter", mode: "markers", x: bt.map((r) => r.year), y: bt.map((r) => r.value), name: "1-year-ahead backtest", marker: { size: 8, color: C.PALETTE[2], line: { width: 1.5, color: C.css("--surface") } } });
      if (state.band) traces.push(C.band(f.map((r) => r.year), f.map((r) => r.low), f.map((r) => r.high), C.PALETTE[0]));
      traces.push(C.line([y0, ...f.map((r) => r.year)], [v0, ...f.map((r) => r.value)], "Forecast", C.PALETTE[0], { dash: "dash", markers: true, width: 2.8 }));
      C.plot(main.plot, traces, { ...C.yTitle("M.TND"), annotations: f.map((r) => ({ x: r.year, y: r.value, text: fmt(r.value), showarrow: false, yshift: 16, font: { size: 12, color: C.css("--ink") } })) });

      const order = Object.keys(MODELS).map((m) => ({ m, v: D.forecast.metrics[state.series][m]["MAPE_%"] })).sort((a, b) => a.v - b.v);
      const score = h("div", { class: "card" }, h("div", { class: "card-head" }, h("div", {}, h("h3", {}, "Which model forecasts this series best"), h("div", { class: "sub" }, "Average error on past years, lower is better"))),
        bars(order.map((o) => ({ name: MODELS[o.m], value: o.v, label: fmt(o.v, 2) + "%", me: o.m === state.model })), Math.max(...order.map((o) => o.v)) * 1.05),
        h("p", { class: "muted small", style: { marginTop: "14px" } }, `Best here: ${MODELS[order[0].m]}. The ensemble is the final forecast: it is not always first on one series, but it is steady across all five.`));

      const rows = f.map((r, i) => h("tr", {}, h("td", { class: "strong" }, r.year), h("td", { class: "num" }, fmt(r.value)), h("td", { class: "num muted" }, fmt(r.low)), h("td", { class: "num muted" }, fmt(r.high)), h("td", { class: "num" }, pct(100 * (r.value / (i ? f[i - 1].value : v0) - 1)))));
      const table = h("div", { class: "card" }, h("div", { class: "card-head" }, h("div", {}, h("h3", {}, "Forecast values"), h("div", { class: "sub" }, "M.TND, with the 80% range"))),
        h("table", { class: "tbl" }, h("thead", {}, h("tr", {}, h("th", {}, "Year"), h("th", { class: "num" }, "Forecast"), h("th", { class: "num" }, "Low"), h("th", { class: "num" }, "High"), h("th", { class: "num" }, "Growth"))), h("tbody", {}, rows)),
        h("p", { class: "muted small", style: { marginTop: "12px" } }, "The range comes from the model's own errors on past years. With only a few years of testing, treat it as a guide, not a guarantee."));
      view.append(grid("g2", score, table));

      const hz = card({ title: "Accuracy gets worse the further ahead you look", sub: "Average error across all five series, by how many years ahead", height: 280 });
      view.append(hz.el);
      C.plot(hz.plot, Object.keys(MODELS).map((m, i) => ({ type: "bar", name: MODELS[m], x: ["1 year ahead", "2 years ahead", "3 years ahead"], y: ["1", "2", "3"].map((k) => D.forecast.by_horizon[m][k]), marker: { color: m === "ensemble" ? C.PALETTE[0] : C.rgba("#6b7280", 0.22 + 0.1 * i), cornerradius: 2 } })),
        { barmode: "group", hovermode: "closest", ...C.yTitle("average error, %") });
    },
  };
})();
