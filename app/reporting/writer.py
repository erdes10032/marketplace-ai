from __future__ import annotations



import csv

import json

from dataclasses import asdict

from datetime import datetime

from pathlib import Path



from app.pipeline.types import AnalysisResult





class ReportWriter:

    CSV_COLUMNS = [

        "cluster",

        "title",

        "root_cause",

        "reviews_count",

        "avg_rating",

        "negative_share",

        "severity",

        "top_products",

    ]



    def write(self, result: AnalysisResult, output_dir: Path) -> tuple[Path, Path]:

        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        safe_brand = (

            result.brand.replace("https://", "")

            .replace("http://", "")

            .replace("/", "_")

        )

        base_name = f"analysis_{safe_brand}_{timestamp}"

        csv_path = output_dir / f"{base_name}.csv"

        json_path = output_dir / f"{base_name}.json"



        rows = [asdict(row) for row in result.report_rows]

        csv_rows = [{column: row[column] for column in self.CSV_COLUMNS} for row in rows]

        with csv_path.open("w", encoding="utf-8-sig", newline="") as csv_file:

            writer = csv.DictWriter(csv_file, fieldnames=self.CSV_COLUMNS)

            writer.writeheader()

            writer.writerows(csv_rows)



        payload = {

            "generated_at": datetime.now().isoformat(timespec="seconds"),

            "brand": result.brand,

            "raw_reviews_count": result.raw_reviews_count,

            "filtered_reviews_count": result.filtered_reviews_count,

            "clustering_method": result.clustering_method,

            "clusters_found": result.clusters_found,

            "clusters_reported": result.clusters_reported,

            "noise_count": result.noise_count,

            "assigned_count": result.assigned_count,

            "rating_histogram": {

                "null" if rating is None else str(rating): count

                for rating, count in result.rating_histogram.items()

            },

            "clusters": rows,

        }

        with json_path.open("w", encoding="utf-8") as json_file:

            json.dump(payload, json_file, ensure_ascii=False, indent=2)



        return csv_path, json_path



    @staticmethod

    def print_summary(result: AnalysisResult) -> None:

        print()

        print(f"Проанализировано отзывов: {result.filtered_reviews_count}")

        print(f"Обнаружено проблемных кластеров: {result.clusters_found}")

        if result.clusters_reported < result.clusters_found:

            print(f"Показано в отчёте (топ): {result.clusters_reported}")

        print()

        print("ТОП критичных проблем:")

        for idx, row in enumerate(result.report_rows, start=1):

            print("-" * 120)

            print(

                f"{idx}. [{row.severity}] {row.title} | "

                f"Отзывы: {row.reviews_count} | Ср.оценка: {row.avg_rating} | "

                f"Негатив: {row.negative_share}%"

            )

            print(f"Товары: {row.top_products}")

            print(f"Первопричина: {row.root_cause}")

