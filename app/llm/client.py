from __future__ import annotations

from typing import Any

import requests

from app.config import get_settings
from app.llm.exceptions import LLMConnectionError, LLMResponseError
from app.llm.text_cleaning import clean_llm_text

PRODUCT_ANALYST_SYSTEM = (
    "Ты аналитик отзывов на товары (одежда, детские товары) на маркетплейсе. "
    "Отвечай только на русском языке. Не упоминай платформу, сайт, отзывы как "
    "активность, пользователей или идентификацию. Фокус — дефекты и проблемы товара."
)


class OllamaClient:
    def __init__(
        self,
        model: str | None = None,
        system_prompt: str = PRODUCT_ANALYST_SYSTEM,
        timeout_sec: float | None = None,
    ) -> None:
        settings = get_settings()
        self.model = model or settings.ollama_model
        self.system_prompt = system_prompt
        self.timeout_sec = timeout_sec or settings.ollama_timeout_sec

    def chat(self, prompt: str) -> str:
        try:
            import ollama
        except ImportError as exc:
            raise LLMConnectionError(
                "Пакет ollama не установлен. Установите зависимости проекта."
            ) from exc

        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt},
                ],
                options={"timeout": int(self.timeout_sec * 1000)},
            )
        except (requests.RequestException, TimeoutError, OSError) as exc:
            raise LLMConnectionError(
                f"Не удалось получить ответ от Ollama (модель {self.model})."
            ) from exc
        except Exception as exc:
            message = str(exc).lower()
            if any(
                token in message
                for token in ("connection", "timeout", "refused", "unreachable")
            ):
                raise LLMConnectionError(
                    f"Ollama недоступна для модели {self.model}."
                ) from exc
            raise LLMResponseError(
                f"Ollama вернула ошибку для модели {self.model}: {exc}"
            ) from exc

        content = self._extract_message_content(response)
        cleaned = clean_llm_text(content.strip())
        if not cleaned:
            raise LLMResponseError("Ollama вернула пустой ответ.")
        return cleaned

    @staticmethod
    def _extract_message_content(response: Any) -> str:
        if isinstance(response, dict):
            message = response.get("message") or {}
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str):
                    return content
        message = getattr(response, "message", None)
        content = getattr(message, "content", None) if message is not None else None
        if isinstance(content, str):
            return content
        raise LLMResponseError("Ollama вернула ответ без текста сообщения.")
