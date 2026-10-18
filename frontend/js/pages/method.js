/* How it works: a five-step overview, then sources, models, testing and the honest limits of the forecasts. */
(function () {
  const { h, fmt, grid, D, MODELS, modelMape } = UI;

  Pages.method = {
    title: "How it works", subtitle: "Where the numbers come from, how the forecasts are made and how far to trust them",
    render(view) {
      const ens = modelMape("ensemble"), arima = modelMape("arima");
      const block = (title, ...kids) => h("div", { class: "card method" }, h("h3", { style: { marginTop: 0 } }, title), ...kids);
      const steps = [
        ["1", "Collect", "Official figures for insurance, the economy, jobs, agriculture and climate, all for Tunisia."],
        ["2", "Clean", "Fill gaps only when two sources agree, chain-link changed base years, drop what cannot be repaired."],
        ["3", "Forecast", "Five small models each predict 1 to 3 years ahead. Their weighted average is the ensemble."],
        ["4", "Test", `Replay the past from 2012: forecast each year blind, compare with reality. Ensemble error: ${fmt(ens, 1)}%.`],
        ["5", "Ask", "The chat assistant answers from these same figures and lists the files it used."],
      ];
      view.append(h("div", { class: "card flow-card" }, h("h3", { style: { marginTop: 0 } }, "From raw data to answer"),
        h("div", { class: "flow" }, steps.map(([n, t, d]) => h("div", { class: "flow-step", "data-n": n }, h("span", { class: "flow-n" }, n), h("b", {}, t), h("p", {}, d))))));
      view.append(grid("g2",
        block("The data",
          h("p", {}, "Every figure is for Tunisia only. Raw files from official sources were cleaned before use: gaps are filled only when two sources agree, series whose base year changed are chain-linked, and data that could not be repaired was removed instead of guessed."),
          h("ul", {}, h("li", {}, h("b", {}, "Insurance: "), "premiums and claims by branch and company, from the CGA and FTUSA annual reports, 2003 onwards."),
            h("li", {}, h("b", {}, "Economy: "), "GDP, inflation, exchange rate, credit, trade and money, from the World Bank, FRED, the BCT and the INS."),
            h("li", {}, h("b", {}, "Labour: "), "unemployment and employment, from the INS and the World Bank."),
            h("li", {}, h("b", {}, "Agriculture: "), "production indices and crops, from the FAO and the World Bank."),
            h("li", {}, h("b", {}, "Climate: "), "daily rain and temperature for Tunis, from Open-Meteo."))),
        block("The forecasts",
          h("p", {}, "Five models forecast premiums (total, life, motor, health) and total paid claims, one to three years ahead. The final forecast is their weighted average, called the ensemble. Each model's weight follows how accurate it was on years it could already see."),
          h("ul", {}, ...Object.entries(MODELS).filter(([k]) => k !== "ensemble").map(([k, v]) => h("li", {}, h("b", {}, v + ": "), ({ arima: "a classic time-series model that extends each series' own growth.", prophet: "a trend model with no seasonal pattern, since the data is yearly.", gbm: "small decision trees that learn from the series' recent growth and labour data.", random_forest: "many small trees averaged, the steadier of the two tree models.", lstm: "a small neural network that reads the last two years." })[k])))),
        block("How it was tested",
          h("p", {}, `Every model was tested the way it would be used: from 2012 onwards, it was refitted on the years before each date and asked to forecast the next one to three years, then compared with what really happened. The ensemble's average error was ${fmt(ens, 1)}%, against ${fmt(arima, 1)}% for ARIMA alone.`),
          h("p", {}, "Error means the average miss as a percentage of the true value: 3% on a 1,000 M.TND series is a miss of 30 M.TND. Forecasts further ahead are less accurate (see the Forecasts page).")),
        block("How far to trust them",
          h("ul", {}, h("li", {}, "There are only 22 yearly data points per series, so the models are deliberately small, and the results carry real uncertainty."),
            h("li", {}, "The shaded 80% range comes from past errors, which are few. Treat it as a guide, not a guarantee."),
            h("li", {}, "Outside data such as the economy, jobs, harvests and weather adds only a little over a series' own history, and none of these models forecasts the weather itself."),
            h("li", {}, "A shock such as Covid in 2020 cannot be predicted from earlier years, and the forecasts assume no such shock.")))));
    },
  };
})();
