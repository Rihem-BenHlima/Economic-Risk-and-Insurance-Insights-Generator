"""Shared evaluation code, so every model is compared on exactly the same terms.

Layout of step_02_forecasting/
    data/                  the preprocessed tables every model reads (modeling_table.csv holds the targets; see features.py for the inputs)
    features.py            the inputs of the models, built in one place; INPUT_GROUPS says which groups of outside data the models use
    <model>/               arima, prophet, gbm, random_forest, lstm: EVERYTHING of one model
        <model>.py             the code (defines fit_forecast and ends with run_model("<model>", fit_forecast, ...))
        metrics/<model>_metrics.csv    its metrics (the backtest and forecast tables are saved inside the model file)
        model/<model>.joblib / .json   the fitted final model of every series, saved together with its metrics, backtest and forecast
        plots/<model>_forecast.png     history, 1-year-ahead backtest, 2025-27 forecast with its band, settings, inputs, metrics
        plots/<model>_inputs.png       gbm / random_forest only: which inputs the model relied on
        plots/<model>_errors_*.png     errors over time, errors vs every outside variable, and the strongest link as a scatter
    results/               metrics.csv (all models, overall / per series / per horizon), champions.csv, champions_forecast.csv, ablation.csv
    plots/                 comparison.png, champion_<series>.png, and the plots of the data (data_plots.py)

fit_forecast(train, h, origin, art=None) -> np.ndarray of h forecasts, in the units of the target
  train  : pandas Series of the target indexed by year, only years < origin
  origin : first year to forecast (inputs are looked up with information known before `origin`)
  art    : if a list is given, the fitted model is appended to it so run_model can save it

Backtest: expanding window; for every origin year from FIRST_ORIGIN on, refit on the earlier years and forecast 1..3 years ahead.
Intervals: 80% bands calibrated on the model's own backtest errors (finite-sample 10th/90th order statistics of log(actual/forecast) per horizon,
widened to contain the forecast); coverage is scored leave-one-out, so an origin never calibrates its own interval.
Metrics: MAE, RMSE, CV(RMSE) = RMSE / mean(actual), R2 = 1 - SSE/SST, MAPE, MASE (scaled by the in-sample error of repeating the
last value), bias (forecast - actual) and calibrated 80% coverage.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
TARGETS = {"premiums_total": "Total net premiums", "premiums_life": "Life premiums", "premiums_auto": "Motor premiums",
           "premiums_health": "Health premiums", "claims_paid_total": "Total paid claims"}
LABELS = dict(TARGETS)
SHORT = {"premiums_total": "Total prem.", "premiums_life": "Life", "premiums_auto": "Motor", "premiums_health": "Health", "claims_paid_total": "Claims"}
FIRST_ORIGIN, HORIZON, LEVEL = 2012, 3, 0.80
METRIC_COLS = ["MAE", "RMSE", "CVRMSE_%", "R2", "MAPE_%", "MASE", "bias", "coverage_80_%"]
TREES = ("gbm", "random_forest")
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": 0.3, "axes.spines.top": False, "axes.spines.right": False})


def model_dir(name):
    return HERE / name


def model_names():
    return sorted(p.name for p in HERE.iterdir() if (p / "metrics").is_dir())


def load_saved(name, what):
    """The backtest or the forecast table of a model, read from its saved file model/<name>.joblib (what = "backtest" or "forecast")."""
    import joblib
    return joblib.load(model_dir(name) / "model" / f"{name}.joblib")[what]


def results_dir():
    d = HERE / "results"
    d.mkdir(exist_ok=True)
    return d


def plots_dir():
    d = HERE / "plots"
    d.mkdir(exist_ok=True)
    return d


def table():
    return pd.read_csv(DATA / "modeling_table.csv").set_index("year")


def backtest(y, name, fn):
    rows, last = [], int(y.index[-1])
    for origin in range(FIRST_ORIGIN, last + 1):
        train = y[y.index < origin]
        h = min(HORIZON, last - origin + 1)
        scale = np.abs(np.diff(train.values)).mean()      # scaling number for MASE (error of repeating the last value); not a candidate model
        fc = fn(train, h, origin)
        if fc is None:                       # the model cannot be fitted at this origin (too little data): skip it
            continue
        fc = np.asarray(fc, dtype=float)
        for k in range(h):
            rows.append({"origin": origin, "step": k + 1, "year": origin + k, "model": name,
                         "actual": float(y[origin + k]), "forecast": float(fc[k]), "scale": scale})
    bt = pd.DataFrame(rows)
    bt["error"] = bt.forecast - bt.actual
    bt["log_err"] = np.log(bt.actual / bt.forecast)
    return bt


def calibrated_bounds(log_errs, leave_out=None):
    """Bounds of the 80% band as log(actual / forecast): finite-sample order statistics of the model's own backtest errors (the floor / ceil of
    (n+1) * 10% and 90% rank, which widens the plain quantiles that are too narrow with 7-13 errors per horizon), and the band always contains
    its own forecast (lower <= 0 <= upper). Leave-one-out coverage of this rule is about 80% (results/ metrics, column coverage_80_%)."""
    import math
    e = np.sort(np.asarray(log_errs, dtype=float) if leave_out is None else np.delete(np.asarray(log_errs, dtype=float), leave_out))
    n, a = len(e), 1 - LEVEL
    lo = e[max(0, math.floor(a / 2 * (n + 1)) - 1)]
    hi = e[min(n - 1, math.ceil((1 - a / 2) * (n + 1)) - 1)]
    return min(lo, 0.0), max(hi, 0.0)


def metrics(bt):
    out = []
    for (model, step), g in bt.groupby(["model", "step"]):
        g = g.reset_index(drop=True)
        cover = []
        if len(g) >= 8:
            for i in range(len(g)):
                a, b = calibrated_bounds(g.log_err.values, i)
                cover.append(g.forecast[i] * np.exp(a) <= g.actual[i] <= g.forecast[i] * np.exp(b))
        rmse = np.sqrt((g.error ** 2).mean())
        sst = ((g.actual - g.actual.mean()) ** 2).sum()
        out.append({"model": model, "step": step, "n": len(g), "MAE": g.error.abs().mean(), "RMSE": rmse,
                    "CVRMSE_%": 100 * rmse / g.actual.mean(),                       # RMSE as a percentage of the mean actual value
                    "R2": 1 - (g.error ** 2).sum() / sst,                            # 1 - SSE/SST on the backtest forecasts (levels)
                    "MAPE_%": 100 * (g.error.abs() / g.actual).mean(), "MASE": (g.error.abs() / g.scale).mean(), "bias": g.error.mean(),
                    "coverage_80_%": 100 * np.mean(cover) if cover else np.nan})
    return pd.DataFrame(out).round({"MAE": 2, "RMSE": 2, "CVRMSE_%": 2, "R2": 4, "MAPE_%": 2, "MASE": 2, "bias": 2, "coverage_80_%": 2})


def future(y, name, fn, bt):
    """Forecast beyond the data with the model fitted on ALL the data; returns the forecast table and the fitted artifacts (for saving)."""
    origin, art = int(y.index[-1]) + 1, []
    fc = np.asarray(fn(y, HORIZON, origin, art=art), dtype=float)
    rows = []
    for k in range(HORIZON):
        a, b = calibrated_bounds(bt[bt.step == k + 1].log_err.values)
        rows.append({"model": name, "year": origin + k, "forecast": fc[k], "lower_80": fc[k] * np.exp(a), "upper_80": fc[k] * np.exp(b)})
    return pd.DataFrame(rows), art


def _panels(n=5):
    rows = -(-(n + 1) // 3)                      # n series plus one panel for the text box, 3 per row
    fig, ax = plt.subplots(rows, 3, figsize=(15, 3.5 * rows))
    ax = list(np.ravel(ax))
    for a in ax[n + 1:]:
        a.axis("off")
    return fig, ax


def plot_model(name):
    """The model's plots in <model>/plots/: <name>_forecast.png (one chart per series: history, 1-year-ahead backtest, 2025-27 forecast with its
    calibrated band; a box with the model's settings, its inputs and its metrics) and, for the tree models, <name>_inputs.png."""
    import joblib
    md, t = model_dir(name), table()
    (md / "plots").mkdir(exist_ok=True)
    saved = joblib.load(md / "model" / f"{name}.joblib")
    BT, F = saved["backtest"], saved["forecast"]
    M = pd.read_csv(md / "metrics" / f"{name}_metrics.csv")
    cols = list(TARGETS)
    fig, ax = _panels(len(cols))
    for a, col in zip(ax, cols):
        y, b, f = t[col], BT[(BT.series == col) & (BT.step == 1)], F[F.series == col]
        a.plot(y.index, y.values, "k-", lw=1, label="actual")
        a.plot(b.year, b.forecast, "o", color="tab:blue", ms=4, label="1-year-ahead (backtest)")
        a.plot([y.index[-1]] + list(f.year), [y.iloc[-1]] + list(f.forecast), "r--o", ms=4, label="forecast 2025-27")
        a.fill_between(f.year, f.lower_80, f.upper_80, color="red", alpha=0.15, label="80% band")
        a.set_title(f"{LABELS[col]} (M.TND): mean MAPE {M[M.series == col]['MAPE_%'].mean():.2f}%", fontsize=9)
    ax[0].legend(fontsize=7, loc="upper left")
    o = M.groupby("step")[["MAPE_%", "CVRMSE_%", "R2", "MASE"]].mean().round(3)
    nl = chr(10)
    box = saved["settings"] + nl + nl + "overall metrics:" + nl + nl.join(
        f"{k}-year ahead: MAPE {r['MAPE_%']:.2f}%  CV(RMSE) {r['CVRMSE_%']:.2f}%" + nl + f"               R2 {r['R2']:.3f}  MASE {r['MASE']:.2f}" for k, r in o.iterrows())
    bx = ax[len(cols)]
    bx.axis("off")
    bx.text(0.0, 0.98, box, va="top", ha="left", family="monospace", fontsize=7.5, wrap=True)
    fig.suptitle(name)
    fig.tight_layout()
    fig.savefig(md / "plots" / f"{name}_forecast.png")
    plt.close(fig)
    if name in TREES:
        inputs = saved["inputs"]
        imp = pd.DataFrame({LABELS[c]: np.mean([a["estimator"].feature_importances_ for a in b["artifacts"]], axis=0) for c, b in saved["series"].items()}, index=inputs)
        fig, ax = plt.subplots(figsize=(1.6 * imp.shape[1] + 3, 0.34 * len(inputs) + 2.2))
        im = ax.imshow(imp.values, cmap="Blues", vmin=0, vmax=max(0.5, imp.values.max()), aspect="auto")
        ax.set_xticks(range(imp.shape[1]), imp.columns, fontsize=8, rotation=20, ha="right")
        ax.set_yticks(range(len(inputs)), inputs, fontsize=8)
        ax.grid(False)
        for i in range(imp.shape[0]):
            for j in range(imp.shape[1]):
                ax.text(j, i, f"{imp.values[i, j]:.2f}", ha="center", va="center", fontsize=7, color="white" if imp.values[i, j] > 0.3 else "black")
        fig.colorbar(im, ax=ax, label="share of the model's splits")
        ax.set_title(f"{name}: which inputs the model relied on (columns sum to 1)", fontsize=9)
        fig.tight_layout()
        fig.savefig(md / "plots" / f"{name}_inputs.png")
        plt.close(fig)


def plot_errors(name):
    """Where the model's errors fall, in three files in <model>/plots/:
    <name>_errors_over_time.png  1-year-ahead error (%, + = forecast too low) of every series, by year;
    <name>_errors_vs_data.png    correlation of that error with every outside variable (all four groups) of the year before, i.e. known at forecast time:
                                 a strong cell means that variable could explain part of what the model misses (bold = distinguishable from zero);
    <name>_error_scatter.png     the strongest of those links as a scatter."""
    from features import GROUPS, outside
    md = model_dir(name)
    BT = load_saved(name, "backtest")
    E = BT[BT.step == 1].pivot(index="year", columns="series", values="log_err")[list(TARGETS)]
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    for c in TARGETS:
        ax.plot(E.index, 100 * E[c], "o-", ms=3, label=LABELS[c])
    ax.axhline(0, color="k", lw=0.6)
    ax.set_title(f"{name}: 1-year-ahead error (%), + = forecast too low", fontsize=9)
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(md / "plots" / f"{name}_errors_over_time.png")
    plt.close(fig)
    O = outside()
    names = [v for g in GROUPS.values() for v in g]
    R = pd.DataFrame(index=names, columns=E.columns, dtype=float)
    N = R.copy()
    for v in names:
        for c in E.columns:
            d = pd.concat([O[v].shift(1), E[c]], axis=1).dropna()
            R.loc[v, c], N.loc[v, c] = (d.corr().iloc[0, 1] if len(d) > 5 else np.nan), len(d)
    fig, ax = plt.subplots(figsize=(7, 0.26 * len(names) + 2))
    im = ax.imshow(R.values.astype(float), cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(E.shape[1]), [SHORT[c] for c in E.columns], fontsize=8, rotation=25, ha="right")
    ax.set_yticks(range(len(names)), names, fontsize=7)
    ax.grid(False)
    for i, v in enumerate(names):
        for j, c in enumerate(E.columns):
            r, n = R.loc[v, c], N.loc[v, c]
            weak = not (abs(r) >= 2 / np.sqrt(n))
            ax.text(j, i, f"{r:.2f}", ha="center", va="center", fontsize=6.5, color="0.35" if weak else "black", fontweight="normal" if weak else "bold")
    edge = 0
    for g in list(GROUPS)[:-1]:
        edge += len(GROUPS[g])
        ax.axhline(edge - 0.5, color="k", lw=0.8)
    fig.colorbar(im, ax=ax, label="correlation")
    ax.set_title(f"{name}: error vs each outside variable of the year before (groups: economy, labour, agriculture, climate)", fontsize=8)
    fig.tight_layout()
    fig.savefig(md / "plots" / f"{name}_errors_vs_data.png")
    plt.close(fig)
    v, c = R.abs().stack().idxmax()
    d = pd.concat([O[v].shift(1), E[c]], axis=1).dropna()
    fig, ax = plt.subplots(figsize=(6, 4.4))
    ax.scatter(d.iloc[:, 0], 100 * d.iloc[:, 1], s=22, color="tab:blue")
    b = np.polyfit(d.iloc[:, 0], 100 * d.iloc[:, 1], 1)
    xs = np.linspace(d.iloc[:, 0].min(), d.iloc[:, 0].max(), 20)
    ax.plot(xs, np.polyval(b, xs), "k--", lw=1)
    ax.axhline(0, color="k", lw=0.6)
    ax.set_xlabel(f"{v}, year before", fontsize=8)
    ax.set_ylabel(f"{name} error, {LABELS[c]} (%, + = too low)", fontsize=8)
    ax.set_title(f"strongest link: r = {R.loc[v, c]:.2f} (n = {len(d)})", fontsize=9)
    fig.tight_layout()
    fig.savefig(md / "plots" / f"{name}_error_scatter.png")
    plt.close(fig)


def _print_metrics(name, M):
    per = M.groupby("series")[METRIC_COLS].mean().reindex(list(TARGETS)).round(3)
    per.loc["OVERALL"] = M[METRIC_COLS].mean().round(3)
    n = M.groupby("step").n.first()
    print(f"{nl_}[{name}]  metrics, mean over the 1-3 year horizons  (backtest n per series at 1y/2y/3y = {'/'.join(str(int(n[k])) for k in sorted(n.index))})")
    print(per.to_string())
    bh = M.groupby("step")[METRIC_COLS].mean().round(3)
    bh.index = [f"{k}-year ahead" for k in bh.index]
    print("by horizon (mean over series):")
    print(bh.to_string())


nl_ = chr(10)


def run_model(name, fn, settings, inputs=None):
    """Backtest and forecast one model on every target. Everything lands in its own folder <name>/: metrics csv, the fitted final model of every series
    together with its metrics, backtest and forecast (model/<name>.joblib + .json) and its plots. Prints the full metrics.
    settings: text for the plot box (the model's settings and inputs); inputs: input names, saved for the importance plot of the tree models."""
    import json
    import datetime
    import joblib
    md = model_dir(name)
    for sub in ("metrics", "model", "plots"):
        (md / sub).mkdir(parents=True, exist_ok=True)
    t = table()
    bts, mets, futs, bundle = [], [], [], {}
    for col in TARGETS:
        y = t[col].astype(float)
        bt = backtest(y, name, fn)
        m = metrics(bt)
        f, art = future(y, name, fn, bt)
        m_rows = m.to_dict("records")
        for d in (bt, m, f):
            d.insert(0, "series", col)
        bts.append(bt.drop(columns="scale")); mets.append(m); futs.append(f)
        bundle[col] = {"last_level": float(y.iloc[-1]), "trained_years": [int(y.index[0]), int(y.index[-1])], "artifacts": art,
                       "metrics_by_horizon": m_rows, "forecast": f.round(2).drop(columns=["series", "model"]).to_dict("records")}
    BT, M, F = pd.concat(bts), pd.concat(mets), pd.concat(futs).round(1)
    M.to_csv(md / "metrics" / f"{name}_metrics.csv", index=False)
    created = datetime.datetime.now().isoformat(timespec="seconds")
    overall = M[METRIC_COLS].mean().round(4).to_dict()
    joblib.dump({"model": name, "created": created, "settings": settings, "inputs": inputs, "overall_metrics": overall, "series": bundle,
                 "backtest": BT, "forecast": F}, md / "model" / f"{name}.joblib")
    summary = {"model": name, "created": created, "settings": settings, "inputs": inputs, "overall_metrics_mean_over_series_and_horizons": overall,
               "series": {c: {k: v for k, v in b.items() if k != "artifacts"} | {"artifact_kinds": sorted({a["kind"] for a in b["artifacts"]})} for c, b in bundle.items()}}
    (md / "model" / f"{name}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    plot_model(name)
    plot_errors(name)
    _print_metrics(name, M)
    print(f"  saved in step_02_forecasting/{name}/ : metrics/, model/ and plots/")


def verify_saved():
    """Reload every saved model and check that it reproduces the saved forecasts without refitting."""
    import joblib
    import algorithms as A
    rows = []
    for name in model_names():
        p = model_dir(name) / "model" / f"{name}.joblib"
        if not p.exists():
            continue
        bundle = joblib.load(p)
        if "members" in bundle:             # the ensemble is rebuilt from its members' forecasts and its saved weights, nothing is fitted
            continue
        F = bundle["forecast"]
        diffs = []
        for col, b in bundle["series"].items():
            lv = A.predict_artifacts(b["artifacts"], b["last_level"], HORIZON)
            ref = F[F.series == col].sort_values("year").forecast.values
            diffs.append(float(np.max(np.abs(lv - ref))))
        rows.append({"model": name, "series_checked": len(diffs), "max_abs_diff_M.TND": round(max(diffs), 3), "reproduced": max(diffs) < 0.06})
    out = pd.DataFrame(rows)
    print(out.to_string(index=False))
    return out


def _backtests():
    return pd.concat([load_saved(n, "backtest") for n in model_names()])


def _common_rows():
    """Backtest rows of all models, restricted to the (series, origin, step) combinations that EVERY model produced, with the MASE scale rebuilt."""
    t = table()
    BT = _backtests()
    n_models = BT.model.nunique()
    key = BT.groupby(["series", "origin", "step"]).model.nunique()
    keep = key[key == n_models].index
    BT = BT.set_index(["series", "origin", "step"]).loc[keep].reset_index()
    BT["scale"] = [np.abs(np.diff(t[r.series][t.index < r.origin].values)).mean() for r in BT.itertuples()]
    BT["error"] = BT.forecast - BT.actual
    BT["log_err"] = np.log(BT.actual / BT.forecast)
    return BT, n_models


def plot_champions():
    """The result the dashboard will use: the champion's forecast of each series with its calibrated band, one file per series."""
    res, plots, t = results_dir(), plots_dir(), table()
    C = pd.read_csv(res / "champions_forecast.csv")
    avg = pd.read_csv(res / "champions.csv").set_index("series")["mean_MAPE_1to3y_%"]
    for col in TARGETS:
        fig, a = plt.subplots(figsize=(7, 4.2))
        y, f = t[col], C[C.series == col]
        a.plot(y.index, y.values, "k-o", ms=3, label="actual")
        a.plot([y.index[-1]] + list(f.year), [y.iloc[-1]] + list(f.forecast), "r--o", ms=4, label="champion forecast")
        a.fill_between(f.year, f.lower_80, f.upper_80, color="red", alpha=0.15, label="80% band")
        for _, r in f.iterrows():
            a.annotate(f"{r.forecast:,.0f}", (r.year, r.forecast), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=8)
        a.set_title(f"{LABELS[col]} (M.TND): champion {f.model.iloc[0]}, mean MAPE {avg[col]:.2f}%", fontsize=9)
        a.legend(fontsize=8, loc="upper left")
        fig.tight_layout()
        fig.savefig(plots / f"champion_{col}.png")
        plt.close(fig)


def compare():
    """Compare the models on the rows they all share, and pick the champion per series (lowest MAPE averaged over 1-3 years)."""
    res, plots = results_dir(), plots_dir()
    BT, n_models = _common_rows()
    M = pd.concat([metrics(BT[BT.series == col]).assign(series=col) for col in TARGETS])
    models = sorted(M.model.unique())
    first = int(BT.origin.min())
    print(f"{nl_}{n_models} models compared on the same backtest rows (origins {first}-{int(BT.origin.max())}; "
          f"{', '.join(f'{k}y: n={int(M[M.step == k].n.iloc[0])}' for k in (1, 2, 3))})")
    avg = M.groupby(["series", "model"])["MAPE_%"].mean().unstack().reindex(list(TARGETS))
    print(f"mean MAPE over the 1-3 year horizons (%), models: {models}")
    print(avg.round(2).to_string())
    champ = pd.DataFrame({"series": avg.index, "champion": avg.idxmin(axis=1).values, "mean_MAPE_1to3y_%": avg.min(axis=1).round(2).values})
    print(f"{nl_}champions:{nl_}" + champ.to_string(index=False))
    overall = M.groupby("model")[METRIC_COLS].mean().sort_values("MAPE_%").round(3)
    print(f"{nl_}overall metrics (mean over series and horizons, common rows):{nl_}" + overall.to_string())
    # ONE metrics file: overall rows, then per series (mean over the horizons), then per series and horizon
    rows = [overall.reset_index().assign(series="ALL", step="ALL")]
    rows.append(M.groupby(["series", "model"])[METRIC_COLS].mean().round(3).reset_index().assign(step="ALL"))
    rows.append(M.drop(columns="n").round(3).assign(step=M.step.astype(str)))
    pd.concat(rows)[["series", "step", "model"] + METRIC_COLS].to_csv(res / "metrics.csv", index=False)
    champ.to_csv(res / "champions.csv", index=False)
    F = pd.concat([load_saved(n, "forecast") for n in model_names()])
    pd.concat([F[(F.series == r.series) & (F.model == r.champion)] for r in champ.itertuples()]).to_csv(res / "champions_forecast.csv", index=False)
    # the data the dashboard and the chatbot read: every model's forecasts with bands, and every model's backtest (no model files needed)
    F.to_csv(res / "forecasts.csv", index=False)
    _backtests()[["series", "model", "origin", "step", "year", "actual", "forecast"]].round(2).to_csv(res / "backtest.csv", index=False)
    fig, ax = plt.subplots(figsize=(11, 4.6))
    avg.plot.bar(ax=ax, width=0.8)
    ax.set_xticklabels([LABELS[s] for s in avg.index], rotation=0, fontsize=8)
    ax.set_ylabel("mean MAPE over 1-3 year horizons (%)")
    ax.set_title(f"Model comparison on common backtest rows, origins {first}+ (lower is better)")
    fig.tight_layout(); fig.savefig(plots / "comparison.png"); plt.close(fig)
    plot_champions()
    print(f"{nl_}  saved results/ (metrics.csv, champions.csv, champions_forecast.csv) and plots/ (comparison, champion_<series>)")
    return champ
