"""Local tools: read-only lookups in the preprocessed tables (step 1) and the forecasting results (step 2). No network, no file paths from the user:
tables and columns are checked against a fixed allow-list."""
from functools import lru_cache
import pandas as pd
from config import DATA, RESULTS

SERIES = {"premiums_total": "Total premiums", "premiums_life": "Life premiums", "premiums_auto": "Motor premiums", "premiums_health": "Health premiums",
          "claims_paid_total": "Total paid claims"}
MODELS = {"ensemble": "Ensemble (final forecast)", "random_forest": "Random Forest", "gbm": "Gradient boosting", "lstm": "LSTM", "arima": "ARIMA", "prophet": "Prophet"}
TABLES = {   # name -> (file, what it holds)
    "modeling_table": ("modeling_table.csv", "insurance (premiums and claims by branch, M.TND) with the economy, labour, agriculture and climate columns, by year"),
    "insurance_annual": ("insurance_annual.csv", "insurance premiums and claims by branch, by year, M.TND"),
    "economy_annual": ("economy_annual.csv", "GDP, growth, inflation, exchange rate, credit, trade, money, by year"),
    "labour_annual": ("labour_annual.csv", "employment and unemployment, by year"),
    "agriculture_annual": ("agriculture_annual.csv", "production indices, agriculture's share of GDP and employment, by year"),
    "climate_annual": ("climate_annual.csv", "rainfall, heat days, heavy-rain days, dry spell, temperature for Tunis, by year"),
}
MAX_ROWS = 40


@lru_cache(maxsize=None)
def _csv(folder, name):
    return pd.read_csv((DATA if folder == "data" else RESULTS) / name)


def _clean(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    return round(float(v), 3) if isinstance(v, (int, float)) and not isinstance(v, bool) else v


def _check_series(series):
    if series not in SERIES:
        raise ValueError(f"unknown series '{series}'. Choose one of: {', '.join(SERIES)}")


def get_forecast(series, year=None, model="ensemble"):
    """Forecast of one series with its 80% range, and the last actual value."""
    _check_series(series)
    if model not in MODELS:
        raise ValueError(f"unknown model '{model}'. Choose one of: {', '.join(MODELS)}")
    f = _csv("results", "forecasts.csv")
    f = f[(f.series == series) & (f.model == model)].sort_values("year")
    if year is not None:
        year = int(year)
        f = f[f.year == year]
        if f.empty:
            raise ValueError(f"no forecast for {year}; forecasts cover {int(_csv('results', 'forecasts.csv').year.min())} to {int(_csv('results', 'forecasts.csv').year.max())}")
    t = _csv("data", "modeling_table.csv")
    last = t.dropna(subset=[series]).iloc[-1]
    return {"kind": "FORECAST", "series": SERIES[series], "model": MODELS[model], "unit": "M.TND",
            "forecast": [{"year": int(r.year), "value": _clean(r.forecast), "low_80": _clean(r.lower_80), "high_80": _clean(r.upper_80)} for r in f.itertuples()],
            "last_actual": {"year": int(last.year), "value": _clean(last[series])},
            "note": "model estimate with an 80% range from past errors, not a fact",
            "source": "step_02_forecasting/results/forecasts.csv"}


def get_accuracy(series=None):
    """How accurate each model was on past years (average error MAPE %, lower is better), for one series or overall."""
    m = _csv("results", "metrics.csv")
    if series:
        _check_series(series)
        rows = m[(m.series == series) & (m.step == "ALL")]
        scope = SERIES[series]
    else:
        rows = m[(m.series == "ALL") & (m.step == "ALL")]
        scope = "all five series"
    rows = rows.sort_values("MAPE_%")
    return {"kind": "ACCURACY", "scope": scope, "unit": "MAPE %: average miss as a percentage of the true value; MASE below 1 beats repeating last year",
            "models": [{"model": MODELS.get(r["model"], r["model"]), "mape_pct": _clean(r["MAPE_%"]), "r2": _clean(r["R2"]), "mase": _clean(r["MASE"])} for r in rows.to_dict("records")],
            "tested": "backtest from 2012, refitting on past years only, 1 to 3 years ahead",
            "source": "step_02_forecasting/results/metrics.csv"}


def get_history(series, start_year=None, end_year=None):
    """Actual (historical) values of one series."""
    _check_series(series)
    t = _csv("data", "modeling_table.csv").dropna(subset=[series])
    if start_year is not None:
        t = t[t.year >= int(start_year)]
    if end_year is not None:
        t = t[t.year <= int(end_year)]
    t = t.tail(MAX_ROWS)
    return {"kind": "HISTORY", "series": SERIES[series], "unit": "M.TND", "values": [{"year": int(r.year), "value": _clean(getattr(r, series))} for r in t.itertuples()],
            "source": "data/processed/modeling_table.csv"}


def list_data():
    """The tables and columns that query_data can read."""
    out = {}
    for name, (file, what) in TABLES.items():
        cols = [c for c in _csv("data", file).columns if c != "year"]
        out[name] = {"holds": what, "columns": cols}
    return {"kind": "CATALOGUE", "tables": out, "source": "data/processed"}


def query_data(table, column, year=None):
    """History of one column of one allowed table (all years, or one year)."""
    if table not in TABLES:
        raise ValueError(f"unknown table '{table}'. Choose one of: {', '.join(TABLES)}")
    df = _csv("data", TABLES[table][0])
    if column not in df.columns or column == "year":
        raise ValueError(f"unknown column '{column}' in {table}. Call list_data to see the columns")
    d = df[["year", column]].dropna()
    if year is not None:
        d = d[d.year == int(year)]
        if d.empty:
            raise ValueError(f"no value for {year}")
    d = d.tail(MAX_ROWS)
    return {"kind": "HISTORY", "table": table, "column": column, "values": [{"year": int(r.year), "value": _clean(getattr(r, column))} for r in d.itertuples()],
            "source": f"data/processed/{TABLES[table][0]}"}
