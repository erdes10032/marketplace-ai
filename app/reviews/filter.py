from __future__ import annotations



from dataclasses import dataclass

from typing import Iterable



from app.parsers.models import ReviewItem

from app.reviews.constants import MIN_REVIEW_TEXT_LEN

from app.reviews.text import normalize_review_text





@dataclass(frozen=True, slots=True)

class FilteredReview:

    text: str

    rating: int | None

    nm_id: int

    product_title: str

    review_id: str | None = None

    product_rating: float | None = None





class ReviewFilter:

    def __init__(

        self,

        *,

        include_neutral: bool = False,

        min_text_len: int = MIN_REVIEW_TEXT_LEN,

        max_rating: int = 3,

    ) -> None:

        self.include_neutral = include_neutral

        self.min_text_len = min_text_len

        self.max_rating = max_rating



    def apply(self, items: Iterable[ReviewItem]) -> list[FilteredReview]:

        seen_review_ids: set[str] = set()

        seen_without_id: set[tuple[int, str, int | None]] = set()

        result: list[FilteredReview] = []



        for item in items:

            if not self.include_neutral:

                if item.review_rating is None:

                    continue

                if item.review_rating > self.max_rating:

                    continue



            text = normalize_review_text(item.review_text)

            if len(text) < self.min_text_len:

                continue



            if item.review_id:

                if item.review_id in seen_review_ids:

                    continue

                seen_review_ids.add(item.review_id)

            else:

                content_key = (item.nm_id, text, item.review_rating)

                if content_key in seen_without_id:

                    continue

                seen_without_id.add(content_key)



            result.append(

                FilteredReview(

                    text=text,

                    rating=item.review_rating,

                    nm_id=item.nm_id,

                    product_title=item.product_title,

                    review_id=item.review_id,

                    product_rating=item.product_rating,

                )

            )

        return result

