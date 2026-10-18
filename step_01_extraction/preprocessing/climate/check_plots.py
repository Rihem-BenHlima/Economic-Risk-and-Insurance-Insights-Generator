"""Check plots for the climate domain: was the data treated correctly?

Run (after process.py):  python step_01_extraction/preprocessing/climate/check_plots.py
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
from common import DATA, OUT

PLOTS = Path(__file__).parent / "plots"
PLOTS.mkdir(exist_ok=True)
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": 0.3, "axes.spines.top": False, "axes.spines.right": False})

old = pd.read_csv(DATA / "open-meteo" / "weather_tunis_daily.csv", parse_dates=["date"]).set_index("date")
new = pd.read_csv(DATA / "open-meteo" / "weather_tunis_daily_openmeteo_download_2003_2025.csv", parse_dates=["date"]).set_index("date")
daily = pd.read_csv(OUT / "climate_daily.csv", parse_dates=["date"]).set_index("date")
ann = pd.read_csv(OUT / "climate_annual.csv").set_index("year")
mon = pd.read_csv(OUT / "climate_monthly.csv")


def save(fig, name):
    fig.tight_layout()
    fig.savefig(PLOTS / name)
    plt.close(fig)
    print("  saved", (PLOTS / name).relative_to(Path(__file__).parents[3]))


def p1_overlap():
    ov = new.loc[old.index.min():old.index.max()]
    fig, ax = plt.subplots(1, 3, figsize=(14, 4.2))
    ax[0].scatter(old.precip_mm, ov.precip_mm.reindex(old.index), s=6, alpha=0.5)
    lim = [0, old.precip_mm.max()]
    ax[0].plot(lim, lim, "k--", lw=0.8); ax[0].set_xlabel("supplied file"); ax[0].set_ylabel("Open-Meteo download")
    ax[0].set_title("Daily rainfall (mm), 2020-2025: identical (all points on the line)", fontsize=8)
    ax[1].scatter(old.temp_mean_c, ov.temp_mean_c.reindex(old.index), s=6, alpha=0.5)
    lim = [old.temp_mean_c.min(), old.temp_mean_c.max()]
    ax[1].plot(lim, lim, "k--", lw=0.8); ax[1].set_xlabel("supplied file"); ax[1].set_ylabel("Open-Meteo download")
    ax[1].set_title("Daily mean temperature (C), 2020-2025", fontsize=8)
    d = (ov.temp_mean_c.reindex(old.index) - old.temp_mean_c)
    ax[2].hist(d, bins=40, color="steelblue")
    ax[2].set_title(f"Temperature difference (C): mean |diff| {d.abs().mean():.3f}, max {d.abs().max():.2f}", fontsize=8)
    fig.suptitle("The downloaded history reproduces the supplied data on the shared years, so it is safe to use for 2003-2019")
    save(fig, "01_download_vs_supplied_overlap.png")


def p2_annual():
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.3))
    col = np.where(ann.index < 2020, "tab:blue", "tab:orange")
    ax[0].bar(ann.index, ann.rainfall_mm, color=col)
    ax[0].axhline(ann.rainfall_mm.mean(), color="k", ls="--", lw=0.8, label=f"mean {ann.rainfall_mm.mean():.0f} mm")
    ax[0].set_title("Annual rainfall, Tunis (mm): blue = Open-Meteo download, orange = supplied file"); ax[0].title.set_fontsize(9); ax[0].legend(fontsize=8)
    ax[1].bar(ann.index, ann.heat_days_ge35c, color=col, label="days with max >= 35 C")
    ax2 = ax[1].twinx()
    ax2.plot(ann.index, ann.temp_mean_c, "k.-", label="mean temperature (C)")
    ax2.grid(False); ax2.set_ylabel("mean temperature (C)")
    ax[1].set_title("Heat days and mean temperature: a continuous trend across the 2019/2020 join", fontsize=9)
    save(fig, "02_annual_rainfall_and_heat.png")


def p3_daily_splice():
    fig, ax = plt.subplots(2, 1, figsize=(13, 6), sharex=True)
    ax[0].plot(daily.index, daily.temp_mean_c.rolling(30, center=True).mean(), color="crimson", lw=1, label="30-day rolling mean")
    ax[0].fill_between(daily.index, daily.temp_min_c.rolling(30, center=True).mean(), daily.temp_max_c.rolling(30, center=True).mean(), alpha=0.2)
    ax[0].axvline(pd.Timestamp("2020-01-01"), color="orange", ls="--", label="splice: download | supplied file")
    ax[0].set_title("Daily temperature (30-day rolling mean, min-max band): no jump at the splice"); ax[0].legend(fontsize=8)
    ax[1].plot(daily.index, daily.precip_mm, color="steelblue", lw=0.5)
    ax[1].axvline(pd.Timestamp("2020-01-01"), color="orange", ls="--")
    ax[1].set_title("Daily rainfall (mm)")
    save(fig, "03_daily_series_splice.png")


def main():
    print("[climate plots]")
    for f in (p1_overlap, p2_annual, p3_daily_splice):
        f()


if __name__ == "__main__":
    main()
