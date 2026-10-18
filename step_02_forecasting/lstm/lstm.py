"""LSTM: a small recurrent network (8 hidden units) that reads the inputs of features.py for the last 2 years and predicts the next growth rate;
trained with weight decay and averaged over 5 random seeds, because there are only 7-20 training examples.
Run:  python step_02_forecasting/lstm/lstm.py
Everything of this model lives in this folder: this code, plots/, model/lstm.joblib (+ .json: the fitted models with their metrics, backtest and
forecast) and metrics/lstm_metrics.csv.
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
    return forecast_levels(train, h, origin, features(train), columns(), A.lstm, window=2, art=art)


if __name__ == "__main__":
    nl = chr(10)
    run_model("lstm", fit_forecast, "LSTM: 8 hidden units, window of 2 years, mean of 5 seeds" + nl + "inputs: " + ", ".join(columns()))
