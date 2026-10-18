"""Random Forest: 200 shallow trees (depth 3), the lower-variance tree model, on the inputs of features.py (the series' own growth plus the outside groups
chosen in features.INPUT_GROUPS).
Run:  python step_02_forecasting/random_forest/random_forest.py
Everything of this model lives in this folder: this code, plots/, model/random_forest.joblib (+ .json: the fitted models with their metrics, backtest
and forecast) and metrics/random_forest_metrics.csv.
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
    return forecast_levels(train, h, origin, features(train), columns(), A.random_forest, art=art)


if __name__ == "__main__":
    nl = chr(10)
    run_model("random_forest", fit_forecast, "random forest: 200 trees, depth 3" + nl + "inputs: " + ", ".join(columns()), inputs=columns())
