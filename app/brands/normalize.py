from __future__ import annotations

import re

_BRAND_TOKEN_RE = re.compile(r"[^a-zа-я0-9]+", re.IGNORECASE)

JS_NORMALIZE_BRAND = r"""
const normalizeBrand = (v) =>
    String(v || "").toLowerCase().replace(/[^a-zа-я0-9]+/g, "");
"""


def normalize_brand_token(value: str) -> str:
    return _BRAND_TOKEN_RE.sub("", (value or "").lower())


def product_brand_key(brand_name: str | None, title: str) -> str | None:
    brand = (brand_name or "").strip()
    if brand:
        return normalize_brand_token(brand)
    if " / " in title:
        return normalize_brand_token(title.split(" / ", 1)[0])
    return None
