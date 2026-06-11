from __future__ import annotations



from sqlalchemy.orm import Session



from app.models import AnalysisRun, ClusterReview, ProblemCluster, Product, Review

from app.pipeline.types import AnalysisResult, ClusterReportRow

from app.reviews.filter import FilteredReview





class AnalysisStore:

    def __init__(self, session: Session) -> None:

        self._session = session



    def save(self, result: AnalysisResult) -> AnalysisRun:

        run = AnalysisRun(

            brand=result.brand,

            raw_reviews_count=result.raw_reviews_count,

            filtered_reviews_count=result.filtered_reviews_count,

            clustering_method=result.clustering_method,

            clusters_found=result.clusters_found,

            clusters_reported=result.clusters_reported,

            noise_count=result.noise_count,

        )

        self._session.add(run)

        self._session.flush()



        product_by_article = self._upsert_products(result.filtered_reviews)

        review_by_index = self._upsert_reviews(result.filtered_reviews, product_by_article)

        self._insert_clusters(run.id, result.report_rows, review_by_index)

        self._session.commit()

        return run



    def _upsert_products(

        self, filtered: tuple[FilteredReview, ...]

    ) -> dict[str, Product]:

        articles = {str(row.nm_id) for row in filtered}

        existing = {

            product.article: product

            for product in self._session.query(Product)

            .filter(Product.article.in_(articles))

            .all()

        }



        product_by_article: dict[str, Product] = {}

        for row in filtered:

            article = str(row.nm_id)

            product = existing.get(article)

            if product is None:

                product = Product(

                    article=article,

                    title=row.product_title,

                    rating=row.product_rating,

                )

                self._session.add(product)

                existing[article] = product

            else:

                product.title = row.product_title or product.title

                if row.product_rating is not None:

                    product.rating = row.product_rating

            product_by_article[article] = product



        self._session.flush()

        return product_by_article



    def _upsert_reviews(

        self,

        filtered: tuple[FilteredReview, ...],

        product_by_article: dict[str, Product],

    ) -> dict[int, Review]:

        review_by_index: dict[int, Review] = {}

        pending_by_external: dict[tuple[int, str], Review] = {}

        pending_by_text: dict[tuple[int, str, int | None], Review] = {}



        for index, row in enumerate(filtered):

            product = product_by_article[str(row.nm_id)]

            review = self._find_existing_review(

                product.id,

                row,

                pending_by_external=pending_by_external,

                pending_by_text=pending_by_text,

            )

            if review is None:

                review = Review(

                    product_id=product.id,

                    external_id=row.review_id,

                    text=row.text,

                    rating=row.rating,

                )

                self._session.add(review)

                if row.review_id:

                    pending_by_external[(product.id, row.review_id)] = review

                else:

                    pending_by_text[(product.id, row.text, row.rating)] = review

            review_by_index[index] = review



        self._session.flush()

        return review_by_index



    def _find_existing_review(

        self,

        product_id: int,

        row: FilteredReview,

        *,

        pending_by_external: dict[tuple[int, str], Review],

        pending_by_text: dict[tuple[int, str, int | None], Review],

    ) -> Review | None:

        if row.review_id:

            key = (product_id, row.review_id)

            pending = pending_by_external.get(key)

            if pending is not None:

                return pending

            return (

                self._session.query(Review)

                .filter(

                    Review.product_id == product_id,

                    Review.external_id == row.review_id,

                )

                .one_or_none()

            )



        key = (product_id, row.text, row.rating)

        pending = pending_by_text.get(key)

        if pending is not None:

            return pending

        return (

            self._session.query(Review)

            .filter(

                Review.product_id == product_id,

                Review.text == row.text,

                Review.rating == row.rating,

                Review.external_id.is_(None),

            )

            .one_or_none()

        )



    def _insert_clusters(

        self,

        run_id: int,

        report_rows: list[ClusterReportRow],

        review_by_index: dict[int, Review],

    ) -> None:

        for cluster_row in report_rows:

            cluster = ProblemCluster(

                run_id=run_id,

                cluster_label=cluster_row.cluster,

                cluster_name=cluster_row.title,

                reviews_count=cluster_row.reviews_count,

                severity_score=cluster_row.severity,

                description=cluster_row.root_cause,

                avg_rating=cluster_row.avg_rating,

                negative_share=cluster_row.negative_share,

                top_products=cluster_row.top_products,

            )

            self._session.add(cluster)

            self._session.flush()



            for review_index in cluster_row.member_indexes:

                review = review_by_index[review_index]

                self._session.add(

                    ClusterReview(

                        cluster_id=cluster.id,

                        review_id=review.id,

                    )

                )

