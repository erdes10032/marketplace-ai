from __future__ import annotations

from dataclasses import dataclass

import hdbscan
import numpy as np
from sklearn.cluster import KMeans


@dataclass(frozen=True, slots=True)
class ClusteringResult:
    labels: np.ndarray
    method: str
    clusters: dict[int, list[int]]
    cluster_count: int
    noise_count: int
    small_clusters: int
    assigned_count: int


class ReviewClusterer:
    METRIC = "euclidean"
    MAX_HDBSCAN_NOISE_RATIO = 0.65
    DEFAULT_MIN_CLUSTER_REVIEWS = 3

    METHOD_LABELS = {
        "hdbscan": "HDBSCAN (плотные группы)",
        "kmeans": "KMeans (разнородные жалобы, HDBSCAN оставил >65% шума)",
        "none": "не применялась",
    }

    def __init__(self) -> None:
        self.last_method = "none"

    def cluster_and_group(
        self,
        embeddings,
        *,
        min_cluster_reviews: int | None = None,
    ) -> ClusteringResult:
        min_size = min_cluster_reviews or self.DEFAULT_MIN_CLUSTER_REVIEWS
        labels = self.cluster(embeddings)
        cluster_count, noise_count = self.count_clusters(labels)

        raw_clusters: dict[int, list[int]] = {}
        for idx, label in enumerate(labels):
            if label < 0:
                continue
            raw_clusters.setdefault(int(label), []).append(idx)

        small_clusters = sum(
            1 for indexes in raw_clusters.values() if len(indexes) < min_size
        )
        clusters = {
            label: indexes
            for label, indexes in raw_clusters.items()
            if len(indexes) >= min_size
        }
        assigned_count = sum(len(indexes) for indexes in clusters.values())

        return ClusteringResult(
            labels=labels,
            method=self.last_method,
            clusters=clusters,
            cluster_count=cluster_count,
            noise_count=noise_count,
            small_clusters=small_clusters,
            assigned_count=assigned_count,
        )

    def cluster(self, embeddings) -> np.ndarray:
        n_samples = len(embeddings)
        if n_samples < 3:
            self.last_method = "none"
            return np.full(n_samples, -1, dtype=int)

        embeddings = np.asarray(embeddings)
        best_hdbscan: np.ndarray | None = None

        for params in self._hdbscan_configs(n_samples):
            labels = self._run_hdbscan(embeddings, **params)
            if not self._has_clusters(labels):
                continue
            if best_hdbscan is None:
                best_hdbscan = labels
            if self._noise_ratio(labels) <= self.MAX_HDBSCAN_NOISE_RATIO:
                self.last_method = "hdbscan"
                return labels

        if best_hdbscan is not None and self._noise_ratio(best_hdbscan) <= self.MAX_HDBSCAN_NOISE_RATIO:
            self.last_method = "hdbscan"
            return best_hdbscan

        labels = self._kmeans_fallback(embeddings, n_samples)
        self.last_method = "kmeans"
        return labels

    @staticmethod
    def _noise_ratio(labels: np.ndarray) -> float:
        labels = np.asarray(labels)
        if not len(labels):
            return 1.0
        return float(np.sum(labels < 0)) / len(labels)

    @staticmethod
    def _has_clusters(labels: np.ndarray) -> bool:
        return bool(np.any(labels >= 0))

    def _hdbscan_configs(self, n_samples: int) -> list[dict]:
        base = max(3, min(12, n_samples // 12))
        configs: list[dict] = [
            {
                "min_cluster_size": base,
                "min_samples": max(2, base // 2),
                "cluster_selection_method": "eom",
                "cluster_selection_epsilon": 0.0,
            },
            {
                "min_cluster_size": max(3, base - 2),
                "min_samples": 2,
                "cluster_selection_method": "eom",
                "cluster_selection_epsilon": 0.05,
            },
            {
                "min_cluster_size": 3,
                "min_samples": 2,
                "cluster_selection_method": "leaf",
                "cluster_selection_epsilon": 0.0,
            },
            {
                "min_cluster_size": 3,
                "min_samples": 2,
                "cluster_selection_method": "leaf",
                "cluster_selection_epsilon": 0.12,
            },
        ]
        unique: list[dict] = []
        seen: set[tuple] = set()
        for cfg in configs:
            key = tuple(cfg.items())
            if key not in seen:
                seen.add(key)
                unique.append(cfg)
        return unique

    def _run_hdbscan(self, embeddings: np.ndarray, **kwargs) -> np.ndarray:
        model = hdbscan.HDBSCAN(metric=self.METRIC, **kwargs)
        return model.fit_predict(embeddings)

    def _kmeans_fallback(self, embeddings: np.ndarray, n_samples: int) -> np.ndarray:
        k = max(3, min(20, n_samples // 25))
        if k >= n_samples:
            k = max(2, n_samples // 2)
        model = KMeans(n_clusters=k, random_state=42, n_init=10)
        return model.fit_predict(embeddings)

    @staticmethod
    def count_clusters(labels: np.ndarray) -> tuple[int, int]:
        labels = np.asarray(labels)
        cluster_ids = {int(x) for x in labels if int(x) >= 0}
        noise = int(np.sum(labels < 0))
        return len(cluster_ids), noise
