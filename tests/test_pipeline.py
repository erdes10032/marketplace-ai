from __future__ import annotations

from unittest.mock import MagicMock

from app.pipeline.analysis import BrandAnalysisPipeline

from tests.factories import make_filtered_review


def _filtered_reviews(count: int):
    return [
        make_filtered_review(
            text=f"Проблема номер {index}, товар сломался быстро",
            rating=1,
            nm_id=100000 + index,
            review_id=f"review-{index}",
        )
        for index in range(count)
    ]


def test_llm_called_only_for_top_clusters():
    analyzer = MagicMock()
    analyzer.generate_cluster_title.return_value = "брак"
    analyzer.describe_root_cause.return_value = "Плохой контроль качества."

    pipeline = BrandAnalysisPipeline(analyzer=analyzer)
    filtered = _filtered_reviews(12)
    clusters = {
        0: list(range(0, 4)),
        1: list(range(4, 8)),
        2: list(range(8, 12)),
    }

    drafts = pipeline._build_cluster_drafts(filtered, clusters)
    drafts.sort(key=lambda draft: draft.severity, reverse=True)
    top_drafts = drafts[:2]

    rows = pipeline._enrich_drafts_with_llm(top_drafts, filtered)

    assert len(rows) == 2
    assert analyzer.generate_cluster_title.call_count == 2
    assert analyzer.describe_root_cause.call_count == 2
