/* Offline answers: understands questions about the numbers on this page (forecasts, accuracy, latest figures) and answers from window.DATA.
 * It is a simple keyword matcher, not a language model, and it says so when it cannot answer. */
(function () {
  const D = window.DATA, F = D.forecast, SERIES = D.meta.series, MODELS = D.meta.models, y0 = D.meta.last_year;
  const fmt = (n, d = 0) => Number(n).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
  const pct = (n, d = 1) => (n > 0 ? "+" : "") + n.toFixed(d) + "%";
  const last = (a) => a[a.length - 1];
  const has = (t, ...words) => words.some((w) => t.includes(w));

  const SERIES_WORDS = [["premiums_life", ["life"]], ["premiums_auto", ["motor", "auto", "car "]], ["premiums_health", ["health"]], ["claims_paid_total", ["claim"]], ["premiums_total", ["premium", "total", "market"]]];
  const MODEL_WORDS = [["ensemble", ["ensemble"]], ["random_forest", ["forest"]], ["gbm", ["boost", "gbm"]], ["lstm", ["lstm"]], ["arima", ["arima"]], ["prophet", ["prophet"]]];
  const findSeries = (t) => (SERIES_WORDS.find(([, ws]) => has(t, ...ws)) || [])[0];
  const findModel = (t) => (MODEL_WORDS.find(([, ws]) => has(t, ...ws)) || [])[0];
  const findYear = (t) => { const m = t.match(/20\d\d/); return m ? Number(m[0]) : null; };
  const avgMape = (m) => Object.keys(SERIES).reduce((s, k) => s + F.metrics[k][m]["MAPE_%"], 0) / Object.keys(SERIES).length;

  function forecast(t) {
    const s = findSeries(t) || "premiums_total", m = findModel(t) || "ensemble", yr = findYear(t), f = F.forecasts[m][s], h = F.history[s], v0 = last(h.value);
    if (yr && yr > y0 && yr <= y0 + 3) {
      const r = f.find((x) => x.year === yr);
      return `**${MODELS[m]}** forecasts **${SERIES[s].toLowerCase()}** of **${fmt(r.value)} M.TND** in ${yr} (80% range ${fmt(r.low)} to ${fmt(r.high)}), compared with ${fmt(v0)} in ${y0}.`;
    }
    const g = 100 * (Math.pow(f[2].value / v0, 1 / 3) - 1);
    return `**${MODELS[m]}** forecasts **${SERIES[s].toLowerCase()}** (M.TND):\n` + f.map((r) => `${r.year}: **${fmt(r.value)}** (range ${fmt(r.low)} to ${fmt(r.high)})`).join("\n") + `\nThat is about ${pct(g)} a year from ${fmt(v0)} in ${y0}.`;
  }

  function accuracy(t) {
    const s = findSeries(t);
    const rows = Object.keys(MODELS).map((m) => [m, s ? F.metrics[s][m]["MAPE_%"] : avgMape(m)]).sort((a, b) => a[1] - b[1]);
    return `Average error on past years${s ? ` for **${SERIES[s].toLowerCase()}**` : " across all five series"} (lower is better):\n` + rows.map(([m, v], i) => `${i + 1}. ${MODELS[m]}: **${fmt(v, 2)}%**`).join("\n") +
      `\nThe ensemble is the final forecast: it averages the models, so it is steady across series even when one model wins a single series.`;
  }

  const FIG = [
    [["unemploy", "jobless"], () => { const a = D.labour.annual, n = a.year.length - 1; return `Unemployment was **${fmt(a.unemployment_rate[n], 1)}%** in ${a.year[n]} (${fmt(a.unemployment_rate[n - 1], 1)}% a year earlier).`; }],
    [["gdp", "growth rate of the economy"], () => { const a = D.economy.annual, n = a.year.length - 1; return `Real GDP growth was **${fmt(a.gdp_growth_pct[n], 1)}%** in ${a.year[n]}, with inflation at **${fmt(a.inflation_pct[n], 1)}%**.`; }],
    [["inflation", "prices"], () => { const a = D.economy.annual, n = a.year.length - 1, m = D.economy.monthly, k = m.month.length - 1; return `Inflation was **${fmt(a.inflation_pct[n], 1)}%** in ${a.year[n]}; the latest monthly reading (${m.month[k]}) is **${fmt(m.inflation_yoy_pct[k], 1)}%** against a year earlier.`; }],
    [["exchange", "dinar", "currency", "usd"], () => { const a = D.economy.annual, n = a.year.length - 1; return `The dinar stood at **${fmt(a.tnd_per_usd[n], 2)}** per US dollar in ${a.year[n]}, from ${fmt(a.tnd_per_usd[0], 2)} in ${a.year[0]}.`; }],
    [["rain"], () => { const a = D.climate.annual, n = a.year.length - 1, avg = a.rainfall_mm.reduce((s, x) => s + x, 0) / a.rainfall_mm.length; return `Tunis had **${fmt(a.rainfall_mm[n])} mm** of rain in ${a.year[n]}, against an average of ${fmt(avg)} mm. It was the wettest in ${a.year[a.rainfall_mm.indexOf(Math.max(...a.rainfall_mm))]} (${fmt(Math.max(...a.rainfall_mm))} mm).`; }],
    [["heat", "hot", "temperature"], () => { const a = D.climate.annual, n = a.year.length - 1; return `Tunis had **${fmt(a.heat_days_ge35c[n])}** days at or above 35 °C in ${a.year[n]} and a mean temperature of **${fmt(a.temp_mean_c[n], 1)} °C** (${fmt(a.temp_mean_c[0], 1)} °C in ${a.year[0]}).`; }],
    [["penetration"], () => { const a = D.insurance, n = a.year.length - 1; return `Insurance penetration was **${fmt(a.penetration_pct_gdp[n], 2)}%** of GDP in ${a.year[n]} (${fmt(a.penetration_pct_gdp[0], 2)}% in ${a.year[0]}), about **${fmt(a.density_tnd_per_capita[n])} TND** per person.`; }],
    [["loss ratio", "claims ratio"], () => { const a = D.insurance, n = a.year.length - 1; return `The loss ratio (claims paid over premiums) was **${fmt(a.loss_ratio_pct[n])}%** in ${a.year[n]}.`; }],
    [["company", "companies", "insurer", "biggest", "largest"], () => { const c = D.insurance.companies; return `The largest insurers by premiums in ${c.year}:\n` + c.rows.slice(0, 5).map((r, i) => `${i + 1}. ${r.name}: **${fmt(r.value)} M.TND**`).join("\n"); }],
    [["share", "motor branch", "life branch", "health branch", "branch"], () => { const a = D.insurance, n = a.year.length - 1; return `In ${a.year[n]}, motor was **${fmt(a.auto_share_pct[n])}%** of premiums, life **${fmt(a.life_share_pct[n])}%** and health **${fmt(a.health_share_pct[n])}%**. Life has grown from ${fmt(a.life_share_pct[0])}% in ${a.year[0]}.`; }],
    [["crop", "harvest", "agricultur"], () => { const a = D.agriculture.annual, n = a.year.length - 1; return `The crops index (2014-16 = 100) was **${fmt(a.crops_index_2014_16[n])}** in ${a.year[n]}. Agriculture is **${fmt(a.agri_value_added_pct_gdp[n], 1)}%** of GDP and **${fmt(a.agri_employment_pct_total[n], 1)}%** of employment.`; }],
  ];

  function latest(t) {
    const s = findSeries(t);
    if (s && has(t, "premium", "claim", "how big", "how much", "size", "motor", "life", "health", "market")) {
      const h = F.history[s], n = h.value.length - 1, yr = findYear(t), i = yr ? h.year.indexOf(yr) : n;
      if (i >= 0) return `**${SERIES[s]}** were **${fmt(h.value[i])} M.TND** in ${h.year[i]}` + (i > 0 ? ` (${pct(100 * (h.value[i] / h.value[i - 1] - 1))} on the year before).` : ".");
    }
    for (const [words, fn] of FIG) if (has(t, ...words)) return fn();
    return null;
  }

  const DEFS = [
    [["mape"], "**MAPE** is the average miss as a percentage of the true value. A MAPE of 3% on a 1,000 M.TND series means a typical miss of about 30 M.TND."],
    [["ensemble"], "The **ensemble** is the final forecast: a weighted average of the five models (ARIMA, Prophet, gradient boosting, Random Forest and LSTM). Each model's weight follows how accurate it was on years it could already see."],
    [["backtest", "tested", "validat"], "Each model was tested from 2012 onwards: refitted on the years before each date, then asked to forecast the next one to three years, and compared with what really happened. Only past years were used at every step."],
    [["range", "interval", "band", "confidence"], "The **80% range** comes from the model's own errors on past years: it is where the true value should fall about 4 times in 5. With only a few tested years, treat it as a guide, not a guarantee."],
  ];

  function answer(raw) {
    const t = " " + raw.toLowerCase().replace(/[?!.,]/g, " ") + " ";
    if (has(t, " hello ", " hi ", " hey ", "good morning", "good evening")) return "Hello! Ask me about the forecasts, how accurate they are, or the latest figures for insurance, the economy, jobs, agriculture and climate.";
    if (has(t, " help ", "what can you", "what do you")) return "I can tell you:\n- forecasts of premiums and claims to " + (y0 + 3) + " (try \"premiums in 2027\")\n- which model is most accurate\n- latest figures: premiums, claims, GDP, inflation, unemployment, rain, heat\n- the largest companies and the branch mix\n- what terms like MAPE and ensemble mean";
    if (has(t, "weather", "tomorrow", "this week", "today")) return "I do not forecast the weather: weather here is only history (yearly rain, heat and drought for Tunis). Live weather and web lookups need the full assistant, which is not connected yet.";
    for (const [words, text] of DEFS) if (has(t, ...words) && !has(t, "which model", "best model")) return text;
    if (has(t, "accura", "error", "best model", "which model", "how good", "reliab", "trust", "precise")) return accuracy(t);
    if (has(t, "forecast", "predict", "expect", "project", "will ", "future", "next year", "by 202", "in 2025", "in 2026", "in 2027")) return forecast(t);
    const l = latest(t);
    if (l) return l;
    if (findSeries(t) && findYear(t)) return latest(t + " premium") || forecast(t);
    return "I could not match that to the data on this page. Try: \"What will premiums be in 2027?\", \"Which model is most accurate?\", \"How big is the motor branch?\" or \"What is the unemployment rate?\". Open-ended questions, live weather and report search need the full assistant, which is not connected yet.";
  }

  window.ChatLocal = { answer };
})();
