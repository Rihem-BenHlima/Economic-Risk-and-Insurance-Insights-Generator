"""Gradient boosting: 60 shallow trees (depth 2) with strong shrinkage on the inputs of features.py (the series' own growth plus the outside groups chosen
in features.INPUT_GROUPS). Very small, because there are only 7-20 training years; it can capture threshold / regime effects that linear models miss.
Run:  python step_02_forecasting/gbm/gbm.py
Everything of this model lives in this folder: this code, plots/, model/gbm.joblib (+ .json: the fitted models with their metrics, backtest and
forecast) and metrics/gbm_metrics.csv.
"""
import sys
import warnings
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))      # step_02_forecasting: common, features, algorithms, lagged
from common import run_model
from lagged import forecast_levels
import algorithms as A
from features import columns, features

warnings.filterwarnings("ignore")


def fit_forecast(train, h, origin, art=None):
    return forecast_levels(train, h, origin, features(train), columns(), A.gbm, art=art)


if __name__ == "__main__":
    nl = chr(10)
    run_model("gbm", fit_forecast, "gradient boosting: 60 trees, depth 2" + nl + "inputs: " + ", ".join(columns()), inputs=columns())
