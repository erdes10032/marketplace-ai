from __future__ import annotations

import re

_WS_RE = re.compile(r"\s+")


def normalize_review_text(text: str) -> str:
    return _WS_RE.sub(" ", (text or "")).strip()


def join_review_parts(parts: list[str]) -> str:
    return normalize_review_text(" ".join(parts))
