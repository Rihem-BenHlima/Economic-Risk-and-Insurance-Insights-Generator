"""Join the domain outputs into one yearly modelling table (2003-2024): data/processed/modeling_table.csv.

Insurance columns come first (targets); economy, labour, agriculture and climate follow (predictors / context).
Also adds real premium growth (deflated by World Bank inflation) and premiums relative to GDP.
"""
import pandas as pd
from common import OUT, write, log

INSURANCE = ["premiums_total", "premiums_life", "premiums_nonlife", "premiums_auto", "premiums_health", "premiums_transport",
             "premiums_fire_and_misc_combined", "premiums_agri", "claims_paid_total", "claims_paid_life", "claims_paid_nonlife",
             "claims_paid_auto", "claims_paid_health", "tech_provisions_total", "tech_result_total", "own_funds_total",
             "net_result", "premiums_total_growth_pct", "loss_ratio_pct", "loss_ratio_auto_pct", "loss_ratio_health_pct",
             "life_share_pct", "auto_share_pct", "health_share_pct", "agri_share_pct"]


def main():
    print("[modelling table]")
    ins = pd.read_csv(OUT / "insurance_annual.csv").set_index("year")
    ins = ins[[c for c in INSURANCE if c in ins.columns]]
    eco = pd.read_csv(OUT / "economy_annual.csv").set_index("year")
    lab = pd.read_csv(OUT / "labour_annual.csv").set_index("year")[["unemployment_rate", "employed_thousand"]]
    agr = pd.read_csv(OUT / "agriculture_annual.csv").set_index("year")[["agri_value_added_pct_gdp", "agri_employment_pct_total", "crops_index_2014_16",
                                                                            "livestock_index_2014_16", "food_index_2014_16"]]
    cli = pd.read_csv(OUT / "climate_annual.csv").set_index("year")[["rainfall_mm", "heat_days_ge35c", "temp_mean_c", "dry_spell_max_days"]].rename(columns={"temp_mean_c": "tunis_temp_mean_c"})
    t = ins.join(eco, how="left").join(lab, how="left").join(agr, how="left").join(cli, how="left").loc[2003:2024]
    t["premiums_total_real_growth_pct"] = 100 * ((1 + t.premiums_total.pct_change()) / (1 + t.inflation_pct / 100) - 1)
    t["penetration_pct_gdp"] = 100 * t.premiums_total / (t.gdp_usd * t.tnd_per_usd / 1e6)
    t["density_tnd_per_capita"] = t.premiums_total * 1e6 / t.population_national
    t.index.name = "year"
    write(t, "modeling_table.csv")
    miss = t.isna().sum()
    print("  columns with missing years:", {c: int(n) for c, n in miss[miss > 0].items()})
    print("  penetration (% GDP) 2024:", round(t.penetration_pct_gdp.iloc[-1], 2), "| density (TND/person) 2024:", round(t.density_tnd_per_capita.iloc[-1], 1))
    src = pd.read_csv(OUT.parent / "CGA" / "tunisia_insurance_annual.csv").set_index("year")
    cmp_ = pd.concat([t.penetration_pct_gdp, src.insurance_penetration_pct_gdp], axis=1).dropna().loc[2016:]
    cmp_.columns = ["computed", "CGA"]
    print("  penetration, computed vs CGA (%):", cmp_.round(2).T.to_dict("list") if len(cmp_) < 1 else {int(i): (round(r.computed, 2), round(r.CGA, 2)) for i, r in cmp_.iterrows()})


if __name__ == "__main__":
    main()
