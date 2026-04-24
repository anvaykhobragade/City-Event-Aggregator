"""
agents/judge_agent.py â€” Agent 5: LLM-as-Judge Agent
Role: Evaluates the quality of the full recommendation output using a
structured rubric. Returns scores, feedback, and an overall grade.
This is the evaluation / QA layer of the multi-agent system.
"""

from datetime import datetime
from typing import Any, Dict, List

from agents.base_agent import BaseAgent
from config import TODAY
from utils import safe_log


RUBRIC = {
    "relevance": {
        "description": "Events match user interests and city",
        "weight": 0.25,
        "criteria": [
            "Events are actually in the specified city",
            "Categories align with user preferences",
            "Price range suits user budget",
        ],
    },
    "accuracy": {
        "description": "Information is current and factual",
        "weight": 0.20,
        "criteria": [
            "Dates are realistic and upcoming",
            "Venues are real places in the city",
            "No obviously fabricated events",
        ],
    },
    "weather_integration": {
        "description": "Weather data is meaningfully used",
        "weight": 0.20,
        "criteria": [
            "Outdoor events flagged appropriately based on weather",
            "Weather tips are practical and specific",
            "Day plan accounts for weather conditions",
        ],
    },
    "completeness": {
        "description": "Output covers all required information",
        "weight": 0.15,
        "criteria": [
            "Each event has title, date, venue, price, description",
            "Day plan covers morning / afternoon / evening",
            "Transport and dining tips included",
        ],
    },
    "usefulness": {
        "description": "Would a real user find this helpful?",
        "weight": 0.20,
        "criteria": [
            "Recommendations are actionable",
            "Writing is clear and engaging",
            "Itinerary is realistic and doable",
        ],
    },
}


class JudgeAgent(BaseAgent):
    """
    Agent 5 â€” LLM-as-Judge (Quality Evaluator)
    Tool used      : Groq
    Responsibility : Evaluate recommendation quality using a structured rubric.
    Output         : Scores per dimension, overall grade, feedback, improvement tips.
    """

    def __init__(self):
        super().__init__(
            name="JudgeAgent",
            description="Evaluates recommendation quality using a multi-dimensional rubric.",
        )

    def evaluate(
        self,
        city: str,
        user_preferences: Dict[str, Any],
        events: List[Dict[str, Any]],
        weather: Dict[str, Any],
        recommendation: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Run full evaluation.
        Returns:
          {
            scores: {dimension: {score, feedback}},
            overall_score: float (0-10),
            grade: str (A+/A/B/C/D),
            strengths: [...],
            improvements: [...],
            judge_summary: str,
            rubric: {...},
            fetched: str
          }
        """
        safe_log(f"[JudgeAgent] Evaluating recommendations for {city}...")

        scores = self._score_all_dimensions(
            city, user_preferences, events, weather, recommendation
        )
        overall = self._weighted_score(scores)
        grade = self._letter_grade(overall)
        strengths, improvements = self._extract_feedback(scores)
        summary = self._generate_summary(city, overall, grade, strengths, improvements)

        return {
            "scores": scores,
            "overall_score": round(overall, 1),
            "grade": grade,
            "strengths": strengths,
            "improvements": improvements,
            "judge_summary": summary,
            "rubric": RUBRIC,
            "fetched": datetime.now().isoformat(),
        }

    def _score_all_dimensions(
        self,
        city: str,
        prefs: Dict,
        events: List[Dict],
        weather: Dict,
        reco: Dict,
    ) -> Dict[str, Dict]:
        """Score each rubric dimension using Groq."""
        events_summary = "\n".join(
            f"  - {event.get('title', 'Unknown')} | {event.get('category')} | "
            f"{event.get('date')} | {event.get('venue')} | {event.get('price')}"
            for event in events[:6]
        )
        weather_now = weather.get("quick_summary", "No weather data")
        day_plan_snip = (
            reco.get("day_plan", "")[:500] if reco.get("day_plan") else "No day plan generated"
        )
        prefs_str = (
            f"City: {city} | Interests: {', '.join(prefs.get('interests', []))} | "
            f"Budget: {prefs.get('budget', 'moderate')} | Group: {prefs.get('group_type', 'solo')}"
        )
        dimensions_str = "\n".join(
            f"- {dimension}: {info['description']} (weight {int(info['weight'] * 100)}%)"
            for dimension, info in RUBRIC.items()
        )

        prompt = f"""
Today is {TODAY}. You are a strict but fair AI output evaluator.

USER PROFILE: {prefs_str}
WEATHER: {weather_now}

EVENTS RECOMMENDED ({len(events)} total):
{events_summary}

DAY PLAN (excerpt):
{day_plan_snip}

ITINERARY ITEMS: {len(reco.get('itinerary', []))} slots
HAS DINING TIPS: {'Yes' if reco.get('dining_tips') else 'No'}
HAS TRANSPORT TIPS: {'Yes' if reco.get('transport_tips') else 'No'}

Evaluate the above output on these 5 dimensions:
{dimensions_str}

For EACH dimension, provide a score from 1-10 and one sentence of specific feedback.

Return a JSON object with this exact structure:
{{
  "relevance":           {{"score": 0, "feedback": ""}},
  "accuracy":            {{"score": 0, "feedback": ""}},
  "weather_integration": {{"score": 0, "feedback": ""}},
  "completeness":        {{"score": 0, "feedback": ""}},
  "usefulness":          {{"score": 0, "feedback": ""}}
}}

Be honest and critical. Score 8+ only if truly excellent.
Respond ONLY with the JSON object.
"""
        response = self.generate(prompt)
        parsed = self.parse_json_response(response)

        if isinstance(parsed, dict) and "relevance" in parsed:
            return parsed

        return self._fallback_scores(events, weather, reco)

    def _fallback_scores(self, events: List[Dict], weather: Dict, reco: Dict) -> Dict[str, Dict]:
        """Rule-based fallback scoring if LLM JSON parsing fails."""
        has_events = len(events) > 0
        has_weather = bool(weather.get("quick_summary"))
        has_plan = bool(reco.get("day_plan"))
        has_dining = bool(reco.get("dining_tips"))
        has_transport = bool(reco.get("transport_tips"))

        return {
            "relevance": {
                "score": 7 if has_events else 3,
                "feedback": "Based on available event coverage",
            },
            "accuracy": {
                "score": 6 if has_events else 3,
                "feedback": "Unable to fully verify every detail automatically",
            },
            "weather_integration": {
                "score": 8 if has_weather else 2,
                "feedback": "Weather data present" if has_weather else "No weather data",
            },
            "completeness": {
                "score": sum([has_events, has_plan, has_dining, has_transport]) * 2 + 2,
                "feedback": "Scored from section coverage",
            },
            "usefulness": {
                "score": 7 if has_plan else 4,
                "feedback": "Day plan present" if has_plan else "Limited output",
            },
        }

    def _weighted_score(self, scores: Dict[str, Dict]) -> float:
        """Compute weighted overall score."""
        total = 0.0
        for dimension, info in RUBRIC.items():
            raw_score = scores.get(dimension, {}).get("score", 5)
            total += float(raw_score) * info["weight"]
        return total

    def _letter_grade(self, score: float) -> str:
        if score >= 9.0:
            return "A+"
        if score >= 8.0:
            return "A"
        if score >= 7.0:
            return "B+"
        if score >= 6.0:
            return "B"
        if score >= 5.0:
            return "C"
        return "D"

    def _extract_feedback(self, scores: Dict[str, Dict]) -> tuple:
        """Extract top strengths and improvement areas."""
        sorted_dims = sorted(
            scores.items(),
            key=lambda item: item[1].get("score", 0),
            reverse=True,
        )
        strengths = [
            f"{dimension.replace('_', ' ').title()} ({info['score']}/10): {info['feedback']}"
            for dimension, info in sorted_dims[:2]
        ]
        improvements = [
            f"{dimension.replace('_', ' ').title()} ({info['score']}/10): {info['feedback']}"
            for dimension, info in sorted_dims[-2:]
            if info.get("score", 10) < 8
        ]
        return strengths, improvements

    def _generate_summary(
        self,
        city: str,
        overall: float,
        grade: str,
        strengths: List[str],
        improvements: List[str],
    ) -> str:
        """Generate a final judge verdict paragraph."""
        strengths_str = "; ".join(strengths[:2])
        improvements_str = (
            "; ".join(improvements[:2]) if improvements else "minor refinements possible"
        )

        prompt = f"""
You are an AI quality evaluator summarising a city event recommendation system's output.

City: {city} | Date: {TODAY}
Overall score: {overall:.1f}/10 | Grade: {grade}
Strengths: {strengths_str}
Areas for improvement: {improvements_str}

Write a 2-3 sentence judge's verdict in an authoritative but constructive tone.
Mention the score and grade. Highlight the main strength and the main improvement area.
Be direct. No bullet points.
"""
        generated = self.generate(prompt).strip()
        return generated or (
            f"The recommendation set for {city} earned a {overall:.1f}/10 ({grade}). "
            f"Its strongest area is {strengths[0] if strengths else 'overall structure'}, while the main opportunity "
            f"is {improvements[0] if improvements else 'sharpening the weaker sections'}."
        )

    def get_rubric_display(self) -> List[Dict[str, str]]:
        """Return rubric in display-friendly format."""
        return [
            {
                "dimension": dimension.replace("_", " ").title(),
                "description": info["description"],
                "weight": f"{int(info['weight'] * 100)}%",
            }
            for dimension, info in RUBRIC.items()
        ]
