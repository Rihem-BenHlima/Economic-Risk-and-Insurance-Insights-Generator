"""Climate domain: daily weather for Tunis (36.80N, 10.17E), 2003-2025.

Sources
  * data/open-meteo/weather_tunis_daily.csv                            2020-2025 (the supplied file)
  * data/open-meteo/weather_tunis_daily_openmeteo_download_2003_2025.csv  2003-2025, downloaded from the Open-Meteo archive API
Treatment: the download is validated against the supplied file on 2020-2025 (rainfall must be identical, temperatures within
0.5 C on average); then 2003-2019 comes from the download and 2020-2025 stays as supplied. The soil-temperature column exists
only in the supplied file and is dropped (not used).
Outputs: climate_daily.csv (2003-2025), climate_monthly.csv, climate_annual.csv
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import DATA, log, write

D = "climate"
COLS = ["precip_mm", "temp_mean_c", "temp_max_c", "temp_min_c", "wind_max_kmh"]


def load():
    old = pd.read_csv(DATA / "open-meteo" / "weather_tunis_daily.csv", parse_dates=["date"]).set_index("date")
    new = pd.read_csv(DATA / "open-meteo" / "weather_tunis_daily_openmeteo_download_2003_2025.csv", parse_dates=["date"]).set_index("date")
    ov = new.loc[old.index.min():old.index.max(), COLS]
    rain_diff = (ov.precip_mm - old.precip_mm.reindex(ov.index)).abs().max()
    temp_diff = max((ov[c] - old[c].reindex(ov.index)).abs().mean() for c in ("temp_mean_c", "temp_max_c", "temp_min_c"))
    print(f"  validation on 2020-2025: max rainfall difference {rain_diff:.2f} mm, mean temperature difference {temp_diff:.3f} C")
    if rain_diff > 0.2 or temp_diff > 0.5:
        raise SystemExit("downloaded history does not match the supplied file: not splicing")
    log(D, "weather_daily", "2003-01-01..2019-12-31", "filled from Open-Meteo archive download",
        f"validated on 2020-2025: max rainfall difference {rain_diff:.2f} mm, mean temperature difference {temp_diff:.3f} C")
    log(D, "soil_temp_7_28cm_c", "all", "dropped column", "exists only in the supplied 2020-2025 file")
    w = pd.concat([new.loc[:"2019-12-31", COLS], old[COLS]]).sort_index()
    full = pd.date_range(w.index.min(), w.index.max(), freq="D")
    print(f"  daily calendar {w.index.min().date()}..{w.index.max().date()}: {len(w)} days, missing {len(full.difference(w.index))}")
    w = w.reindex(full)
    w.index.name = "date"
    return w


def longest_dry(s):
    best = cur = 0
    for v in (s < 1).tolist():
        cur = cur + 1 if v else 0
        best = max(best, cur)
    return best


def agg(g):
    return pd.Series({
        "rainfall_mm": g.precip_mm.sum(), "rain_days_ge1mm": int((g.precip_mm >= 1).sum()),
        "heavy_rain_days_ge20mm": int((g.precip_mm >= 20).sum()), "max_daily_rain_mm": g.precip_mm.max(),
        "temp_mean_c": g.temp_mean_c.mean(), "temp_max_c": g.temp_max_c.max(), "heat_days_ge35c": int((g.temp_max_c >= 35).sum()),
        "dry_spell_max_days": longest_dry(g.precip_mm)})


def main():
    print("[climate]")
    w = load()
    bad = ~((w.temp_min_c <= w.temp_mean_c) & (w.temp_mean_c <= w.temp_max_c))
    print(f"  rows where min <= mean <= max fails: {int(bad.sum())}; negative rain: {int((w.precip_mm < 0).sum())}")
    write(w, "climate_daily.csv")
    m = w.groupby(w.index.to_period("M")).apply(agg).round(2)
    m.index = m.index.astype(str)
    m.index.name = "month"
    write(m, "climate_monthly.csv")
    a = w.groupby(w.index.year).apply(agg).round(2)
    a.index.name = "year"
    write(a, "climate_annual.csv")
    print(f"  annual: {a.index.min()}-{a.index.max()}, missing cells {int(a.isna().sum().sum())}; driest year {int(a.rainfall_mm.idxmin())} ({a.rainfall_mm.min():.0f} mm), wettest {int(a.rainfall_mm.idxmax())} ({a.rainfall_mm.max():.0f} mm)")


if __name__ == "__main__":
    main()
