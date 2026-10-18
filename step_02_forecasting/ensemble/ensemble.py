"""Final ensemble: a weighted average of the five models' forecasts, series by series and horizon by horizon.

Weights: proportional to 1 / MAPE of each member on the rows whose actual value was already known when the forecast was made (target year before the
origin), per series and horizon; equal weights until every member has at least 3 such rows. So the backtest of the ensemble never uses an error it
could not have seen (no look-ahead), and the weights are not tuned on the rows the ensemble is scored on.
The forecast beyond the data uses the weights from all the members' backtest rows. Bands are calibrated on the ensemble's own backtest errors like any
other model's.
Run:  python step_02_forecasting/ensemble/ensemble.py      (after the five models; compare.py then ranks it against them)
Everything of this model lives in this folder: this code, plots/, model/ensemble.joblib (+ .json with the final weights) and metrics/ensemble_metrics.csv.
"""
import sys
import json
import datetime
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))      # step_02_forecasting: common
from common import HORIZON, METRIC_COLS, TARGETS, _print_metrics, calibrated_bounds, load_saved, metrics, model_dir, plot_errors, plot_model, table

warnings.filterwarnings("ignore")
NAME = "ensemble"
MEMBERS = ["arima", "prophet", "gbm", "random_forest", "lstm"]
MIN_ROWS = 3


def weights(history, series, step, before):
    """Weight of each member for (series, step), from its absolute percentage errors on rows with target year < `before`."""
    mape = {}
    for m in MEMBERS:
        g = history[m]
        g = g[(g.series == series) & (g.step == step) & (g.year < before)]
        if len(g) < MIN_ROWS:
            return {m: 1 / len(MEMBERS) for m in MEMBERS}
        mape[m] = max(100 * ((g.forecast - g.actual).abs() / g.actual).mean(), 0.5)
    inv = {m: 1 / v for m, v in mape.items()}
    tot = sum(inv.values())
    return {m: v / tot for m, v in inv.items()}


def main():
    t = table()
    history = {m: load_saved(m, "backtest") for m in MEMBERS}
    keys = ["series", "origin", "step"]
    wide = None
    for m in MEMBERS:
        d = history[m][keys + ["year", "actual", "forecast"]].rename(columns={"forecast": m})
        wide = d if wide is None else wide.merge(d[keys + [m]], on=keys)          # rows that EVERY member produced
    rows = []
    for r in wide.itertuples():
        w = weights(history, r.series, r.step, r.origin)
        f = sum(w[m] * getattr(r, m) for m in MEMBERS)
        scale = np.abs(np.diff(t[r.series][t.index < r.origin].values)).mean()
        rows.append({"series": r.series, "origin": r.origin, "step": r.step, "year": r.year, "model": NAME, "actual": r.actual, "forecast": f, "scale": scale})
    bt = pd.DataFrame(rows)
    bt["error"] = bt.forecast - bt.actual
    bt["log_err"] = np.log(bt.actual / bt.forecast)
    mets, futs, final_w = [], [], {}
    for col in TARGETS:
        g = bt[bt.series == col]
        m = metrics(g)
        fut = []
        for k in range(1, HORIZON + 1):
            w = weights(history, col, k, 10 ** 6)
            final_w[f"{col}|{k}"] = {mm: round(v, 4) for mm, v in w.items()}
            yr = int(t.index.max()) + k
            fc = sum(w[mm] * float(next(r for r in load_saved(mm, "forecast").itertuples() if r.series == col and r.year == yr).forecast) for mm in MEMBERS)
            a, b = calibrated_bounds(g[g.step == k].log_err.values)
            fut.append({"model": NAME, "year": yr, "forecast": fc, "lower_80": fc * np.exp(a), "upper_80": fc * np.exp(b)})
        f = pd.DataFrame(fut)
        for d in (m, f):
            d.insert(0, "series", col)
        mets.append(m)
        futs.append(f)
    BT, M, F = bt.drop(columns="scale"), pd.concat(mets), pd.concat(futs).round(1)
    md = model_dir(NAME)
    for sub in ("metrics", "model", "plots"):
        (md / sub).mkdir(parents=True, exist_ok=True)
    M.to_csv(md / "metrics" / f"{NAME}_metrics.csv", index=False)
    created = datetime.datetime.now().isoformat(timespec="seconds")
    overall = M[METRIC_COLS].mean().round(4).to_dict()
    nl = chr(10)
    settings = ("ensemble: weighted average of" + nl + ", ".join(MEMBERS) + nl + "weights ~ 1 / MAPE on rows already known" + nl + "(per series and horizon; equal until 3 rows)")
    joblib.dump({"model": NAME, "created": created, "settings": settings, "inputs": None, "members": MEMBERS, "weights": final_w, "overall_metrics": overall,
                 "backtest": BT, "forecast": F}, md / "model" / f"{NAME}.joblib")
    (md / "model" / f"{NAME}.json").write_text(json.dumps({"model": NAME, "created": created, "members": MEMBERS, "weights_by_series_and_horizon": final_w,
                                                           "overall_metrics_mean_over_series_and_horizons": overall}, indent=2), encoding="utf-8")
    plot_model(NAME)
    plot_errors(NAME)
    _print_metrics(NAME, M)
    print("  weights of the final forecast (series | horizon):")
    print(pd.DataFrame(final_w).T.round(2).to_string())
    print(f"  saved in step_02_forecasting/{NAME}/ : metrics/, model/ and plots/")


if __name__ == "__main__":
    main()
