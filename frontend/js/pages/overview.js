/* Overview: headline, key figures, the final forecast, branch mix and how accurate the models were. */
(function () {
  const { h, fmt, pct, last, cagr, mean, kpi, card, grid, bars, D, SERIES, MODELS, modelMape } = UI;
  const C = Charts;

  Pages.overview = {
    title: "Overview", subtitle: "Where Tunisian insurance stands today and where the models see it going",
    render(view) {
      const y = D.meta.last_year, ins = D.insurance, n = ins.year.length - 1;
      const ens = D.forecast.forecasts.ensemble;
      const prem = ins.premiums_total, claims = ins.claims_paid_total, tot = ens.premiums_total, cl = ens.claims_paid_total;
      const growth = 100 * (prem[n] / prem[n - 1] - 1), yrs = tot[2].year - y;
      const ensMape = modelMape("ensemble");

      view.append(h("div", { class: "hero" }, h("div", { class: "hero-text" },
        h("div", { class: "hero-eyebrow" }, "Final forecast · ensemble of five models"),
        h("h2", {}, `Insurance premiums are projected to reach ${fmt(tot[2].value)} M.TND by ${tot[2].year}`),
        h("p", {}, `That is about ${pct(cagr(prem[n], tot[2].value, yrs))} a year from ${fmt(prem[n])} M.TND in ${y}. Paid claims are projected to reach ${fmt(cl[2].value)} M.TND. The forecast averages five models and was tested on past years with an average error of ${fmt(ensMape, 1)}%.`),
        h("div", { class: "hero-stats" },
          h("div", { class: "hero-stat" }, h("span", {}, `Premiums ${y}`), h("b", {}, fmt(prem[n]) + " M.TND")),
          h("div", { class: "hero-stat" }, h("span", {}, `Growth ${y}`), h("b", {}, pct(growth))),
          h("div", { class: "hero-stat" }, h("span", {}, `Claims ${y}`), h("b", {}, fmt(claims[n]) + " M.TND")),
          h("div", { class: "hero-stat" }, h("span", {}, `${tot[2].year} range (80%)`), h("b", {}, `${fmt(tot[2].low)} to ${fmt(tot[2].high)}`)))), Art.hero()));

      const e = D.economy.annual, ne = e.year.length - 1, lab = D.labour.annual, nl = lab.year.length - 1, tail = (a, k = 10) => a.slice(-k);
      view.append(grid("g4",
        kpi({ label: "Premiums", value: fmt(prem[n]), unit: "M.TND", delta: growth, deltaText: pct(growth) + " vs " + (y - 1), values: tail(prem), delay: 0 }),
        kpi({ label: "Paid claims", value: fmt(claims[n]), unit: "M.TND", delta: 100 * (claims[n] / claims[n - 1] - 1), goodUp: false, deltaText: pct(100 * (claims[n] / claims[n - 1] - 1)) + " vs " + (y - 1), values: tail(claims), delay: 60 }),
        kpi({ label: "Real GDP growth", value: fmt(e.gdp_growth_pct[ne], 1), unit: "%", delta: e.gdp_growth_pct[ne] - e.gdp_growth_pct[ne - 1], deltaText: (e.gdp_growth_pct[ne] - e.gdp_growth_pct[ne - 1] > 0 ? "+" : "") + fmt(e.gdp_growth_pct[ne] - e.gdp_growth_pct[ne - 1], 1) + " pts", values: tail(e.gdp_growth_pct), delay: 120 }),
        kpi({ label: "Unemployment", value: fmt(lab.unemployment_rate[nl], 1), unit: "%", delta: lab.unemployment_rate[nl] - lab.unemployment_rate[nl - 1], goodUp: false, deltaText: (lab.unemployment_rate[nl] - lab.unemployment_rate[nl - 1] > 0 ? "+" : "") + fmt(lab.unemployment_rate[nl] - lab.unemployment_rate[nl - 1], 1) + " pts", values: tail(lab.unemployment_rate), delay: 180 })));

      const main = card({ title: "Premiums and claims", sub: `History to ${y}, ensemble forecast to ${tot[2].year}, shaded area = 80% range`, height: 360, delay: 100 });
      const tbody = Object.keys(SERIES).map((s) => {
        const f = ens[s], v0 = D.forecast.history[s].value.slice(-1)[0];
        return h("tr", {}, h("td", { class: "strong" }, SERIES[s]), f.map((r) => h("td", { class: "num" }, fmt(r.value))), h("td", { class: "num" }, pct(cagr(v0, f[2].value, yrs))));
      });
      const side = h("div", { class: "card", style: { animationDelay: "160ms" } },
        h("div", { class: "card-head" }, h("div", {}, h("h3", {}, "Final forecast"), h("div", { class: "sub" }, "M.TND, ensemble"))),
        h("table", { class: "tbl" }, h("thead", {}, h("tr", {}, h("th", {}, "Series"), tot.map((r) => h("th", { class: "num" }, r.year)), h("th", { class: "num" }, "per year"))), h("tbody", {}, tbody)),
        h("p", { class: "muted small", style: { marginTop: "12px" } }, "The ensemble weights each model by how accurate it was on years it could already see. Explore any series and model in the Forecasts page."));
      view.append(grid("g-main", main.el, side));
      const x = ins.year;
      C.plot(main.plot, [
        C.line(x, prem, "Total premiums", C.PALETTE[0]), C.line(x, claims, "Paid claims", C.PALETTE[2]),
        C.band(tot.map((r) => r.year), tot.map((r) => r.low), tot.map((r) => r.high), C.PALETTE[0]), C.band(cl.map((r) => r.year), cl.map((r) => r.low), cl.map((r) => r.high), C.PALETTE[2]),
        C.line([y, ...tot.map((r) => r.year)], [prem[n], ...tot.map((r) => r.value)], "Premiums forecast", C.PALETTE[0], { dash: "dash", markers: true }),
        C.line([y, ...cl.map((r) => r.year)], [claims[n], ...cl.map((r) => r.value)], "Claims forecast", C.PALETTE[2], { dash: "dash", markers: true })], C.yTitle("M.TND"));

      const mix = card({ title: `Premiums by branch, ${y}`, sub: "Share of total premiums", height: 300, delay: 120 });
      const parts = [["Motor", ins.premiums_auto[n]], ["Life", ins.premiums_life[n]], ["Health", ins.premiums_health[n]], ["Fire & misc.", ins.premiums_fire_and_misc_combined[n]], ["Transport", ins.premiums_transport[n]]];
      parts.push(["Other", prem[n] - parts.reduce((s, p) => s + p[1], 0)]);
      const order = Object.keys(MODELS).map((m) => ({ m, v: modelMape(m) })).sort((a, b) => a.v - b.v);
      const acc = h("div", { class: "card", style: { animationDelay: "180ms" } },
        h("div", { class: "card-head" }, h("div", {}, h("h3", {}, "Model accuracy"), h("div", { class: "sub" }, "Average error on past years, lower is better"))),
        bars(order.map((o) => ({ name: MODELS[o.m], value: o.v, label: fmt(o.v, 2) + "%", me: o.m === "ensemble" })), Math.max(...order.map((o) => o.v)) * 1.05),
        h("p", { class: "muted small", style: { marginTop: "14px" } }, "Error is the average miss as a percentage of the true value over all five series and 1 to 3 years ahead, on years each model could not see when it forecast them."));
      view.append(grid("g-side", mix.el, acc));
      const total = parts.reduce((t, p) => t + p[1], 0);
      C.plot(mix.plot, [{ type: "pie", hole: 0.62, labels: parts.map((p) => p[0]), values: parts.map((p) => p[1]), marker: { colors: C.MIX, line: { color: C.css("--surface"), width: 2 } }, text: parts.map((p) => (p[1] / total > 0.06 ? fmt(100 * p[1] / total) + "%" : "")), textinfo: "text", textposition: "inside", textfont: { color: ["#fff", "#fff", "#181c22", "#fff", "#fff", "#181c22"], size: 13 }, sort: false, hovertemplate: "%{label}: %{value:,.0f} M.TND (%{percent})<extra></extra>" }],
        { showlegend: true, legend: { orientation: "v", x: 1, y: 0.5 }, margin: { l: 10, r: 10, t: 10, b: 10 }, hovermode: "closest" });
    },
  };
})();
