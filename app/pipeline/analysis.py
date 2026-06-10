from __future__ import annotations



from collections import Counter

from dataclasses import dataclass



from app.ai.review_analyzer import ReviewAnalyzer

from app.clustering.review_clusterer import ReviewClusterer

from app.embeddings.embedder import ReviewEmbedder

from app.parsers.wb_parser import WBParser

from app.pipeline.types import AnalysisResult, ClusterReportRow

from app.reviews.filter import FilteredReview, ReviewFilter

from app.services.problem_score import calculate_severity

from app.utils.log import log





@dataclass(frozen=True, slots=True)

class _ClusterDraft:

    cluster: int

    indexes: tuple[int, ...]

    reviews_count: int

    avg_rating: float | None

    negative_share: float

    severity: float

    top_products: str





class BrandAnalysisPipeline:

    def __init__(

        self,

        *,

        parser: WBParser | None = None,

        embedder: ReviewEmbedder | None = None,

        clusterer: ReviewClusterer | None = None,

        analyzer: ReviewAnalyzer | None = None,

    ) -> None:

        self._parser = parser or WBParser()

        self._embedder = embedder

        self._clusterer = clusterer or ReviewClusterer()

        self._analyzer = analyzer or ReviewAnalyzer()



    def run(

        self,

        brand: str,

        *,

        max_products: int,

        max_reviews_per_product: int,

        include_neutral: bool = False,

        top: int = 10,

    ) -> AnalysisResult | None:

        raw_reviews = self._parser.parse_brand_reviews(

            brand_input=brand,

            max_products=max_products,

            max_reviews_per_product=max_reviews_per_product,

        )



        review_filter = ReviewFilter(include_neutral=include_neutral)

        filtered = review_filter.apply(raw_reviews)

        if not filtered:

            log("Analysis", "Недостаточно отзывов после фильтра. Увеличьте лимиты или --include-neutral.")

            return None



        self._log_filter_stats(raw_reviews, filtered, include_neutral)



        embedder = self._embedder or ReviewEmbedder()

        if self._embedder is None:

            log("Analysis", "Загружаю модель эмбеддингов...")



        texts = [item.text for item in filtered]

        log("Analysis", f"Кодирую отзывы: {len(texts)} шт.")

        embeddings = embedder.encode_reviews(texts)



        log("Analysis", "Кластеризация отзывов...")

        clustering = self._clusterer.cluster_and_group(embeddings)

        if not clustering.clusters:

            log(

                "Analysis",

                f"Кластеры не сформированы (групп: {clustering.cluster_count}, "

                f"шум: {clustering.noise_count}, малых: {clustering.small_clusters}).",

            )

            return None



        method_label = ReviewClusterer.METHOD_LABELS.get(

            clustering.method, clustering.method

        )

        log("Analysis", f"Метод: {method_label}")

        log(

            "Analysis",

            f"Кластеров: {len(clustering.clusters)}, "

            f"отзывов в кластерах: {clustering.assigned_count}, "

            f"вне кластеров: {clustering.noise_count}",

        )

        if clustering.method == "hdbscan" and clustering.noise_count > len(filtered) * 0.5:

            log(

                "Analysis",

                "Внимание: большая часть отзывов не попала в кластеры — темы жалоб разрознены.",

            )



        drafts = self._build_cluster_drafts(filtered, clustering.clusters)

        drafts.sort(key=lambda draft: draft.severity, reverse=True)

        top_drafts = drafts[:top]



        log(

            "Analysis",

            f"Генерация описаний для топ-{len(top_drafts)} из {len(drafts)} кластеров...",

        )

        report_rows = self._enrich_drafts_with_llm(top_drafts, filtered)



        rating_hist = dict(Counter(item.rating for item in filtered))

        return AnalysisResult(

            brand=brand,

            raw_reviews_count=len(raw_reviews),

            filtered_reviews=tuple(filtered),

            rating_histogram=rating_hist,

            clustering_method=clustering.method,

            clusters_found=len(clustering.clusters),

            clusters_reported=len(report_rows),

            noise_count=clustering.noise_count,

            assigned_count=clustering.assigned_count,

            report_rows=report_rows,

        )



    def _build_cluster_drafts(

        self,

        filtered: list[FilteredReview],

        clusters: dict[int, list[int]],

    ) -> list[_ClusterDraft]:

        total = len(filtered)

        drafts: list[_ClusterDraft] = []



        for label, indexes in clusters.items():

            cluster_ratings = [

                filtered[i].rating for i in indexes if filtered[i].rating is not None

            ]

            product_counter = Counter(filtered[i].product_title for i in indexes)

            negative_count = sum(

                1 for i in indexes if filtered[i].rating is not None and filtered[i].rating <= 3

            )

            avg_rating = (

                round(sum(cluster_ratings) / len(cluster_ratings), 2)

                if cluster_ratings

                else None

            )

            negative_share = negative_count / len(indexes) if indexes else 0.0

            severity = calculate_severity(

                cluster_reviews_count=len(indexes),

                total_reviews=total,

                avg_rating=avg_rating if avg_rating is not None else 3.0,

                negative_share=negative_share,

            )

            drafts.append(

                _ClusterDraft(

                    cluster=label,

                    indexes=tuple(indexes),

                    reviews_count=len(indexes),

                    avg_rating=avg_rating,

                    negative_share=round(negative_share * 100, 2),

                    severity=severity,

                    top_products=", ".join(

                        f"{name} ({count})"

                        for name, count in product_counter.most_common(3)

                    ),

                )

            )

        return drafts



    def _enrich_drafts_with_llm(

        self,

        drafts: list[_ClusterDraft],

        filtered: list[FilteredReview],

    ) -> list[ClusterReportRow]:

        rows: list[ClusterReportRow] = []

        for draft in drafts:

            cluster_reviews = [filtered[i].text for i in draft.indexes]

            title = self._analyzer.generate_cluster_title(cluster_reviews)

            root_cause = self._analyzer.describe_root_cause(title, cluster_reviews)

            rows.append(

                ClusterReportRow(

                    cluster=draft.cluster,

                    title=title,

                    root_cause=root_cause,

                    reviews_count=draft.reviews_count,

                    avg_rating=draft.avg_rating,

                    negative_share=draft.negative_share,

                    severity=draft.severity,

                    top_products=draft.top_products,

                    member_indexes=draft.indexes,

                )

            )

        return rows



    @staticmethod

    def _log_filter_stats(

        raw_reviews: list,

        filtered: list[FilteredReview],

        include_neutral: bool,

    ) -> None:

        if include_neutral:

            filter_desc = "все оценки, текст≥8"

        else:

            filter_desc = "оценка≤3, текст≥8"

        log(

            "Analysis",

            f"Собрано отзывов: {len(raw_reviews)}, "

            f"после фильтра ({filter_desc}): {len(filtered)}",

        )

        if include_neutral:

            return

        hist = Counter(item.rating for item in filtered)

        rating_line = ", ".join(

            f"{rating}★={count}"

            for rating, count in sorted(hist.items(), key=lambda x: (x[0] is None, x[0] or 0))

        )

        log("Analysis", f"Распределение оценок в выборке: {rating_line}")

