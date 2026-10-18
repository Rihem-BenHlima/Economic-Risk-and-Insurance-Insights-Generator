"""Compare every model on identical backtest rows (run after the model files): metrics.csv, champions per series, comparison and champion plots,
and a reload check of every saved model.
Run:  python step_02_forecasting/compare.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import compare, verify_saved

if __name__ == "__main__":
    compare()
    print()
    print("reload check of every saved model (rebuilds the forecasts from the saved files, no refitting):")
    verify_saved()
