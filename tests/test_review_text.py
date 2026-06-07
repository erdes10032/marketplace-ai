from __future__ import annotations

import pytest

from app.reviews.text import join_review_parts, normalize_review_text


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  много   пробелов  ", "много пробелов"),
        ("", ""),
        ("нормальный текст", "нормальный текст"),
    ],
)
def test_normalize_review_text(raw: str, expected: str):
    assert normalize_review_text(raw) == expected


def test_join_review_parts_collapses_whitespace():
    assert join_review_parts(["плюсы", "  минусы  ", "коммент"]) == "плюсы минусы коммент"
