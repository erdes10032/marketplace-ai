from __future__ import annotations

from typing import Any

import requests

from app.brands.normalize import normalize_brand_token
from app.parsers.models import ProductSummary
from app.parsers.wb_constants import WB_CATALOG_PARAMS, WB_JSON_HEADERS

CARD_DETAIL_API = "https://card.wb.ru/cards/v4/detail"


def product_from_catalog_row(row: dict[str, Any], target_key: str) -> ProductSummary | None:
    brand = str(row.get("brand") or "").strip()
    if not brand or normalize_brand_token(brand) != target_key:
        return None

    nm_id = int(row["id"])
    name = str(row.get("name") or f"nm_{nm_id}")
    title = f"{brand} / {name}" if brand else name
    rating_raw = row.get("reviewRating") or row.get("rating")
    rating = float(rating_raw) if rating_raw is not None else None

    root_id = row.get("root")
    imt_id = int(root_id) if root_id is not None else None

    return ProductSummary(
        nm_id=nm_id,
        title=title,
        product_url=f"https://www.wildberries.ru/catalog/{nm_id}/detail.aspx",
        rating=rating,
        brand_name=brand,
        imt_id=imt_id,
    )


def ensure_imt_ids(session: requests.Session, products: list[ProductSummary]) -> None:
    missing = [product for product in products if not product.imt_id]
    if not missing:
        return

    chunk_size = 50
    for start in range(0, len(missing), chunk_size):
        chunk = missing[start : start + chunk_size]
        nm_query = ";".join(str(product.nm_id) for product in chunk)
        try:
            response = session.get(
                CARD_DETAIL_API,
                params={**WB_CATALOG_PARAMS, "nm": nm_query},
                timeout=30,
                headers=WB_JSON_HEADERS,
            )
        except requests.RequestException:
            continue
        if response.status_code != 200:
            continue

        root_by_nm = {
            int(item["id"]): int(item["root"])
            for item in response.json().get("products", [])
            if item.get("id") is not None and item.get("root") is not None
        }
        for product in chunk:
            product.imt_id = root_by_nm.get(product.nm_id)
