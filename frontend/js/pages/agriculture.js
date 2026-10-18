/* Agriculture: production indices, weight in the economy, and a crop explorer. */
(function () {
  const { h, fmt, kpi, card, grid, insight, D } = UI;
  const C = Charts;
  const state = { crop: "Olives" };

  Pages.agriculture = {
    title: "Agriculture", subtitle: "Harvests and farming's weight in the economy",
    render(view) {
      const a = D.agriculture.annual, x = a.year, n = x.length - 1, crops = Object.keys(D.agriculture.crops).sort();
      const k = a.crops_index_2014_16, worst = k.indexOf(Math.min(...k)), best = k.indexOf(Math.max(...k)), sign = (v, d = 1) => (v > 0 ? "+" : "") + fmt(v, d);
      view.append(insight(`Crop output swings widely: the index (2014-16 = 100) fell to <b>${fmt(k[worst])}</b> in <b>${x[worst]}</b> and peaked at <b>${fmt(k[best])}</b> in <b>${x[best]}</b>. Agriculture is <b>${fmt(a.agri_value_added_pct_gdp[n], 1)}%</b> of GDP and employs <b>${fmt(a.agri_employment_pct_total[n], 1)}%</b> of workers, down from ${fmt(a.agri_employment_pct_total[0], 1)}% in ${x[0]}.`));
      view.append(grid("g3",
        kpi({ label: `Crops index ${x[n]}`, value: fmt(k[n]), delta: 100 * (k[n] / k[n - 1] - 1), values: k.slice(-10), delay: 0 }),
        kpi({ label: "Share of GDP", value: fmt(a.agri_value_added_pct_gdp[n], 1), unit: "%", delta: a.agri_value_added_pct_gdp[n] - a.agri_value_added_pct_gdp[n - 1], deltaText: sign(a.agri_value_added_pct_gdp[n] - a.agri_value_added_pct_gdp[n - 1]) + " pts", values: a.agri_value_added_pct_gdp.slice(-10), delay: 60 }),
        kpi({ label: "Share of employment", value: fmt(a.agri_employment_pct_total[n], 1), unit: "%", delta: a.agri_employment_pct_total[n] - a.agri_employment_pct_total[n - 1], goodUp: false, deltaText: sign(a.agri_employment_pct_total[n] - a.agri_employment_pct_total[n - 1]) + " pts", values: a.agri_employment_pct_total.slice(-10), delay: 120 })));
      const c1 = card({ title: "Production indices", sub: "2014-16 = 100", height: 320 }), c2 = card({ title: "Agriculture in the economy", sub: "% of GDP and % of employment", height: 320, delay: 60 });
      view.append(grid("g2", c1.el, c2.el));
      C.plot(c1.plot, [C.line(x, k, "Crops", C.PALETTE[3], { markers: true }), C.line(x, a.livestock_index_2014_16, "Livestock", C.PALETTE[2]), C.line(x, a.food_index_2014_16, "Food", C.PALETTE[0], { dash: "dot" })]);
      C.plot(c2.plot, [C.line(x, a.agri_value_added_pct_gdp, "Share of GDP", C.PALETTE[3], { markers: true }), C.line(x, a.agri_employment_pct_total, "Share of employment", C.PALETTE[5], { markers: true })], { yaxis: { ticksuffix: "%" } });

      const select = h("select", { class: "select", onchange: (e) => { state.crop = e.target.value; draw(); } }, crops.map((c) => h("option", { value: c, ...(c === state.crop ? { selected: true } : {}) }, c)));
      const ex = card({ title: "Crop explorer", sub: "Production (bars) and yield per hectare (line)", height: 340, right: select });
      view.append(ex.el);
      function draw() {
        const c = D.agriculture.crops[state.crop];
        C.plot(ex.plot, [{ type: "bar", x: c.year, y: c.production_t.map((v) => v / 1000), name: "Production (thousand t)", marker: { color: C.rgba(C.PALETTE[3], 0.85), cornerradius: 4 } },
          { ...C.line(c.year, c.yield_kg_per_ha, "Yield (kg per ha)", C.PALETTE[4], { markers: true }), yaxis: "y2" }],
        { yaxis: { title: { text: "thousand tonnes" } }, yaxis2: { overlaying: "y", side: "right", showgrid: false, title: { text: "kg per ha" }, linecolor: C.css("--line") } });
      }
      draw();
    },
  };
})();
