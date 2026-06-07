from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import requests

from app.brands.resolver import BrandResolver
from app.parsers.models import ProductSummary


def test_resolve_name_from_slug_url():
    resolver = BrandResolver(requests.Session())

    assert (
        resolver.resolve_name("https://www.wildberries.ru/brands/scan-to")
        == "scan to"
    )


def test_resolve_id_from_numeric_brand_url():
    resolver = BrandResolver(requests.Session())

    assert (
        resolver.resolve_id("https://www.wildberries.ru/brands/312053770-onetechcam")
        == 312053770
    )


def test_resolve_name_from_meta_api():
    session = MagicMock()
    session.get.return_value.status_code = 200
    session.get.return_value.json.return_value = {"name": "OneTechCam"}
    resolver = BrandResolver(session)

    name = resolver.resolve_name(
        "https://www.wildberries.ru/brands/312053770-onetechcam"
    )

    assert name == "OneTechCam"


def test_resolve_id_by_name_uses_first_matching_product():
    session = MagicMock()
    session.get.return_value.status_code = 200
    session.get.return_value.json.return_value = {
        "products": [
            {"brand": "Other", "brandId": 1},
            {"brand": "CITY VIBE", "brandId": 4242},
        ]
    }
    resolver = BrandResolver(session)

    assert resolver.resolve_id("CITY VIBE") == 4242


def test_matches_product_by_normalized_brand():
    resolver = BrandResolver(requests.Session())
    product = ProductSummary(
        nm_id=1,
        title="CITY VIBE / Очки",
        product_url="https://example.com",
        brand_name="CITY VIBE",
    )

    assert resolver.matches_product("cityvibe", product) is True
    assert resolver.matches_product("blackbox", product) is False
