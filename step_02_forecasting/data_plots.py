"""Plots of the data: does each group of outside data move before the insurance series?
For every group (economy, labour, agriculture, climate) and every lag k (1, 2, 3 years), a heatmap of the correlation between a variable of the group in
year t-k and the growth of each insurance series in year t (the same timing the models use). Cells with |r| below ~2/sqrt(n) cannot be told apart
from zero and are shown grey. One file each, in plots/lead_lag/.
Run:  python step_02_forecasting/data_plots.py
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import SHORT, TARGETS, plots_dir, table
from features import GROUPS, outside


def heatmap(F, G, k, group, path):
    R = pd.DataFrame(index=F.columns, columns=G.columns, dtype=float)
    N = R.copy()
    for f in F.columns:
        for c in G.columns:
            d = pd.concat([F[f].shift(k), G[c]], axis=1).dropna()
            R.loc[f, c], N.loc[f, c] = (d.corr().iloc[0, 1] if len(d) > 5 else np.nan), len(d)
    fig, ax = plt.subplots(figsize=(7, 0.45 * len(F.columns) + 2.6))
    im = ax.imshow(R.values.astype(float), cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(G.shape[1]), [SHORT[c] for c in G.columns], fontsize=8, rotation=25, ha="right")
    ax.set_yticks(range(len(F.columns)), F.columns, fontsize=9)
    ax.grid(False)
    for i, f in enumerate(F.columns):
        for j, c in enumerate(G.columns):
            r, n = R.loc[f, c], N.loc[f, c]
            weak = not (abs(r) >= 2 / np.sqrt(n))
            ax.text(j, i, f"{r:.2f}", ha="center", va="center", fontsize=8, color="0.35" if weak else "black", fontweight="normal" if weak else "bold")
    fig.colorbar(im, ax=ax, label="correlation")
    ax.set_title(f"{group}: variable {k} year{'s' if k > 1 else ''} earlier vs insurance growth (bold = distinguishable from zero)", fontsize=9)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main():
    out = plots_dir() / "lead_lag"
    out.mkdir(exist_ok=True)
    t, E = table(), outside()
    G = pd.DataFrame({c: np.log(t[c]).diff() for c in TARGETS})
    for group, cols in GROUPS.items():
        for k in (1, 2, 3):
            heatmap(E[cols], G, k, group, out / f"{group}_{k}y.png")
    print("  saved plots/lead_lag/: 4 groups x 3 lags")


if __name__ == "__main__":
    main()
