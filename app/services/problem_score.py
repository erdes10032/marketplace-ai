def calculate_severity(
    cluster_reviews_count,
    total_reviews,
    avg_rating,
    negative_share=1.0
):
    if total_reviews <= 0:
        return 0.0

    frequency = (
        cluster_reviews_count
        / total_reviews
    )

    safe_rating = avg_rating if avg_rating is not None else 3.0
    rating_factor = (
        6 - safe_rating
    ) / 5

    impact_factor = max(
        0.0,
        min(1.0, float(negative_share))
    )

    return round(
        frequency * rating_factor * impact_factor * 100,
        2
    )