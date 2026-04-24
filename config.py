"""
config.py — Central configuration for City Event Aggregator
All API keys, model settings, and constants live here.
"""

import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(override=True)

# ── API Keys ─────────────────────────────────────────────────────────────────
GROQ_API_KEY        = os.getenv("GROQ_API_KEY", "")
TAVILY_API_KEY      = os.getenv("TAVILY_API_KEY", "")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

# ── Groq Model ───────────────────────────────────────────────────────────────
GROQ_MODEL   = "llama-3.3-70b-versatile"
TEMPERATURE  = 0.7
MAX_TOKENS   = 2048

# ── Resilience ────────────────────────────────────────────────────────────────
MAX_RETRIES  = 3
RETRY_DELAY  = 2    # seconds between retries (exponential backoff applied)
CACHE_TTL    = 300  # 5-minute in-memory cache for search results

# ── Search Config ─────────────────────────────────────────────────────────────
MAX_SEARCH_RESULTS = 6
EVENTS_LOOKAHEAD   = 7   # days ahead to search for events

# ── Runtime Date/Time ─────────────────────────────────────────────────────────
TODAY     = datetime.now().strftime("%B %d, %Y")
TODAY_ISO = datetime.now().strftime("%Y-%m-%d")
YEAR      = datetime.now().year
MONTH     = datetime.now().strftime("%B")

# ── Validation ────────────────────────────────────────────────────────────────
def validate_keys() -> dict:
    """Returns a dict of which keys are configured."""
    return {
        "groq":         bool(GROQ_API_KEY),
        "tavily":       bool(TAVILY_API_KEY),
        "openweather":  bool(OPENWEATHER_API_KEY),
    }
