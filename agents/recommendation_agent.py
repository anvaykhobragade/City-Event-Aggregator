"""
agents/recommendation_agent.py â€” Agent 4: Personalised Recommendation Agent
Role: Combines curated events + weather + user profile to generate a
personalised "day plan" recommendation. Also uses DuckDuckGo to fetch
local transport and dining tips for each top event.
"""

from datetime import datetime
from typing import Any, Dict, List

from agents.base_agent import BaseAgent
from config import TODAY, YEAR
from tools.duckduckgo_tool import DuckDuckGoTool
from utils import safe_log


class RecommendationAgent(BaseAgent):
    """
    Agent 4 â€” Personalised Recommendations
    Tools used      : Groq + DuckDuckGo (nearby places lookup)
    Responsibility  : Build a personalised day plan from curated events,
                      weather data, and user preferences.
    Output          : Full recommendation report with day plan, tips, and itinerary.
    """

    def __init__(self):
        super().__init__(
            name="RecommendationAgent",
            description="Generates personalised event day-plans combining events, weather, and user profile.",
        )
        try:
            self.ddg = DuckDuckGoTool()
        except ImportError:
            self.ddg = None
            safe_log("[RecommendationAgent] DuckDuckGo unavailable.")

    def generate_recommendations(
        self,
        city: str,
        curated_events: List[Dict[str, Any]],
        weather: Dict[str, Any],
        user_preferences: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate full personalised recommendations.
        Returns:
          {
            day_plan, top_3_events, itinerary, dining_tips, transport_tips,
            personalised_note, summary_card, fetched
          }
        """
        safe_log(f"[RecommendationAgent] Generating recommendations for {city}...")

        if not curated_events:
            return self._empty_response(city)

        top_3 = curated_events[:3]
        dining_tips = self._get_dining_tips(city, top_3)
        transport = self._get_transport_tips(city)
        day_plan = self._build_day_plan(city, top_3, weather, user_preferences)
        itinerary = self._build_itinerary(city, top_3, weather, user_preferences)
        note = self._personalised_note(top_3, weather, user_preferences)
        summary = self._summary_card(city, top_3, weather)

        return {
            "city": city,
            "day_plan": day_plan,
            "top_3_events": top_3,
            "itinerary": itinerary,
            "dining_tips": dining_tips,
            "transport_tips": transport,
            "personalised_note": note,
            "summary_card": summary,
            "all_events_count": len(curated_events),
            "fetched": datetime.now().isoformat(),
        }

    def _build_day_plan(self, city: str, events: List[Dict], weather: Dict, prefs: Dict) -> str:
        """Generate a rich narrative day plan."""
        event_details = "\n".join(
            f"  - {event.get('title')} @ {event.get('venue')} - {event.get('date')} "
            f"({event.get('category')}, {event.get('price')}) - {event.get('description', '')[:100]}"
            for event in events
        )
        prefs_text = (
            f"Interests: {', '.join(prefs.get('interests', ['general']))} | "
            f"Budget: {prefs.get('budget', 'moderate')} | "
            f"Group: {prefs.get('group_type', 'solo')}"
        )
        weather_now = weather.get("quick_summary", "Weather data unavailable")
        advice = weather.get("advice", "")

        prompt = f"""
Today is {TODAY}. You are a knowledgeable local city guide in {city}.

User profile  : {prefs_text}
Weather today : {weather_now}
Weather advice: {advice}

Top events available:
{event_details}

Create an engaging, personalised day plan for this user. Structure it as:

MORNING (9 AM - 12 PM): [activity]
AFTERNOON (12 PM - 5 PM): [event + activity]
EVENING (5 PM - 10 PM): [event + dining]

For each slot:
- Recommend 1 specific event or activity
- Include a practical weather-aware tip
- Suggest what to bring or wear

Write in a warm, enthusiastic guide's voice. Be specific to {city}.
Keep it to 250-300 words.
"""
        generated = self.generate(prompt).strip()
        return generated or self._fallback_day_plan(city, events, weather, prefs)

    def _build_itinerary(
        self,
        city: str,
        events: List[Dict],
        weather: Dict,
        prefs: Dict,
    ) -> List[Dict[str, str]]:
        """Return a structured itinerary as a list of time slots."""
        event_list = "\n".join(
            f"{index + 1}. {event.get('title')} | {event.get('venue')} | {event.get('date')} | {event.get('price')}"
            for index, event in enumerate(events)
        )
        prompt = f"""
Today is {TODAY}. City: {city}. Weather: {weather.get('quick_summary', '')}

Events:
{event_list}

Build a structured itinerary as a JSON array. Each element:
{{
  "time"     : "e.g. 10:00 AM",
  "activity" : "event or activity name",
  "location" : "venue or area",
  "tip"      : "one practical tip",
  "duration" : "e.g. 2 hours"
}}

Include 5-6 slots from morning to evening.
Respond ONLY with the JSON array.
"""
        response = self.generate(prompt)
        itinerary = self.parse_json_response(response)
        if isinstance(itinerary, list):
            return itinerary

        return [
            {
                "time": event.get("date", "Daytime"),
                "activity": event.get("title", ""),
                "location": event.get("venue", city),
                "tip": event.get("weather_tip", ""),
                "duration": "2 hours",
            }
            for event in events
        ]

    def _get_dining_tips(self, city: str, events: List[Dict]) -> str:
        """Use DuckDuckGo + Groq to find dining tips near top event venues."""
        raw_dining = ""
        if self.ddg:
            try:
                result = self.ddg.search(
                    f"best restaurants near {city} city centre {YEAR}",
                    max_results=4,
                )
                raw_dining = self.summarise_search_results(result, max_chars=1500)
            except Exception:
                pass

        venues = [event.get("venue", "") for event in events if event.get("venue")]
        prompt = f"""
City: {city}. Top event venues: {', '.join(venues[:3])}.

{f'From search results: {raw_dining}' if raw_dining else ''}

Suggest 3 dining options for someone attending events today:
1. Quick/affordable option
2. Mid-range sit-down restaurant
3. Special occasion / rooftop option

For each: name, cuisine type, price range, and why it works with the event day.
Write as 3 short paragraphs. No bullet points.
"""
        generated = self.generate(prompt).strip()
        return generated or self._fallback_dining_tips(city, events)

    def _get_transport_tips(self, city: str) -> str:
        """Generate transport tips for the city."""
        raw_transport = ""
        if self.ddg:
            try:
                result = self.ddg.search(
                    f"how to get around {city} public transport metro tips",
                    max_results=3,
                )
                raw_transport = self.summarise_search_results(result, max_chars=1000)
            except Exception:
                pass

        prompt = f"""
City: {city}.
{f'From search: {raw_transport}' if raw_transport else ''}

Give 3 practical transport tips for a visitor attending events in {city} today.
Cover: best way to get around, app to use for booking, and one money-saving tip.
Write as 3 concise bullet points (maximum 2 lines each).
"""
        generated = self.generate(prompt).strip()
        return generated or self._fallback_transport_tips(city)

    def _personalised_note(self, events: List[Dict], weather: Dict, prefs: Dict) -> str:
        """Short personalised note from the agent to the user."""
        group = prefs.get("group_type", "solo")
        budget = prefs.get("budget", "moderate")
        weather_emoji = weather.get("current", {}).get("emoji", "Weather")
        top_title = events[0].get("title", "the top event") if events else "today's events"

        prompt = f"""
Write a warm, 2-sentence personalised note for a {group} traveller on a {budget} budget,
recommending they check out "{top_title}" today.
The weather is {weather_emoji} {weather.get('current', {}).get('description', 'pleasant')}.
Sound like a friend who knows the city well. Be specific and enthusiastic.
"""
        generated = self.generate(prompt).strip()
        return generated or self._fallback_personalised_note(events, weather, prefs)

    def _summary_card(self, city: str, events: List[Dict], weather: Dict) -> Dict[str, str]:
        """Machine-readable summary for UI display."""
        current = weather.get("current", {})
        return {
            "city": city,
            "date": TODAY,
            "weather": weather.get("quick_summary", ""),
            "top_event": events[0].get("title", "") if events else "",
            "top_venue": events[0].get("venue", "") if events else "",
            "top_category": events[0].get("category", "") if events else "",
            "events_count": str(len(events)),
            "outdoor_score": str(current.get("outdoor_score", "?")),
        }

    def _empty_response(self, city: str) -> Dict[str, Any]:
        return {
            "city": city,
            "day_plan": f"No events found in {city} for today. Try a different city or category.",
            "top_3_events": [],
            "itinerary": [],
            "dining_tips": "",
            "transport_tips": "",
            "personalised_note": "",
            "summary_card": {},
            "all_events_count": 0,
            "fetched": datetime.now().isoformat(),
        }

    def _fallback_day_plan(
        self,
        city: str,
        events: List[Dict],
        weather: Dict,
        prefs: Dict,
    ) -> str:
        weather_summary = weather.get("quick_summary", "Weather details are limited right now")
        first = events[0] if events else {}
        second = events[1] if len(events) > 1 else first
        third = events[2] if len(events) > 2 else second
        return (
            f"MORNING (9 AM - 12 PM): Ease into the day around {city} while keeping an eye on local conditions. "
            f"{weather_summary}.\n\n"
            f"AFTERNOON (12 PM - 5 PM): Make {first.get('title', 'your top event')} the anchor plan, especially if "
            f"you're interested in {', '.join(prefs.get('interests', [])) or 'local experiences'}.\n\n"
            f"EVENING (5 PM - 10 PM): Wrap up with {second.get('title', 'another strong pick')} or "
            f"{third.get('title', 'a relaxed city stop')}, then leave time for dinner near the venue."
        )

    def _fallback_dining_tips(self, city: str, events: List[Dict]) -> str:
        venue = events[0].get("venue", f"{city} city centre") if events else f"{city} city centre"
        return (
            f"Look for a quick local cafe near {venue} before the main event. "
            f"For a sit-down meal, choose a well-reviewed mid-range restaurant in central {city}. "
            f"If you want to end the day on a higher note, book a signature dining spot close to your evening venue."
        )

    def _fallback_transport_tips(self, city: str) -> str:
        return (
            f"- Use the fastest reliable public transport option available in {city} for major venues.\n"
            f"- Keep a ride-hailing app ready for late evening transfers.\n"
            f"- Leave a small buffer before the headline event to avoid peak-time traffic."
        )

    def _fallback_personalised_note(
        self,
        events: List[Dict],
        weather: Dict,
        prefs: Dict,
    ) -> str:
        group = prefs.get("group_type", "solo")
        budget = prefs.get("budget", "moderate")
        top_title = events[0].get("title", "today's top event") if events else "today's top event"
        return (
            f"For a {group} outing on a {budget} budget, {top_title} is the strongest place to start. "
            f"Pair it with a simple meal nearby and let the weather guide how long you stay outdoors."
        )
