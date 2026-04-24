"""
tools/tavily_tool.py â€” Tavily Search Tool
Free tier: 1,000 searches/month. Used as primary event search.
Falls back gracefully; caller catches TavilyError.
"""

import functools
import time
from datetime import datetime
from typing import Any, Dict, Optional

from config import CACHE_TTL, MAX_RETRIES, MAX_SEARCH_RESULTS, RETRY_DELAY, TAVILY_API_KEY
from utils import safe_log

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


class TavilyTool:
    """Wrapper around Tavily Search API with retry + caching."""

    def __init__(self):
        if not TAVILY_API_KEY:
            raise EnvironmentError(
                "TAVILY_API_KEY not set. Get a free key at https://tavily.com"
            )
        try:
            from tavily import TavilyClient

            self.client = TavilyClient(api_key=TAVILY_API_KEY)
        except ImportError:
            raise ImportError("Run: pip install tavily-python")

    @_cached
    def search(
        self,
        query: str,
        max_results: int = MAX_SEARCH_RESULTS,
        search_depth: str = "basic",
        include_answer: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute a Tavily search with retry logic.
        Returns dict with keys: query, answer, results (list of dicts)
        Each result: title, url, content, score, published_date
        """
        last_err = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self.client.search(
                    query=query,
                    max_results=max_results,
                    search_depth=search_depth,
                    include_answer=include_answer,
                )
                return {
                    "query": query,
                    "answer": response.get("answer", ""),
                    "results": response.get("results", []),
                    "source": "tavily",
                    "fetched": datetime.now().isoformat(),
                }
            except Exception as exc:
                last_err = exc
                wait = RETRY_DELAY * (2 ** (attempt - 1))
                safe_log(
                    f"[TavilyTool] attempt {attempt} failed: {exc}. Retrying in {wait}s..."
                )
                time.sleep(wait)

        raise RuntimeError(f"Tavily search failed after {MAX_RETRIES} attempts: {last_err}")

    def search_events(
        self,
        city: str,
        category: str = "all",
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Convenience method: search for upcoming events in a city."""
        from config import TODAY, YEAR

        category_str = f" {category}" if category and category != "all" else ""
        date_str = ""
        if date_from and date_to:
            date_str = f" from {date_from} to {date_to}"
        elif date_from:
            date_str = f" from {date_from}"
        elif date_to:
            date_str = f" until {date_to}"

        query = (
            f"upcoming{category_str} events in {city} {YEAR}{date_str} concerts "
            f"festivals exhibitions shows {TODAY}"
        )
        return self.search(query, include_answer=True)
