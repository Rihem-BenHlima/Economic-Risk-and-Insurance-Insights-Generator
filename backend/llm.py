"""llm.py: the language models, behind ONE interface so the rest of the backend never cares which one is running.

    generate(system, messages, specs) -> {"text": "..."}                                  the model answered
                                      or {"tool_calls": [{"name": ..., "args": {...}}]}   the model wants tools run first

Messages are plain dicts: {"role": "user", "content": ...}, {"role": "assistant", "content": ...} or {"role": "assistant", "tool_calls": [...]},
and {"role": "tool", "name": ..., "result": {...}}.

OfflineLLM  no key, no network. A small keyword router: it picks a tool and writes the answer from the tool's result. The default until a key exists.
GeminiLLM   used when GEMINI_API_KEY is in .env. Builds the request for Google's Gemini REST API and parses the reply. Written from the public documentation
            and NOT yet run against the real service. The key travels only in a request header, never in the address, the body or any log.
Step 5 later adds a local model (Ollama) behind the same interface.
"""
import json
import re
import urllib.error
import urllib.request

SERIES_WORDS = [("premiums_life", ["life"]), ("premiums_auto", ["motor", "auto", "car "]), ("premiums_health", ["health"]), ("claims_paid_total", ["claim"]),
                ("premiums_total", ["premium", "total", "market"])]
DATA_WORDS = [  # keywords -> (table, column, label)
    (["unemploy", "jobless"], ("labour_annual", "unemployment_rate", "Unemployment rate (%)")),
    (["gdp"], ("economy_annual", "gdp_growth_pct", "Real GDP growth (%)")),
    (["inflation"], ("economy_annual", "inflation_pct", "Inflation (%)")),
    (["exchange", "dinar", "usd"], ("economy_annual", "tnd_per_usd", "Dinars per US dollar")),
    (["rain"], ("climate_annual", "rainfall_mm", "Annual rainfall in Tunis (mm)")),
    (["heat", "hot day"], ("climate_annual", "heat_days_ge35c", "Days at or above 35 C in Tunis")),
    (["temperature"], ("climate_annual", "temp_mean_c", "Mean temperature in Tunis (C)")),
    (["crop", "harvest"], ("agriculture_annual", "crops_index_2014_16", "Crops index (2014-16 = 100)")),
    (["penetration"], ("modeling_table", "penetration_pct_gdp", "Insurance penetration (% of GDP)")),
    (["loss ratio", "claims ratio"], ("modeling_table", "loss_ratio_pct", "Loss ratio (%)")),
]
WEATHER_WORDS = ["tomorrow", "today", "this week", "next few days", "next days", "weather"]
CITIES = ["tunis", "sfax", "sousse", "bizerte", "gabes", "kairouan", "nabeul", "monastir"]
FORECAST_WORDS = ["forecast", "predict", "expect", "project", "will ", "future", "next year"]
FUTURE_WORDS = ["what will", "will ", "predict", "expect", "project", "next year", "by 20", "in 20", "outlook"]       # asks for a value that does not exist yet
RELIABLE_WORDS = ["accura", "error", "best model", "which model", "how good", "reliab", "trust", "precise", "uncertain", "confiden", "range"]
COMPARE_WORDS = ["how big", "how large", "size", "compare", "compared", "versus", " vs ", "share", "bigger", "larger", "biggest", "largest", "than", "relative", "weigh"]
BRANCHES = [("premiums_auto", ["motor", "auto", "car "]), ("premiums_life", ["life"]), ("premiums_health", ["health"])]


def _has(t, words):
    return any(w in t for w in words)


def _series_all(t):
    """Every series the question mentions, in this order: the branches, then claims, then the total (the total only when no branch is named, or when it says 'total')."""
    found = [k for k, ws in BRANCHES if _has(t, ws)]
    if _has(t, ["claim"]):
        found.append("claims_paid_total")
    if _has(t, ["total", "market", "overall"]) or (not found and _has(t, ["premium"])) or (_has(t, ["premium"]) and not any(k.startswith("premiums_") for k in found)):
        found.append("premiums_total")
    return found


def _fmt(n, d=0):
    return f"{n:,.{d}f}" if isinstance(n, (int, float)) else str(n)


class OfflineLLM:
    name = "offline"

    def generate(self, system, messages, specs):
        if messages and messages[-1]["role"] == "tool":
            return {"text": self._compose(messages)}
        t = " " + (messages[-1].get("content", "") if messages else "").lower().replace("?", " ").replace(",", " ") + " "
        names = {s["name"] for s in specs}
        year = re.search(r"20\d\d", t)
        series = next((s for s, ws in SERIES_WORDS if _has(t, ws)), None)
        many = _series_all(t)
        if _has(t, [" hello ", " hi ", " hey "]):
            return {"text": "Hello. Ask me about the forecasts of premiums and claims, how accurate they are, or the figures for insurance, the economy, jobs, agriculture and climate."}
        if _has(t, WEATHER_WORDS) and not _has(t, ["premium", "claim"]):
            if "get_weather" not in names:
                return {"text": "Live weather lookup is switched off, so I cannot tell you the weather for the coming days. I only have yearly weather history for Tunis."}
            return {"tool_calls": [{"name": "get_weather", "args": {"city": next((c for c in CITIES if c in t), "tunis").title(), "days": 3}}]}
        future = (year is not None and int(year.group()) > 2024) or _has(t, FUTURE_WORDS)
        reliab = _has(t, RELIABLE_WORDS)
        if future and not _has(t, ["which model", "best model"]):
            fargs = {"series": many[0] if many else "premiums_total"}
            if year is not None and int(year.group()) > 2024:
                fargs["year"] = int(year.group())
            calls = [{"name": "get_forecast", "args": fargs}]
            if reliab:                                                  # "what will X be, and how reliable is that?" -> the forecast AND how accurate it has been
                calls.append({"name": "get_accuracy", "args": {"series": fargs["series"]}})
            return {"tool_calls": calls}
        if reliab:
            return {"tool_calls": [{"name": "get_accuracy", "args": {"series": series} if series else {}}]}
        branches = [k for k, _ in BRANCHES if k in many]
        if branches and (len(branches) > 1 or _has(t, COMPARE_WORDS)):    # a size question or a comparison: the branches asked for (all three if one is named) next to the total
            order = branches + [k for k, _ in BRANCHES if k not in branches] if len(branches) == 1 else branches
            return {"tool_calls": [{"name": "get_history", "args": {"series": k}} for k in order + ["premiums_total"]]}
        if _has(t, FORECAST_WORDS):
            return {"tool_calls": [{"name": "get_forecast", "args": {"series": series or "premiums_total"}}]}
        for words, (table, col, _) in DATA_WORDS:
            if _has(t, words):
                args = {"table": table, "column": col}
                if year:
                    args["year"] = int(year.group())
                return {"tool_calls": [{"name": "query_data", "args": args}]}
        if series:
            args = {"series": series}
            if year:
                args["start_year"] = args["end_year"] = int(year.group())
            return {"tool_calls": [{"name": "get_history", "args": args}]}
        if _has(t, ["what data", "which data", "what can you"]):
            return {"tool_calls": [{"name": "list_data", "args": {}}]}
        return {"text": "I could not match that to the project's data. Try: \"What will premiums be in 2027?\", \"Which model is most accurate?\", \"What is the unemployment rate?\" "
                        "or \"How big is the motor branch?\". I am the offline assistant: open-ended questions need the Gemini model, which is not connected yet."}

    def _compose(self, messages):
        results = []
        for m in reversed(messages):
            if m["role"] != "tool":
                break
            results.append(m["result"])
        results.reverse()
        out, histories, forecast_shown = [], [], False
        for r in results:
            if "error" in r:
                out.append(f"I could not get that: {r['error']}.")
            elif r["kind"] == "FORECAST":
                out.append(self._forecast(r))
                forecast_shown = True
            elif r["kind"] == "ACCURACY":
                out.append(self._accuracy(r, forecast_shown))
            elif r["kind"] == "HISTORY" and r.get("series") and len(results) > 1:
                histories.append(r)                                  # several series asked for together: written up as one comparison below
            elif r["kind"] == "HISTORY":
                label = next((lab for ws, (tb, col, lab) in DATA_WORDS if col == r.get("column")), r.get("series") or r.get("column"))
                out.append(f"HISTORY, {label}: " + "; ".join(f"{x['year']}: {_fmt(x['value'], 1 if isinstance(x['value'], float) and abs(x['value']) < 1000 else 0)}" for x in r["values"][-5:]) + ".")
            elif r["kind"] == "CATALOGUE":
                out.append("I can read these tables: " + "; ".join(f"{k} ({v['holds']})" for k, v in r["tables"].items()) + ".")
            elif r["kind"] == "WEATHER_FORECAST":
                days = "; ".join(f"{d['date']}: {d['min_c']} to {d['max_c']} C, rain {d['rain_mm']} mm ({d['rain_chance_pct']}% chance)" for d in r["days"])
                out.append(f"WEATHER in {r['place']} ({r['label']}, fetched {r['fetched_at']}): {days}.")
        if histories:
            out.insert(0, self._compare(histories))
        return " ".join(out)

    @staticmethod
    def _forecast(r):
        f, last = r["forecast"], r["last_actual"]
        rows = "; ".join(f"{x['year']}: {_fmt(x['value'])} M.TND (80% range {_fmt(x['low_80'])} to {_fmt(x['high_80'])})" for x in f)
        end = f[-1]
        years = end["year"] - last["year"]
        growth = ""
        if years > 0 and last["value"] and end["value"]:
            growth = f" That is about {((end['value'] / last['value']) ** (1 / years) - 1) * 100:.1f}% a year from {_fmt(last['value'])} M.TND in {last['year']}, the last actual."
        return f"FORECAST ({r['model']}), {r['series'].lower()}: {rows}.{growth} This is a model estimate, not a fact."

    @staticmethod
    def _accuracy(r, after_forecast=False):
        ms = r["models"]
        if not ms:
            return "I have no accuracy figures for that."
        best = ms[0]
        ens = next((m for m in ms if m["model"].startswith("Ensemble")), None)
        rank = "; ".join(f"{i + 1}. {m['model']} {m['mape_pct']}%" for i, m in enumerate(ms))
        if after_forecast and ens:
            text = (f"How reliable: on past years (tested from 2012, forecasting 1 to 3 years ahead) the ensemble missed {r['scope'].lower()} by {ens['mape_pct']}% on average"
                    + (f"; the best single model was {best['model']} at {best['mape_pct']}%" if best is not ens else "")
                    + ". The 80% range comes from those past errors. There are only about 22 yearly points, so treat it as a guide, not a guarantee.")
            return text
        lead = f"Most accurate for {r['scope'].lower()}: {best['model']}, with an average error of {best['mape_pct']}% (lower is better)."
        if len(ms) > 1:
            gap = round(ms[1]["mape_pct"] - best["mape_pct"], 3)
            lead += f" The next is {ms[1]['model']} at {ms[1]['mape_pct']}%, only {gap} points behind" if gap < 0.25 else f" The next is {ms[1]['model']} at {ms[1]['mape_pct']}%, {gap} points behind"
            lead += (", so the top models are practically tied." if gap < 0.25 else ".")
        if ens and best is not ens and ens is not ms[1]:
            lead += f" The final forecast uses the ensemble ({ens['mape_pct']}%), which is {round(ens['mape_pct'] - best['mape_pct'], 3)} points off the best."
        return f"{lead} Full ranking: {rank}."

    @staticmethod
    def _compare(hs):
        latest = {h["series"]: h["values"][-1] for h in hs if h["values"]}
        total = latest.get("Total premiums")
        parts = [(name, v) for name, v in latest.items() if name != "Total premiums"]
        if not parts:
            return ""
        year = parts[0][1]["year"]
        parts.sort(key=lambda p: -p[1]["value"])
        def line(name, v):
            share = f" ({v['value'] / total['value'] * 100:.0f}% of total premiums)" if total and total["year"] == v["year"] and name.endswith("premiums") else ""
            return f"{name.replace(' premiums', '')} {_fmt(v['value'])} M.TND{share}"
        text = f"HISTORY, {year}: " + "; ".join(line(n, v) for n, v in parts) + (f"; total premiums {_fmt(total['value'])} M.TND" if total else "") + "."
        if len(parts) > 1 and parts[1][1]["value"]:
            text += f" {parts[0][0].replace(' premiums', '')} is the largest, about {parts[0][1]['value'] / parts[1][1]['value']:.1f} times {parts[1][0].replace(' premiums', '').lower()}."
        first = {h["series"]: h["values"][-6] for h in hs if len(h["values"]) >= 6}
        moves = [f"{n.replace(' premiums', '')} {((v['value'] / first[n]['value']) ** (1 / (v['year'] - first[n]['year'])) - 1) * 100:+.1f}% a year" for n, v in parts if n in first and first[n]["value"] and v["year"] > first[n]["year"]]
        if moves:
            text += f" Growth since {first[parts[0][0]]['year']}: " + ", ".join(moves) + "."
        return text


class GeminiLLM:
    name = "gemini"
    URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    RETRY_CODES = (429, 500, 503, 404)                          # busy, overloaded or retired model: try the next model instead of failing

    def __init__(self, api_key, model, timeout=30, opener=urllib.request.urlopen, fallbacks=()):
        self.key, self.model, self.timeout, self.opener = api_key, model, timeout, opener
        self.fallbacks = [m for m in fallbacks if m and m != model]

    def build_request(self, system, messages, specs):
        """Our messages and tool specs as the JSON body Gemini expects."""
        contents = []
        for m in messages:
            if m["role"] == "user":
                role, parts = "user", [{"text": m["content"]}]
            elif m["role"] == "assistant" and m.get("tool_calls"):
                role, parts = "model", [self._call_part(c) for c in m["tool_calls"]]
            elif m["role"] == "assistant":
                role, parts = "model", [{"text": m["content"]}]
            else:                                                    # a tool result goes back as a user turn holding a functionResponse part
                fr = {"name": m["name"], "response": {"result": m["result"]}}
                if m.get("call_id"):
                    fr["id"] = m["call_id"]
                role, parts = "user", [{"functionResponse": fr}]
            prev = contents[-1] if contents else None
            if prev and role == "user" and "functionResponse" in parts[0] and "functionResponse" in prev["parts"][0]:
                prev["parts"].extend(parts)                          # the results of one round share one turn
            else:
                contents.append({"role": role, "parts": parts})
        body = {"systemInstruction": {"parts": [{"text": system}]}, "contents": contents, "generationConfig": {"temperature": 0.2, "maxOutputTokens": 800}}
        if specs:
            body["tools"] = [{"functionDeclarations": specs}]
        return body

    @staticmethod
    def _call_part(c):
        """A tool call as Gemini sent it: newer models need its id and thought signature echoed back with the tool result, or the next request is refused (HTTP 400)."""
        fc = {"name": c["name"], "args": c.get("args") or {}}
        if c.get("id"):
            fc["id"] = c["id"]
        part = {"functionCall": fc}
        if c.get("thought_signature"):
            part["thoughtSignature"] = c["thought_signature"]
        return part

    def headers(self):
        return {"Content-Type": "application/json", "x-goog-api-key": self.key}

    @staticmethod
    def parse_response(data):
        """Gemini's JSON reply as {"text": ...} or {"tool_calls": [...]}."""
        if data.get("promptFeedback", {}).get("blockReason"):
            return {"text": "I cannot answer that request."}
        cands = data.get("candidates") or []
        if not cands:
            return {"text": "The model returned no answer. Please try again."}
        parts = (cands[0].get("content") or {}).get("parts") or []
        calls = []
        for p in parts:
            if "functionCall" in p:
                c = {"name": p["functionCall"]["name"], "args": p["functionCall"].get("args") or {}}
                if p["functionCall"].get("id"):
                    c["id"] = p["functionCall"]["id"]
                if p.get("thoughtSignature"):
                    c["thought_signature"] = p["thoughtSignature"]
                calls.append(c)
        if calls:
            return {"tool_calls": calls}
        return {"text": "".join(p.get("text", "") for p in parts).strip() or "The model returned an empty answer. Please try again."}

    def generate(self, system, messages, specs):
        body = json.dumps(self.build_request(system, messages, specs)).encode("utf-8")
        last = None
        for model in [self.model] + self.fallbacks:
            req = urllib.request.Request(self.URL.format(model=model), data=body, headers=self.headers(), method="POST")
            try:
                with self.opener(req, timeout=self.timeout) as r:
                    return self.parse_response(json.loads(r.read().decode("utf-8")))
            except urllib.error.HTTPError as e:
                last = e
                if e.code not in self.RETRY_CODES:
                    raise
        raise last
