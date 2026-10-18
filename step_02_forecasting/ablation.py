"""Which outside data helps which insurance series? Scores the tree models and Prophet with different inputs, on IDENTICAL backtest rows:
    trees (gbm, random_forest):  own growth only | + economy | + labour | + agriculture | + climate | + all four groups
    prophet:                     pure trend | + the two core variables of each group
Writes results/ablation.csv (every model x input set x series) and prints the overall and per-series tables.
The input choice of the final models (INPUT_GROUPS, PROPHET_GROUP in features.py) is read from this table.
Run:  python step_02_forecasting/ablation.py
"""
import sys
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
warnings.filterwarnings("ignore")
import algorithms as A
from common import TARGETS, backtest, results_dir, table
from features import CORE, GROUPS, columns, features
from lagged import forecast_levels

TREE_SETS = {"own only": [], "+ economy": ["economy"], "+ labour": ["labour"], "+ agriculture": ["agriculture"], "+ climate": ["climate"], "+ all four": list(GROUPS)}
PROPHET_SETS = {"trend only": None, **{f"+ {g} core": g for g in GROUPS}}


def tree_fn(algo, groups):
    return lambda train, h, origin, art=None: forecast_levels(train, h, origin, features(train, groups), columns(groups), algo, art=art)


def prophet_fn(group):
    if group is None:
        return lambda train, h, origin, art=None: A.prophet_levels(train, h, origin, None, [], art=art)
    return lambda train, h, origin, art=None: A.prophet_levels(train, h, origin, features(train, [group]), CORE[group], art=art)


def main():
    t = table()
    runs = {("gbm", k): tree_fn(A.gbm, v) for k, v in TREE_SETS.items()}
    runs |= {("random_forest", k): tree_fn(A.random_forest, v) for k, v in TREE_SETS.items()}
    runs |= {("prophet", k): prophet_fn(v) for k, v in PROPHET_SETS.items()}
    parts = []
    for (model, inputs), fn in runs.items():
        for col in TARGETS:
            bt = backtest(t[col].astype(float), f"{model}|{inputs}", fn)
            parts.append(bt.assign(model_name=model, inputs=inputs, series=col))
        print(f"  done {model} / {inputs}", flush=True)
    BT = pd.concat(parts)
    rows = []
    for model, g in BT.groupby("model_name"):
        n_sets = g.inputs.nunique()
        keys = g.groupby(["series", "origin", "step"]).inputs.nunique()
        g = g.set_index(["series", "origin", "step"]).loc[keys[keys == n_sets].index].reset_index()     # identical rows for every input set of this model
        g["ape"] = 100 * (g.forecast - g.actual).abs() / g.actual
        r = g.groupby(["inputs", "series"]).ape.mean().reset_index().assign(model=model)
        r["rows"] = len(g) // (n_sets * len(TARGETS))
        rows.append(r)
    out = pd.concat(rows)[["model", "inputs", "series", "ape", "rows"]].rename(columns={"ape": "MAPE_%"}).round(2)
    out.to_csv(results_dir() / "ablation.csv", index=False)
    for model, g in out.groupby("model"):
        piv = g.pivot(index="inputs", columns="series", values="MAPE_%")[list(TARGETS)]
        piv["MEAN"] = piv.mean(axis=1)
        print(f"{chr(10)}{model}: MAPE % by input set (identical rows, {int(g.rows.iloc[0])} per series per horizon-origin), best first")
        print(piv.sort_values("MEAN").round(2).to_string())


if __name__ == "__main__":
    main()
