"""Data of the dashboard: the preprocessed tables of step 1 (data/processed) and the results of step 2 (step_02_forecasting/results).
Everything is read from CSV files, so the dashboard needs no model file and no internet connection."""
from functools import lru_cache
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
RESULTS = ROOT / "step_02_forecasting" / "results"

TARGETS = {"premiums_total": "Total premiums", "premiums_life": "Life premiums", "premiums_auto": "Motor premiums",
           "premiums_health": "Health premiums", "claims_paid_total": "Total paid claims"}
MODEL_NAMES = {"ensemble": "Ensemble (final)", "random_forest": "Random Forest", "gbm": "Gradient boosting", "lstm": "LSTM", "arima": "ARIMA", "prophet": "Prophet"}


@lru_cache(maxsize=None)
def proc(name):
    return pd.read_csv(PROC / f"{name}.csv")


@lru_cache(maxsize=None)
def table():
    """modeling_table.csv: insurance and the outside variables by year."""
    return proc("modeling_table").set_index("year")


@lru_cache(maxsize=None)
def result(name):
    return pd.read_csv(RESULTS / f"{name}.csv")


def last_year():
    return int(table().index.max())


def month_index(df, col="month"):
    df = df.copy()
    df[col] = pd.to_datetime(df[col])
    return df
