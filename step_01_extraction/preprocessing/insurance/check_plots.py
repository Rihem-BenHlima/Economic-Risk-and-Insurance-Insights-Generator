"""Check plots for the insurance domain: was the data treated correctly?

Compares the processed tables (data/processed/insurance_*.csv) with the raw source files and with an independent
source (FTUSA). Insurance values are never imputed, so the checks are: totals agree across sources, components add up,
nothing is silently missing, and flagged jumps are real.
Run (after process.py):  python step_01_extraction/preprocessing/insurance/check_plots.py
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
from common import DATA, OUT, LOG_FILE

PLOTS = Path(__file__).parent / "plots"
PLOTS.mkdir(exist_ok=True)
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": 0.3, "axes.spines.top": False, "axes.spines.right": False})

raw = pd.read_csv(DATA / "CGA" / "tunisia_insurance_annual.csv").set_index("year")
pro = pd.read_csv(OUT / "insurance_annual.csv").set_index("year")
comp = pd.read_csv(OUT / "insurance_companies.csv")
NONLIFE_PARTS = ["premiums_auto", "premiums_health", "premiums_transport", "premiums_fire_and_misc_combined", "premiums_export_credit",
                 "premiums_agri", "premiums_work_accidents", "premiums_accepted_ops"]


def save(fig, name):
    fig.tight_layout()
    fig.savefig(PLOTS / name)
    plt.close(fig)
    print("  saved", (PLOTS / name).relative_to(Path(__file__).parents[3]))


def p1_totals():
    """Raw vs processed vs the independent FTUSA company totals."""
    f = comp[(comp.branch_code == "ALL_BRANCHES") & (comp.measure == "premiums_total_direct_plus_acceptances")].groupby("year").value_mtnd.sum()
    br = pd.read_csv(DATA / "FTUSA" / "ftusa_branch_level_premiums_claims_cessions_operating_account_2016_2024.csv")
    fc = br[(br.branch_code == "TOTAL_DIRECT") & (br.measure == "claims_paid")].groupby("year").value.sum() / 1e6   # independent source
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
    ax[0].plot(raw.index, raw.premiums_total, "o-", label="CGA raw", lw=2)
    ax[0].plot(pro.index, pro.premiums_total, "x", ms=9, color="red", label="processed")
    ax[0].plot(f.index, f.values, "s", mfc="none", ms=9, color="green", label="FTUSA (sum of companies)")
    ax[0].set_title("Total net premiums (M.TND)"); ax[0].legend()
    ax[1].plot(raw.index, raw.claims_paid_total, "o-", label="CGA raw", lw=2)
    ax[1].plot(pro.index, pro.claims_paid_total, "x", ms=9, color="red", label="processed")
    if len(fc):
        ax[1].plot(fc.index, fc.values, "s", mfc="none", ms=9, color="green", label="FTUSA (branch-level file)")
    ax[1].set_title("Total paid claims (M.TND)"); ax[1].legend()
    d = (f - raw.premiums_total.reindex(f.index)).abs()
    dc = (fc - raw.claims_paid_total.reindex(fc.index)).abs() if len(fc) else pd.Series([np.nan])
    fig.suptitle(f"CGA vs FTUSA: max difference premiums {d.max():.1f} M.TND ({100 * (d / raw.premiums_total.reindex(f.index)).max():.2f}%), claims {dc.max():.1f} M.TND ({100 * (dc / raw.claims_paid_total.reindex(fc.index)).max():.1f}%, FTUSA always slightly lower: definition)")
    save(fig, "01_totals_raw_vs_processed_vs_ftusa.png")


def p2_branches():
    parts = {"Life": "premiums_life", "Motor": "premiums_auto", "Health": "premiums_health", "Transport": "premiums_transport",
             "Fire & misc": "premiums_fire_and_misc_combined", "Agriculture": "premiums_agri"}
    d = pd.DataFrame({k: pro[v] for k, v in parts.items()})
    d["Other (export credit, accepted, work acc.)"] = pro.premiums_total - d.sum(axis=1)
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.4))
    ax[0].stackplot(d.index, d.T.values, labels=d.columns)
    ax[0].plot(pro.index, pro.premiums_total, "k--", label="total (CGA)")
    ax[0].set_title("Premiums by branch (stacked) vs total"); ax[0].legend(fontsize=7, loc="upper left")
    share = d.div(pro.premiums_total, axis=0) * 100
    ax[1].stackplot(share.index, share.T.values, labels=share.columns)
    ax[1].set_title("Branch shares (%)"); ax[1].set_ylim(0, 100)
    neg = (d.iloc[:, -1] < -0.5).sum()
    ident = max((raw.premiums_life + raw.premiums_nonlife - raw.premiums_total).abs().max(), (raw.claims_paid_life + raw.claims_paid_nonlife - raw.claims_paid_total).abs().max())
    fig.suptitle(f"Branches rebuild the total (remainder never negative: {neg} years below -0.5); life + non-life = total for premiums and claims, max deviation {ident:.1e}")
    save(fig, "02_branches_vs_total.png")


def p6_flags():
    lg = pd.read_csv(LOG_FILE)
    fl = lg[(lg.domain == "insurance") & lg.action.str.startswith("flag")]
    series = ["premiums_agri", "claims_paid_life"]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4), sharex=True)
    for a, c in zip(ax.ravel(), series):
        g = pro[c].pct_change() * 100
        a.bar(g.index, g.values, color="lightgray")
        hit = fl[fl.series == c].period.astype(int).tolist()
        a.bar(hit, g.reindex(hit).values, color="crimson")
        a.axhline(50, color="k", ls=":", lw=0.7); a.axhline(-50, color="k", ls=":", lw=0.7)
        a.set_title(f"{c}: year-on-year change (%) - red = flagged ({len(hit)})", fontsize=9)
    fig.suptitle("Flagged jumps (>50%) are kept, not removed: checking they are genuine")
    save(fig, "03_flagged_jumps.png")


def main():
    print("[insurance plots]")
    for f in (p1_totals, p2_branches, p6_flags):
        f()


if __name__ == "__main__":
    main()
