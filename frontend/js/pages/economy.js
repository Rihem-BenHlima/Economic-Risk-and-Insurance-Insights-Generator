/* Economy: growth, inflation, currency, credit, trade and money. */
(function () {
  const { h, fmt, kpi, card, grid, insight, D } = UI;
  const C = Charts;

  Pages.economy = {
    title: "Economy", subtitle: "Growth, prices, currency and credit: the conditions insurance works in",
    render(view) {
      const e = D.economy.annual, x = e.year, n = x.length - 1, q = D.economy.quarterly, m = D.economy.monthly;
      const worst = e.gdp_growth_pct.indexOf(Math.min(...e.gdp_growth_pct));
      const sign = (v, d = 1) => (v > 0 ? "+" : "") + fmt(v, d);
      view.append(insight(`Real GDP shrank by <b>${fmt(-e.gdp_growth_pct[worst], 1)}%</b> in <b>${x[worst]}</b>, the worst year since ${x[0]}. In ${x[n]} growth was <b>${fmt(e.gdp_growth_pct[n], 1)}%</b> with inflation at <b>${fmt(e.inflation_pct[n], 1)}%</b>, and the dinar stood at <b>${fmt(e.tnd_per_usd[n], 2)}</b> per US dollar, from ${fmt(e.tnd_per_usd[0], 2)} in ${x[0]}.`));
      view.append(grid("g4",
        kpi({ label: `GDP growth ${x[n]}`, value: fmt(e.gdp_growth_pct[n], 1), unit: "%", delta: e.gdp_growth_pct[n] - e.gdp_growth_pct[n - 1], deltaText: sign(e.gdp_growth_pct[n] - e.gdp_growth_pct[n - 1]) + " pts", values: e.gdp_growth_pct.slice(-10), delay: 0 }),
        kpi({ label: `Inflation ${x[n]}`, value: fmt(e.inflation_pct[n], 1), unit: "%", delta: e.inflation_pct[n] - e.inflation_pct[n - 1], goodUp: false, deltaText: sign(e.inflation_pct[n] - e.inflation_pct[n - 1]) + " pts", values: e.inflation_pct.slice(-10), delay: 60 }),
        kpi({ label: "TND per USD", value: fmt(e.tnd_per_usd[n], 2), delta: 100 * (e.tnd_per_usd[n] / e.tnd_per_usd[n - 1] - 1), goodUp: false, deltaText: sign(100 * (e.tnd_per_usd[n] / e.tnd_per_usd[n - 1] - 1)) + "%", values: e.tnd_per_usd.slice(-10), delay: 120 }),
        kpi({ label: "Private credit", value: fmt(e.private_credit_pct_gdp[n]), unit: "% of GDP", delta: e.private_credit_pct_gdp[n] - e.private_credit_pct_gdp[n - 1], deltaText: sign(e.private_credit_pct_gdp[n] - e.private_credit_pct_gdp[n - 1]) + " pts", values: e.private_credit_pct_gdp.slice(-10), delay: 180 })));
      const c1 = card({ title: "GDP growth and inflation", sub: "% per year", height: 320 }), c2 = card({ title: "Dinar exchange rate", sub: "Tunisian dinars per US dollar", height: 320, delay: 60 });
      const c3 = card({ title: "Credit and trade", sub: "% of GDP", height: 300 }), c4 = card({ title: "Quarterly real GDP growth", sub: "% against the same quarter a year earlier", height: 300, delay: 60 });
      const c5 = card({ title: "Monthly inflation", sub: "% against the same month a year earlier", height: 300 }), c6 = card({ title: "Broad money growth", sub: "% per year", height: 300, delay: 60 });
      view.append(grid("g2", c1.el, c2.el), grid("g2", c3.el, c4.el), grid("g2", c5.el, c6.el));
      C.plot(c1.plot, [C.bar(x, e.gdp_growth_pct, "Real GDP growth", C.PALETTE[0], { colors: e.gdp_growth_pct.map((v) => (v < 0 ? C.PALETTE[4] : C.PALETTE[0])) }), C.line(x, e.inflation_pct, "Inflation", C.PALETTE[2], { markers: true })], { yaxis: { ticksuffix: "%" } });
      C.plot(c2.plot, [C.line(x, e.tnd_per_usd, "TND per USD", C.PALETTE[1], { markers: true })]);
      C.plot(c3.plot, [C.line(x, e.private_credit_pct_gdp, "Private credit", C.PALETTE[0]), C.line(x, e.exports_pct_gdp, "Exports", C.PALETTE[3]), C.line(x, e.imports_pct_gdp, "Imports", C.PALETTE[4])], { yaxis: { ticksuffix: "%" } });
      C.plot(c4.plot, [C.bar(q.period, q.gdp_real_yoy_pct, "Real GDP growth", C.PALETTE[0], { colors: q.gdp_real_yoy_pct.map((v) => (v < 0 ? C.PALETTE[4] : C.PALETTE[0])) })], { yaxis: { ticksuffix: "%" }, xaxis: { nticks: 10 } });
      C.plot(c5.plot, [C.line(m.month, m.inflation_yoy_pct, "Inflation", C.PALETTE[2])], { yaxis: { ticksuffix: "%" } });
      C.plot(c6.plot, [C.line(x, e.broad_money_growth_pct, "Broad money growth", C.PALETTE[5], { markers: true })], { yaxis: { ticksuffix: "%" } });
    },
  };
})();
