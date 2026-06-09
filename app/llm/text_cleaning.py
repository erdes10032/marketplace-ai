from __future__ import annotations

import re

_CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")
_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]+")
_BAD_TITLE_RE = re.compile(
    r"идентиф|пользовател|активност|платформ|"
    r"отзыв[аеуоы]?|сайт|wildberries|маркетплейс|память|memory|"
    r"логин|авториз|регистрац",
    re.IGNORECASE,
)


def cyrillic_ratio(text: str) -> float:
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return 0.0
    cyrillic = sum(1 for ch in letters if _CYRILLIC_RE.match(ch))
    return cyrillic / len(letters)


def clean_llm_text(text: str) -> str:
    if not text:
        return text

    cleaned = _CJK_RE.sub("", text)
    cleaned = cleaned.replace("**", "").replace("__", "")
    cleaned = re.sub(r"^#{1,6}\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^###\s*Ответ:\s*", "", cleaned, flags=re.IGNORECASE | re.MULTILINE)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()

    if cyrillic_ratio(cleaned) < 0.35:
        russian_lines = [
            line.strip()
            for line in cleaned.splitlines()
            if cyrillic_ratio(line) >= 0.5
        ]
        if russian_lines:
            cleaned = "\n".join(russian_lines)

    return cleaned.strip()


def is_bad_product_title(title: str) -> bool:
    if not title or _BAD_TITLE_RE.search(title):
        return True
    return cyrillic_ratio(title) < 0.6
