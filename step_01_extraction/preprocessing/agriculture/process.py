"""Agriculture domain: FAOSTAT context + production indices (2012-2024), crop production (2012-2024), World Bank (long history).

Treatments (all logged)
  * series the World Bank also publishes (crop / livestock / food production indices, land, agriculture's share of GDP and of
    employment) are extended back to 2003 from the World Bank, after checking they agree with FAO on 2012-2024
  * series that exist only from 2012 (cereals, olives, meat, milk, eggs, temperature anomaly, food CPI ...) cannot be extended
    without inventing data: they go to a separate table that is complete within 2012-2024
Outputs: agriculture_annual.csv (2003-2024, no gaps), agriculture_context_2012_2024.csv (no gaps), agriculture_crops.csv
"""
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import DATA, log, splice, write, drop_unusable

D = "agriculture"
SPLICE = {  # FAO column -> (World Bank code, scale, file it comes from)
    "crops_index_2014_16": ("AG.PRD.CROP.XD", 1.0, "idx"),
    "livestock_index_2014_16": ("AG.PRD.LVSK.XD", 1.0, "idx"),
    "food_index_2014_16": ("AG.PRD.FOOD.XD", 1.0, "idx"),
    "agri_value_added_pct_gdp": ("NV.AGR.TOTL.ZS", 1.0, "ctx"),
    "agri_employment_pct_total": ("SL.AGR.EMPL.ZS", 1.0, "ctx"),
    "agri_land_1000ha": ("AG.LND.AGRI.K2", 0.1, "ctx"),
    "arable_land_1000ha": ("AG.LND.ARBL.HA", 1e-3, "ctx"),
}


def crops():
    c = pd.read_csv(DATA / "FAOSTAT" / "agri_crops_annual.csv").sort_values(["crop", "year"])
    bad = ((1000 * c.production_t / c.area_harvested_ha - c.yield_kg_per_ha).abs() / c.yield_kg_per_ha) > 0.02
    print(f"  yield identity (yield = production/area): {int(bad.sum())} of {len(c)} rows differ by more than 2%")
    c["production_change_pct"] = c.groupby("crop").production_t.pct_change() * 100
    for _, r in c[c.production_change_pct.abs() > 50].iterrows():
        log(D, f"{r.crop}_production", r.year, f"flag: change {r.production_change_pct:+.0f}%", "weather-driven swing, kept")
    n = c.groupby("crop").year.nunique()
    print("  crops:", n.to_dict(), "(all years 2012-2024 present)" if (n == 13).all() else "")
    write(c.set_index(["crop", "year"]), "agriculture_crops.csv")


def annual():
    ctx = pd.read_csv(DATA / "FAOSTAT" / "agri_context_annual.csv").set_index("year")
    idx = pd.read_csv(DATA / "FAOSTAT" / "agri_production_indices.csv").set_index("year")
    src = {"ctx": ctx, "idx": idx}
    wb = pd.read_csv(DATA / "API_TUN_DS2_en_csv_v2_17970" / "API_TUN_DS2_en_csv_v2_17970.csv", skiprows=4, encoding="utf-8-sig").set_index("Indicator Code")
    yrs = [c for c in wb.columns if str(c).isdigit()]
    full = pd.DataFrame(index=range(2003, 2025))
    for col, (code, k, which) in SPLICE.items():
        second = wb.loc[code, yrs].astype(float) * k
        second.index = second.index.astype(int)
        s, filled = splice(src[which][col].reindex(range(2003, 2025)), second, D, col, f"World Bank {code}")
        full[col] = s
    full.index.name = "year"
    full["cereals_index_yoy_pct"] = float("nan")
    full = full.drop(columns="cereals_index_yoy_pct")
    full["crops_index_yoy_pct"] = 100 * full.crops_index_2014_16.pct_change()
    full["livestock_index_yoy_pct"] = 100 * full.livestock_index_2014_16.pct_change()
    full = full.dropna(axis=1, how="any") if full.drop(columns=["crops_index_yoy_pct", "livestock_index_yoy_pct"]).isna().any().any() else full
    write(full, "agriculture_annual.csv")
    print(f"  agriculture_annual: {full.index.min()}-{full.index.max()}, missing cells {int(full.isna().sum().sum()) - 2}  (the 2 are the first year's growth rates)")

    rest_cols = [c for c in list(ctx.columns) + list(idx.columns) if c not in SPLICE]
    rest = pd.concat([ctx, idx], axis=1)[rest_cols].loc[2012:2024]
    rest = rest.loc[:, ~rest.columns.duplicated()]
    rest, _ = drop_unusable(rest, D, min_coverage=0.9, max_trailing_gap=0)   # a gap-free table: columns ending before 2024 go
    for c in rest.columns:
        log(D, c, "2003-2011", "kept only for 2012-2024", "no second source to extend it; stored in agriculture_context_2012_2024.csv, not used in 2003-2024 models")
    write(rest, "agriculture_context_2012_2024.csv")
    print(f"  agriculture_context_2012_2024: {rest.shape}, missing cells {int(rest.isna().sum().sum())}")
    return full, rest


def main():
    print("[agriculture]")
    crops()
    annual()


if __name__ == "__main__":
    main()
