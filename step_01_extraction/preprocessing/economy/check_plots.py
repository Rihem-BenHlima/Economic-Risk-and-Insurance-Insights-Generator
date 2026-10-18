"""Check plots for the economy domain: was the data treated correctly?

Each plot compares the RAW source with the PROCESSED series and, where possible, with an independent source.
Run (after process.py):  python step_01_extraction/preprocessing/economy/check_plots.py
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
pm = lambda s: pd.PeriodIndex(s, freq="M").to_timestamp()
pq = lambda s: pd.PeriodIndex(s, freq="Q").to_timestamp()


def save(fig, name):
    fig.tight_layout()
    fig.savefig(PLOTS / name)
    plt.close(fig)
    print("  saved", (PLOTS / name).relative_to(Path(__file__).parents[3]))


def p1_cpi():
    raw = pd.read_csv(DATA / "BCT" / "cpi_all_items_monthly_2010_2026.csv")
    pro = pd.read_csv(OUT / "economy_cpi_monthly.csv")
    ins = pd.read_csv(DATA / "INS" / "cpi_annual.csv")
    ins = ins[ins.category == "All items"].set_index("year").cpi_index_2015_100
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.4))
    ax[0].plot(pm(raw.month), raw.cpi_index_2015_100, "o-", ms=3, color="gray", label="BCT raw (NaN = gap)")
    ax[0].plot(pm(pro.month), pro.cpi_index_2015_100, "-", color="crimson", lw=1.5, label="processed")
    ax[0].plot(pd.to_datetime(ins.index.astype(str) + "-07-01"), ins.values, "D", color="green", ms=7, label="INS annual average (independent)")
    ax[0].axvspan(pd.Timestamp("2021-01-01"), pd.Timestamp("2021-12-31"), color="orange", alpha=0.18, label="2021: raw is a copy of 2020")
    ax[0].axvspan(pd.Timestamp("2022-10-01"), pd.Timestamp("2023-04-30"), color="blue", alpha=0.12, label="7 missing months, interpolated")
    ax[0].set_title("CPI (2015 = 100)"); ax[0].legend(fontsize=7, loc="upper left")
    z = (pm(raw.month) >= "2019-06-01")
    ax[1].plot(pm(raw.month)[z], raw.cpi_index_2015_100[z], "o-", ms=4, color="gray", label="raw")
    zz = pm(pro.month) >= "2019-06-01"
    ax[1].plot(pm(pro.month)[zz], pro.cpi_index_2015_100[zz], "-", color="crimson", label="processed")
    ax[1].set_title("Zoom 2019-2026: raw 2021 repeats 2020 (flat step), processed continues the trend"); ax[1].legend(fontsize=8)
    ax[1].title.set_fontsize(9)
    save(fig, "01_cpi_raw_vs_processed.png")
    y = pd.Series(pro.cpi_index_2015_100.values, index=pro.month.str[:4].astype(int)).groupby(level=0).mean()
    print("  CPI processed yearly mean vs INS (%):", (100 * (y / ins - 1)).dropna().loc[2019:].round(2).to_dict())


def p2_trade():
    raw = pd.read_csv(DATA / "BCT" / "trade_monthly_2014_2026.csv")
    pro = pd.read_csv(OUT / "economy_monthly.csv")
    fig, ax = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
    for a, (ind, col, lab) in zip(ax, (("exports_fob", "exports_fob", "Exports (fob)"), ("imports_cif", "imports_cif", "Imports (cif)"))):
        r = raw[raw.indicator == ind]
        a.plot(pm(pro.month), pro[col], "-", color="crimson", label="processed")
        a.plot(pm(r.month), r.value, "o", ms=3, color="black", label="raw (observed)")
        miss = pro.month[pro[col].notna() & ~pro.month.isin(r.month)]
        miss = miss[miss >= "2014-01"]
        a.plot(pm(miss), pro.set_index("month").loc[miss, col], "s", mfc="none", color="blue", ms=7, label="filled by seasonal-aware interpolation")
        a.set_title(lab); a.legend(fontsize=8, ncol=3)
    fig.suptitle("Trade: 9 missing months (2020-10 and 2021-01..08) filled keeping the seasonal pattern")
    save(fig, "02_trade_filled_months.png")


def p3_gdp_chain():
    n = pd.read_csv(DATA / "BCT" / "national_accounts_quarterly_2010_2026.csv")
    con = n[(n.item == "GDP at market prices") & (n.price_basis == "constant_prices")].set_index("period").value_million_tnd
    q = pd.read_csv(OUT / "economy_quarterly.csv")
    fig, ax = plt.subplots(1, 3, figsize=(18, 4.4))
    ax[0].plot(pq(con.index), con.values, "o-", ms=3, color="gray", label="raw constant prices (base year changes)")
    ax[0].plot(pq(q.period), q.gdp_constant_chained_mtnd, "-", color="crimson", lw=1.8, label="chain-linked")
    for b in ("2015Q1", "2021Q1"):
        ax[0].axvline(pq([b])[0], color="orange", ls="--", lw=0.9)
    ax[0].set_title("Real GDP (M.TND): artificial level jumps at 2015Q1 and 2021Q1 removed"); ax[0].title.set_fontsize(9); ax[0].legend(fontsize=8)
    full = pd.period_range(con.index.min(), con.index.max(), freq="Q")
    rawq = pd.Series(con.values, index=pd.PeriodIndex(con.index, freq="Q")).reindex(full)
    ax[1].bar(pq(full.astype(str)), rawq.pct_change() * 100, width=60, color="lightgray", label="raw q/q %")
    ax[1].plot(pq(q.period), q.gdp_constant_chained_mtnd.pct_change() * 100, ".-", color="crimson", ms=4, label="chain-linked q/q %")
    ax[1].set_title("Quarter-on-quarter growth (%): the +16% and +31% break artefacts vanish (2020 Covid dip is real)"); ax[1].title.set_fontsize(9); ax[1].legend(fontsize=8)
    yr = pd.Series(q.gdp_constant_chained_mtnd.values, index=q.period.str[:4].astype(int))
    cnt = yr.groupby(level=0).count()
    tot = yr.groupby(level=0).sum()[cnt == 4]
    g = (100 * tot.pct_change())[tot.index.to_series().diff() == 1]
    wb = pd.read_csv(OUT / "economy_annual.csv").set_index("year").gdp_growth_pct
    both = pd.concat([g.rename("BCT quarterly (chain-linked)"), wb.rename("World Bank")], axis=1).dropna().loc[2012:]
    both.plot.bar(ax=ax[2], width=0.8)
    ax[2].set_title(f"Annual real growth (%) vs World Bank: mean gap {(both.iloc[:, 0] - both.iloc[:, 1]).abs().mean():.1f} pp", fontsize=9)
    ax[2].axhline(0, color="k", lw=0.6)
    save(fig, "03_gdp_chain_linking.png")


def p4_gdp_current():
    n = pd.read_csv(DATA / "BCT" / "national_accounts_quarterly_2010_2026.csv")
    cur = n[(n.item == "GDP at market prices") & (n.price_basis == "current_prices")].set_index("period").value_million_tnd
    q = pd.read_csv(OUT / "economy_quarterly.csv")
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.2))
    ax[0].plot(pq(q.period), q.gdp_current_mtnd, "-", color="crimson", label="processed")
    obs = cur.dropna()
    ax[0].plot(pq(obs.index), obs.values, "o", ms=3, color="black", label="raw (observed)")
    imp = q[q.current_imputed.astype(bool)]
    ax[0].plot(pq(imp.period), imp.gdp_current_mtnd, "s", mfc="none", color="blue", ms=8, label=f"rebuilt via deflator ({len(imp)} quarters)")
    ax[0].set_title("GDP at current prices (M.TND)"); ax[0].legend(fontsize=8)
    ax[1].plot(pq(q.period), q.gdp_deflator, "-", color="purple")
    ax[1].plot(pq(imp.period), imp.gdp_deflator, "s", mfc="none", color="blue", ms=8)
    ax[1].set_title("Implicit GDP deflator used for the rebuild (smooth, so interpolation is safe)"); ax[1].title.set_fontsize(9)
    save(fig, "04_gdp_current_prices_filled.png")


def p5_annual_splice():
    raw = pd.read_csv(DATA / "FRED" / "macro_fred_annual.csv").set_index("year")
    pro = pd.read_csv(OUT / "economy_annual.csv").set_index("year").join(pd.read_csv(OUT / "economy_annual_from_2012.csv").set_index("year"), how="outer")
    cols = ["current_account_usd_bn", "broad_money_growth_pct", "old_age_dependency_pct"]
    fig, ax = plt.subplots(1, 3, figsize=(15, 4), sharex=True)
    for a, c in zip(ax.ravel(), cols):
        a.plot(pro.index, pro[c], "-", color="crimson", label="processed")
        a.plot(raw.index, raw[c], "o", ms=5, color="black", label="FRED (original)")
        filled = pro[c].notna() & raw[c].reindex(pro.index).isna()
        a.plot(pro.index[filled], pro[c][filled], "s", mfc="none", color="blue", ms=7, label="filled from World Bank")
        a.set_title(c + ("" if filled.any() else "  (NOT filled: second source could not be validated)"), fontsize=9)
        a.legend(fontsize=7)
    fig.suptitle("Annual series: gaps filled only from a second source that agrees on the shared years")
    save(fig, "05_annual_gaps_filled_from_world_bank.png")


def main():
    print("[economy plots]")
    for f in (p1_cpi, p2_trade, p3_gdp_chain, p4_gdp_current, p5_annual_splice):
        f()


if __name__ == "__main__":
    main()
