from __future__ import annotations

import pytest

from app.services.problem_score import calculate_severity


def test_calculate_severity_for_negative_cluster():
    severity = calculate_severity(
        cluster_reviews_count=10,
        total_reviews=100,
        avg_rating=1.5,
        negative_share=1.0,
    )

    assert severity == 9.0


def test_calculate_severity_returns_zero_for_empty_sample():
    assert calculate_severity(5, 0, 1.0) == 0.0


@pytest.mark.parametrize(
    ("negative_share", "expected"),
    [
        (-0.5, 0.0),
        (0.0, 0.0),
        (0.5, 5.0),
        (1.0, 10.0),
        (1.5, 10.0),
    ],
)
def test_calculate_severity_clamps_negative_share(negative_share: float, expected: float):
    severity = calculate_severity(10, 100, 1.0, negative_share=negative_share)

    assert severity == expected
