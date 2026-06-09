class ReviewEmbedder:

    def __init__(self):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(
            "BAAI/bge-m3"
        )

    def encode_reviews(
        self,
        reviews: list[str]
    ):
        return self.model.encode(
            reviews,
            normalize_embeddings=True,
            show_progress_bar=True
        )