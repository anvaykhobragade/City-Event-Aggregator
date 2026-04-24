"""
agents/curator_agent.py â€” Agent 3: Event Curator Agent
Role: Takes raw events from EventDiscoveryAgent, enriches them with
weather context, deduplicates, scores, and ranks them.
"""

from datetime import datetime
from typing import Any, Dict, List

from agents.base_agent import BaseAgent
from config import TODAY
from utils import safe_log


class EventCuratorAgent(BaseAgent):
    """
    Agent 3 â€” Event Curator
    Tools used      : Groq (LLM enrichment + scoring)
    Responsibility  : Filter, enrich, score, and rank raw events using
                      weather context and user preferences.
    Output          : Curated, ranked list of events with enriched metadata.
    """

    def __init__(self):
        super().__init__(
            name="EventCuratorAgent",
            description="Filters, enriches, and ranks events using Groq + weather context.",
        )

    def curate_events(
        self,
        events: List[Dict[str, Any]],
        weather: Dict[str, Any],
        user_preferences: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Curate and rank events.
        Args:
          events           : raw event list from EventDiscoveryAgent
          weather          : weather dict from WeatherAgent
          user_preferences : {interests: [...], budget: str, group_type: str}
        Returns:
          {curated_events: [...], insights: str, top_pick: dict, fetched}
        """
        safe_log(f"[EventCuratorAgent] Curating {len(events)} events...")

        if not events:
            return {
                "curated_events": [],
                "insights": "No events found to curate.",
                "top_pick": None,
                "fetched": datetime.now().isoformat(),
            }

        scored_events = self._score_events(events, weather, user_preferences)
        deduped = self._deduplicate(scored_events)
        top_events = deduped[:8]
        enriched = self._enrich_events(top_events, weather)
        insights = self._generate_insights(enriched, weather, user_preferences)
        top_pick = enriched[0] if enriched else None

        return {
            "curated_events": enriched,
            "insights": insights,
            "top_pick": top_pick,
            "total_found": len(events),
            "after_curation": len(enriched),
            "fetched": datetime.now().isoformat(),
        }

    def _score_events(
        self,
        events: List[Dict],
        weather: Dict,
        prefs: Dict,
    ) -> List[Dict]:
        """Score each event 1-10 based on weather fit, user prefs, and event quality."""
        outdoor_score = weather.get("outdoor_score", 5)
        interests = [interest.lower() for interest in prefs.get("interests", [])]
        budget = prefs.get("budget", "moderate").lower()

        for event in events:
            score = 5.0

            category = event.get("category", "").lower()
            if category in ("outdoor", "sports", "food") and outdoor_score >= 7:
                score += 1.5
            elif category in ("outdoor", "sports") and outdoor_score < 4:
                score -= 1.5
            elif category in ("music", "art", "theatre", "comedy"):
                score += 0.5

            title_desc = (
                event.get("title", "") + event.get("description", "")
            ).lower()
            if any(interest in title_desc for interest in interests):
                score += 2.0
            if any(interest in category for interest in interests):
                score += 1.0

            price = event.get("price", "").lower()
            if budget == "free" and price == "free":
                score += 2.0
            elif budget == "budget" and ("free" in price or price == "tbd"):
                score += 1.0
            elif budget == "luxury" and price not in ("free", "tbd", ""):
                score += 0.5

            if event.get("date") and event["date"].lower() not in ("upcoming", "tbd", ""):
                score += 0.5

            event["relevance_score"] = round(min(10.0, max(1.0, score)), 1)

        return sorted(events, key=lambda event: event.get("relevance_score", 0), reverse=True)

    def _deduplicate(self, events: List[Dict]) -> List[Dict]:
        """Remove near-duplicate events by title similarity."""
        seen, unique = set(), []
        for event in events:
            key = event.get("title", "").lower().strip()[:40]
            if key and key not in seen:
                seen.add(key)
                unique.append(event)
        return unique

    def _enrich_events(self, events: List[Dict], weather: Dict) -> List[Dict]:
        """Use Groq to enrich events with weather-aware tips and badges."""
        if not events:
            return events

        event_list_text = "\n".join(
            f"{index + 1}. {event.get('title')} | {event.get('category')} | {event.get('date')} | "
            f"{event.get('venue')} | {event.get('price')} | Score: {event.get('relevance_score')}"
            for index, event in enumerate(events)
        )
        weather_summary = (
            f"{weather.get('current', {}).get('emoji', '')} "
            f"{weather.get('current', {}).get('temperature', '?')}C, "
            f"{weather.get('current', {}).get('description', '')}, "
            f"Outdoor score {weather.get('outdoor_score', 5)}/10"
        )
        prompt = f"""
Today is {TODAY}. Current weather: {weather_summary}

You are an expert city event curator. For each event below, add:
- "weather_tip" : 1 sentence tip based on current weather (bring umbrella, wear layers, etc.)
- "badge"       : one of: Top Pick | Must-See | Trending | Outdoor Fun |
                          Cultural Gem | Free Entry | Music Special | Foodie Pick
- "why_go"      : 1 punchy sentence on why to attend

Events:
{event_list_text}

Return a JSON array with exactly {len(events)} objects, each having:
"index" (1-based), "weather_tip", "badge", "why_go"
Respond ONLY with the JSON array.
"""
        response = self.generate(prompt)
        enrichments = self.parse_json_response(response)

        if isinstance(enrichments, list):
            enrich_map = {item.get("index", index + 1): item for index, item in enumerate(enrichments)}
            for index, event in enumerate(events):
                extras = enrich_map.get(index + 1, {})
                event["weather_tip"] = extras.get("weather_tip", "")
                event["badge"] = extras.get("badge", "")
                event["why_go"] = extras.get("why_go", "")

        for event in events:
            event["weather_tip"] = event.get("weather_tip") or self._fallback_weather_tip(event, weather)
            event["badge"] = event.get("badge") or self._fallback_badge(event)
            event["why_go"] = event.get("why_go") or self._fallback_why_go(event)

        return events

    def _generate_insights(self, events: List[Dict], weather: Dict, prefs: Dict) -> str:
        """Generate a short curator's note summarising the event landscape."""
        if not events:
            return "No events found matching your criteria."

        titles = [event.get("title", "") for event in events[:5]]
        interests_str = ", ".join(prefs.get("interests", ["everything"]))

        prompt = f"""
Today is {TODAY}. You are a friendly city events curator.

Top events found: {', '.join(titles)}
User interests: {interests_str}
Weather: {weather.get('quick_summary', 'See weather section')}

Write a 2-3 sentence curator's note introducing this week's event picks.
Be enthusiastic, specific, and mention 1-2 events by name.
Do NOT use bullet points. Write as natural, engaging prose.
"""
        generated = self.generate(prompt).strip()
        return generated or self._fallback_insights(events, weather, prefs)

    def _fallback_weather_tip(self, event: Dict, weather: Dict) -> str:
        outdoor_score = weather.get("outdoor_score", 5)
        category = event.get("category", "").lower()
        if category in ("outdoor", "sports", "food") and outdoor_score < 5:
            return "Check the latest conditions before heading out and keep a backup indoor option in mind."
        if outdoor_score >= 7:
            return "Conditions look comfortable overall, so light layers and comfortable shoes should work well."
        return "Carry water and a light layer so you can adapt to changing conditions."

    def _fallback_badge(self, event: Dict) -> str:
        category = event.get("category", "").lower()
        price = event.get("price", "").lower()
        score = event.get("relevance_score", 0)
        if price == "free":
            return "Free Entry"
        if score >= 8.5:
            return "Top Pick"
        if category == "music":
            return "Music Special"
        if category == "food":
            return "Foodie Pick"
        if category == "outdoor":
            return "Outdoor Fun"
        if category in ("art", "culture", "theatre"):
            return "Cultural Gem"
        return "Must-See"

    def _fallback_why_go(self, event: Dict) -> str:
        description = event.get("description", "").strip()
        if description:
            return description[:140]
        return f"A strong local pick if you're interested in {event.get('category', 'live events').lower()}."

    def _fallback_insights(self, events: List[Dict], weather: Dict, prefs: Dict) -> str:
        top = events[0].get("title", "the top event")
        interests = ", ".join(prefs.get("interests", [])) or "general city experiences"
        weather_summary = weather.get("quick_summary", "Weather conditions are mixed")
        return (
            f"{top} leads this set of picks, with the shortlist leaning toward {interests}. "
            f"{weather_summary}, so the ranking slightly favours plans that stay practical in today's conditions."
        )
