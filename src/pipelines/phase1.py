from __future__ import annotations

from core.config import load_settings
from core.utils import now_utc, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Xây dựng và thực thi Baseline Data Pipeline (Pha 1) End-to-End."""
    print("=" * 60)
    print("🚀 BẮT ĐẦU PHA 1: BASELINE DATA PIPELINE & OBSERVABILITY")
    print("=" * 60)

    # 1. Cấu hình
    settings = load_settings()

    # 2. Ingestion dữ liệu thô
    print("\n[1/6] Ingestion dữ liệu từ Crossref API...")
    records = fetch_source_records(settings)
    print(f" -> Đã thu thập thành công {len(records)} bản ghi thô.")

    # 3. Làm sạch dữ liệu và tạo text_for_embedding chuẩn 5 phần
    print("\n[2/6] Tiền xử lý, tính age_days và text_for_embedding...")
    df_clean = build_clean_dataframe(records, now_utc())
    write_csv(df_clean, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, df_clean.to_dict(orient="records"))
    print(f" -> Đã làm sạch và lưu trữ {len(df_clean)} bài báo vào:")
    print(f"    - {settings.paths.clean_csv}")
    print(f"    - {settings.paths.clean_json}")

    # 4. Đánh chỉ mục Vector Store ChromaDB
    print("\n[3/6] Tạo vector embeddings và lập chỉ mục ChromaDB...")
    index = LocalEmbeddingIndex.build(df_clean, settings, settings.paths.embeddings_json)
    print(f" -> Đã nạp thành công {len(df_clean)} tài liệu vào collection '{index.collection_name}'.")

    # 5. Sinh hoặc tải bộ câu hỏi đánh giá Benchmark
    print("\n[4/6] Chuẩn bị bộ câu hỏi đánh giá Benchmark...")
    test_set = build_test_set(df_clean, settings.paths.eval_testset)
    print(f" -> Đã sinh {len(test_set)} câu hỏi kiểm thử tại {settings.paths.eval_testset}.")

    # 6. Đánh giá Baseline RAG Agent
    print("\n[5/6] Đánh giá hiệu năng RAG Agent (Baseline Benchmarks)...")
    eval_bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    hit_rate = eval_bundle.summary.get("retrieval_hit_rate", 0.0)
    token_f1 = eval_bundle.summary.get("mean_token_f1", 0.0)
    print(f" -> Retrieval Hit Rate: {hit_rate * 100:.1f}%")
    print(f" -> Mean Token F1:     {token_f1:.4f}")

    # 7. Kiểm định Data Observability (GX 1.x & Freshness SLA)
    print("\n[6/6] Chạy Data Quality Gate (GX 1.x) & Freshness SLA...")
    quality_report = run_data_quality_checks(df_clean, settings, "baseline")
    freshness_report = build_freshness_report(df_clean, settings, settings.paths.freshness_report)

    # 8. Xuất báo cáo Markdown Pha 1
    source_summary = {
        "timestamp": now_utc().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "source_api": settings.source_api,
        "collection_name": settings.baseline_collection_name,
        "raw_records_count": len(records),
        "clean_records_count": len(df_clean),
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=eval_bundle.summary,
        quality=quality_report,
        freshness=freshness_report,
    )

    print(f"\n✅ HOÀN THÀNH PHA 1! Báo cáo đã xuất tại: {settings.paths.baseline_report}")
    print("=" * 60)


if __name__ == "__main__":
    main()
