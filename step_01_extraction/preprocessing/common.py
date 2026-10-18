"""Shared helpers for the domain preprocessing scripts."""
import warnings
from pathlib import Path
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
OUT = DATA / "processed"
OUT.mkdir(parents=True, exist_ok=True)
LOG_FILE = OUT / "preprocessing_log.csv"


def log(domain, series, period, action, note=""):
    """Append one imputation / correction / flag to the shared log (re-created by run_all.py)."""
    row = pd.DataFrame([{"domain": domain, "series": series, "period": str(period), "action": action, "note": note}])
    row.to_csv(LOG_FILE, mode="a", header=not LOG_FILE.exists(), index=False)


def reset_log():
    LOG_FILE.unlink(missing_ok=True)


def fill_interior(s, domain, log_scale=False, note=""):
    """Linear interpolation of INTERIOR gaps only (nothing before the first or after the last value)."""
    s = s.astype(float)
    if s.first_valid_index() is None:
        return s
    work = np.log(s) if log_scale else s
    out = work.interpolate(method="linear", limit_area="inside")
    out = np.exp(out) if log_scale else out
    for idx in s.index[s.isna() & out.notna()]:
        log(domain, s.name, idx, f"{'log-' if log_scale else ''}linear interpolation", note)
    return out


def seasonal_fill(s, domain, note=""):
    """Fill interior gaps of a positive series with a regular M/Q index: season factors from complete years,
    log-linear interpolation of the deseasonalised series, then re-seasonalise."""
    s = s.astype(float)
    per = s.index.month if s.index.freqstr.startswith("M") else s.index.quarter
    n = 12 if s.index.freqstr.startswith("M") else 4
    yr = s.index.year
    full = [y for y in sorted(set(yr)) if (yr == y).sum() == n and s[yr == y].notna().all()]
    if len(full) < 2:
        return fill_interior(s, domain, log_scale=True, note=note)
    ratio = {k: np.median([s[(yr == y) & (per == k)].iloc[0] / s[yr == y].mean() for y in full]) for k in range(1, n + 1)}
    factor = pd.Series([ratio[k] for k in per], index=s.index)
    des = np.log(s / factor).interpolate(limit_area="inside")
    out = np.exp(des) * factor
    for idx in s.index[s.isna() & out.notna()]:
        log(domain, s.name, idx, "seasonal-aware log-linear interpolation", f"{note} (season factors from {len(full)} complete years)".strip())
    return out


def write(df, name):
    p = OUT / name
    df.to_csv(p)
    print(f"  wrote {p.relative_to(ROOT)}  {df.shape}")


def drop_unusable(df, domain, min_coverage=0.6, always_drop=None, max_trailing_gap=2):
    """Remove columns that cannot be repaired: too few observations, or listed in always_drop ({column: reason}).
    Only the processed table loses them - raw files in data/ are never touched. Every drop is logged with its reason."""
    always_drop = always_drop or {}
    drop = []
    for c in df.columns:
        cov = df[c].notna().mean()
        if c in always_drop:
            drop.append(c); log(domain, c, "all", "dropped column", always_drop[c])
        elif df[c].nunique(dropna=True) <= 1:
            drop.append(c); log(domain, c, "all", "dropped column", "constant value: carries no information")
        elif df[c].last_valid_index() is not None and df.index.get_loc(df.index[-1]) - df.index.get_loc(df[c].last_valid_index()) > max_trailing_gap:
            drop.append(c); log(domain, c, "all", "dropped column", f"no data after {df[c].last_valid_index()} (more than {max_trailing_gap} trailing years missing); useless for recent years")
        elif cov < min_coverage:
            drop.append(c); log(domain, c, "all", "dropped column", f"only {cov:.0%} of years present (< {min_coverage:.0%}); cannot be repaired without inventing data")
    kept = df.drop(columns=drop)
    print(f"  dropped {len(drop)} unusable columns, kept {kept.shape[1]}")
    return kept, drop


def splice(primary, secondary, domain, name, source, tol=0.10, min_overlap=8):
    """Fill the years the primary series lacks from a second source, but only if the two agree on the years they share
    (mean relative difference <= tol over >= min_overlap years). Returns (series, was_filled)."""
    primary = primary.astype(float)
    ov = pd.concat([primary, secondary], axis=1, keys=["a", "b"]).dropna()
    err = ((ov.b - ov.a).abs().mean() / ov.a.abs().mean()) if len(ov) else np.nan
    if len(ov) >= min_overlap and err <= tol:
        out = primary.combine_first(secondary)
        added = [y for y in out.index if pd.isna(primary.get(y)) and pd.notna(out[y])]
        if added:
            log(domain, name, ",".join(str(y) for y in added), f"filled from {source}", f"validated on {len(ov)} shared years: mean difference {100 * err:.1f}%")
        return out, bool(added)
    log(domain, name, "all", "NOT filled", f"{source} cannot be validated (overlap {len(ov)} years" + (f", mean difference {100 * err:.0f}%)" if len(ov) else ")"))
    return primary, False
