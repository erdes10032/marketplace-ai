from __future__ import annotations



from app.pipeline.types import AnalysisResult, ClusterReportRow

from app.reviews.filter import FilteredReview





def make_filtered_review(**overrides) -> FilteredReview:

    defaults = {

        "text": "Товар пришёл с браком, не работает",

        "rating": 1,

        "nm_id": 100001,

        "product_title": "TEST BRAND / Товар",

        "review_id": "review-1",

        "product_rating": 4.2,

    }

    defaults.update(overrides)

    return FilteredReview(**defaults)





def make_analysis_result(**overrides) -> AnalysisResult:

    filtered = overrides.pop("filtered_reviews", (make_filtered_review(),))

    report_rows = overrides.pop(

        "report_rows",

        [

            ClusterReportRow(

                cluster=0,

                title="брак",

                root_cause="Некачественная сборка",

                reviews_count=1,

                avg_rating=1.0,

                negative_share=100.0,

                severity=42.0,

                top_products="TEST BRAND / Товар (1)",

                member_indexes=(0,),

            )

        ],

    )

    defaults = {

        "brand": "TEST BRAND",

        "raw_reviews_count": len(filtered),

        "filtered_reviews": filtered,

        "rating_histogram": {1: len(filtered)},

        "clustering_method": "kmeans",

        "clusters_found": len(report_rows),

        "clusters_reported": len(report_rows),

        "noise_count": 0,

        "assigned_count": len(filtered),

        "report_rows": report_rows,

    }

    defaults.update(overrides)

    return AnalysisResult(**defaults)

