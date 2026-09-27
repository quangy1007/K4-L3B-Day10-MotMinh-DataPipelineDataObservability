from __future__ import annotations

from pathlib import Path
from typing import Any
import uuid

import great_expectations as gx
import great_expectations.expectations as gxe
import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Chạy bộ Data Quality Gate theo chuẩn Great Expectations 1.x và Freshness SLA."""
    uid = uuid.uuid4().hex[:6]
    context = gx.get_context(mode="ephemeral")

    # Cấu hình Ephemeral Data Source theo chuẩn GX 1.x
    ds_name = f"papers_source_{report_name}_{uid}"
    asset_name = f"papers_asset_{report_name}_{uid}"
    batch_def_name = f"papers_batch_{report_name}_{uid}"
    suite_name = f"papers_suite_{report_name}_{uid}"

    data_source = context.data_sources.add_pandas(name=ds_name)
    data_asset = data_source.add_dataframe_asset(name=asset_name)
    batch_definition = data_asset.add_batch_definition_whole_dataframe(batch_def_name)
    batch = batch_definition.get_batch(batch_parameters={"dataframe": df})

    # Định nghĩa 4 Expectations thiết yếu
    suite = context.suites.add(gx.ExpectationSuite(name=suite_name))
    suite.add_expectation(gxe.ExpectTableRowCountToBeBetween(min_value=1, max_value=1000))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="paper_id"))
    suite.add_expectation(gxe.ExpectColumnValuesToBeUnique(column="paper_id"))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="title"))
    suite.add_expectation(gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=10, max_value=5000))

    # Thực thi kiểm định chất lượng
    try:
        val_def = context.validation_definitions.add(
            gx.ValidationDefinition(
                name=f"papers_val_{report_name}_{uid}",
                data=batch_definition,
                suite=suite,
            )
        )
        val_result = val_def.run(batch_parameters={"dataframe": df})
    except Exception:
        val_result = batch.validate(suite)

    success = bool(getattr(val_result, "success", False))

    # Bóc tách kết quả chi tiết từng expectation
    results_detail = []
    for r in getattr(val_result, "results", []):
        exp_config = getattr(r, "expectation_config", None)
        exp_type = getattr(exp_config, "type", str(type(exp_config).__name__)) if exp_config else "UnknownExpectation"
        r_success = bool(getattr(r, "success", False))
        result_info = getattr(r, "result", {})
        results_detail.append(
            {
                "expectation": exp_type,
                "success": r_success,
                "result": result_info if isinstance(result_info, dict) else str(result_info),
            }
        )

    # Đánh giá Freshness SLA
    freshness_report_path = (
        settings.paths.freshness_report
        if report_name == "baseline"
        else settings.paths.quality_dir / f"{report_name}_freshness_report.json"
    )
    freshness_info = build_freshness_report(df, settings, freshness_report_path)

    report_payload = {
        "report_name": report_name,
        "success": success,
        "row_count": len(df),
        "expectations_count": len(results_detail),
        "results": results_detail,
        "freshness": freshness_info,
    }

    # Lưu artifact chất lượng dữ liệu
    report_output_path = (
        settings.paths.baseline_quality_report
        if report_name == "baseline"
        else settings.paths.corrupted_quality_report
        if report_name == "corrupted"
        else settings.paths.quality_dir / f"{report_name}_quality_report.json"
    )
    write_json(report_output_path, report_payload)

    return report_payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path: Path | str) -> dict[str, Any]:
    """Tổng hợp Freshness report dựa trên trường age_days và ngưỡng Freshness SLA."""
    out_path = Path(report_path)
    total_rows = len(df)
    threshold = settings.freshness_threshold_days  # Mặc định 180 ngày

    if "age_days" in df.columns and total_rows > 0:
        stale_rows = int((df["age_days"] > threshold).sum())
    else:
        stale_rows = 0

    stale_ratio = float(stale_rows / total_rows) if total_rows > 0 else 0.0
    # Freshness SLA: Cảnh báo vi phạm (is_fresh = False) nếu tỷ lệ quá hạn vượt quá 25% (0.25)
    is_fresh = bool(stale_ratio <= 0.25)

    latest_published = str(df["published"].max()) if "published" in df.columns and total_rows > 0 else "N/A"
    oldest_published = str(df["published"].min()) if "published" in df.columns and total_rows > 0 else "N/A"

    report = {
        "total_rows": total_rows,
        "threshold_days": threshold,
        "stale_rows": stale_rows,
        "stale_ratio": round(stale_ratio, 4),
        "is_fresh": is_fresh,
        "latest_published": latest_published,
        "oldest_published": oldest_published,
    }

    write_json(out_path, report)
    return report
