"""Direct multi-horizon set-up shared by every model (real-time honest: nothing from the future is ever used).

To forecast the growth of year t = origin + k - 1 (k = 1, 2, 3 years ahead), a model is trained on pairs
    (growth in year t',  inputs of the `window` years ending at t' - k)        for every past year t' < origin
and applied to the features of the `window` years ending at origin - 1 (the last known year).
Levels are rebuilt as  last known level x exp(cumulative predicted growth).

F is a DataFrame of the inputs indexed by year; features.features(train) builds it (the series' own past growth plus the outside variables).
"""
import numpy as np

MIN_PAIRS = 7          # a model needs at least this many training pairs, otherwise it declines the origin (returns None)


def pairs(train, k, origin, F, cols, window=1):
    F = F[cols]
    g = np.log(train).diff().dropna()                                       # growth of year t (index = t), t < origin
    years, X = [], []
    for t in g.index:
        ys = [t - k - w for w in range(window - 1, -1, -1)]                   # oldest ... newest = t-k-window+1 ... t-k
        if all(y in F.index for y in ys) and not F.loc[ys].isna().any().any():
            years.append(t)
            X.append(F.loc[ys].values)
    last = [origin - 1 - w for w in range(window - 1, -1, -1)]
    if len(years) < MIN_PAIRS or not all(y in F.index for y in last) or F.loc[last].isna().any().any():
        return None
    X, x_last = np.stack(X), F.loc[last].values
    if window == 1:
        X, x_last = X[:, 0, :], x_last[0]
    return X, g.loc[years].values, x_last


def forecast_levels(train, h, origin, F, cols, fit_predict, window=1, art=None):
    """fit_predict(X, g, x_last, art=None) -> predicted growth of one year. Returns h levels, or None if there is too little data.
    If `art` is a list, the fitted model of each horizon is appended to it (tagged with k) so the model can be saved."""
    growth = []
    for k in range(1, h + 1):
        p = pairs(train, k, origin, F, cols, window)
        if p is None:
            return None
        a = [] if art is not None else None
        growth.append(float(fit_predict(*p, art=a)))
        if art is not None and a:
            art.append({**a[0], "k": k})
    return float(train.iloc[-1]) * np.exp(np.cumsum(growth))
