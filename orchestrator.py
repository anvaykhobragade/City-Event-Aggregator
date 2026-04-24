"""
orchestrator.py â€” Multi-Agent Orchestrator
Coordinates all 5 agents in sequence, handles errors between stages,
and returns a unified result object for the UI.
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.curator_agent import EventCuratorAgent
from agents.event_discovery_agent import EventDiscoveryAgent
from agents.judge_agent import JudgeAgent
from agents.recommendation_agent import RecommendationAgent
from agents.weather_agent import WeatherAgent
from utils import safe_log


class CityEventOrchestrator:
    """
    Orchestrates all 5 agents for the City Event Aggregator.

    Usage:
        orch   = CityEventOrchestrator()
        result = orch.run(city="Mumbai", category="music", preferences={...})
    """

    def __init__(self):
        safe_log("Initializing City Event Aggregator agents...")
        self._discovery = None
        self._weather = None
        self._curator = None
        self._recommender = None
        self._judge = None
        self._init_agents()

    def _init_agents(self) -> None:
        errors = []
        try:
            self._discovery = EventDiscoveryAgent()
            safe_log("  [OK] EventDiscoveryAgent ready")
        except Exception as exc:
            errors.append(f"EventDiscoveryAgent: {exc}")
            safe_log(f"  [ERROR] EventDiscoveryAgent: {exc}")

        try:
            self._weather = WeatherAgent()
            safe_log("  [OK] WeatherAgent ready")
        except Exception as exc:
            errors.append(f"WeatherAgent: {exc}")
            safe_log(f"  [ERROR] WeatherAgent: {exc}")

        try:
            self._curator = EventCuratorAgent()
            safe_log("  [OK] EventCuratorAgent ready")
        except Exception as exc:
            errors.append(f"EventCuratorAgent: {exc}")
            safe_log(f"  [ERROR] EventCuratorAgent: {exc}")

        try:
            self._recommender = RecommendationAgent()
            safe_log("  [OK] RecommendationAgent ready")
        except Exception as exc:
            errors.append(f"RecommendationAgent: {exc}")
            safe_log(f"  [ERROR] RecommendationAgent: {exc}")

        try:
            self._judge = JudgeAgent()
            safe_log("  [OK] JudgeAgent ready")
        except Exception as exc:
            errors.append(f"JudgeAgent: {exc}")
            safe_log(f"  [ERROR] JudgeAgent: {exc}")

        if errors:
            safe_log(f"\n[WARN] {len(errors)} agent(s) failed to initialise. Check your .env file.")

    def run(
        self,
        city: str,
        category: str = "all",
        preferences: Optional[Dict] = None,
        run_judge: bool = True,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute the full 5-agent pipeline.
        Returns a unified result dict with all agent outputs + pipeline metadata.
        """
        if not preferences:
            preferences = {
                "interests": ["music", "food"],
                "budget": "moderate",
                "group_type": "solo",
            }

        pipeline_start = time.time()
        result: Dict[str, Any] = {
            "city": city,
            "category": category,
            "preferences": preferences,
            "date_from": date_from,
            "date_to": date_to,
            "pipeline": {},
            "errors": [],
            "timing": {},
            "started_at": datetime.now().isoformat(),
        }

        t0 = time.time()
        safe_log(f"\n{'=' * 60}")
        safe_log(f"Stage 1/5 - Event Discovery ({city}, {category})")
        discovery_result = self._run_stage(
            "discovery",
            (
                lambda: self._discovery.discover_events(
                    city, category, date_from=date_from, date_to=date_to
                )
            )
            if self._discovery
            else None,
            fallback={"events": [], "count": 0, "city": city},
            result=result,
        )
        result["pipeline"]["discovery"] = discovery_result
        result["timing"]["discovery"] = round(time.time() - t0, 2)
        raw_events = discovery_result.get("events", [])
        safe_log(f"  -> Found {len(raw_events)} raw events ({result['timing']['discovery']}s)")

        t0 = time.time()
        safe_log(f"\nStage 2/5 - Weather Analysis ({city})")
        weather_result = self._run_stage(
            "weather",
            (
                lambda: self._weather.analyse_weather(
                    city,
                    date_from=date_from,
                    date_to=date_to,
                )
            )
            if self._weather
            else None,
            fallback={
                "current": {},
                "forecast": [],
                "advice": "Weather data unavailable",
                "outdoor_score": 5,
                "quick_summary": "",
            },
            result=result,
        )
        result["pipeline"]["weather"] = weather_result
        result["timing"]["weather"] = round(time.time() - t0, 2)
        safe_log(
            f"  -> {weather_result.get('quick_summary', 'Weather fetched')} "
            f"({result['timing']['weather']}s)"
        )

        t0 = time.time()
        safe_log("\nStage 3/5 - Event Curation")
        curation_result = self._run_stage(
            "curation",
            (
                lambda: self._curator.curate_events(
                    raw_events,
                    weather_result,
                    preferences,
                )
            )
            if self._curator
            else None,
            fallback={
                "curated_events": raw_events[:8],
                "insights": "",
                "top_pick": raw_events[0] if raw_events else None,
            },
            result=result,
        )
        result["pipeline"]["curation"] = curation_result
        result["timing"]["curation"] = round(time.time() - t0, 2)
        curated_events = curation_result.get("curated_events", raw_events[:8])
        safe_log(f"  -> Curated to {len(curated_events)} events ({result['timing']['curation']}s)")

        t0 = time.time()
        safe_log("\nStage 4/5 - Personalised Recommendations")
        reco_result = self._run_stage(
            "recommendations",
            (
                lambda: self._recommender.generate_recommendations(
                    city,
                    curated_events,
                    weather_result,
                    preferences,
                )
            )
            if self._recommender
            else None,
            fallback={
                "day_plan": "Recommendations unavailable.",
                "top_3_events": curated_events[:3],
                "itinerary": [],
            },
            result=result,
        )
        result["pipeline"]["recommendations"] = reco_result
        result["timing"]["recommendations"] = round(time.time() - t0, 2)
        safe_log(f"  -> Day plan generated ({result['timing']['recommendations']}s)")

        if run_judge:
            t0 = time.time()
            safe_log("\nStage 5/5 - Quality Evaluation (LLM-as-Judge)")
            judge_result = self._run_stage(
                "evaluation",
                (
                    lambda: self._judge.evaluate(
                        city,
                        preferences,
                        curated_events,
                        weather_result,
                        reco_result,
                    )
                )
                if self._judge
                else None,
                fallback={
                    "overall_score": 0,
                    "grade": "N/A",
                    "judge_summary": "Evaluation unavailable.",
                },
                result=result,
            )
            result["pipeline"]["evaluation"] = judge_result
            result["timing"]["evaluation"] = round(time.time() - t0, 2)
            safe_log(
                f"  -> Grade: {judge_result.get('grade', '?')} "
                f"({judge_result.get('overall_score', 0)}/10) "
                f"({result['timing']['evaluation']}s)"
            )

        total_time = round(time.time() - pipeline_start, 2)
        result["timing"]["total"] = total_time
        result["completed_at"] = datetime.now().isoformat()
        result["success"] = len(result["errors"]) == 0

        safe_log(f"\n{'=' * 60}")
        safe_log(
            f"Pipeline complete in {total_time}s | "
            f"Events: {len(curated_events)} | "
            f"Errors: {len(result['errors'])}"
        )

        return result

    def _run_stage(
        self,
        stage_name: str,
        fn,
        fallback: Dict,
        result: Dict,
    ) -> Dict:
        """Execute a pipeline stage, catch errors, and return fallback on failure."""
        if fn is None:
            result["errors"].append(f"{stage_name}: agent not initialised")
            return fallback
        try:
            return fn()
        except Exception as exc:
            err_msg = f"{stage_name}: {exc}"
            safe_log(f"  [WARN] {err_msg}")
            result["errors"].append(err_msg)
            return fallback

    def get_supported_cities(self) -> List[str]:
        """Popular Indian + global cities pre-configured."""
        return [
            "Mumbai",
            "Delhi",
            "Bangalore",
            "Hyderabad",
            "Chennai",
            "Kolkata",
            "Pune",
            "Ahmedabad",
            "Jaipur",
            "Goa",
            "Nagpur",
            "Lucknow",
            "Chandigarh",
            "Kochi",
            "Indore",
            "London",
            "New York",
            "Singapore",
            "Dubai",
            "Tokyo",
            "Paris",
            "Sydney",
            "Toronto",
            "Amsterdam",
            "Bangkok",
        ]

    def get_supported_categories(self) -> List[str]:
        return [
            "all",
            "Music Concerts",
            "Food Festivals",
            "Art Exhibitions",
            "Sports Events",
            "Cultural Festivals",
            "Comedy Shows",
            "Theatre",
            "Outdoor Activities",
            "Markets & Fairs",
        ]
