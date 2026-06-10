from __future__ import annotations



from dataclasses import dataclass

from typing import TYPE_CHECKING



if TYPE_CHECKING:

    from app.reviews.filter import FilteredReview





@dataclass(frozen=True, slots=True)

class ClusterReportRow:

    cluster: int

    title: str

    root_cause: str

    reviews_count: int

    avg_rating: float | None

    negative_share: float

    severity: float

    top_products: str

    member_indexes: tuple[int, ...]





@dataclass(frozen=True, slots=True)

class AnalysisResult:

    brand: str

    raw_reviews_count: int

    filtered_reviews: tuple["FilteredReview", ...]

    rating_histogram: dict[int | None, int]

    clustering_method: str

    clusters_found: int

    clusters_reported: int

    noise_count: int

    assigned_count: int

    report_rows: list[ClusterReportRow]



    @property

    def filtered_reviews_count(self) -> int:

        return len(self.filtered_reviews)

