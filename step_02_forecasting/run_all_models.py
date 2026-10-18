"""Run every model, then the final ensemble (which needs the five models), then the comparison and the reload check of the saved models.

Run:  python step_02_forecasting/run_all_models.py [model ...]      (no argument = all models, then compare + reload check)
Each model file can also be run alone, e.g. python step_02_forecasting/gbm/gbm.py, then python step_02_forecasting/compare.py.
The input choice of the models comes from results/ablation.csv (python step_02_forecasting/ablation.py) and is set in features.py.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODELS = [("arima", "arima.py"), ("prophet", "prophet_model.py"), ("gbm", "gbm.py"), ("random_forest", "random_forest.py"), ("lstm", "lstm.py"), ("ensemble", "ensemble.py")]


def run(label, script, env):
    t0 = time.time()
    r = subprocess.run([sys.executable, str(HERE / script)], capture_output=True, text=True, env=env, cwd=str(HERE))
    lines = [ln for ln in (r.stdout + r.stderr).splitlines() if ln.strip() and "cmdstanpy" not in ln and "INFO" not in ln and "warn" not in ln.lower()]
    print(f"===== [{label}] {'ok' if r.returncode == 0 else 'FAILED'}, {time.time() - t0:.0f}s =====", flush=True)
    print(chr(10).join(lines), flush=True)


def main():
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    wanted = sys.argv[1:]
    for m, script in MODELS:
        if not wanted or m in wanted:
            run(m, f"{m}/{script}", env)
    if not wanted:
        run("compare + reload check", "compare.py", env)
        print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
