from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ProductSummary:
    nm_id: int
    title: str
    product_url: str
    rating: float | None = None
    brand_name: str | None = None
    imt_id: int | None = None


@dataclass(slots=True)
class ReviewItem:
    nm_id: int
    product_title: str
    product_rating: float | None
    review_text: str
    review_rating: int | None
    review_id: str | None
    created_at: str | None
