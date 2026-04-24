"""
tools/weather_tool.py - Weather data helpers.

Current weather comes from OpenWeatherMap.
Daily forecasts come from Open-Meteo so the UI can support a user-defined
forecast range instead of a fixed 5-day window.
"""

import functools
import time
from datetime import datetime
from typing import Any, Dict, Optional

import requests

from config import CACHE_TTL, MAX_RETRIES, OPENWEATHER_API_KEY, RETRY_DELAY
from utils import safe_log

OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"
OPENWEATHER_GEO_URL = "https://api.openweathermap.org/geo/1.0"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
MAX_FORECAST_DAYS = 16

CURRENT_WEATHER_LABELS = {
    "clear sky": "Sunny",
    "few clouds": "Partly Cloudy",
    "scattered clouds": "Cloudy",
    "broken clouds": "Cloudy",
    "overcast clouds": "Overcast",
    "light rain": "Rain",
    "moderate rain": "Rain",
    "heavy rain": "Heavy Rain",
    "thunderstorm": "Storm",
    "snow": "Snow",
    "mist": "Mist",
    "fog": "Fog",
    "haze": "Haze",
    "drizzle": "Drizzle",
    "smoke": "Smoke",
    "dust": "Dust",
    "tornado": "Tornado",
}

OPEN_METEO_CODES = {
    0: "Clear",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Dense drizzle",
    56: "Freezing drizzle",
    57: "Freezing drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    66: "Freezing rain",
    67: "Freezing rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Rain showers",
    81: "Rain showers",
    82: "Heavy showers",
    85: "Snow showers",
    86: "Snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm",
    99: "Thunderstorm",
}

_cache: Dict[str, tuple] = {}


def _cached(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        key = str(args) + str(sorted(kwargs.items()))
        now = time.time()
        if key in _cache:
            result, timestamp = _cache[key]
            if now - timestamp < CACHE_TTL:
                return result
        result = func(*args, **kwargs)
        _cache[key] = (result, now)
        return result

    return wrapper


def _current_weather_label(description: str) -> str:
    lowered = description.lower()
    for key, label in CURRENT_WEATHER_LABELS.items():
        if key in lowered:
            return label
    return "Weather"


def _forecast_weather_label(code: int) -> str:
    return OPEN_METEO_CODES.get(code, "Weather")


def _forecast_suitability(code: int, rain_chance: int) -> str:
    if code >= 95 or code in {65, 67, 75, 82, 86}:
        return "Indoor Better"
    if rain_chance >= 45 or code in {61, 63, 66, 71, 73, 77, 80, 81, 85}:
        return "Indoor Better"
    return "Outdoor OK"


class WeatherTool:
    """Weather API wrapper with retry, caching, and daily summaries."""

    def __init__(self):
        if not OPENWEATHER_API_KEY:
            raise EnvironmentError(
                "OPENWEATHER_API_KEY not set. Free key at https://openweathermap.org/api"
            )

    def _request(self, url: str, params: dict) -> dict:
        """Make a GET request with retry logic."""
        last_err = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = requests.get(url, params=params, timeout=12)
                response.raise_for_status()
                return response.json()
            except Exception as exc:
                last_err = exc
                wait = RETRY_DELAY * (2 ** (attempt - 1))
                safe_log(
                    f"[WeatherTool] attempt {attempt} failed: {exc}. Retrying in {wait}s..."
                )
                time.sleep(wait)
        raise RuntimeError(f"Weather request failed after {MAX_RETRIES} attempts: {last_err}")

    @_cached
    def geocode(self, city: str) -> Optional[Dict[str, Any]]:
        """Convert city name to lat/lon."""
        try:
            data = self._request(
                f"{OPENWEATHER_GEO_URL}/direct",
                {"q": city, "limit": 1, "appid": OPENWEATHER_API_KEY},
            )
            if not data:
                return None
            return {
                "lat": data[0]["lat"],
                "lon": data[0]["lon"],
                "name": data[0].get("name", city),
            }
        except Exception as exc:
            return {"error": str(exc), "name": city}

    @_cached
    def get_current_weather(self, city: str) -> Dict[str, Any]:
        """Fetch current weather for a city."""
        geo = self.geocode(city)
        if not geo:
            return {"error": f"City '{city}' not found", "city": city}
        if geo.get("error"):
            return {"error": geo["error"], "city": city}

        try:
            data = self._request(
                f"{OPENWEATHER_BASE_URL}/weather",
                {
                    "lat": geo["lat"],
                    "lon": geo["lon"],
                    "units": "metric",
                    "appid": OPENWEATHER_API_KEY,
                },
            )
            description = data["weather"][0]["description"]
            return {
                "city": data.get("name", city),
                "country": data["sys"].get("country", ""),
                "temperature": round(data["main"]["temp"], 1),
                "feels_like": round(data["main"]["feels_like"], 1),
                "temp_min": round(data["main"]["temp_min"], 1),
                "temp_max": round(data["main"]["temp_max"], 1),
                "humidity": data["main"]["humidity"],
                "pressure": data["main"]["pressure"],
                "wind_speed": round(data["wind"].get("speed", 0) * 3.6, 1),
                "wind_dir": data["wind"].get("deg", 0),
                "visibility": data.get("visibility", 10000) // 1000,
                "description": description.title(),
                "emoji": _current_weather_label(description),
                "clouds": data["clouds"]["all"],
                "sunrise": datetime.fromtimestamp(data["sys"]["sunrise"]).strftime("%H:%M"),
                "sunset": datetime.fromtimestamp(data["sys"]["sunset"]).strftime("%H:%M"),
                "timezone": data["timezone"],
                "fetched": datetime.now().isoformat(),
                "outdoor_score": _outdoor_score(data),
            }
        except Exception as exc:
            return {"error": str(exc), "city": city}

    @_cached
    def get_forecast(self, city: str, days: int = 7) -> Dict[str, Any]:
        """Fetch daily forecast summaries up to the requested number of days."""
        geo = self.geocode(city)
        if not geo:
            return {"error": f"City '{city}' not found", "daily": []}
        if geo.get("error"):
            return {"error": geo["error"], "daily": []}

        safe_days = max(1, min(days, MAX_FORECAST_DAYS))

        try:
            data = self._request(
                OPEN_METEO_FORECAST_URL,
                {
                    "latitude": geo["lat"],
                    "longitude": geo["lon"],
                    "timezone": "auto",
                    "forecast_days": safe_days,
                    "daily": ",".join(
                        [
                            "weather_code",
                            "temperature_2m_max",
                            "temperature_2m_min",
                            "precipitation_probability_max",
                        ]
                    ),
                },
            )

            daily = data.get("daily", {})
            times = daily.get("time", [])
            codes = daily.get("weather_code", [])
            temp_max = daily.get("temperature_2m_max", [])
            temp_min = daily.get("temperature_2m_min", [])
            rain = daily.get("precipitation_probability_max", [])

            summaries = []
            for index, day_str in enumerate(times):
                code = int(codes[index]) if index < len(codes) and codes[index] is not None else 0
                rain_chance = int(rain[index]) if index < len(rain) and rain[index] is not None else 0
                summaries.append(
                    {
                        "date": day_str,
                        "day": datetime.strptime(day_str, "%Y-%m-%d").strftime("%A"),
                        "short_date": datetime.strptime(day_str, "%Y-%m-%d").strftime("%m-%d"),
                        "temp_min": round(float(temp_min[index]), 1)
                        if index < len(temp_min) and temp_min[index] is not None
                        else None,
                        "temp_max": round(float(temp_max[index]), 1)
                        if index < len(temp_max) and temp_max[index] is not None
                        else None,
                        "description": _forecast_weather_label(code),
                        "emoji": _forecast_weather_label(code),
                        "rain_chance": rain_chance,
                        "suitability_label": _forecast_suitability(code, rain_chance),
                    }
                )

            return {
                "city": city,
                "daily": summaries,
                "fetched": datetime.now().isoformat(),
            }
        except Exception as exc:
            return {"error": str(exc), "daily": []}

    def get_weather_advice(self, weather: dict) -> str:
        """Generate brief human-readable outdoor advice based on weather."""
        if "error" in weather:
            return "Weather data unavailable. Check conditions before heading out."

        temp = weather.get("temperature", 20)
        wind = weather.get("wind_speed", 0)
        score = weather.get("outdoor_score", 5)

        if score >= 8:
            advice = "Great weather for getting out and exploring."
        elif score >= 6:
            advice = "Conditions look good for outdoor events."
        elif score >= 4:
            advice = "Bring a layer because conditions may shift through the day."
        else:
            advice = "Indoor events are the safer bet today."

        if temp < 10:
            advice += " It is cold, so dress warmly."
        elif temp > 35:
            advice += " It is very hot, so stay hydrated."
        if wind > 30:
            advice += " Expect strong winds."
        return advice


def _outdoor_score(data: dict) -> int:
    """Score 1-10 for outdoor suitability based on current weather."""
    score = 10
    temp = data["main"]["temp"]
    description = data["weather"][0]["description"].lower()
    wind = data["wind"].get("speed", 0) * 3.6
    humidity = data["main"]["humidity"]

    if temp < 5 or temp > 40:
        score -= 4
    elif temp < 10 or temp > 35:
        score -= 2
    if "rain" in description or "storm" in description or "snow" in description:
        score -= 3
    if "drizzle" in description:
        score -= 1
    if wind > 40:
        score -= 2
    elif wind > 25:
        score -= 1
    if humidity > 85:
        score -= 1

    return max(1, min(10, score))
