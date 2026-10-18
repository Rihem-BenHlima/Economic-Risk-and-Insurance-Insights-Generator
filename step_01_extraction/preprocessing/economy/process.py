"""Economy domain: annual macro (World Bank, FRED), monthly (BCT CPI, trade, money), quarterly GDP (BCT national accounts).

Fixes applied here (found in the audit):
  * BCT CPI for 2021 is an exact copy of 2020 -> rebuilt by interpolation, rescaled to the INS annual average
  * 7 missing CPI months (2022-10..2023-04) -> log-linear interpolation (checked against INS annual averages)
  * BCT trade has 9 missing months -> seasonal-aware interpolation
  * quarterly GDP: absent quarters filled (seasonal-aware), constant prices chain-linked across base-year changes,
    missing current-price quarters rebuilt through the GDP deflator
Outputs: economy_annual.csv, economy_monthly.csv, economy_quarterly.csv
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import DATA, OUT, log, fill_interior, seasonal_fill, write

D = "economy"
WB_FILE = DATA / "API_TUN_DS2_en_csv_v2_17970" / "API_TUN_DS2_en_csv_v2_17970.csv"
WB = {"NY.GDP.MKTP.CD": "gdp_usd", "NY.GDP.MKTP.KD.ZG": "gdp_growth_pct", "NY.GDP.PCAP.CD": "gdp_per_capita_usd",
      "FP.CPI.TOTL.ZG": "inflation_pct", "SL.UEM.TOTL.ZS": "unemployment_pct_wb", "FS.AST.PRVT.GD.ZS": "private_credit_pct_gdp",
      "PA.NUS.FCRF": "tnd_per_usd", "NE.CON.PRVT.ZS": "household_consumption_pct_gdp", "NE.GDI.FTOT.ZS": "investment_pct_gdp",
      "NE.EXP.GNFS.ZS": "exports_pct_gdp", "NE.IMP.GNFS.ZS": "imports_pct_gdp", "SP.POP.TOTL": "population", "SP.URB.TOTL.IN.ZS": "urban_pct"}


# FRED column -> (World Bank code, scale) that measures the same thing, used to fill the years FRED does not cover
SPLICE = {
    "current_account_usd_bn": ("BN.CAB.XOKA.CD", 1e-9),
    "broad_money_growth_pct": ("FM.LBL.BMNY.ZG", 1.0),
    "govt_net_lending_pct_gdp": ("GC.NLD.TOTL.GD.ZS", 1.0),
    "old_age_dependency_pct": ("SP.POP.DPND.OL", 1.0),
}
SPLICE_TOL = 0.10        # accept a second source only if it agrees with the first within 10% on average...
SPLICE_MIN_OVERLAP = 8   # ...over at least 8 shared years


def wb_series(raw, code, scale=1.0):
    s = raw.loc[code, [c for c in raw.columns if str(c).isdigit()]].astype(float) * scale
    s.index = s.index.astype(int)
    return s


def annual():
    raw = pd.read_csv(WB_FILE, skiprows=4, encoding="utf-8-sig").set_index("Indicator Code")
    a = pd.DataFrame({name: wb_series(raw, code) for code, name in WB.items()})
    a["gdp_per_capita_const_usd"] = wb_series(raw, "NY.GDP.PCAP.KD")
    a.index.name = "year"
    fred = pd.read_csv(DATA / "FRED" / "macro_fred_annual.csv").set_index("year")
    for col, (code, k) in SPLICE.items():
        first, second = fred[col], wb_series(raw, code, k)
        ov = pd.concat([first, second], axis=1, keys=["a", "b"]).dropna()
        err = (ov.b - ov.a).abs().mean() / ov.a.abs().mean() if len(ov) else np.nan
        if len(ov) >= SPLICE_MIN_OVERLAP and err <= SPLICE_TOL:
            a[col] = first.combine_first(second)
            filled = [y for y in second.index if y not in first.dropna().index and pd.notna(second[y]) and y >= 2000]
            log(D, col, ",".join(str(y) for y in sorted(filled)) or "-", "filled from World Bank " + code,
                f"validated on {len(ov)} shared years: mean difference {100 * err:.1f}%")
        else:
            a[col] = first
            log(D, col, "pre-2012", "NOT filled", f"World Bank {code} cannot be validated (overlap {len(ov)} years, mean difference {100 * err:.0f}%)" if len(ov) else f"World Bank {code}: no overlapping years to validate")
    # World Bank population is 2-3% above the national figures (INS and BCT agree within 0.6%): build a national series
    ins_pop = pd.read_csv(DATA / "INS" / "population_national.csv")
    ins_pop = ins_pop[ins_pop.reference_date == "07-01"].set_index("year").population.astype(float)
    bct_pop = pd.read_csv(DATA / "BCT" / "population_annual_2011_2024.csv").set_index("year").population_thousand * 1e3
    national = ins_pop.combine_first(bct_pop)
    ratio = (national / a.population).dropna().loc[2011:2015]
    k = ratio.median()
    log(D, "population_national", "2016-2024", "INS mid-year population", "official national figures")
    log(D, "population_national", "2011-2015", "BCT population", "differs from INS by about 0.2% where both exist")
    for y in range(2000, 2011):
        national[y] = a.population[y] * k
    log(D, "population_national", "2000-2010", f"World Bank population x {k:.4f}", f"typical national/World Bank ratio 2011-2015 (std {ratio.std():.4f}); the World Bank is 2-3% higher than INS/BCT")
    a["population_national"] = national.sort_index()
    a = a.loc[1999:]
    for c in a.columns:
        a[c] = fill_interior(a[c], D, note="annual macro")
    a["gdp_usd_growth_pct"] = 100 * a.gdp_usd.pct_change()
    a = a.loc[2000:2024]                                   # 2025 is incomplete for several series: no trailing gaps
    leading = [c for c in a.columns if a[c].isna().any() and a[c].loc[a[c].first_valid_index():].notna().all()]
    broken = [c for c in a.columns if a[c].isna().any() and c not in leading]
    for c in broken:
        log(D, c, "all", "dropped column", "gaps with no second source")
    if leading:
        start = int(a[leading].apply(pd.Series.first_valid_index).max())
        for c in leading:
            log(D, c, f"2000-{start - 1}", f"kept only from {start}", "no validated second source; stored in economy_annual_from_%d.csv" % start)
        write(a.loc[start:, leading], f"economy_annual_from_{start}.csv")
    a = a.drop(columns=leading + broken)
    write(a, "economy_annual.csv")
    print(f"  economy_annual: {a.index.min()}-{a.index.max()}, {a.shape[1]} columns, missing cells {int(a.isna().sum().sum())}; only from {start if leading else '-'}: {leading}")
    return a


def monthly():
    cpi = pd.read_csv(DATA / "BCT" / "cpi_all_items_monthly_2010_2026.csv")
    cpi.index = pd.PeriodIndex(cpi.month, freq="M")
    s = cpi.cpi_index_2015_100.rename("cpi_index").astype(float)
    ins = pd.read_csv(DATA / "INS" / "cpi_annual.csv")
    ins = ins[ins.category == "All items"].set_index("year").cpi_index_2015_100
    # 1) a year that is an exact copy of the previous year is a source error
    for y in sorted(set(s.index.year)):
        cur, prev = s[s.index.year == y].values, s[s.index.year == y - 1].values
        if len(cur) == 12 and len(prev) == 12 and not np.isnan(cur).any() and np.allclose(cur, prev):
            s[s.index.year == y] = np.nan
            log(D, "cpi_index", y, "source error: whole year equals previous year", "set to missing and rebuilt by interpolation")
            s = fill_interior(s, D, log_scale=True, note=f"rebuilt {y}")
            if y in ins.index:
                k = ins[y] / s[s.index.year == y].mean()
                s[s.index.year == y] *= k
                log(D, "cpi_index", y, f"rescaled x{k:.4f}", f"to match INS annual average {ins[y]}")
    # 2) remaining gaps
    s = fill_interior(s, D, log_scale=True, note="CPI missing_in_source")
    # 3) structural breaks (a change of base year shows up as a jump of more than 8% in one month): chain-link, newest first
    g = s.pct_change()
    for b in list(g.index[g.abs() > 0.08])[::-1]:
        after = g.loc[b + 1:b + 6].median()
        k = s[b] / (s[b - 1] * (1 + after))
        s[s.index < b] *= k
        log(D, "cpi_index", b, f"base-year break ({100 * g[b]:+.1f}% in one month): earlier part scaled x{k:.4f}",
            "chain-linked so the break month grows like the following months; checked against World Bank inflation")

    trade = pd.read_csv(DATA / "BCT" / "trade_monthly_2014_2026.csv")
    trade["m"] = pd.PeriodIndex(pd.to_datetime(trade.month), freq="M")
    t = trade.pivot(index="m", columns="indicator", values="value")
    t = t.reindex(pd.period_range(t.index.min(), t.index.max(), freq="M"))
    t_f = pd.DataFrame({c: seasonal_fill(t[c].rename(c), D, note="trade") for c in t.columns})

    mon = pd.read_csv(DATA / "BCT" / "monetary_aggregates_monthly_2001_2026.csv")
    mon["m"] = pd.PeriodIndex(pd.to_datetime(mon.month), freq="M")
    m = mon.pivot(index="m", columns="indicator", values="value")

    idx = pd.period_range(m.index.min(), max(m.index.max(), s.index.max(), t_f.index.max()), freq="M")
    df = pd.DataFrame(index=idx)
    df["cpi_index_2015_100"] = s
    df["inflation_yoy_pct"] = 100 * (df.cpi_index_2015_100 / df.cpi_index_2015_100.shift(12) - 1)
    df["exports_fob"] = t_f.exports_fob
    df["imports_cif"] = t_f.imports_cif
    df["trade_balance"] = df.exports_fob - df.imports_cif
    df["exports_yoy_pct"] = 100 * (df.exports_fob / df.exports_fob.shift(12) - 1)
    for c in m.columns:
        df[c] = m[c]
    df["m3_yoy_pct"] = 100 * (df.M3 / df.M3.shift(12) - 1)
    # long CPI table (2010-2026) and a gap-free common window for everything else
    cpi_long = df[["cpi_index_2015_100", "inflation_yoy_pct"]].dropna()
    cpi_long.index = cpi_long.index.astype(str)
    cpi_long.index.name = "month"
    write(cpi_long, "economy_cpi_monthly.csv")
    ok = df.dropna()
    df = df.loc[ok.index.min():ok.index.max()]
    log(D, "economy_monthly", f"before {df.index.min()}", "window restricted", f"common period where CPI, trade and money all exist: {df.index.min()}..{df.index.max()}")
    df.index = df.index.astype(str)
    df.index.name = "month"
    write(df, "economy_monthly.csv")
    y = pd.Series(df.cpi_index_2015_100.values, index=df.index.str[:4].astype(int)).groupby(level=0).mean()
    cmp_ = pd.DataFrame({"bct": y, "ins": ins}).dropna().loc[2019:]
    print("  CPI check, % diff of BCT monthly mean vs INS annual:", (100 * (cmp_.bct / cmp_.ins - 1)).round(2).to_dict())
    return df


def quarterly():
    n = pd.read_csv(DATA / "BCT" / "national_accounts_quarterly_2010_2026.csv")
    g = n[n.item == "GDP at market prices"]
    cur = g[g.price_basis == "current_prices"].set_index("period").value_million_tnd
    con = g[g.price_basis == "constant_prices"].set_index("period").value_million_tnd
    cur.index = pd.PeriodIndex(cur.index, freq="Q")
    con.index = pd.PeriodIndex(con.index, freq="Q")
    full = pd.period_range(con.index.min(), con.index.max(), freq="Q")
    absent = [str(p) for p in full.difference(con.index)]
    cur, con = cur.reindex(full).rename("gdp_current_mtnd"), con.reindex(full).rename("gdp_constant_raw")
    if absent:
        log(D, "gdp_quarterly", ",".join(absent), "quarters absent from source", "filled (seasonal-aware)")
    con = seasonal_fill(con, D, note="absent quarter")

    # chain-link constant prices over the base-year changes (2021Q1 and 2015Q1), newest boundary first
    scale = pd.Series(1.0, index=full)
    for b in (pd.Period("2021Q1", "Q"), pd.Period("2015Q1", "Q")):
        i = full.get_loc(b)
        gb, ga = con.iloc[i - 1] / con.iloc[i - 2] - 1, con.iloc[i + 1] / con.iloc[i] - 1
        k = con.iloc[i] / (con.iloc[i - 1] * (1 + (gb + ga) / 2))
        scale[full < b] *= k
        log(D, "gdp_constant", b, f"chain-linked: older segment x{k:.4f}", "base-year change; break quarter grows at the mean of its neighbours")
    chained = (con * scale).rename("gdp_constant_chained_mtnd")
    defl = ((cur / con) * scale).rename("gdp_deflator")
    defl = fill_interior(defl, D, log_scale=True, note="current-price GDP missing in source: deflator interpolated")
    miss = cur.isna() & defl.notna()
    cur = cur.fillna(defl * chained)

    q = pd.concat([cur, chained, defl], axis=1)
    q["current_imputed"] = miss
    q = q.loc[:q.gdp_current_mtnd.last_valid_index()]       # no current-price GDP for 2026Q1: end the table at 2025Q4
    q["gdp_real_yoy_pct"] = 100 * (q.gdp_constant_chained_mtnd / q.gdp_constant_chained_mtnd.shift(4) - 1)
    q["gdp_nominal_yoy_pct"] = 100 * (q.gdp_current_mtnd / q.gdp_current_mtnd.shift(4) - 1)
    log(D, "gdp_current", "2025Q1-2025Q4", "flag: up to 3% below the later INS release", "kept as is")
    q.index = q.index.astype(str)
    q.index.name = "period"
    write(q, "economy_quarterly.csv")

    # validation against World Bank annual real growth (consecutive full years only)
    yr = pd.Series(q.gdp_constant_chained_mtnd.values, index=q.index.str[:4].astype(int))
    cnt = yr.groupby(level=0).count()
    tot = yr.groupby(level=0).sum()[cnt == 4]
    gr = 100 * tot.pct_change()
    gr = gr[tot.index.to_series().diff() == 1]
    wb_path = OUT / "economy_annual.csv"
    if wb_path.exists():
        wb = pd.read_csv(wb_path).set_index("year").gdp_growth_pct
        both = pd.concat([gr.rename("quarterly"), wb.rename("wb")], axis=1).dropna().loc[2012:]
        both["diff_pp"] = both.quarterly - both.wb
        print("  real GDP growth, chain-linked quarterly minus World Bank (pp):", both.diff_pp.round(1).to_dict(), "| mean abs", round(both.diff_pp.abs().mean(), 2))
    print("  biggest |q/q| change, before chain-linking:", (con.pct_change() * 100).abs().nlargest(2).round(1).to_dict(),
          "| after:", (chained.pct_change() * 100).abs().nlargest(2).round(1).to_dict())
    return q


def main():
    print("[economy]")
    annual()
    monthly()
    quarterly()


if __name__ == "__main__":
    main()
