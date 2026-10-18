/* Labour: unemployment and employment. */
(function () {
  const { h, fmt, kpi, card, grid, insight, D } = UI;
  const C = Charts;

  Pages.labour = {
    title: "Labour", subtitle: "Jobs and unemployment: the income side of insurance demand",
    render(view) {
      const a = D.labour.annual, x = a.year, n = x.length - 1, q = D.labour.quarterly;
      const hi = a.unemployment_rate.indexOf(Math.max(...a.unemployment_rate)), sign = (v, d = 1) => (v > 0 ? "+" : "") + fmt(v, d);
      const qn = q.period.length - 1;
      view.append(insight(`Unemployment peaked at <b>${fmt(a.unemployment_rate[hi], 1)}%</b> in <b>${x[hi]}</b> and stood at <b>${fmt(a.unemployment_rate[n], 1)}%</b> in ${x[n]}. In the latest quarter (${q.period[qn]}), it was <b>${fmt(q.unemployment_rate_female[qn], 1)}%</b> for women, <b>${fmt(q.unemployment_rate_male[qn], 1)}%</b> for men and <b>${fmt(q.higher_ed_graduates_unemployment_rate_total[qn], 1)}%</b> for higher-education graduates.`));
      view.append(grid("g3",
        kpi({ label: `Unemployment ${x[n]}`, value: fmt(a.unemployment_rate[n], 1), unit: "%", delta: a.unemployment_rate[n] - a.unemployment_rate[n - 1], goodUp: false, deltaText: sign(a.unemployment_rate[n] - a.unemployment_rate[n - 1]) + " pts", values: a.unemployment_rate.slice(-10), delay: 0 }),
        kpi({ label: "Employed people", value: fmt(a.employed_thousand[n] / 1000, 2), unit: "million", delta: 100 * (a.employed_thousand[n] / a.employed_thousand[n - 1] - 1), values: a.employed_thousand.slice(-10), delay: 60 }),
        kpi({ label: "Employed / labour force", value: fmt(100 * a.employment_rate_proxy[n], 1), unit: "%", delta: 100 * (a.employment_rate_proxy[n] - a.employment_rate_proxy[n - 1]), deltaText: sign(100 * (a.employment_rate_proxy[n] - a.employment_rate_proxy[n - 1])) + " pts", values: a.employment_rate_proxy.slice(-10).map((v) => 100 * v), delay: 120 })));
      const c1 = card({ title: "Unemployment rate", sub: "% of the labour force", height: 320 }), c2 = card({ title: "Employed people", sub: "Thousand. Paler bars are estimates (derived from the unemployment rate)", height: 320, delay: 60 });
      const c3 = card({ title: "Unemployment by group", sub: "Recent quarters, %", height: 300 }), c4 = card({ title: "Employed as a share of the labour force", sub: "%", height: 300, delay: 60 });
      view.append(grid("g2", c1.el, c2.el), grid("g2", c3.el, c4.el));
      C.plot(c1.plot, [C.line(x, a.unemployment_rate, "Unemployment", C.PALETTE[4], { markers: true })], { yaxis: { ticksuffix: "%" } });
      C.plot(c2.plot, [C.bar(x, a.employed_thousand, "Employed", C.PALETTE[0], { colors: a.employed_source.map((s) => (/estimated/.test(s) ? C.rgba(C.PALETTE[0], 0.4) : C.PALETTE[0])) })]);
      C.plot(c3.plot, [C.line(q.period, q.unemployment_rate_total, "Total", C.PALETTE[0], { markers: true }), C.line(q.period, q.unemployment_rate_male, "Men", C.PALETTE[1], { markers: true }),
        C.line(q.period, q.unemployment_rate_female, "Women", C.PALETTE[2], { markers: true }), C.line(q.period, q.higher_ed_graduates_unemployment_rate_total, "Graduates", C.PALETTE[4], { markers: true })], { yaxis: { ticksuffix: "%" } });
      C.plot(c4.plot, [C.line(x, a.employment_rate_proxy.map((v) => 100 * v), "Employed / labour force", C.PALETTE[3], { markers: true })], { yaxis: { ticksuffix: "%" } });
    },
  };
})();
