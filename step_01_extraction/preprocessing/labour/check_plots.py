"""Check plots for the labour domain: was the data treated correctly?

Run (after process.py):  python step_01_extraction/preprocessing/labour/check_plots.py
Writes PNGs to the plots/ folder next to this file.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import DATA, OUT

PLOTS = Path(__file__).parent / "plots"
PLOTS.mkdir(exist_ok=True)
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": 0.3, "axes.spines.top": False, "axes.spines.right": False})
pq = lambda s: pd.PeriodIndex(s, freq="Q").to_timestamp()

ins = pd.read_csv(DATA / "INS" / "labour_quarterly.csv")
raw_q = ins.pivot(index="period", columns=["indicator", "sex"], values="value")
pro_q = pd.read_csv(OUT / "labour_quarterly.csv").set_index("period")
raw_a = pd.read_csv(DATA / "BCT" / "labour_annual_2011_2025.csv").pivot(index="year", columns="indicator", values="value")
pro_a = pd.read_csv(OUT / "labour_annual.csv").set_index("year")


def save(fig, name):
    fig.tight_layout()
    fig.savefig(PLOTS / name)
    plt.close(fig)
    print("  saved", (PLOTS / name).relative_to(Path(__file__).parents[3]))


def p1_employed():
    k = (pro_a.employed_thousand / pro_a.employed_wb_derived_thousand)[pro_a.employed_source == "BCT"].loc[2011:2023].median()
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.4))
    ax[0].plot(pro_a.index, pro_a.employed_wb_derived_thousand, "--", color="gray", label="World Bank-derived (labour force x employment rate)")
    ax[0].plot(pro_a.index, pro_a.employed_wb_derived_thousand * k, ":", color="green", label=f"derived x {k:.3f} (BCT scale)")
    ax[0].plot(raw_a.index, raw_a.employed, "o", color="black", label="BCT raw")
    col = pro_a.employed_source.map({"BCT": "crimson", "estimated from World Bank": "blue", "INS 2025 quarterly mean": "orange"}).fillna("gray")
    ax[0].scatter(pro_a.index, pro_a.employed_thousand, c=col, marker="x", s=60, zorder=5, label="processed (red = BCT, blue = estimated, orange = INS 2025 mean)")
    ax[0].plot(pro_a.index, pro_a.employed_thousand, "-", color="crimson", lw=1)
    ax[0].set_title("Employed persons (thousand)"); ax[0].legend(fontsize=6.5, loc="lower right")
    ratio = (raw_a.employed / (pro_a.employed_wb_derived_thousand)).dropna()
    ax[1].bar(ratio.index, ratio.values, color=np.where(ratio.index == 2024, "crimson", "steelblue"))
    ax[1].axhline(k, color="k", ls="--", lw=0.8); ax[1].set_ylim(0.9, 1.1)
    ax[1].set_title(f"BCT / World Bank-derived: stable around {k:.2f} (std 0.02) except 2024 = {ratio.loc[2024]:.2f} (red, replaced)", fontsize=9)
    save(fig, "01_employed_annual.png")


def p2_unemployment():
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.plot(pro_a.index, pro_a.unemployment_rate_wb, "s--", ms=4, color="gray", label="World Bank")
    ax.plot(raw_a.index, raw_a.unemployment_rate, "o", color="black", label="BCT raw")
    ax.plot(pro_a.index, pro_a.unemployment_rate, "-", color="crimson", lw=1.8, label="processed (World Bank before 2011, BCT after; 2025 = mean of INS quarters)")
    ax.set_title("Unemployment rate (%)"); ax.legend(fontsize=8)
    save(fig, "02_unemployment_annual.png")


def p3_levels():
    fig, ax = plt.subplots(2, 3, figsize=(14, 6), sharex=True)
    for j, sex in enumerate(("female", "male", "total")):
        for i, ind in enumerate(("active_population", "employed")):
            a = ax[i, j]
            r = raw_q[(ind, sex)].dropna()
            a.plot(pq(r.index), r.values, "o", color="black", ms=5, label="raw")
            a.plot(pq(pro_q.index), pro_q[f"{ind}_{sex}"], "-", color="crimson", label="processed")
            fl = pd.PeriodIndex(["2024Q4"], freq="Q").to_timestamp()
            a.axvspan(fl[0] - pd.Timedelta(days=30), fl[0] + pd.Timedelta(days=60), color="orange", alpha=0.2)
            a.set_title(f"{ind} - {sex}", fontsize=9)
            if i == 0 and j == 0: a.legend(fontsize=7)
    fig.suptitle("INS quarterly levels (thousand): the 2024Q4 values flagged as a break (orange band) are replaced by interpolation")
    save(fig, "03_quarterly_levels_break_treated.png")


def p4_rates():
    """Only the treated rate: the graduates' unemployment rate (2024Q4 is a flagged break). The total/sex rates were not changed."""
    fig, ax = plt.subplots(figsize=(8, 4))
    for sex, c in (("total", "k"), ("female", "tab:red"), ("male", "tab:blue")):
        g = raw_q[("higher_ed_graduates_unemployment_rate", sex)].dropna()
        ax.plot(pq(g.index), g.values, "o", color=c, ms=5)
        ax.plot(pq(pro_q.index), pro_q[f"higher_ed_graduates_unemployment_rate_{sex}"], "-", color=c, label=sex)
    ax.set_title("Higher-education graduates' unemployment rate (%): raw points, processed lines" + chr(10) + "the 2024Q4 dip is a flagged break and is interpolated", fontsize=9)
    ax.legend(fontsize=8)
    save(fig, "04_graduate_unemployment_rate.png")


def main():
    print("[labour plots]")
    for f in (p1_employed, p2_unemployment, p3_levels, p4_rates):
        f()


if __name__ == "__main__":
    main()
