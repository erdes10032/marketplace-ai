from __future__ import annotations

import re
from typing import Any

import requests

from app.brands.normalize import normalize_brand_token, product_brand_key
from app.parsers.models import ProductSummary
from app.parsers.wb_constants import WB_CATALOG_PARAMS, WB_JSON_HEADERS, WB_SEARCH_API

_BRAND_ID_RE = re.compile(r"/brands/(\d+)-")
_BRAND_SLUG_ID_RE = re.compile(r"^(\d+)-")


class BrandResolver:
    META_API = (
        "https://static-basket-01.wbbasket.ru/vol0/data/brands-by-id/{brand_id}.json"
    )

    def __init__(self, session: requests.Session) -> None:
        self._session = session

    def resolve_name(self, brand_input: str) -> str:
        candidate = brand_input.strip()
        if candidate.startswith(("http://", "https://")):
            match = _BRAND_ID_RE.search(candidate)
            if match:
                meta = self._fetch_meta(int(match.group(1)))
                if meta and meta.get("name"):
                    return str(meta["name"])
            slug = candidate.rstrip("/").split("/")[-1]
            return slug.replace("-", " ")
        return candidate

    def canonical_key(self, brand_input: str) -> str:
        return normalize_brand_token(self.resolve_name(brand_input))

    def resolve_id(self, brand_input: str) -> int | None:
        candidate = brand_input.strip()
        if candidate.startswith(("http://", "https://")):
            match = _BRAND_ID_RE.search(candidate)
            if match:
                return int(match.group(1))
            slug = candidate.rstrip("/").split("/")[-1]
            slug_match = _BRAND_SLUG_ID_RE.match(slug)
            if slug_match:
                return int(slug_match.group(1))

        return self._lookup_brand_id_by_name(self.resolve_name(brand_input))

    def matches_product(self, expected_key: str, product: ProductSummary) -> bool:
        if not expected_key:
            return False
        product_key = product_brand_key(product.brand_name, product.title)
        return product_key == expected_key

    def _lookup_brand_id_by_name(self, brand_name: str) -> int | None:
        target_key = normalize_brand_token(brand_name)
        if not target_key:
            return None

        params = {
            **WB_CATALOG_PARAMS,
            "page": 1,
            "query": brand_name,
            "resultset": "catalog",
            "sort": "popular",
            "spp": 30,
        }
        try:
            response = self._session.get(
                WB_SEARCH_API,
                params=params,
                timeout=30,
                headers=WB_JSON_HEADERS,
            )
            if response.status_code != 200:
                return None
            payload = response.json()
        except (requests.RequestException, ValueError):
            return None

        for row in payload.get("products") or []:
            brand = str(row.get("brand") or "").strip()
            if normalize_brand_token(brand) != target_key:
                continue
            brand_id = row.get("brandId")
            if brand_id is not None:
                return int(brand_id)
        return None

    def _fetch_meta(self, brand_id: int) -> dict[str, Any] | None:
        url = self.META_API.format(brand_id=brand_id)
        try:
            response = self._session.get(url, timeout=15)
            if response.status_code == 200:
                payload = response.json()
                if isinstance(payload, dict):
                    return payload
        except (requests.RequestException, ValueError):
            pass
        return None
