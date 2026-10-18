"""Exports everything the web page needs into frontend/data/data.js (one JavaScript file, so the page works when opened by double-click).
Reads the preprocessed tables of step 1 (data/processed) and the results of step 2 (step_02_forecasting/results). Run it again after step 1 or 2 change:
    python frontend/build_data.py
"""
import json
import datetime
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC, RES = ROOT / "data" / "processed", ROOT / "step_02_forecasting" / "results"
OUT = Path(__file__).resolve().parent / "data" / "data.js"

SERIES = {"premiums_total": "Total premiums", "premiums_life": "Life premiums", "premiums_auto": "Motor premiums", "premiums_health": "Health premiums", "claims_paid_total": "Total paid claims"}
MODELS = {"ensemble": "Ensemble", "random_forest": "Random Forest", "gbm": "Gradient boosting", "lstm": "LSTM", "arima": "ARIMA", "prophet": "Prophet"}


def csv(name, folder=PROC):
    return pd.read_csv(folder / f"{name}.csv")


def cols(df, names, rounding=3):
    """{column: [values]} with NaN as null, so the page can draw gaps."""
    out = {}
    for n in names:
        v = df[n]
        out[n] = [None if pd.isna(x) else (round(float(x), rounding) if not isinstance(x, str) else x) for x in v]
    return out


def main():
    t = csv("modeling_table").set_index("year")
    ins = csv("insurance_annual").set_index("year")
    last = int(t.index.max())
    d = {"meta": {"last_year": last, "built": datetime.date.today().isoformat(), "series": SERIES, "models": MODELS}}

    keep = ["premiums_total", "premiums_life", "premiums_auto", "premiums_health", "premiums_transport", "premiums_fire_and_misc_combined",
            "claims_paid_total", "claims_paid_life", "claims_paid_auto", "claims_paid_health"]
    d["insurance"] = {"year": [int(y) for y in ins.index], **cols(ins.reset_index(), keep, 2),
                      **cols(t.reset_index(), ["loss_ratio_pct", "penetration_pct_gdp", "life_share_pct", "auto_share_pct", "health_share_pct", "density_tnd_per_capita"], 3)}
    c = csv("insurance_companies")
    top = c[(c.branch_code == "ALL_BRANCHES") & (c.measure == "premiums_total_direct_plus_acceptances") & (c.year == c.year.max())].sort_values("value_mtnd", ascending=False).head(10)
    d["insurance"]["companies"] = {"year": int(c.year.max()), "rows": [{"name": r.company, "value": round(r.value_mtnd, 1)} for r in top.itertuples()]}

    e = csv("economy_annual")
    d["economy"] = {"annual": cols(e, ["year", "gdp_growth_pct", "inflation_pct", "tnd_per_usd", "private_credit_pct_gdp", "exports_pct_gdp", "imports_pct_gdp",
                                       "current_account_usd_bn", "broad_money_growth_pct"], 3),
                    "quarterly": cols(csv("economy_quarterly"), ["period", "gdp_real_yoy_pct"], 2), "monthly": cols(csv("economy_monthly"), ["month", "inflation_yoy_pct"], 2)}
    lab = csv("labour_annual")
    d["labour"] = {"annual": cols(lab, ["year", "unemployment_rate", "employed_thousand", "employment_rate_proxy", "employed_source"], 3),
                   "quarterly": cols(csv("labour_quarterly"), ["period", "unemployment_rate_total", "unemployment_rate_male", "unemployment_rate_female",
                                                                  "higher_ed_graduates_unemployment_rate_total"], 2)}
    ag, cr = csv("agriculture_annual"), csv("agriculture_crops")
    d["agriculture"] = {"annual": cols(ag, ["year", "crops_index_2014_16", "livestock_index_2014_16", "food_index_2014_16", "agri_value_added_pct_gdp", "agri_employment_pct_total"], 2),
                        "crops": {k: cols(g, ["year", "production_t", "yield_kg_per_ha", "area_harvested_ha"], 1) for k, g in cr.groupby("crop")}}
    cl = csv("climate_annual")
    d["climate"] = {"annual": cols(cl, ["year", "rainfall_mm", "heat_days_ge35c", "heavy_rain_days_ge20mm", "dry_spell_max_days", "temp_mean_c", "max_daily_rain_mm"], 2),
                    "monthly": cols(csv("climate_monthly"), ["month", "rainfall_mm"], 1)}

    f, b, m, ch = csv("forecasts", RES), csv("backtest", RES), csv("metrics", RES), csv("champions", RES)
    b = b[b.step == 1]
    d["forecast"] = {
        "history": {s: {"year": [int(y) for y in t.index], "value": [round(float(v), 1) for v in t[s]]} for s in SERIES},
        "forecasts": {mod: {s: [{"year": int(r.year), "value": round(r.forecast, 1), "low": round(r.lower_80, 1), "high": round(r.upper_80, 1)} for r in g.itertuples()]
                            for s, g in fm.groupby("series")} for mod, fm in f.groupby("model")},
        "backtest": {mod: {s: [{"year": int(r.year), "value": round(r.forecast, 1)} for r in g.sort_values("year").itertuples()] for s, g in bm.groupby("series")} for mod, bm in b.groupby("model")},
        "metrics": {s: {mod: {k: (None if pd.isna(v) else round(float(v), 3)) for k, v in row.items()} for mod, row in g[g.step == "ALL"].set_index("model")[["MAPE_%", "R2", "MASE", "CVRMSE_%", "MAE", "bias"]].iterrows()}
                    for s, g in m.groupby("series")},
        "by_horizon": {mod: {str(k): round(float(v), 2) for k, v in g[(g.step != "ALL") & (g.series != "ALL")].groupby("step")["MAPE_%"].mean().items()} for mod, g in m.groupby("model")},
        "champions": {r.series: {"model": r.champion, "mape": r._3} for r in ch.itertuples()},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("window.DATA = " + json.dumps(d, separators=(",", ":"), allow_nan=False) + ";\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}  ({OUT.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
