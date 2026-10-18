"""The inputs of every model, built in ONE place from the preprocessed tables in step_02_forecasting/data/.

A model forecasts one insurance series. Its inputs are
    own      the series' own growth of the last two years (computed from the training years only, so nothing from the future is used)
    groups   outside variables, in four groups by source of data:  economy, labour, agriculture, climate
Which groups a model uses is decided in ONE place (INPUT_GROUPS below), by the ablation test (ablation.py -> results/ablation.csv), which scores
every group alone and together on the same backtest rows.

Every outside variable is a growth or a change, never a trending level, so a model cannot learn "time" from it.
The forecast stays yearly: the monthly climate file only feeds four yearly seasonal features.
"""
from pathlib import Path
import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parent / "data"

GROUPS = {
    "economy": ["gdp_growth", "inflation", "fx_change", "credit_change", "money_growth", "current_account", "investment", "consumption", "trade_balance"],
    "labour": ["unemployment_rate", "unemployment_change", "employed_growth", "employment_rate"],
    "agriculture": ["crops_index", "crops_growth", "livestock_growth", "food_growth", "agri_va_pct", "agri_va_change", "agri_emp_change"],
    "climate": ["rainfall", "rain_days", "heavy_rain_days", "max_daily_rain", "dry_spell", "heat_days", "temp_change", "temp_max",
                "autumn_rain", "winter_rain", "summer_heat_days", "wettest_month"],
}
CORE = {"economy": ["gdp_growth", "inflation"], "labour": ["unemployment_change", "employed_growth"],
        "agriculture": ["crops_growth", "agri_va_pct"], "climate": ["rainfall", "heat_days"]}      # the two regressors Prophet gets from a group
OWN = ["own_growth", "own_growth_prev"]

INPUT_GROUPS = ["labour"]  # groups the tree models and the LSTM use besides the series' own growth: best mean MAPE for gbm and random_forest in results/ablation.csv
PROPHET_GROUP = None       # group whose two core variables Prophet uses as regressors: None = pure trend, which beat every group in results/ablation.csv


def _read(name):
    return pd.read_csv(DATA / name).set_index("year")


def outside():
    """All outside variables of all four groups, one row per year."""
    t, c, m, lab = _read("modeling_table.csv"), _read("climate_annual.csv"), pd.read_csv(DATA / "climate_monthly.csv"), _read("labour_annual.csv")
    e = pd.DataFrame(index=t.index)
    e["gdp_growth"] = t.gdp_growth_pct
    e["inflation"] = t.inflation_pct
    e["fx_change"] = 100 * np.log(t.tnd_per_usd).diff()                              # dinar depreciation against the USD, %
    e["credit_change"] = t.private_credit_pct_gdp.diff()                             # change in private credit / GDP, points
    e["money_growth"] = t.broad_money_growth_pct
    e["current_account"] = 100 * t.current_account_usd_bn * 1e9 / t.gdp_usd          # % of GDP
    e["investment"] = t.investment_pct_gdp
    e["consumption"] = t.household_consumption_pct_gdp
    e["trade_balance"] = t.exports_pct_gdp - t.imports_pct_gdp                       # % of GDP
    e["unemployment_rate"] = lab.unemployment_rate
    e["unemployment_change"] = lab.unemployment_rate.diff()
    e["employed_growth"] = 100 * lab.employed_thousand.pct_change()                  # employment before 2011 and in 2024 is estimated
    e["employment_rate"] = 100 * lab.employment_rate_proxy
    e["crops_index"] = t.crops_index_2014_16                                         # low = bad harvest
    e["crops_growth"] = 100 * t.crops_index_2014_16.pct_change()
    e["livestock_growth"] = 100 * t.livestock_index_2014_16.pct_change()
    e["food_growth"] = 100 * t.food_index_2014_16.pct_change()
    e["agri_va_pct"] = t.agri_value_added_pct_gdp
    e["agri_va_change"] = t.agri_value_added_pct_gdp.diff()
    e["agri_emp_change"] = t.agri_employment_pct_total.diff()
    e["rainfall"] = c.rainfall_mm
    e["rain_days"] = c.rain_days_ge1mm
    e["heavy_rain_days"] = c.heavy_rain_days_ge20mm                                  # days >= 20 mm: floods
    e["max_daily_rain"] = c.max_daily_rain_mm
    e["dry_spell"] = c.dry_spell_max_days                                            # longest run of days under 1 mm: drought
    e["heat_days"] = c.heat_days_ge35c
    e["temp_change"] = c.temp_mean_c.diff()
    e["temp_max"] = c.temp_max_c
    m["year"], m["month_no"] = m.month.str[:4].astype(int), m.month.str[5:].astype(int)
    e["autumn_rain"] = m[m.month_no.isin([9, 10, 11])].groupby("year").rainfall_mm.sum()        # Sep-Nov: the flood season
    e["winter_rain"] = m[m.month_no.isin([12, 1, 2])].groupby("year").rainfall_mm.sum()
    e["summer_heat_days"] = m[m.month_no.isin([6, 7, 8])].groupby("year").heat_days_ge35c.sum()
    e["wettest_month"] = m.groupby("year").rainfall_mm.max()
    return e


_OUTSIDE = None


def columns(groups=None):
    """Input names of a model: the series' own growth plus the variables of the given groups (default: INPUT_GROUPS)."""
    groups = INPUT_GROUPS if groups is None else groups
    return OWN + [c for g in groups for c in GROUPS[g]]


def features(train, groups=None):
    """Input table indexed by year: the series' own growth of that year and of the year before (from `train` only) joined with the outside variables."""
    global _OUTSIDE
    if _OUTSIDE is None:
        _OUTSIDE = outside()
    g = np.log(train).diff().dropna()
    own = pd.DataFrame({"own_growth": g, "own_growth_prev": g.shift(1)}).dropna()
    cols = columns(groups)[len(OWN):]
    return own.join(_OUTSIDE[cols], how="left") if cols else own
