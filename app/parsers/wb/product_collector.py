from __future__ import annotations

import time
from typing import TYPE_CHECKING

import requests

from app.brands.normalize import normalize_brand_token
from app.parsers.models import ProductSummary
from app.parsers.wb.catalog import product_from_catalog_row
from app.parsers.wb_constants import (
    WB_BRAND_CATALOG_API,
    WB_CATALOG_PARAMS,
    WB_JSON_HEADERS,
    WB_SEARCH_API,
)
from app.utils.log import log

if TYPE_CHECKING:
    from app.brands.resolver import BrandResolver


class WBProductCollector:
    def __init__(self, session: requests.Session, brand_resolver: BrandResolver) -> None:
        self._session = session
        self._brands = brand_resolver

    def collect(
        self,
        *,
        brand_input: str,
        brand_name: str,
        max_products: int,
    ) -> list[ProductSummary]:
        brand_id = self._brands.resolve_id(brand_input)
        if brand_id is not None:
            products = self._collect_via_brand_catalog(
                brand_id=brand_id,
                brand_name=brand_name,
                max_products=max_products,
            )
            if products:
                log(
                    "WBParser",
                    f"Товары получены через каталог бренда WB (brandId={brand_id}): "
                    f"{len(products)}",
                )
                return products

        products = self._collect_via_text_search(brand_name, max_products)
        if products:
            log("WBParser", f"Товары получены через поиск WB: {len(products)}")
        return products

    def filter_by_brand(
        self, products: list[ProductSummary], brand_input: str
    ) -> list[ProductSummary]:
        brand_key = self._brands.canonical_key(brand_input)
        if not brand_key:
            return products

        filtered = [
            product for product in products if self._brands.matches_product(brand_key, product)
        ]
        log(
            "WBParser",
            f"Фильтр по бренду '{brand_input}': {len(filtered)} из {len(products)}",
        )
        return filtered

    def _collect_via_brand_catalog(
        self,
        *,
        brand_id: int,
        brand_name: str,
        max_products: int,
    ) -> list[ProductSummary]:
        target_key = normalize_brand_token(brand_name)
        seen: set[int] = set()
        products: list[ProductSummary] = []
        page_size = 100
        catalog_total: int | None = None

        for page_num in range(1, 50):
            if len(products) >= max_products:
                break

            params = {
                **WB_CATALOG_PARAMS,
                "brand": brand_id,
                "page": page_num,
                "sort": "popular",
                "spp": page_size,
            }
            try:
                response = self._session.get(
                    WB_BRAND_CATALOG_API,
                    params=params,
                    timeout=30,
                    headers=WB_JSON_HEADERS,
                )
            except requests.RequestException:
                break

            if response.status_code != 200:
                log(
                    "WBParser",
                    f"API brand catalog: HTTP {response.status_code} (страница {page_num})",
                )
                break

            try:
                payload = response.json()
            except ValueError:
                break

            rows = payload.get("products") or payload.get("data", {}).get("products") or []
            if catalog_total is None and payload.get("total") is not None:
                catalog_total = int(payload["total"])
            if not rows:
                break

            for row in rows:
                product = product_from_catalog_row(row, target_key)
                if product is None or product.nm_id in seen:
                    continue
                seen.add(product.nm_id)
                products.append(product)
                if len(products) >= max_products:
                    break

            if catalog_total is not None and len(products) >= catalog_total:
                break
            if len(rows) < page_size:
                break
            time.sleep(0.25)

        return products

    def _collect_via_text_search(
        self, brand_name: str, max_products: int
    ) -> list[ProductSummary]:
        target_key = normalize_brand_token(brand_name)
        if not target_key:
            return []

        seen: set[int] = set()
        products: list[ProductSummary] = []
        page_size = 100
        search_total: int | None = None

        for page_num in range(1, 30):
            if len(products) >= max_products:
                break

            params = {
                **WB_CATALOG_PARAMS,
                "page": page_num,
                "query": brand_name,
                "resultset": "catalog",
                "sort": "popular",
                "spp": page_size,
            }
            try:
                response = self._session.get(
                    WB_SEARCH_API,
                    params=params,
                    timeout=30,
                    headers=WB_JSON_HEADERS,
                )
            except requests.RequestException:
                break

            if response.status_code != 200:
                log(
                    "WBParser",
                    f"API search: HTTP {response.status_code} (страница {page_num})",
                )
                break

            try:
                payload = response.json()
            except ValueError:
                break

            rows = payload.get("products") or payload.get("data", {}).get("products") or []
            if search_total is None and payload.get("total") is not None:
                search_total = int(payload["total"])
            if not rows:
                break

            matched_on_page = 0
            for row in rows:
                product = product_from_catalog_row(row, target_key)
                if product is None or product.nm_id in seen:
                    continue
                seen.add(product.nm_id)
                matched_on_page += 1
                products.append(product)
                if len(products) >= max_products:
                    break

            if page_num == 1 and matched_on_page == 0:
                break
            if search_total is not None and len(products) >= search_total:
                break
            if len(rows) < page_size:
                break
            time.sleep(0.25)

        return products
