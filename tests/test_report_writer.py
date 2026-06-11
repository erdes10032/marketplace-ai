from __future__ import annotations

import csv
import json
from pathlib import Path

from app.reporting.writer import ReportWriter

from tests.factories import make_analysis_result


def test_csv_excludes_internal_member_indexes(tmp_path: Path):
    result = make_analysis_result()
    csv_path, _ = ReportWriter().write(result, tmp_path)

    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert rows
    assert "member_indexes" not in rows[0]
    assert set(rows[0]) == set(ReportWriter.CSV_COLUMNS)


def test_json_keeps_member_indexes(tmp_path: Path):
    result = make_analysis_result()
    _, json_path = ReportWriter().write(result, tmp_path)

    payload = json.loads(json_path.read_text(encoding="utf-8"))

    assert payload["clusters"][0]["member_indexes"] == [0]
    assert payload["clusters_found"] == 1
    assert payload["clusters_reported"] == 1
    assert payload["clustering_method"] == "kmeans"
