from __future__ import annotations



from app.models import Product, Review

from app.repositories.analysis_store import AnalysisStore



from tests.factories import make_analysis_result, make_filtered_review





def test_saves_reviews_with_same_text_but_different_external_ids(db_session):

    reviews = (

        make_filtered_review(

            review_id="wb-1",

            text="ru Замира False",

            rating=1,

            nm_id=100001,

        ),

        make_filtered_review(

            review_id="wb-2",

            text="ru Замира False",

            rating=1,

            nm_id=100001,

        ),

    )

    result = make_analysis_result(

        filtered_reviews=reviews,

        report_rows=[],

        clusters_found=0,

        clusters_reported=0,

        assigned_count=0,

    )



    AnalysisStore(db_session).save(result)



    saved = db_session.query(Review).order_by(Review.external_id).all()

    assert len(saved) == 2

    assert {row.external_id for row in saved} == {"wb-1", "wb-2"}





def test_reuses_review_by_external_id_within_same_batch(db_session):

    reviews = (

        make_filtered_review(review_id="dup-id", nm_id=100001),

        make_filtered_review(

            review_id="dup-id",

            text="Другой текст в фильтре, тот же external_id",

            nm_id=100001,

        ),

    )

    result = make_analysis_result(

        filtered_reviews=reviews,

        report_rows=[],

        clusters_found=0,

        clusters_reported=0,

    )



    store = AnalysisStore(db_session)

    store.save(result)



    assert db_session.query(Review).count() == 1





def test_persists_product_rating(db_session):

    result = make_analysis_result(

        filtered_reviews=(make_filtered_review(product_rating=3.7),),

    )



    AnalysisStore(db_session).save(result)



    product = db_session.query(Product).one()

    assert product.rating == 3.7

