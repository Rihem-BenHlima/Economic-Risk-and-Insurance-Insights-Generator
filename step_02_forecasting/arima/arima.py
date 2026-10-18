"""ARIMA: ARMA(p,q) with a constant on the series' yearly log growth (best of four small orders by AIC), which is the same as ARIMA(p,1,q)
with drift on the log level. It uses only each series' own history and no outside data: the baseline every other model has to beat.
Run:  python step_02_forecasting/arima/arima.py
Everything of this model lives in this folder: this code, plots/, model/arima.joblib (+ .json: the fitted models with their metrics, backtest and
forecast) and metrics/arima_metrics.csv.
"""
import sys
import warnings
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))      # step_02_forecasting: common, features, algorithms, lagged
from common import run_model
import algorithms as A

warnings.filterwarnings("ignore")


def fit_forecast(train, h, origin, art=None):
    return A.arima(train, h, art=art)


if __name__ == "__main__":
    nl = chr(10)
    run_model("arima", fit_forecast, "ARMA on yearly log growth + constant" + nl + "(= ARIMA(p,1,q) with drift), (p,q) chosen by AIC" + nl + "inputs: the series' own history only")
