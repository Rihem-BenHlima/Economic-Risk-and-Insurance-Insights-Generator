"""The tool registry: what the model is allowed to call, with a description and a parameter schema for each, and one safe way to run them.
A tool never raises to the model: errors come back as {"error": "..."} so the model can correct itself or tell the user."""
import inspect

import tools_local as L
import tools_web as W

_S = {"type": "string", "enum": list(L.SERIES), "description": "premiums_total, premiums_life, premiums_auto (motor), premiums_health, or claims_paid_total"}
_M = {"type": "string", "enum": list(L.MODELS), "description": "which model; default ensemble, the final forecast"}

LOCAL = {
    "get_forecast": (L.get_forecast, "Forecast of premiums or claims for 2025 to 2027 with its 80% range (a model estimate, not a fact).",
                     {"series": _S, "year": {"type": "integer", "description": "2025, 2026 or 2027; leave out for all three"}, "model": _M}, ["series"]),
    "get_accuracy": (L.get_accuracy, "How accurate each model was on past years (average error %), for one series or overall. Use it for 'which model is best' and 'how reliable'.",
                     {"series": _S}, []),
    "get_history": (L.get_history, "Actual past values of premiums or claims (history, not a forecast).",
                    {"series": _S, "start_year": {"type": "integer"}, "end_year": {"type": "integer"}}, ["series"]),
    "list_data": (L.list_data, "List the tables and columns about the economy, labour, agriculture, climate and insurance that query_data can read. Call it first when unsure of a column name.", {}, []),
    "query_data": (L.query_data, "History of one column of one table, for example labour_annual / unemployment_rate or climate_annual / rainfall_mm. Optional single year.",
                   {"table": {"type": "string", "enum": list(L.TABLES)}, "column": {"type": "string"}, "year": {"type": "integer"}}, ["table", "column"]),
}
WEB = {   # the only web tool: live weather
    "get_weather": (W.get_weather, "LIVE weather forecast for a Tunisian city for the next 1 to 7 days (temperature, rain, wind). Use only for weather questions about the coming days.",
                    {"city": {"type": "string", "description": "a Tunisian city, default Tunis"}, "days": {"type": "integer", "description": "1 to 7"}}, []),
}


def tools(enable_web=False):
    """name -> (function, description, properties, required) of the tools that are switched on."""
    return {**LOCAL, **(WEB if enable_web else {})}


def specs(enable_web=False):
    """Declarations in the shape function-calling APIs expect."""
    return [{"name": n, "description": d, "parameters": {"type": "object", "properties": p, "required": r}} for n, (_, d, p, r) in tools(enable_web).items()]


def call(name, args, enable_web=False, **extra):
    """Runs one allowed tool; returns (result_dict, source_or_None). `extra` goes to the tool (tests pass a fake network opener)."""
    t = tools(enable_web)
    if name not in t:
        return {"error": f"unknown or disabled tool '{name}'"}, None
    fn, _, props, _ = t[name]
    args = {k: v for k, v in (args or {}).items() if k in props and v is not None}            # drop anything the schema does not declare
    extra = {k: v for k, v in extra.items() if k in inspect.signature(fn).parameters}          # test-only helpers go only to tools that take them
    try:
        res = fn(**args, **extra)
        return res, res.get("source")
    except (ValueError, TypeError, KeyError) as e:
        return {"error": str(e)}, None
    except Exception as e:                                                                       # network or file problems
        return {"error": f"{type(e).__name__}: {e}"}, None
