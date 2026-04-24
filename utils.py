"""Shared runtime helpers for resilient console logging."""

from __future__ import annotations

import sys
from typing import Any


def safe_text(value: Any, encoding: str | None = None) -> str:
    """Convert any value into a string the active console can safely print."""
    text = value if isinstance(value, str) else str(value)
    target_encoding = encoding or getattr(sys.stdout, "encoding", None) or "utf-8"
    return text.encode(target_encoding, errors="replace").decode(
        target_encoding, errors="replace"
    )


def safe_log(*parts: Any, sep: str = " ", end: str = "\n") -> None:
    """Write to stdout without crashing on limited terminal encodings."""
    text = sep.join("" if part is None else str(part) for part in parts)
    stream = getattr(sys, "stdout", None)
    if stream is None:
        return

    try:
        stream.write(text + end)
    except UnicodeEncodeError:
        stream.write(safe_text(text) + end)
    except Exception:
        try:
            print(safe_text(text), end=end)
        except Exception:
            return

    try:
        stream.flush()
    except Exception:
        pass
