from __future__ import annotations

import time
from typing import Any

import requests

from app.parsers.models import ReviewItem
from app.reviews.constants import MIN_REVIEW_TEXT_LEN
from app.reviews.text import join_review_parts, normalize_review_text
from app.utils.log import log


class WBReviewFetcher:
    FEEDBACK_ENDPOINTS = (
        "https://feedbacks1.wb.ru/feedbacks/v1/{imt_id}",
        "https://feedbacks2.wb.ru/feedbacks/v1/{imt_id}",
        "https://feedbacks1.wb.ru/feedbacks/v2/{imt_id}",
        "https://feedbacks2.wb.ru/feedbacks/v2/{imt_id}",
    )

    def __init__(self, session: requests.Session) -> None:
        self._session = session

    def fetch_product_reviews(
        self,
        *,
        nm_id: int,
        imt_id: int | None,
        product_title: str,
        product_rating: float | None,
        max_reviews: int,
    ) -> list[ReviewItem]:
        if not imt_id:
            log("WBParser", f"nm_id={nm_id}: нет imt_id, отзывы пропущены")
            return []

        offset = 0
        take = 50
        collected: list[ReviewItem] = []
        while len(collected) < max_reviews:
            payload = self._request_reviews_page(imt_id=imt_id, offset=offset, take=take)
            if not payload:
                break
            rows = self._extract_review_rows(payload)
            if not rows:
                break
            for row in rows:
                text = self._extract_text(row)
                if len(text) < MIN_REVIEW_TEXT_LEN:
                    continue
                collected.append(
                    ReviewItem(
                        nm_id=nm_id,
                        product_title=product_title,
                        product_rating=product_rating,
                        review_text=text,
                        review_rating=self._extract_rating(row),
                        review_id=str(row.get("id")) if row.get("id") else None,
                        created_at=row.get("createdDate") or row.get("created"),
                    )
                )
                if len(collected) >= max_reviews:
                    break
            if len(rows) < take:
                break
            offset += take
            time.sleep(0.15)
        return collected

    def _request_reviews_page(
        self, imt_id: int, offset: int, take: int
    ) -> dict[str, Any] | None:
        params_candidates = (
            {"skip": offset, "take": take},
            {"offset": offset, "limit": take},
        )
        referer = f"https://www.wildberries.ru/catalog/0/feedbacks?imtId={imt_id}"
        headers = {
            "Accept": "application/json",
            "Origin": "https://www.wildberries.ru",
            "Referer": referer,
        }

        for endpoint in self.FEEDBACK_ENDPOINTS:
            url = endpoint.format(imt_id=imt_id)
            for params in params_candidates:
                try:
                    response = self._session.get(
                        url, params=params, timeout=20, headers=headers
                    )
                    if response.status_code != 200:
                        continue
                    data = response.json()
                    if isinstance(data, dict) and self._extract_review_rows(data):
                        return data
                except requests.RequestException:
                    continue
                except ValueError:
                    continue
        return None

    @staticmethod
    def _extract_review_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
        candidates = (
            payload.get("feedbacks"),
            payload.get("data"),
            payload.get("result"),
            payload.get("results"),
            payload.get("items"),
        )
        for block in candidates:
            if isinstance(block, list):
                return [item for item in block if isinstance(item, dict)]
            if isinstance(block, dict):
                nested = (
                    block.get("feedbacks"),
                    block.get("items"),
                    block.get("results"),
                    block.get("data"),
                )
                for inner in nested:
                    if isinstance(inner, list):
                        return [item for item in inner if isinstance(item, dict)]
        return []

    @staticmethod
    def _extract_text(row: dict[str, Any]) -> str:
        parts: list[str] = []
        for key in ("text", "pros", "cons", "comment"):
            raw = row.get(key)
            if not raw:
                continue
            if isinstance(raw, dict):
                raw = " ".join(str(v) for v in raw.values())
            value = normalize_review_text(str(raw))
            if value:
                parts.append(value)

        wb_details = row.get("wbUserDetails")
        if isinstance(wb_details, dict):
            details = normalize_review_text(" ".join(str(v) for v in wb_details.values()))
            if details:
                parts.append(details)

        return join_review_parts(parts)

    @staticmethod
    def _extract_rating(row: dict[str, Any]) -> int | None:
        raw = row.get("productValuation") or row.get("valuation") or row.get("rating")
        try:
            rating = int(raw)
            return rating if 1 <= rating <= 5 else None
        except (TypeError, ValueError):
            return None
