"""Independent audit of the processed tables in data/processed (run after run_all.py).

Checks: completeness, date regularity, duplicates, value ranges, outliers, internal identities, agreement between sources,
redundant columns. Prints a report and writes data/processed/audit_report.csv (one row per finding).
Run:  python step_01_extraction/preprocessing/audit.py
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from common import DATA, OUT

FINDINGS = []


def add(level, area, what):
    FINDINGS.append({"level": level, "area": area, "finding": what})
    print(f"  [{level:4}] {area}: {what}")


def read(name, index=None):
    d = pd.read_csv(OUT / f"{name}.csv")
    return d.set_index(index) if index else d


def structure():
    print("\n1) STRUCTURE: shape, dates, duplicates, missing, non-numeric")
    spec = {  # table -> (index column, frequency)
        "insurance_annual": ("year", "Y"), "insurance_annual_from_2010": ("year", "Y"), "economy_annual": ("year", "Y"),
        "economy_annual_from_2012": ("year", "Y"), "economy_monthly": ("month", "M"), "economy_cpi_monthly": ("month", "M"),
        "economy_quarterly": ("period", "Q"), "labour_annual": ("year", "Y"), "labour_quarterly": ("period", "Q"),
        "agriculture_annual": ("year", "Y"), "agriculture_context_2012_2024": ("year", "Y"), "climate_annual": ("year", "Y"),
        "climate_monthly": ("month", "M"), "climate_daily": ("date", "D"), "modeling_table": ("year", "Y")}
    for name, (ix, fq) in spec.items():
        d = read(name)
        idx = d[ix]
        pi = pd.PeriodIndex(idx.astype(str), freq=fq if fq != "Y" else "Y") if fq != "D" else pd.DatetimeIndex(idx)
        full = pd.period_range(pi.min(), pi.max(), freq=fq) if fq != "D" else pd.date_range(pi.min(), pi.max())
        gaps, dup = len(full) - pi.nunique(), int(pd.Index(pi).duplicated().sum())
        num = d.drop(columns=ix).drop(columns=[c for c in d.columns if c.endswith("_source")])
        non_num = [c for c in num.columns if not pd.api.types.is_numeric_dtype(num[c]) and not c.endswith("_source")]
        miss, inf = int(num.isna().sum().sum()), int(np.isinf(num.select_dtypes("number")).sum().sum())
        const = [c for c in num.select_dtypes("number").columns if num[c].nunique(dropna=True) <= 1]
        bad = []
        if gaps: bad.append(f"{gaps} missing periods")
        if dup: bad.append(f"{dup} duplicate periods")
        if inf: bad.append(f"{inf} infinite values")
        if const: bad.append(f"constant columns {const}")
        if non_num: bad.append(f"non-numeric columns {non_num}")
        undefined = int(num[[c for c in num.columns if c.endswith(('_yoy_pct', '_growth_pct'))]].isna().sum().sum())
        if miss - undefined > 0: bad.append(f"{miss - undefined} missing cells beyond undefined growth rates")
        add("FAIL" if bad else "ok", name, f"{d.shape[0]} rows x {d.shape[1] - 1} cols, {pi.min()}..{pi.max()}, missing {miss} (growth rates undefined at start: {undefined})" + (f" | PROBLEMS: {'; '.join(bad)}" if bad else ""))


def ranges():
    print("\n2) VALUE RANGES and OUTLIERS (modeling_table)")
    t = read("modeling_table", "year")
    pos = [c for c in t.columns if c.startswith(("premiums_", "claims_", "tech_provisions", "own_funds")) and not c.endswith("_pct")] + ["gdp_usd", "population", "tnd_per_usd", "employed_thousand", "rainfall_mm", "gdp_per_capita_usd"]
    for c in pos:
        if c in t and (t[c] <= 0).any():
            add("FAIL", c, f"non-positive values in {t.index[t[c] <= 0].tolist()}")
    pct = [c for c in t.columns if c.endswith("_pct") and ("share" in c or "unemployment" in c or "urban" in c or "pct_gdp" in c and "growth" not in c)]
    for c in pct:
        if c in t and ((t[c] < 0) | (t[c] > 100)).any():
            add("FAIL", c, f"outside 0-100%: {t[c].min():.1f}..{t[c].max():.1f}")
    flagged = []
    for c in t.select_dtypes("number").columns:
        s = t[c].dropna()
        if len(s) > 8 and s.std() > 0:
            ch = s.diff().dropna()
            mad = (ch - ch.median()).abs().median() or ch.std()
            z = (ch - ch.median()).abs() / (1.4826 * mad) if mad else ch * 0
            for y in z.index[z > 6]:
                flagged.append((c, int(y), round(float(ch[y]), 2)))
    add("note" if flagged else "ok", "outliers", f"{len(flagged)} year-on-year changes beyond 6 robust sigmas (kept: inspect, may be real events)")
    for c, y, v in flagged[:14]:
        print(f"           {c:34} {y}  change {v:+.2f}")
    add("ok", "plausibility", f"penetration {t.penetration_pct_gdp.min():.2f}-{t.penetration_pct_gdp.max():.2f}% of GDP, density {t.density_tnd_per_capita.min():.0f}-{t.density_tnd_per_capita.max():.0f} TND/person, "
        f"unemployment {t.unemployment_rate.min():.1f}-{t.unemployment_rate.max():.1f}%, inflation {t.inflation_pct.min():.1f}-{t.inflation_pct.max():.1f}%")


def identities():
    print("\n3) INTERNAL IDENTITIES")
    t = read("modeling_table", "year")
    checks = {
        "life + non-life = total premiums": (t.premiums_life + t.premiums_nonlife - t.premiums_total).abs().max(),
        "life + non-life = total claims": (t.claims_paid_life + t.claims_paid_nonlife - t.claims_paid_total).abs().max(),
        "loss ratio = claims / premiums (pp)": (t.loss_ratio_pct - 100 * t.claims_paid_total / t.premiums_total).abs().max(),
        "life share + non-life share = 100 (pp)": (t.life_share_pct + 100 * t.premiums_nonlife / t.premiums_total - 100).abs().max(),
        "GDP per capita = GDP / World Bank population (rel.)": ((t.gdp_per_capita_usd - t.gdp_usd / read("economy_annual", "year").population.reindex(t.index)).abs() / t.gdp_per_capita_usd).max(),
        "density = premiums / national population (rel.)": ((t.density_tnd_per_capita - t.premiums_total * 1e6 / t.population_national).abs() / t.density_tnd_per_capita).max(),
    }
    for k, v in checks.items():
        add("ok" if v < 0.01 or (v < 0.05 and "rel" in k) else "FAIL", "identity", f"{k}: max deviation {v:.4g}")
    q = read("labour_quarterly", "period")
    for sex in ("female", "male", "total"):
        dev = (100 * (q[f"employed_{sex}"] + q[f"unemployed_{sex}"] - q[f"active_population_{sex}"]).abs() / q[f"active_population_{sex}"]).max()
        add("ok" if dev < 1 else "FAIL", "identity", f"labour {sex}: employed + unemployed vs active population, max {dev:.2f}%")
    f, m = q.active_population_female + q.active_population_male, q.active_population_total
    add("ok" if ((f - m).abs() / m).max() < 0.01 else "FAIL", "identity", f"labour: female + male = total active population, max {100 * ((f - m).abs() / m).max():.2f}%")


def cross_source():
    print("\n4) AGREEMENT BETWEEN INDEPENDENT SOURCES")
    t = read("modeling_table", "year")
    cpi = read("economy_cpi_monthly", "month")
    y = pd.Series(cpi.cpi_index_2015_100.values, index=cpi.index.str[:4].astype(int)).groupby(level=0).mean()
    infl = (100 * y.pct_change()).dropna()
    d = (infl - t.inflation_pct).dropna()
    add("ok" if d.abs().mean() < 0.5 else "WARN", "inflation", f"BCT CPI-implied vs World Bank: mean abs gap {d.abs().mean():.2f} pp, max {d.abs().max():.2f} pp ({int(d.abs().idxmax())})")
    ftusa = pd.read_csv(OUT / "insurance_companies.csv")
    tot = ftusa[(ftusa.branch_code == "ALL_BRANCHES") & (ftusa.measure == "premiums_total_direct_plus_acceptances")].groupby("year").value_mtnd.sum()
    g = (100 * (tot - t.premiums_total.reindex(tot.index)).abs() / t.premiums_total.reindex(tot.index)).max()
    add("ok" if g < 0.5 else "WARN", "premiums", f"FTUSA company sum vs CGA total: max gap {g:.2f}% over {len(tot)} years")
    bct_fx = pd.read_csv(DATA / "BCT" / "bct_fx_interbank_snapshot_2026-10-13.csv") if (DATA / "BCT").exists() else None
    fx = {2020: 2.8111, 2021: 2.7963, 2022: 3.1049, 2023: 3.1069, 2024: 3.1118}   # BCT annual interbank USD (read from bct.gov.tn earlier)
    gap = max(abs(t.tnd_per_usd[y_] - v) / v for y_, v in fx.items())
    add("ok" if gap < 0.01 else "WARN", "exchange rate", f"World Bank TND/USD vs BCT annual interbank: max gap {100 * gap:.2f}%")
    pop = pd.read_csv(DATA / "BCT" / "population_annual_2011_2024.csv").set_index("year").population_thousand * 1e3
    gp = (100 * (pop - t.population_national.reindex(pop.index)).abs() / pop).max()
    add("ok" if gp < 1 else "WARN", "population", f"national series used in the table vs BCT: max gap {gp:.2f}% (the World Bank series is 2-3% higher and is not used for density)")
    qg = read("economy_quarterly", "period")
    yr = pd.Series(qg.gdp_constant_chained_mtnd.values, index=qg.index.str[:4].astype(int))
    tot_q = yr.groupby(level=0).sum()[yr.groupby(level=0).count() == 4]
    gr = (100 * tot_q.pct_change())[tot_q.index.to_series().diff() == 1].loc[2012:]
    dd = (gr - t.gdp_growth_pct.reindex(gr.index)).dropna()
    add("ok" if dd.abs().mean() < 1.5 else "WARN", "GDP growth", f"chain-linked BCT quarterly vs World Bank: mean abs gap {dd.abs().mean():.2f} pp, max {dd.abs().max():.2f} pp ({int(dd.abs().idxmax())})")
    e = read("labour_annual", "year")
    gu = (e.unemployment_rate - e.unemployment_rate_wb).abs().loc[2011:].max()
    add("ok" if gu < 2.5 else "WARN", "unemployment", f"BCT vs World Bank (2011+): max gap {gu:.1f} pp")


def redundancy():
    print("\n5) REDUNDANCY and MODELLING RISKS (modeling_table)")
    t = read("modeling_table", "year")
    num = t.select_dtypes("number").dropna(axis=1)
    c = num.corr().abs()
    pairs = [(a, b, round(float(c.loc[a, b]), 4)) for i, a in enumerate(c.columns) for b in c.columns[i + 1:] if c.loc[a, b] > 0.995]
    add("note", "collinearity", f"{len(pairs)} column pairs with |correlation| > 0.995 (e.g. {pairs[:3]}); drop one of each before modelling")
    add("note", "dimensions", f"{t.shape[0]} years vs {t.shape[1]} columns: more columns than rows, so models need feature selection (a handful of predictors at most)")
    targets = ["premiums_total", "premiums_life", "premiums_auto", "premiums_health", "claims_paid_total"]
    from numpy import corrcoef
    ch = np.log(t[targets]).diff().dropna()
    pred = ["inflation_pct", "gdp_growth_pct", "unemployment_rate", "rainfall_mm", "tnd_per_usd"]
    best = {}
    for tg in targets:
        r = {p: float(np.corrcoef(ch[tg], t[p].diff().dropna().reindex(ch.index).fillna(0))[0, 1]) for p in pred}
        best[tg] = max(r.items(), key=lambda kv: abs(kv[1]))
    add("note", "signal", "strongest |correlation| between growth of each target and the change of a candidate predictor: " + "; ".join(f"{k}: {v[0]} ({v[1]:+.2f})" for k, v in best.items()))
    log = pd.read_csv(OUT / "preprocessing_log.csv")
    add("ok", "log", f"{len(log)} entries: {int(log.action.str.contains('filled|interpolat|chain|rebuilt|replaced|estimated').sum())} fills/corrections, {int((log.action == 'dropped column').sum())} columns dropped")


def main():
    print("AUDIT of data/processed")
    structure(); ranges(); identities(); cross_source(); redundancy()
    f = pd.DataFrame(FINDINGS)
    f.to_csv(OUT / "audit_report.csv", index=False)
    print("\nSUMMARY:", f.level.value_counts().to_dict(), "-> data/processed/audit_report.csv")


if __name__ == "__main__":
    main()
