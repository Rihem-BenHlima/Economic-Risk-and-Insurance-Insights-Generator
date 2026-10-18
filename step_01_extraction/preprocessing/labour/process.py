"""Labour domain: BCT annual labour (2011-2025), INS quarterly labour (2024Q3-2026Q2), World Bank labour force and unemployment.

Treatments (all logged in preprocessing_log.csv)
  * INS 2024Q4 levels/rates flagged "suspect break" by the source: set to missing and interpolated between neighbours
  * INS 2024Q1-Q2 have only unemployed counts (no active population, employed, rates): dropped from the quarterly table
  * BCT employed 2024 (3848) is ~7% above the World Bank-derived figure: rebuilt from the World Bank
  * BCT 2025 annual values equal one INS quarter: replaced by the mean of the four INS 2025 quarters
  * employed before 2011: World Bank labour force x (1 - unemployment rate), scaled by the median BCT/derived ratio (2011-2023)
Outputs: labour_quarterly.csv, labour_annual.csv
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import DATA, OUT, log, write

D = "labour"
LEVELS = ["active_population", "employed", "unemployed"]


def quarterly():
    q = pd.read_csv(DATA / "INS" / "labour_quarterly.csv")
    q["key"] = q.indicator + "_" + q.sex
    w = q.pivot(index="period", columns="key", values="value")
    flagged = q[q.quality_flag.astype(str).str.contains("suspect_break", na=False)]
    w.index = pd.PeriodIndex(w.index, freq="Q")
    # quarters without active population or employed figures cannot be used
    empty = w.index[w["active_population_total"].isna() & w["employed_total"].isna()]
    if len(empty):
        log(D, "labour_quarterly", ",".join(map(str, empty)), "dropped quarters", "only unemployed counts exist; no active population, employed or rates")
        w = w.drop(index=empty)
    # suspect break: blank the flagged values, then interpolate across the break quarter
    for _, r in flagged.iterrows():
        p = pd.Period(r.period, freq="Q")
        if r.key in w.columns and p in w.index:
            w.loc[p, r.key] = np.nan
    for c in w.columns:
        before = w[c].isna()
        w[c] = w[c].interpolate(limit_area="inside")
        for p in w.index[before & w[c].notna()]:
            log(D, c, p, "interpolated", "value missing or flagged 'suspect_break_check_against_INS_release'")
    w.index = w.index.astype(str)
    w.index.name = "period"
    write(w, "labour_quarterly.csv")
    for sex in ("female", "male", "total"):
        calc = w[f"employed_{sex}"] + w[f"unemployed_{sex}"]
        d = 100 * (calc - w[f"active_population_{sex}"]).abs() / w[f"active_population_{sex}"]
        print(f"  {sex}: max gap between employed+unemployed and active population = {d.max():.1f}%")
    print(f"  quarterly table: {w.index[0]}..{w.index[-1]}, missing cells {int(w.isna().sum().sum())}")
    return w


def annual(w):
    a = pd.read_csv(DATA / "BCT" / "labour_annual_2011_2025.csv")
    for _, r in a[a.quality_flag.notna()].iterrows():
        log(D, f"bct_{r.indicator}", r.year, f"flag from source: {r.quality_flag}", "treated below")
    p = a.pivot(index="year", columns="indicator", values="value").rename(columns={"employed": "employed_thousand", "unemployment_rate": "unemployment_rate_bct"})
    wb = pd.read_csv(DATA / "API_TUN_DS2_en_csv_v2_17970" / "API_TUN_DS2_en_csv_v2_17970.csv", skiprows=4, encoding="utf-8-sig").set_index("Indicator Code")
    yrs = [c for c in wb.columns if str(c).isdigit()]
    lf = wb.loc["SL.TLF.TOTL.IN", yrs].astype(float) / 1e3
    un = wb.loc["SL.UEM.TOTL.ZS", yrs].astype(float)
    lf.index = lf.index.astype(int)
    un.index = un.index.astype(int)
    derived = lf * (1 - un / 100)
    p = p.reindex(range(2003, 2026))
    p["employed_wb_derived_thousand"] = derived
    p["unemployment_rate_wb"] = un

    ratio = (p.employed_thousand / p.employed_wb_derived_thousand).loc[2011:2023]
    k = ratio.median()
    print(f"  BCT employed / World Bank-derived: median {k:.3f}, std {ratio.std():.3f} over 2011-2023 (max dev {100 * (ratio - k).abs().max() / k:.1f}%)")
    p["employed_source"] = np.where(p.employed_thousand.notna(), "BCT", "")
    # 2025: BCT value equals one INS quarter -> mean of the four INS quarters of 2025
    y25 = w[w.index.str.startswith("2025")]
    if len(y25) == 4:
        for col, src in (("unemployment_rate_bct", "unemployment_rate_total"), ("employed_thousand", "employed_total")):
            new = y25[src].mean()
            log(D, col, 2025, f"replaced {p.loc[2025, col]} by mean of 2025Q1-Q4 = {new:.2f}", "BCT value equals one INS quarter, not an annual average")
            p.loc[2025, col] = new
        p.loc[2025, "employed_source"] = "INS 2025 quarterly mean"
    # 2024: BCT figure is out of line with the World Bank-derived level
    dev = p.loc[2024, "employed_thousand"] / (p.loc[2024, "employed_wb_derived_thousand"] * k) - 1
    if abs(dev) > 0.05:
        new = p.loc[2024, "employed_wb_derived_thousand"] * k
        log(D, "employed_thousand", 2024, f"replaced {p.loc[2024, 'employed_thousand']:.0f} by {new:.0f}", f"BCT value {100 * dev:+.1f}% above World Bank-derived level (other years within {100 * (ratio - k).abs().max() / k:.0f}%)")
        p.loc[2024, "employed_thousand"] = new
        p.loc[2024, "employed_source"] = "estimated from World Bank"
    # before 2011: derived x k
    for y in p.index[p.employed_thousand.isna()]:
        if pd.notna(derived.get(y)):
            p.loc[y, "employed_thousand"] = derived[y] * k
            p.loc[y, "employed_source"] = "estimated from World Bank"
            log(D, "employed_thousand", y, "estimated from World Bank labour force", f"x {k:.3f} (typical BCT/derived ratio); expected error about +/-{100 * ratio.std() / k:.0f}%")
    p["unemployment_rate"] = p.unemployment_rate_bct.combine_first(p.unemployment_rate_wb)
    p["unemployment_source"] = np.where(p.unemployment_rate_bct.notna(), "BCT", "World Bank")
    log(D, "unemployment_rate", "2003-2010", "taken from the World Bank series", "BCT starts in 2011; the two agree within 0.1 pp in 2011-2013")
    p["employment_rate_proxy"] = p.employed_thousand / lf.reindex(p.index)
    p.index.name = "year"
    p = p.drop(columns=["unemployment_rate_bct"])               # helper column with the pre-2011 gap; the final series is unemployment_rate
    write(p, "labour_annual.csv")
    print(f"  annual: {p.index.min()}-{p.index.max()}, missing cells in final columns: {int(p[['employed_thousand', 'unemployment_rate']].isna().sum().sum())}")
    return p


def main():
    print("[labour]")
    w = quarterly()
    annual(w)


if __name__ == "__main__":
    main()
