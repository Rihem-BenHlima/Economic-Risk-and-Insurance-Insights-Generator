"""Insurance domain: CGA annual market table (2003-2024), FTUSA company panel (2016-2024).

Rules: insurance values are never imputed (they are the forecast targets). We validate, derive ratios, and tidy.
Outputs: insurance_annual.csv, insurance_companies.csv
"""
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import DATA, log, write, drop_unusable

D = "insurance"


def annual():
    a = pd.read_csv(DATA / "CGA" / "tunisia_insurance_annual.csv").set_index("year").sort_index()
    a = a.apply(pd.to_numeric, errors="coerce")
    # consistency checks against the source's own totals
    chk = {
        "life+nonlife = total premiums": (a.premiums_life + a.premiums_nonlife - a.premiums_total).abs().max(),
        "life+nonlife = total claims": (a.claims_paid_life + a.claims_paid_nonlife - a.claims_paid_total).abs().max(),
        "source loss ratio vs recomputed (pp)": (a.claims_paid_to_premiums_pct - 100 * a.claims_paid_total / a.premiums_total).abs().max(),
    }
    for k, v in chk.items():
        print(f"  check {k}: max diff {v:.2f}")
        if v > 0.5:
            log(D, k, "all", "consistency check failed", f"max diff {v:.2f}")
    # derived features
    a["premiums_total_growth_pct"] = 100 * a.premiums_total.pct_change()
    a["claims_paid_total_growth_pct"] = 100 * a.claims_paid_total.pct_change()
    a["loss_ratio_pct"] = 100 * a.claims_paid_total / a.premiums_total
    a["loss_ratio_auto_pct"] = 100 * a.claims_paid_auto / a.premiums_auto
    a["loss_ratio_health_pct"] = 100 * a.claims_paid_health / a.premiums_health
    a["life_share_pct"] = 100 * a.premiums_life / a.premiums_total
    a["auto_share_pct"] = 100 * a.premiums_auto / a.premiums_total
    a["health_share_pct"] = 100 * a.premiums_health / a.premiums_total
    a["agri_share_pct"] = 100 * a.premiums_agri / a.premiums_total
    # flag, don't remove, volatile/small series
    for c in ("premiums_agri", "claims_paid_life"):
        g = a[c].pct_change().abs()
        for y in g.index[g > 0.5]:
            log(D, c, y, "flag: year-on-year change > 50%", "kept as is (genuine volatility or small base)")
    # rule: data that cannot be corrected and would mislead a model is removed from the processed table (raw files stay)
    a, dropped = drop_unusable(a, D, min_coverage=0.6, always_drop={
        **{c: "macro indicator copied into the CGA file; the World Bank/BCT series are used instead" for c in
           ("gdp_growth_real_pct", "inflation_avg_pct", "unemployment_pct", "unemployment_higher_ed_pct", "current_account_deficit_pct_gdp",
            "public_debt_pct_gdp", "budget_deficit_pct_gdp")},
        "claims_paid_agri": "agricultural claims (1.9-17.4 M.TND, 14 of 21 yearly swings above 30%) are essentially random: the best reformulation still has 46% backtest error and a negative R2",
        "claims_paid_to_premiums_agri_pct": "derived from the dropped agricultural claims series",
        "insurance_penetration_pct_gdp": "replaced by penetration computed from World Bank GDP (complete series)",
        "insurance_density_tnd_per_capita": "replaced by density computed from World Bank population (complete series)",
    })
    # a gap-free table: columns with gaps in the middle or at the end cannot be repaired (no second source) -> dropped;
    # columns that only start later (leading gap) go to a separate table that is complete within its own window
    def gaps(c):
        s = a[c].iloc[1:] if c.endswith("_growth_pct") else a[c]      # the first growth rate is undefined by definition
        return s.isna()
    complete = [c for c in a.columns if not gaps(c).any()]
    leading, broken = [], []
    for c in a.columns:
        if c in complete:
            continue
        first = a[c].first_valid_index()
        (leading if a[c].loc[first:].notna().all() else broken).append(c)
    for c in broken:
        log(D, c, ",".join(str(y) for y in a.index[a[c].isna()]), "dropped column",
            "gaps inside the series with no second source to fill them (the FTUSA technical result overlaps the CGA on only 4 years and differs by up to 11%)")
    late = a[leading].dropna(how="all")
    start = int(late.apply(pd.Series.first_valid_index).max()) if len(leading) else None
    full = a[complete]
    write(full, "insurance_annual.csv")
    print(f"  insurance_annual: {full.index.min()}-{full.index.max()}, {full.shape[1]} columns, missing cells {int(full.isna().sum().sum())} (growth rates start in 2004)")
    if leading:
        late = a.loc[start:, leading]
        for c in leading:
            log(D, c, f"2003-{start - 1}", "kept only from " + str(start), "series starts later; stored in insurance_annual_from_%d.csv, complete within that window" % start)
        write(late, f"insurance_annual_from_{start}.csv")
        print(f"  insurance_annual_from_{start}: {late.shape}, missing cells {int(late.isna().sum().sum())}")
    print(f"  dropped (gaps that cannot be repaired): {broken}")
    return full


def companies():
    c = pd.read_csv(DATA / "FTUSA" / "ftusa_company_level_premiums_and_claims_2016_2024.csv")
    c["value_mtnd"] = c.amount_dt / 1e6
    # the same company can appear in several rows per year/branch/measure (reports restate): keep the latest report
    c["rep"] = c.value_taken_from_report_year.astype(str).str.extract(r"(\d{4})")[0].astype(float)
    n0 = len(c)
    c = c.sort_values("rep").drop_duplicates(["year", "company", "branch_code", "measure"], keep="last")
    if len(c) < n0:
        log(D, "ftusa_company_panel", "all", f"dropped {n0 - len(c)} duplicate rows", "kept the value from the latest report")
    out = c[["year", "company", "branch_code", "measure", "value_mtnd"]].sort_values(["year", "company", "branch_code", "measure"])
    out = out.set_index(["year", "company"])
    write(out, "insurance_companies.csv")
    tot = c[(c.branch_code == "ALL_BRANCHES") & (c.measure == "premiums_total_direct_plus_acceptances")].groupby("year").value_mtnd.sum()
    print("  FTUSA company premiums, all branches, sum by year (M.TND):", tot.round(0).to_dict())
    return out


def main():
    print("[insurance]")
    annual(); companies()


if __name__ == "__main__":
    main()
