"""
tools/duckduckgo_tool.py — DuckDuckGo search (free, no API key needed).
Used as primary backup when Tavily quota is hit.
"""

import functools
import time
from datetime import datetime
from typing import Any, Dict

from config import CACHE_TTL, MAX_RETRIES, MAX_SEARCH_RESULTS, RETRY_DELAY
from utils import safe_log

try:
    from ddgs import DDGS
except ImportError:
    DDGS = None  # Graceful degradation if package missing

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


class DuckDuckGoTool:
    """DuckDuckGo text search — completely free, no rate limits enforced."""

    def __init__(self):
        if DDGS is None:
            raise ImportError("Run: pip install ddgs")

    @_cached
    def search(self, query: str, max_results: int = MAX_SEARCH_RESULTS) -> Dict[str, Any]:
        """Search DuckDuckGo and return normalised results."""
        last_err = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                with DDGS() as ddgs:
                    raw = list(ddgs.text(query, max_results=max_results))
                results = [
                    {
                        "title":   r.get("title", ""),
                        "url":     r.get("href", ""),
                        "content": r.get("body", ""),
                        "score":   None,
                        "published_date": None,
                    }
                    for r in raw
                ]
                return {
                    "query":   query,
                    "answer":  "",
                    "results": results,
                    "source":  "duckduckgo",
                    "fetched": datetime.now().isoformat(),
                }
            except Exception as exc:
                last_err = exc
                wait = RETRY_DELAY * (2 ** (attempt - 1))
                safe_log(f"[DuckDuckGoTool] attempt {attempt} failed: {exc}. Retrying in {wait}s...")
                time.sleep(wait)

        safe_log("[DuckDuckGoTool] All retries exhausted. Returning empty results.")
        return {"query": query, "answer": "", "results": [], "source": "duckduckgo_failed",
                "fetched": datetime.now().isoformat()}

    def search_events(self, city: str, category: str = "all",
                      date_from: str = None, date_to: str = None) -> Dict[str, Any]:
        """Search for events in a city."""
        from config import TODAY, YEAR
        cat_str  = f" {category}" if category and category != "all" else ""
        date_str = ""
        if date_from and date_to:
            date_str = f" from {date_from} to {date_to}"
        elif date_from:
            date_str = f" from {date_from}"
        elif date_to:
            date_str = f" until {date_to}"
        query = f"upcoming{cat_str} events {city} {YEAR}{date_str} {TODAY}"
        return self.search(query)
