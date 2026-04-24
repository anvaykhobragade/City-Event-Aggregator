"""
agents/weather_agent.py - Weather Intelligence Agent.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.base_agent import BaseAgent
from config import TODAY
from tools.weather_tool import WeatherTool
from utils import safe_log


class WeatherAgent(BaseAgent):
    """Fetches current weather plus a daily forecast for the requested date range."""

    def __init__(self):
        super().__init__(
            name="WeatherAgent",
            description="Fetches real-time weather and generates event-suitability insights.",
        )
        self.weather_tool = WeatherTool()

    def analyse_weather(
        self,
        city: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        safe_log(f"[WeatherAgent] Fetching weather for '{city}'")

        forecast_days = self._forecast_days(date_from=date_from, date_to=date_to)
        current = self.weather_tool.get_current_weather(city)
        forecast = self.weather_tool.get_forecast(city, days=forecast_days)

        if "error" in current:
            safe_log(f"[WeatherAgent] Warning: {current['error']}")

        advice = self._generate_weather_advice(current, forecast)
        best_days = self._identify_best_days(forecast)
        event_recommendations = self._event_type_recommendations(current)

        return {
            "current": current,
            "forecast": forecast.get("daily", []),
            "advice": advice,
            "best_days": best_days,
            "outdoor_score": current.get("outdoor_score", 5),
            "event_recommendations": event_recommendations,
            "quick_summary": self._quick_summary(current),
            "forecast_days": len(forecast.get("daily", [])),
            "requested_until": date_to,
            "fetched": datetime.now().isoformat(),
        }

    def _forecast_days(self, date_from: Optional[str], date_to: Optional[str]) -> int:
        if not date_to:
            return 7

        try:
            start = (
                datetime.strptime(date_from, "%Y-%m-%d").date()
                if date_from
                else datetime.now().date()
            )
            end = datetime.strptime(date_to, "%Y-%m-%d").date()
            return max(1, (end - start).days + 1)
        except Exception:
            return 7

    def _generate_weather_advice(self, current: Dict, forecast: Dict) -> str:
        if "error" in current:
            return "Weather data is currently unavailable. Please plan based on local conditions."

        forecast_text = ""
        for day in forecast.get("daily", [])[:7]:
            forecast_text += (
                f"\n  - {day['short_date']}: {day['description']}, "
                f"{day['temp_max']}C, {day['suitability_label']}"
            )

        label = f"{len(forecast.get('daily', []))}-Day Forecast"
        prompt = f"""
Today is {TODAY}. You are a helpful city guide giving weather-based event advice.

Current weather in {current.get('city', 'the city')}:
- Temperature : {current.get('temperature')}C (feels like {current.get('feels_like')}C)
- Condition   : {current.get('emoji')} {current.get('description')}
- Humidity    : {current.get('humidity')}%
- Wind        : {current.get('wind_speed')} km/h
- Outdoor score: {current.get('outdoor_score')}/10
- Sunrise/Sunset: {current.get('sunrise')} / {current.get('sunset')}

{label}:{forecast_text}

Write a friendly, 3-4 sentence weather briefing for someone planning to attend city events.
Include: current conditions, the best day or days for outdoor events, and one practical tip.
Do not use bullet points.
"""
        generated = self.generate(prompt).strip()
        return generated or self.weather_tool.get_weather_advice(current)

    def _identify_best_days(self, forecast: Dict) -> List[str]:
        daily = forecast.get("daily", [])
        if not daily:
            return []

        scored = sorted(
            daily,
            key=lambda day: (
                0 if day.get("suitability_label") == "Outdoor OK" else 1,
                day.get("rain_chance", 100),
                abs((day.get("temp_max") or 25) - 28),
            ),
        )
        return [day["short_date"] for day in scored[:2]]

    def _event_type_recommendations(self, current: Dict) -> Dict[str, str]:
        score = current.get("outdoor_score", 5)

        if score >= 8:
            outdoor = "Excellent"
            indoor = "Also great"
        elif score >= 6:
            outdoor = "Good"
            indoor = "Great alternative"
        elif score >= 4:
            outdoor = "Check conditions"
            indoor = "Recommended"
        else:
            outdoor = "Not ideal"
            indoor = "Highly recommended"

        return {
            "outdoor_events": outdoor,
            "indoor_concerts": indoor,
            "food_festivals": "Great pick" if score >= 5 else "Consider indoor options",
            "sports_events": outdoor,
            "art_galleries": "Always a good choice",
        }

    def _quick_summary(self, current: Dict) -> str:
        if "error" in current:
            return "Weather data unavailable"
        return (
            f"{current.get('emoji', 'Weather')} {current.get('temperature')}C · "
            f"{current.get('description')} · "
            f"Outdoor score {current.get('outdoor_score')}/10"
        )
