"""The ONLY web tool: live weather for a Tunisian city from Open-Meteo (open service, no key). There is no web search and no other web access.
It is registered only when ENABLE_WEB=true in .env. It can contact exactly two hosts (ALLOWED_HOSTS); any other address is refused before a request is made.
Everything it returns is labelled as web data that this project has not verified. The `opener` argument is the network function, so tests use a fake one."""
import datetime
import json
import urllib.parse
import urllib.request

ALLOWED_HOSTS = {"geocoding-api.open-meteo.com", "api.open-meteo.com"}
GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST = "https://api.open-meteo.com/v1/forecast"
TIMEOUT_S = 10
MAX_BYTES = 200_000


def _get(url, params, opener):
    full = url + "?" + urllib.parse.urlencode(params)
    host = urllib.parse.urlparse(full).hostname
    if urllib.parse.urlparse(full).scheme != "https" or host not in ALLOWED_HOSTS:
        raise ValueError(f"address not allowed: {host}")
    with opener(urllib.request.Request(full, headers={"User-Agent": "tunisia-insights/1.0"}), timeout=TIMEOUT_S) as r:
        return json.loads(r.read(MAX_BYTES).decode("utf-8"))


def get_weather(city="Tunis", days=3, opener=urllib.request.urlopen):
    """Live weather forecast for a Tunisian city for the next 1 to 7 days."""
    days = max(1, min(int(days), 7))
    g = _get(GEOCODE, {"name": str(city)[:60], "count": 5, "country_code": "TN", "language": "en"}, opener)
    if not g.get("results"):
        raise ValueError(f"no Tunisian place called '{city}' was found")
    p = g["results"][0]
    w = _get(FORECAST, {"latitude": p["latitude"], "longitude": p["longitude"], "forecast_days": days, "timezone": "Africa/Tunis",
                        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max"}, opener)
    d = w["daily"]
    return {"kind": "WEATHER_FORECAST", "place": p["name"],
            "days": [{"date": d["time"][i], "max_c": d["temperature_2m_max"][i], "min_c": d["temperature_2m_min"][i], "rain_mm": d["precipitation_sum"][i],
                      "rain_chance_pct": d["precipitation_probability_max"][i], "wind_max_kmh": d["wind_speed_10m_max"][i]} for i in range(len(d["time"]))],
            "label": "live web data from Open-Meteo, a forecast, not verified by this project",
            "fetched_at": datetime.datetime.now().isoformat(timespec="minutes"),
            "source": "Open-Meteo (web)"}
