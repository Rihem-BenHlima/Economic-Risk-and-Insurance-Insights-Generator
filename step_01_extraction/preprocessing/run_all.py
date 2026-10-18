"""Run every domain preprocessing script in order, then build the modelling table.

Run from the project root:  python step_01_extraction/preprocessing/run_all.py
Order matters a little: economy first (labour and the modelling table read economy_annual.csv).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common
import importlib.util
import build_modeling_table


def load(domain):
    """Domains that already have their own folder are loaded from <domain>/process.py."""
    path = Path(__file__).parent / domain / "process.py"
    spec = importlib.util.spec_from_file_location(f"{domain}_process", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    common.reset_log()
    for mod in (load("insurance"), load("economy"), load("labour"), load("agriculture"), load("climate"), build_modeling_table):
        mod.main()
    import pandas as pd
    lg = pd.read_csv(common.LOG_FILE)
    print(f"\nlog: {len(lg)} entries in {common.LOG_FILE.relative_to(common.ROOT)}")
    print(lg.groupby(["domain", "action"]).size().sort_values(ascending=False).head(25).to_string())


if __name__ == "__main__":
    main()
