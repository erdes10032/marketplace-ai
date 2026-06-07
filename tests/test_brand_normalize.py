from __future__ import annotations

import pytest

from app.brands.normalize import normalize_brand_token, product_brand_key


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("CITY VIBE", "cityvibe"),
        ("BLACK-BOX", "blackbox"),
        ("OneTechCam", "onetechcam"),
    ],
)
def test_normalize_brand_token(value: str, expected: str):
    assert normalize_brand_token(value) == expected


def test_product_brand_key_prefers_brand_name():
    assert product_brand_key("CITY VIBE", "Другой бренд / Товар") == "cityvibe"


def test_product_brand_key_falls_back_to_title_prefix():
    assert product_brand_key(None, "BLACK BOX / Очки") == "blackbox"


def test_product_brand_key_returns_none_without_brand():
    assert product_brand_key(None, "Очки без бренда") is None
