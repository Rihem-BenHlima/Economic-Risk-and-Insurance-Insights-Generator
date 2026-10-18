"""Check plot for the agriculture domain: was the data treated correctly?

One plot: the five series that enter the modelling table, extended back to 2003 from the World Bank, with the mean difference
between the two sources on their shared years in each title. (Other agriculture series are context only and were not changed.)
Run (after process.py):  python step_01_extraction/preprocessing/agriculture/check_plots.py
"""
import sys
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import DATA, OUT

PLOTS = Path(__file__).parent / "plots"
PLOTS.mkdir(exist_ok=True)
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": 0.3, "axes.spines.top": False, "axes.spines.right": False})

ctx = pd.read_csv(DATA / "FAOSTAT" / "agri_context_annual.csv").set_index("year")
idx = pd.read_csv(DATA / "FAOSTAT" / "agri_production_indices.csv").set_index("year")
fao = pd.concat([ctx, idx], axis=1)
pro = pd.read_csv(OUT / "agriculture_annual.csv").set_index("year")
WB_CODES = {"crops_index_2014_16": "AG.PRD.CROP.XD", "livestock_index_2014_16": "AG.PRD.LVSK.XD", "food_index_2014_16": "AG.PRD.FOOD.XD",
            "agri_value_added_pct_gdp": "NV.AGR.TOTL.ZS", "agri_employment_pct_total": "SL.AGR.EMPL.ZS"}


def main():
    print("[agriculture plots]")
    wb = pd.read_csv(DATA / "API_TUN_DS2_en_csv_v2_17970" / "API_TUN_DS2_en_csv_v2_17970.csv", skiprows=4, encoding="utf-8-sig").set_index("Indicator Code")
    yrs = [c for c in wb.columns if str(c).isdigit()]
    fig, ax = plt.subplots(2, 3, figsize=(14, 6.5), sharex=True)
    for a, (c, code) in zip(ax.ravel(), WB_CODES.items()):
        b = wb.loc[code, yrs].astype(float)
        b.index = b.index.astype(int)
        ov = pd.concat([fao[c], b], axis=1, keys=["fao", "wb"]).dropna()
        err = 100 * (ov.wb - ov.fao).abs().mean() / ov.fao.abs().mean()
        a.plot(pro.index, pro[c], "-", color="crimson", label="processed")
        a.plot(fao.index, fao[c], "o", color="black", ms=4, label="FAO (original)")
        filled = pro[c].notna() & fao[c].reindex(pro.index).isna()
        a.plot(pro.index[filled], pro[c][filled], "s", mfc="none", color="blue", ms=6, label="filled from World Bank")
        a.set_title(f"{c}\nWorld Bank vs FAO on 2012-2024: mean difference {err:.1f}%", fontsize=9)
    ax.ravel()[0].legend(fontsize=7)
    ax.ravel()[-1].axis("off")
    fig.suptitle("Agriculture series extended back to 2003 from the World Bank (black dots under the red line = the two sources agree)")
    fig.tight_layout()
    fig.savefig(PLOTS / "01_extended_series_vs_fao.png")
    plt.close(fig)
    print("  saved agriculture/plots/01_extended_series_vs_fao.png")


if __name__ == "__main__":
    main()
