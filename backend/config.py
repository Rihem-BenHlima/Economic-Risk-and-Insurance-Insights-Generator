"""Settings of the chatbot backend, read from environment variables and from the project-root .env (never from the code).
The .env file is the ONLY place for the Gemini key; it is listed in .gitignore and is never printed or logged."""
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT / "data" / "processed"
RESULTS = ROOT / "step_02_forecasting" / "results"


def load_env(path=None):
    """Reads KEY=VALUE lines of a .env file into os.environ (values already set in the environment win). Returns the keys it read."""
    path = Path(path) if path else ROOT / ".env"
    keys = []
    if not path.exists():
        return keys
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)
        keys.append(k)
    return keys


def settings():
    """Current settings. The key is returned only to the code that calls Gemini; use public() for anything shown or logged."""
    return {
        "api_key": os.environ.get("GEMINI_API_KEY", "").strip(),
        "model": os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite").strip(),          # check Google AI Studio for the current model names
        "fallback_models": [m.strip() for m in os.environ.get("GEMINI_FALLBACK_MODELS", "gemini-3.1-flash-lite,gemini-3.7-flash").split(",") if m.strip()],
        "enable_web": os.environ.get("ENABLE_WEB", "false").strip().lower() in ("1", "true", "yes"),
        "port": int(os.environ.get("PORT", "8000")),
        "max_tool_rounds": int(os.environ.get("MAX_TOOL_ROUNDS", "5")),
        "max_message_chars": 1000,
        "max_history_turns": 10,
        "rate_per_minute": int(os.environ.get("RATE_PER_MINUTE", "20")),
        "timeout_s": int(os.environ.get("LLM_TIMEOUT_S", "30")),
    }


def public(s=None):
    """Settings that are safe to show: the key is replaced by whether it exists."""
    s = dict(s or settings())
    s["has_key"] = bool(s.pop("api_key"))
    return s
