from __future__ import annotations


class LLMError(Exception):
    """Base error for LLM client failures."""


class LLMConnectionError(LLMError):
    """Ollama is unreachable or the request timed out."""


class LLMResponseError(LLMError):
    """Ollama responded, but the payload was empty or unusable."""
