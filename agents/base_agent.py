"""
agents/base_agent.py â€” Base class for all agents.
Handles Gemini 1.5 Flash setup, retry with exponential backoff,
and common prompt utilities.
"""

import json
import re
import time
from typing import Any, Dict

from groq import Groq

from config import (
    GROQ_API_KEY,
    GROQ_MODEL,
    MAX_RETRIES,
    MAX_TOKENS,
    RETRY_DELAY,
    TEMPERATURE,
)
from utils import safe_log


class BaseAgent:
    """
    All 5 agents inherit from this class.
    Provides:
      - Groq client (configured once)
      - generate(prompt) with retry + backoff
      - parse_json_response() helper
    """

    _groq_configured = False
    _groq_setup_attempted = False
    _groq_error = ""
    _shared_client = None

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.client = None
        self._llm_warning_emitted = False

        if self._configure_groq():
            self.client = BaseAgent._shared_client

    @classmethod
    def _configure_groq(cls) -> bool:
        if BaseAgent._groq_configured:
            return True

        if BaseAgent._groq_setup_attempted and BaseAgent._groq_error:
            return False

        BaseAgent._groq_setup_attempted = True
        if not GROQ_API_KEY:
            BaseAgent._groq_error = (
                "GROQ_API_KEY not set. Add it to .env to enable LLM features."
            )
            return False

        try:
            BaseAgent._shared_client = Groq(api_key=GROQ_API_KEY)
            BaseAgent._groq_configured = True
            BaseAgent._groq_error = ""
            return True
        except Exception as exc:
            BaseAgent._groq_error = str(exc)
            safe_log(f"[{cls.__name__}] Groq configuration failed: {exc}")
            return False

    def has_llm(self) -> bool:
        return self.client is not None

    def _emit_llm_warning_once(self) -> None:
        if not self._llm_warning_emitted:
            message = BaseAgent._groq_error or "Groq is unavailable."
            safe_log(f"[{self.name}] LLM unavailable; using fallback behaviour. {message}")
            self._llm_warning_emitted = True

    def generate(self, prompt: str, system_hint: str = "") -> str:
        """
        Call Groq API with retry + exponential backoff.
        Handles RateLimit errors gracefully.
        """
        if not self.client:
            self._emit_llm_warning_once()
            return ""

        messages = []
        if system_hint:
            messages.append({"role": "system", "content": system_hint})
        messages.append({"role": "user", "content": prompt})

        last_err = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self.client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=messages,
                    temperature=TEMPERATURE,
                    max_tokens=MAX_TOKENS,
                )
                if not response.choices:
                    return "I could not generate a response for this content."
                return response.choices[0].message.content
            except Exception as exc:
                err_str = str(exc).lower()
                last_err = exc

                if "quota" in err_str or "resource" in err_str or "429" in err_str:
                    wait = RETRY_DELAY * (4 ** (attempt - 1))
                    safe_log(
                        f"[{self.name}] Rate limit hit (attempt {attempt}). Waiting {wait}s..."
                    )
                    time.sleep(wait)
                else:
                    wait = RETRY_DELAY * (2 ** (attempt - 1))
                    safe_log(
                        f"[{self.name}] Error (attempt {attempt}): {exc}. Retrying in {wait}s..."
                    )
                    time.sleep(wait)

        safe_log(f"[{self.name}] All retries exhausted: {last_err}")
        return f"[{self.name}] Unable to generate response after {MAX_RETRIES} attempts."

    def parse_json_response(self, text: str) -> Any:
        """
        Extract and parse the first JSON object/array from an LLM response.
        Returns None on failure (never raises).
        """
        if not text:
            return None

        cleaned = re.sub(r"```(?:json)?", "", text).strip().strip("`").strip()
        for start_char, end_char in [("{", "}"), ("[", "]")]:
            start = cleaned.find(start_char)
            end = cleaned.rfind(end_char)
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(cleaned[start : end + 1])
                except json.JSONDecodeError:
                    pass

        try:
            return json.loads(cleaned)
        except Exception:
            return None

    def summarise_search_results(
        self,
        search_data: Dict[str, Any],
        max_chars: int = 4000,
    ) -> str:
        """Convert raw search results into a compact text block for prompts."""
        if not search_data or not search_data.get("results"):
            return "No search results available."

        parts = []
        if search_data.get("answer"):
            parts.append(f"Summary: {search_data['answer']}\n")

        for i, result in enumerate(search_data["results"], 1):
            title = result.get("title", "Untitled")
            content = result.get("content", result.get("body", ""))[:500]
            url = result.get("url", result.get("href", ""))
            published = result.get("published_date", "")

            line = f"{i}. [{title}]({url})"
            if published:
                line += f" - {published}"
            line += f"\n   {content}"
            parts.append(line)

        return "\n".join(parts)[:max_chars]

    def __repr__(self):
        return f"<{self.__class__.__name__} name='{self.name}'>"
