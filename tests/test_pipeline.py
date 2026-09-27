from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from core.config import load_settings
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks


@pytest.fixture
def settings():
    return load_settings()


@pytest.fixture
def raw_records(settings):
    assert settings.paths.raw_records_json.exists(), "Raw records JSON snapshot missing!"
    records = load_raw_records(settings.paths.raw_records_json)
    return records


@pytest.fixture
def clean_df(raw_records):
    df = build_clean_dataframe(raw_records, datetime.now(timezone.utc))
    return df


def test_raw_records_loading(raw_records):
    assert len(raw_records) == 24
    for r in raw_records:
        assert r.paper_id.strip() != ""
        assert r.title.strip() != ""
        assert isinstance(r.authors, list)
        assert isinstance(r.categories, list)


def test_data_cleaning_and_embedding_format(clean_df):
    assert len(clean_df) == 24
    # Kiểm tra cấu trúc 5 phần của text_for_embedding
    sample = clean_df.iloc[0]["text_for_embedding"]
    assert "Title:" in sample
    assert "Authors:" in sample
    assert "Categories:" in sample
    assert "Published:" in sample
    assert "Summary:" in sample

    # Kiểm tra các cột bổ trợ
    assert "age_days" in clean_df.columns
    assert (clean_df["age_days"] >= 0).all()
    assert "summary_chars" in clean_df.columns
    assert (clean_df["summary_chars"] > 0).all()


def test_great_expectations_quality_gate(clean_df, settings):
    res = run_data_quality_checks(clean_df, settings, "test_clean")
    assert res["success"] is True
    assert res["row_count"] == 24


def test_freshness_sla(clean_df, settings, tmp_path):
    report = build_freshness_report(clean_df, settings, tmp_path / "freshness.json")
    assert report["is_fresh"] is True
    assert report["stale_ratio"] <= 0.25


def test_testset_generation(clean_df, tmp_path):
    test_path = tmp_path / "testset.json"
    test_set = build_test_set(clean_df, test_path)
    assert len(test_set) == 10
    types = {q["question_type"] for q in test_set}
    assert "summary" in types
    assert "authors" in types
    assert "date" in types
    assert "categories" in types


def test_corruption_triggers_quality_failure(clean_df, settings, tmp_path):
    log_path = tmp_path / "corruption_log.json"
    corrupted_df = corrupt_clean_dataframe(clean_df, log_path)

    assert log_path.exists()
    assert len(corrupted_df) < len(clean_df) or corrupted_df["paper_id"].duplicated().any()

    # Quality Gate trên dữ liệu bẩn phải FAILED
    res = run_data_quality_checks(corrupted_df, settings, "test_corrupted")
    assert res["success"] is False

    # Freshness trên dữ liệu bẩn phải vi phạm SLA
    freshness = build_freshness_report(corrupted_df, settings, tmp_path / "corrupted_freshness.json")
    assert freshness["is_fresh"] is False
