/* Insurance: market size, branch mix, claims ratio, growth, penetration and the largest companies. */
(function () {
  const { h, fmt, pct, kpi, card, grid, insight, D } = UI;
  const C = Charts;

  Pages.insurance = {
    title: "Insurance", subtitle: "Premiums, claims and the shape of the Tunisian insurance market",
    render(view) {
      const a = D.insurance, x = a.year, n = x.length - 1, y = x[n];
      const other = x.map((_, i) => a.premiums_total[i] - a.premiums_life[i] - a.premiums_auto[i] - a.premiums_health[i] - a.premiums_transport[i] - a.premiums_fire_and_misc_combined[i]);
      const lifeFirst = a.life_share_pct[0], lifeNow = a.life_share_pct[n];
      view.append(insight(`Premiums grew from <b>${fmt(a.premiums_total[0])}</b> M.TND in ${x[0]} to <b>${fmt(a.premiums_total[n])}</b> in ${y}. Motor is still the biggest branch (<b>${fmt(a.auto_share_pct[n])}%</b>), while life grew from <b>${fmt(lifeFirst)}%</b> of the market to <b>${fmt(lifeNow)}%</b>. Insurance is worth ${fmt(a.penetration_pct_gdp[n], 2)}% of GDP.`));
      const tail = (k) => a[k].slice(-10);
      view.append(grid("g4",
        kpi({ label: `Premiums ${y}`, value: fmt(a.premiums_total[n]), unit: "M.TND", delta: 100 * (a.premiums_total[n] / a.premiums_total[n - 1] - 1), values: tail("premiums_total"), delay: 0 }),
        kpi({ label: "Loss ratio", value: fmt(a.loss_ratio_pct[n]), unit: "%", delta: a.loss_ratio_pct[n] - a.loss_ratio_pct[n - 1], goodUp: false, deltaText: (a.loss_ratio_pct[n] - a.loss_ratio_pct[n - 1] > 0 ? "+" : "") + fmt(a.loss_ratio_pct[n] - a.loss_ratio_pct[n - 1], 1) + " pts", values: tail("loss_ratio_pct"), delay: 60 }),
        kpi({ label: "Penetration", value: fmt(a.penetration_pct_gdp[n], 2), unit: "% of GDP", delta: a.penetration_pct_gdp[n] - a.penetration_pct_gdp[n - 1], deltaText: (a.penetration_pct_gdp[n] > a.penetration_pct_gdp[n - 1] ? "+" : "") + fmt(a.penetration_pct_gdp[n] - a.penetration_pct_gdp[n - 1], 2) + " pts", values: tail("penetration_pct_gdp"), delay: 120 }),
        kpi({ label: "Density", value: fmt(a.density_tnd_per_capita[n]), unit: "TND per person", delta: 100 * (a.density_tnd_per_capita[n] / a.density_tnd_per_capita[n - 1] - 1), values: tail("density_tnd_per_capita"), delay: 180 })));

      const c1 = card({ title: "Premiums by branch", sub: "M.TND, stacked", height: 340 }), c2 = card({ title: "Branch shares", sub: "Share of total premiums, %", height: 340, delay: 60 });
      const c3 = card({ title: "Claims paid as a share of premiums", sub: "A lower ratio means more of the premium is kept", height: 320 }), c4 = card({ title: "Annual growth", sub: "% change on the year before", height: 320, delay: 60 });
      const c5 = card({ title: "Penetration", sub: "Premiums as % of GDP", height: 300 }), c6 = card({ title: `Ten largest companies, ${a.companies.year}`, sub: "Premiums, M.TND", height: 300, delay: 60 });
      view.append(grid("g2", c1.el, c2.el), grid("g2", c3.el, c4.el), grid("g2", c5.el, c6.el));

      const parts = [["Life", a.premiums_life], ["Motor", a.premiums_auto], ["Health", a.premiums_health], ["Transport", a.premiums_transport], ["Fire & misc.", a.premiums_fire_and_misc_combined], ["Other", other]];
      C.plot(c1.plot, parts.map(([nm, v], i) => ({ type: "scatter", mode: "lines", stackgroup: "one", x, y: v, name: nm, line: { width: 0.8, color: C.MIX[i] }, fillcolor: C.MIX[i] })), C.yTitle("M.TND"));
      C.plot(c2.plot, parts.map(([nm, v], i) => ({ type: "scatter", mode: "lines", stackgroup: "one", groupnorm: "percent", x, y: v, name: nm, line: { width: 0.8, color: C.MIX[i] }, fillcolor: C.MIX[i] })), { yaxis: { ticksuffix: "%" } });
      const ratio = (c, p) => x.map((_, i) => 100 * a[c][i] / a[p][i]);
      C.plot(c3.plot, [C.line(x, ratio("claims_paid_total", "premiums_total"), "All branches", C.PALETTE[0]), C.line(x, ratio("claims_paid_auto", "premiums_auto"), "Motor", C.PALETTE[2]),
        C.line(x, ratio("claims_paid_health", "premiums_health"), "Health", C.PALETTE[3]), C.line(x, ratio("claims_paid_life", "premiums_life"), "Life", C.PALETTE[4])], { yaxis: { ticksuffix: "%" } });
      const gr = (k) => a[k].map((v, i) => (i ? 100 * (v / a[k][i - 1] - 1) : null));
      C.plot(c4.plot, [C.line(x, gr("premiums_total"), "Total premiums", C.PALETTE[0]), C.line(x, gr("premiums_life"), "Life", C.PALETTE[4]), C.line(x, gr("premiums_auto"), "Motor", C.PALETTE[2]),
        C.line(x, gr("premiums_health"), "Health", C.PALETTE[3]), C.line(x, gr("claims_paid_total"), "Claims", C.PALETTE[1], { dash: "dot" })], { yaxis: { ticksuffix: "%" } });
      C.plot(c5.plot, [C.line(x, a.penetration_pct_gdp, "Penetration", C.PALETTE[5], { markers: true })], { yaxis: { ticksuffix: "%" } });
      const co = a.companies.rows.slice().reverse();
      C.plot(c6.plot, [{ type: "bar", orientation: "h", x: co.map((r) => r.value), y: co.map((r) => r.name), marker: { color: C.PALETTE[0], cornerradius: 4 }, hovertemplate: "%{y}: %{x:,.0f} M.TND<extra></extra>" }], { hovermode: "closest", margin: { l: 150 } });
    },
  };
})();
