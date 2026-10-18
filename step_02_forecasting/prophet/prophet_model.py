"""Prophet: piecewise-linear trend on log values, no seasonality (yearly data). Regressors are the two core variables of features.PROPHET_GROUP, lagged k years
for horizon k; with PROPHET_GROUP = None (the choice made by results/ablation.csv) it is a pure trend model. The file is named prophet_model.py so
it does not shadow the prophet package.
Run:  python step_02_forecasting/prophet/prophet_model.py
Everything of this model lives in this folder: this code, plots/, model/prophet.joblib (+ .json: the fitted models with their metrics, backtest and
forecast) and metrics/prophet_metrics.csv.
"""
import sys
import warnings
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))      # step_02_forecasting: common, features, algorithms, lagged
from common import run_model
import algorithms as A
from features import CORE, PROPHET_GROUP, features

warnings.filterwarnings("ignore")
REGRESSORS = CORE[PROPHET_GROUP] if PROPHET_GROUP else []


def fit_forecast(train, h, origin, art=None):
    F = features(train, [PROPHET_GROUP]) if PROPHET_GROUP else None
    return A.prophet_levels(train, h, origin, F, REGRESSORS, art=art)


if __name__ == "__main__":
    nl = chr(10)
    run_model("prophet", fit_forecast, "Prophet: linear trend on log levels" + nl + "inputs: " + (", ".join(REGRESSORS) if REGRESSORS else "none (pure trend)"))
