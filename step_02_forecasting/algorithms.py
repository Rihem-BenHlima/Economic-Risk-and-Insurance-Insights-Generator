"""The five model algorithms. The inputs they are given come from features.py.

Growth models  fit_predict(X, g, x_last, art=None) -> predicted growth of one year:   gbm, random_forest, lstm
Level models   arima(train, h, art=None);  prophet_levels(train, h, origin, F, cols, art=None)  -> h levels

`art` (a list) is optional: when given, the fitted model is appended to it so it can be SAVED. `predict_artifacts` rebuilds the forecasts from
those saved artifacts, so a saved model can be reloaded and used without refitting.
"""
import logging
import warnings
import numpy as np
import pandas as pd
import torch
import torch.nn as nn

warnings.filterwarnings("ignore")
logging.getLogger("cmdstanpy").setLevel(logging.ERROR)
logging.getLogger("prophet").setLevel(logging.ERROR)
torch.set_num_threads(2)
MIN_PAIRS = 7


def gbm(X, g, x_last, art=None):
    """Gradient boosting with shallow trees (depth 2) and strong shrinkage: very small, because there are only 7-20 training years."""
    from sklearn.ensemble import GradientBoostingRegressor
    m = GradientBoostingRegressor(n_estimators=60, learning_rate=0.05, max_depth=2, min_samples_leaf=3, subsample=0.8, random_state=0).fit(X, g)
    if art is not None:
        art.append({"kind": "sklearn", "estimator": m, "x_last": np.asarray(x_last)})
    return float(m.predict(x_last.reshape(1, -1))[0])


def random_forest(X, g, x_last, art=None):
    """Random Forest: 200 shallow trees (depth 3), the lower-variance tree model."""
    from sklearn.ensemble import RandomForestRegressor
    m = RandomForestRegressor(n_estimators=200, max_depth=3, min_samples_leaf=3, random_state=0).fit(X, g)
    if art is not None:
        art.append({"kind": "sklearn", "estimator": m, "x_last": np.asarray(x_last)})
    return float(m.predict(x_last.reshape(1, -1))[0])


def arima(train, h, art=None):
    """ARIMA = ARMA(p,q) with a constant on the yearly log growth (best of four small orders by AIC), which is the same as ARIMA(p,1,q)
    with drift on the log level. It uses only the series' own history."""
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    g = np.diff(np.log(train.values))
    best = None
    for order in [(0, 0, 0), (1, 0, 0), (0, 0, 1), (1, 0, 1)]:
        try:
            m = SARIMAX(g, order=order, trend="c").fit(disp=False, maxiter=200)
            if best is None or m.aic < best.aic:
                best = m
        except Exception:
            pass
    if art is not None:
        art.append({"kind": "arima", "result": best})
    return float(train.iloc[-1]) * np.exp(np.cumsum(best.forecast(h)))


class LSTMNet(nn.Module):
    def __init__(self, p, hidden):
        super().__init__()
        self.rnn = nn.LSTM(p, hidden, batch_first=True)
        self.out = nn.Linear(hidden, 1)

    def forward(self, x):
        o, _ = self.rnn(x)
        return self.out(o[:, -1]).squeeze(-1)


def lstm(X, g, x_last, seeds=5, epochs=200, hidden=8, art=None):
    """Small LSTM: reads the inputs of the last 2 years (X has shape n x 2 x features) and predicts the next growth.
    Trained with weight decay and averaged over 5 random seeds, because there are only 7-20 training examples."""
    p = X.shape[-1]
    mu, sd = X.reshape(-1, p).mean(0), X.reshape(-1, p).std(0) + 1e-9
    Xt = torch.tensor((X - mu) / sd, dtype=torch.float32)
    xl = torch.tensor(((x_last - mu) / sd)[None], dtype=torch.float32)
    ym, ys = g.mean(), g.std() or 1.0
    Yt = torch.tensor((g - ym) / ys, dtype=torch.float32)
    preds, states = [], []
    for seed in range(seeds):
        torch.manual_seed(seed)
        net = LSTMNet(p, hidden)
        opt = torch.optim.Adam(net.parameters(), lr=0.01, weight_decay=1e-3)
        for _ in range(epochs):
            opt.zero_grad()
            nn.functional.mse_loss(net(Xt), Yt).backward()
            opt.step()
        with torch.no_grad():
            preds.append(net(xl).item() * ys + ym)
        states.append({k: v.numpy().copy() for k, v in net.state_dict().items()})
    if art is not None:
        art.append({"kind": "lstm", "states": states, "mu": mu, "sd": sd, "ym": float(ym), "ys": float(ys), "p": p, "hidden": hidden, "x_last": np.asarray(x_last)})
    return float(np.mean(preds))


def prophet_levels(train, h, origin, F, cols, art=None):
    """Prophet on log levels: piecewise-linear trend, no seasonality (yearly data). With regressors (two core variables) each
    horizon k uses regressors lagged k years and the last known year's values; without regressors it is a pure trend model."""
    from prophet import Prophet
    from prophet.serialize import model_to_json

    def make(regs):
        m = Prophet(growth="linear", yearly_seasonality=False, weekly_seasonality=False, daily_seasonality=False, changepoint_prior_scale=0.05)
        for c in regs:
            m.add_regressor(c)
        return m

    if not cols:
        df = pd.DataFrame({"ds": pd.to_datetime([f"{y}-12-31" for y in train.index]), "y": np.log(train.values)})
        m = make([]).fit(df)
        last = int(train.index[-1])
        fut = pd.DataFrame({"ds": pd.to_datetime([f"{last + k}-12-31" for k in range(1, h + 1)])})
        if art is not None:
            art.append({"kind": "prophet", "json": model_to_json(m), "regressors": [], "last_year": last})
        return np.exp(m.predict(fut)["yhat"].values)
    Fc = F[cols]
    out = []
    for k in range(1, h + 1):
        years = [t for t in train.index if (t - k) in Fc.index and not Fc.loc[t - k].isna().any()]
        if len(years) < MIN_PAIRS + 1 or origin - 1 not in Fc.index or Fc.loc[origin - 1].isna().any():
            return None
        df = pd.DataFrame({"ds": pd.to_datetime([f"{t}-12-31" for t in years]), "y": np.log(train.loc[years].values)})
        for c in cols:
            df[c] = Fc.loc[[t - k for t in years], c].values
        m = make(cols).fit(df)
        fut = pd.DataFrame({"ds": [pd.Timestamp(f"{origin + k - 1}-12-31")]})
        for c in cols:
            fut[c] = Fc.loc[origin - 1, c]
        if art is not None:
            art.append({"kind": "prophet", "k": k, "json": model_to_json(m), "regressors": list(cols), "year": origin + k - 1,
                        "reg_values": {c: float(Fc.loc[origin - 1, c]) for c in cols}})
        out.append(float(np.exp(m.predict(fut)["yhat"].iloc[0])))
    return np.array(out)


def predict_artifacts(arts, last_level, h):
    """Rebuild the h forecasts of a saved model from its artifacts alone (no refitting)."""
    kind = arts[0]["kind"]
    if kind == "sklearn":
        growth = [float(a["estimator"].predict(a["x_last"].reshape(1, -1))[0]) for a in sorted(arts, key=lambda a: a["k"])]
        return last_level * np.exp(np.cumsum(growth))
    if kind == "lstm":
        growth = []
        for a in sorted(arts, key=lambda a: a["k"]):
            xl = torch.tensor(((a["x_last"] - a["mu"]) / a["sd"])[None], dtype=torch.float32)
            vals = []
            for st in a["states"]:
                net = LSTMNet(a["p"], a["hidden"])
                net.load_state_dict({k: torch.tensor(v) for k, v in st.items()})
                with torch.no_grad():
                    vals.append(net(xl).item() * a["ys"] + a["ym"])
            growth.append(float(np.mean(vals)))
        return last_level * np.exp(np.cumsum(growth))
    if kind == "arima":
        return last_level * np.exp(np.cumsum(arts[0]["result"].forecast(h)))
    if kind == "prophet":
        from prophet.serialize import model_from_json
        if not arts[0]["regressors"]:
            m = model_from_json(arts[0]["json"])
            last = arts[0]["last_year"]
            fut = pd.DataFrame({"ds": pd.to_datetime([f"{last + k}-12-31" for k in range(1, h + 1)])})
            return np.exp(m.predict(fut)["yhat"].values)
        out = []
        for a in sorted(arts, key=lambda a: a["k"]):
            m = model_from_json(a["json"])
            fut = pd.DataFrame({"ds": [pd.Timestamp(f"{a['year']}-12-31")], **{c: [v] for c, v in a["reg_values"].items()}})
            out.append(float(np.exp(m.predict(fut)["yhat"].iloc[0])))
        return np.array(out)
    raise ValueError(kind)
