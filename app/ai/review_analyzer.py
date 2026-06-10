from __future__ import annotations

from collections import Counter

from app.llm.client import OllamaClient
from app.llm.exceptions import LLMError
from app.llm.text_cleaning import cyrillic_ratio, is_bad_product_title
from app.utils.log import log


class ReviewAnalyzer:
    def __init__(self, llm: OllamaClient | None = None) -> None:
        self._llm = llm or OllamaClient()

    def generate_cluster_title(self, reviews: list[str]) -> str:
        if not reviews:
            return "Неопределенная проблема"

        reviews_text = "\n".join(reviews[:30])
        prompt = f"""
По отзывам покупателей определи одну конкретную проблему ТОВАРА
(размер, посадка, швы, ткань, цвет, запах, комплектация, брак, линяет, колется и т.п.).

Запрещено: платформа, сайт, «активность в отзыве», пользователи, идентификация.

Отзывы:
{reviews_text}

Ответ: 2-5 слов, только формулировка проблемы товара, без markdown.
"""
        try:
            answer = self._llm.chat(prompt)
        except LLMError as exc:
            log("Analysis", f"LLM не сгенерировала заголовок кластера: {exc}")
            return self._fallback_cluster_title(reviews)

        if not is_bad_product_title(answer):
            return answer
        log("Analysis", "LLM вернула некорректный заголовок кластера, использую fallback.")
        return self._fallback_cluster_title(reviews)

    def describe_root_cause(self, cluster_name: str, reviews: list[str]) -> str:
        if not reviews:
            return "Недостаточно данных для выявления причины."

        reviews_text = "\n".join(reviews[:40])
        prompt = f"""
Проблема товара: {cluster_name}

Отзывы покупателей:
{reviews_text}

Найди скрытую первопричину в продукте или производстве (не пересказывай жалобы).

Ответ на русском, без markdown, ровно 2 предложения:
1) Первопричина.
2) Почему это критично для бренда.
"""
        try:
            answer = self._llm.chat(prompt)
        except LLMError as exc:
            log("Analysis", f"LLM не описала первопричину для «{cluster_name}»: {exc}")
            return self._fallback_root_cause(cluster_name)

        if cyrillic_ratio(answer) >= 0.5:
            return answer
        log("Analysis", f"LLM вернула слабый текст для «{cluster_name}», использую fallback.")
        return self._fallback_root_cause(cluster_name)

    @staticmethod
    def _fallback_cluster_title(reviews: list[str]) -> str:
        stop = {
            "очень", "плохо", "хорошо", "товар", "брак", "размер", "цвет",
            "этот", "этого", "который", "просто", "вообще", "полностью",
        }
        words: list[str] = []
        for text in reviews[:40]:
            words.extend(token.strip(".,!?;:\"'()[]{}").lower() for token in text.split())
        words = [w for w in words if len(w) >= 4 and w not in stop]
        if not words:
            return "Повторяющаяся проблема"
        top = [word for word, _ in Counter(words).most_common(3)]
        return " ".join(top).strip().capitalize()

    @staticmethod
    def _fallback_root_cause(cluster_name: str) -> str:
        return (
            f"Проблема «{cluster_name}» системно повторяется в негативных отзывах и указывает "
            f"на дефект товара или контроля качества. Для бренда это критично, потому что "
            f"снижает оценки, возвраты и доверие к линейке."
        )
