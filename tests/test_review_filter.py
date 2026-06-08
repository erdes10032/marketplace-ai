from __future__ import annotations

from app.parsers.models import ReviewItem
from app.reviews.filter import ReviewFilter


def _item(**overrides) -> ReviewItem:
    defaults = {
        "nm_id": 1,
        "product_title": "BRAND / Product",
        "product_rating": 4.5,
        "review_text": "Плохое качество, разочарован покупкой",
        "review_rating": 2,
        "review_id": "id-1",
        "created_at": None,
    }
    defaults.update(overrides)
    return ReviewItem(**defaults)


def test_keeps_negative_reviews_with_enough_text():
    result = ReviewFilter().apply([_item()])

    assert len(result) == 1
    assert result[0].rating == 2


def test_skips_positive_reviews_by_default():
    result = ReviewFilter().apply([_item(review_rating=5)])

    assert result == []


def test_skips_short_text():
    result = ReviewFilter().apply([_item(review_text="плохо")])

    assert result == []


def test_skips_duplicate_review_id():
    original = _item(review_id="same-id")
    duplicate = _item(review_id="same-id", review_text="Другой текст, но тот же id")
    result = ReviewFilter().apply([original, duplicate])

    assert len(result) == 1
    assert result[0].text == "Плохое качество, разочарован покупкой"


def test_keeps_same_text_with_different_review_ids():
    first = _item(review_id="wb-1", review_text="ru Замира False")
    second = _item(review_id="wb-2", review_text="ru Замира False")
    result = ReviewFilter().apply([first, second])

    assert len(result) == 2


def test_skips_duplicate_content_without_review_id():
    original = _item(review_id=None)
    duplicate = _item(review_id=None, review_text="Плохое качество, разочарован покупкой")
    result = ReviewFilter().apply([original, duplicate])

    assert len(result) == 1


def test_include_neutral_allows_high_ratings():
    result = ReviewFilter(include_neutral=True).apply([_item(review_rating=5)])

    assert len(result) == 1


def test_skips_reviews_without_rating_by_default():
    result = ReviewFilter().apply([_item(review_rating=None)])

    assert result == []
