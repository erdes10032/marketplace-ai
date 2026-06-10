from __future__ import annotations



from sqlalchemy import (

    Column,

    DateTime,

    Float,

    ForeignKey,

    Integer,

    String,

    Text,

    UniqueConstraint,

    func,

)

from sqlalchemy.orm import declarative_base, relationship



Base = declarative_base()





class AnalysisRun(Base):

    __tablename__ = "analysis_runs"



    id = Column(Integer, primary_key=True)

    brand = Column(String, nullable=False)

    raw_reviews_count = Column(Integer, nullable=False)

    filtered_reviews_count = Column(Integer, nullable=False)

    clustering_method = Column(String, nullable=False)

    clusters_found = Column(Integer, nullable=False)

    clusters_reported = Column(Integer, nullable=False)

    noise_count = Column(Integer, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)



    clusters = relationship("ProblemCluster", back_populates="run")





class Product(Base):

    __tablename__ = "products"



    id = Column(Integer, primary_key=True)

    article = Column(String, unique=True, nullable=False)

    title = Column(String, nullable=False)

    rating = Column(Float)



    reviews = relationship("Review", back_populates="product")





class Review(Base):

    __tablename__ = "reviews"

    __table_args__ = (

        UniqueConstraint("product_id", "external_id", name="uq_reviews_product_external"),

    )



    id = Column(Integer, primary_key=True)

    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    external_id = Column(String)

    text = Column(Text, nullable=False)

    rating = Column(Integer)



    product = relationship("Product", back_populates="reviews")

    cluster_links = relationship("ClusterReview", back_populates="review")





class ProblemCluster(Base):

    __tablename__ = "problem_clusters"



    id = Column(Integer, primary_key=True)

    run_id = Column(Integer, ForeignKey("analysis_runs.id"), nullable=False)

    cluster_label = Column(Integer, nullable=False)

    cluster_name = Column(String, nullable=False)

    reviews_count = Column(Integer, nullable=False)

    severity_score = Column(Float, nullable=False)

    description = Column(Text, nullable=False)

    avg_rating = Column(Float)

    negative_share = Column(Float)

    top_products = Column(Text)



    run = relationship("AnalysisRun", back_populates="clusters")

    review_links = relationship("ClusterReview", back_populates="cluster")





class ClusterReview(Base):

    __tablename__ = "cluster_reviews"

    __table_args__ = (UniqueConstraint("cluster_id", "review_id", name="uq_cluster_reviews"),)



    id = Column(Integer, primary_key=True)

    cluster_id = Column(Integer, ForeignKey("problem_clusters.id"), nullable=False)

    review_id = Column(Integer, ForeignKey("reviews.id"), nullable=False)



    cluster = relationship("ProblemCluster", back_populates="review_links")

    review = relationship("Review", back_populates="cluster_links")

