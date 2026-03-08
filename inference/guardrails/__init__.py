"""Input and output guardrails for the RAG pipeline."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shared.config import Settings

logger = logging.getLogger(__name__)

REFUSAL_MESSAGE = (
    "I can only answer questions about our products and support policies. "
    "Please ask a question related to customer support."
)

FALLBACK_OUTPUT = (
    "I'm sorry, I couldn't generate a suitable response. "
    "Please try rephrasing your question or contact support directly."
)

# Heuristic patterns for prompt injection (case-insensitive)
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|above|prior)\s+instructions",
    r"disregard\s+(all\s+)?(previous|above|prior)",
    r"forget\s+(everything|all)\s+(you\s+)?(know|learned)",
    r"you\s+are\s+now\s+(a|in)\s+",
    r"pretend\s+(you\s+are|to\s+be)",
    r"act\s+as\s+if\s+you\s+(are|were)",
    r"system\s*:\s*",
    r"\[INST\]|\[/INST\]",
    r"<\|im_start\|>|<\|im_end\|>",
    r"jailbreak|prompt\s+injection",
]


def _check_prompt_injection(text: str) -> bool:
    """Return True if prompt injection is detected."""
    lower = text.lower()
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, lower, re.IGNORECASE):
            return True
    return False


def validate_input(
    text: str,
    *,
    max_length: int = 2000,
    check_injection: bool = True,
) -> tuple[bool, str]:
    """
    Validate user input before sending to the LLM.
    Returns (passed, message). If passed is False, message is the refusal to show.
    """
    if not text or not text.strip():
        return False, "Please provide a question."

    if len(text) > max_length:
        return False, f"Your message exceeds the maximum length of {max_length} characters."

    if check_injection and _check_prompt_injection(text):
        logger.warning("Prompt injection detected in input")
        return False, REFUSAL_MESSAGE

    return True, ""


def validate_output(
    text: str,
    *,
    max_length: int = 4000,
) -> tuple[bool, str]:
    """
    Validate LLM output before returning to the user.
    Returns (passed, output). If passed is False, output is sanitized/fallback.
    """
    if not text or not text.strip():
        return False, FALLBACK_OUTPUT

    if len(text) > max_length:
        logger.warning("Output exceeded max length, truncating")
        return True, text[: max_length - 50] + "\n\n[Response truncated.]"

    return True, text


def get_guardrails(
    settings: Settings | None = None,
) -> tuple[bool, int, int]:
    """
    Get guardrails config from settings.
    Returns (enabled, input_max_len, output_max_len).
    """
    if settings is None:
        try:
            from shared.config import get_settings
            settings = get_settings()
        except Exception:
            return True, 2000, 4000

    enabled = getattr(settings, "guardrails_enabled", True)
    input_max = getattr(settings, "guardrails_input_max_len", 2000)
    output_max = getattr(settings, "guardrails_output_max_len", 4000)
    return enabled, input_max, output_max
