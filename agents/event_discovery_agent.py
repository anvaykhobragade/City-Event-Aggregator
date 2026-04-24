"""
agents/event_discovery_agent.py â€” Agent 1: Event Discovery Agent
Role: Searches multiple sources (Tavily primary, DuckDuckGo fallback) for
upcoming events in a given city. Returns a raw list of discovered events.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.base_agent import BaseAgent
from config import TODAY
from tools.duckduckgo_tool import DuckDuckGoTool
from tools.tavily_tool import TavilyTool
from utils import safe_log


class EventDiscoveryAgent(BaseAgent):
    """
    Agent 1 â€” Event Discovery
    Tools used : Tavily Search (primary) + DuckDuckGo (secondary / fallback)
    Responsibility : Discover raw event data from the web for a given city.
    Output        : List of event dicts with title, date, venue, category, url, description.
    """

    CATEGORIES = [
        "music concerts",
        "food festivals",
        "art exhibitions",
        "sports events",
        "cultural festivals",
        "comedy shows",
        "theatre",
        "outdoor activities",
    ]

    def __init__(self):
        super().__init__(
            name="EventDiscoveryAgent",
            description="Discovers upcoming city events using Tavily + DuckDuckGo search tools.",
        )
        self.tavily = None
        self.ddg = None

        try:
            self.tavily = TavilyTool()
        except (EnvironmentError, ImportError) as exc:
            safe_log(
                f"[EventDiscoveryAgent] Tavily unavailable: {exc}. Will use DuckDuckGo only."
            )

        try:
            self.ddg = DuckDuckGoTool()
        except ImportError as exc:
            safe_log(f"[EventDiscoveryAgent] DuckDuckGo unavailable: {exc}.")

        if not self.tavily and not self.ddg:
            safe_log(
                "[EventDiscoveryAgent] No search tool available. Discovery will return empty results."
            )

    def discover_events(
        self,
        city: str,
        category: str = "all",
        max_events: int = 12,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Discover events for a city.
        Returns:
          {
            city, category, raw_text, events: [...], sources: [...], fetched
          }
        """
        safe_log(f"[EventDiscoveryAgent] Discovering events in '{city}' - category: {category}")

        search_results = self._multi_search(city, category, date_from, date_to)
        raw_text = self.summarise_search_results(search_results, max_chars=5000)
        events = self._extract_events_with_llm(raw_text, city, category, date_from, date_to)

        if not events:
            events = self._extract_events_from_search_results(search_results, city, category)

        if len(events) < 4 and self.ddg:
            extra_data = self.ddg.search_events(city, category, date_from, date_to)
            extra_text = self.summarise_search_results(extra_data, max_chars=3000)
            extra_events = self._extract_events_with_llm(
                extra_text, city, category, date_from, date_to
            )
            if not extra_events:
                extra_events = self._extract_events_from_search_results(
                    extra_data, city, category
                )
            events = self._merge_events(events, extra_events)

        events = events[:max_events]

        return {
            "city": city,
            "category": category,
            "events": events,
            "count": len(events),
            "sources": search_results.get("results", [])[:3],
            "fetched": datetime.now().isoformat(),
        }

    def _multi_search(
        self,
        city: str,
        category: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Try Tavily first; fall back to DuckDuckGo on any error."""
        if self.tavily:
            try:
                return self.tavily.search_events(city, category, date_from, date_to)
            except Exception as exc:
                safe_log(f"[EventDiscoveryAgent] Tavily failed ({exc}), switching to DuckDuckGo.")

        if self.ddg:
            return self.ddg.search_events(city, category, date_from, date_to)

        return {"query": "", "answer": "", "results": [], "source": "none"}

    def _extract_events_with_llm(
        self,
        raw_text: str,
        city: str,
        category: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Use Groq to parse raw search text into structured event dicts."""
        if not raw_text or raw_text == "No search results available.":
            return []

        date_constraint = ""
        if date_from and date_to:
            date_constraint = (
                f"Filter events based on the date range: {date_from} to {date_to}. "
                "If an event's exact date is unclear but it could plausibly happen within this "
                "range (e.g. month-level dates like 'April 2026'), INCLUDE IT. "
                "Do not aggressively filter out events unless they are definitely outside this range."
            )
        elif date_from:
            date_constraint = (
                f"Filter events to include only those occurring on or after {date_from}. If unclear, INCLUDE IT."
            )
        elif date_to:
            date_constraint = (
                f"Filter events to include only those occurring on or before {date_to}. If unclear, INCLUDE IT."
            )

        prompt = f"""
You are an expert event data extractor. Today's date is {TODAY}.
{date_constraint}

From the search results below, extract all upcoming events in {city}.

Return a JSON array. Each element must have EXACTLY these keys:
- "title"       : string â€” clear event name
- "date"        : string â€” date/time as found ("This Saturday", "May 10", etc.) or "Upcoming"
- "venue"       : string â€” location/venue name, or "{city} City Centre" if unknown
- "category"    : string â€” one of: Music, Food, Art, Sports, Culture, Comedy, Theatre, Outdoor, Other
- "price"       : string â€” ticket price or "Free" or "TBD"
- "description" : string â€” 1â€“2 sentence description (write from the content, be specific)
- "url"         : string â€” source URL if available, else ""
- "highlights"  : string â€” one catchy highlight or unique selling point

Filter to: category matches "{category}" (or include all if "{category}" == "all").
Include only real, verifiable events â€” no fictional ones.
Respond ONLY with the JSON array. No markdown, no preamble.

SEARCH RESULTS:
{raw_text}
"""
        response = self.generate(prompt)
        events = self.parse_json_response(response)

        if isinstance(events, list):
            return [event for event in events if isinstance(event, dict) and event.get("title")]
        return []

    def _extract_events_from_search_results(
        self,
        search_data: Dict[str, Any],
        city: str,
        requested_category: str,
    ) -> List[Dict[str, Any]]:
        """Fallback extractor when LLM parsing is unavailable or malformed."""
        results = search_data.get("results", [])
        events: List[Dict[str, Any]] = []

        for item in results:
            title = self._clean_title(item.get("title", ""))
            content = (item.get("content") or item.get("body") or "").strip()
            combined = f"{title} {content}".strip()
            if not combined:
                continue

            category = self._infer_category(combined, requested_category)
            events.append(
                {
                    "title": title or f"Upcoming event in {city}",
                    "date": self._extract_date(combined),
                    "venue": f"{city} City Centre",
                    "category": category,
                    "price": "TBD",
                    "description": (
                        content[:220] or f"Upcoming {category.lower()} event in {city}."
                    ).strip(),
                    "url": item.get("url", item.get("href", "")),
                    "highlights": self._build_highlight(title, city, category),
                }
            )

        return self._merge_events([], events)

    def _clean_title(self, title: str) -> str:
        cleaned = re.sub(r"\s+\|\s+.*$", "", title or "").strip()
        return cleaned or "Upcoming event"

    def _extract_date(self, text: str) -> str:
        patterns = [
            r"\b\d{4}-\d{2}-\d{2}\b",
            r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+\d{1,2}(?:,\s*\d{4})?\b",
            r"\b\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*(?:\s+\d{4})?\b",
            r"\b(?:today|tonight|tomorrow|this weekend|this saturday|this sunday|weekend)\b",
        ]
        lowered = text.lower()
        for pattern in patterns:
            match = re.search(pattern, lowered, flags=re.IGNORECASE)
            if match:
                return match.group(0).title()
        return "Upcoming"

    def _infer_category(self, text: str, requested_category: str) -> str:
        requested = self._canonical_category(requested_category)
        if requested != "Other":
            return requested

        keywords = {
            "Music": ["concert", "gig", "dj", "music", "live band"],
            "Food": ["food", "dining", "culinary", "restaurant", "tasting"],
            "Art": ["art", "gallery", "museum", "exhibition", "design"],
            "Sports": ["sports", "match", "marathon", "tournament", "cricket", "football"],
            "Culture": ["culture", "festival", "heritage", "traditional", "community"],
            "Comedy": ["comedy", "stand-up", "comic", "improv"],
            "Theatre": ["theatre", "theater", "play", "drama", "stage"],
            "Outdoor": ["outdoor", "park", "hike", "market", "fair"],
        }
        lowered = text.lower()
        for label, terms in keywords.items():
            if any(term in lowered for term in terms):
                return label
        return "Other"

    def _canonical_category(self, requested_category: str) -> str:
        value = (requested_category or "").lower()
        if value == "all":
            return "Other"

        mapping = {
            "music": "Music",
            "food": "Food",
            "art": "Art",
            "sport": "Sports",
            "cultural": "Culture",
            "culture": "Culture",
            "comedy": "Comedy",
            "theatre": "Theatre",
            "theater": "Theatre",
            "outdoor": "Outdoor",
        }
        for key, label in mapping.items():
            if key in value:
                return label
        return "Other"

    def _build_highlight(self, title: str, city: str, category: str) -> str:
        label = category if category != "Other" else "Live Event"
        return f"{label} pick in {city}: {title[:60]}".strip()

    def _merge_events(
        self,
        primary: List[Dict],
        secondary: List[Dict],
    ) -> List[Dict]:
        """Merge two event lists, deduplicating by title similarity."""
        seen_titles = {event["title"].lower()[:30] for event in primary}
        merged = list(primary)
        for event in secondary:
            slug = event.get("title", "").lower()[:30]
            if slug and slug not in seen_titles:
                merged.append(event)
                seen_titles.add(slug)
        return merged
