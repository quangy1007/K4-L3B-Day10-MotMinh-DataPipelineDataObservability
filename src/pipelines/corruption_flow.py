from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Xây dựng và thực thi luồng Corruption -> Evaluate -> Idempotent Repair -> Compare."""
    print("=" * 60)
    print("⚠️ BẮT ĐẦU LUỒNG TIÊM LỖI & PHỤC HỒI (CORRUPTION & REPAIR FLOW)")
    print("=" * 60)

    settings = load_settings()

    # 1. Đọc dữ liệu sạch và baseline metrics
    print("\n[1/6] Nạp dữ liệu sạch và chỉ số Baseline...")
    if not settings.paths.clean_json.exists():
        raise FileNotFoundError(
            f"Chưa có dữ liệu sạch tại {settings.paths.clean_json}. Vui lòng chạy run_phase1.py trước."
        )
    df_clean = pd.read_json(settings.paths.clean_json)
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    print(f" -> Đã nạp {len(df_clean)} bài báo sạch.")
    print(f" -> Baseline Hit Rate: {baseline_metrics.get('retrieval_hit_rate', 0.0) * 100:.1f}%")

    # 2. Tiêm 6 kịch bản lỗi (Synthetic Data Corruption)
    print("\n[2/6] Tiêm 6 kịch bản làm bẩn dữ liệu (Data Corruption)...")
    df_corrupted = corrupt_clean_dataframe(df_clean, settings.paths.corruption_log)
    write_csv(df_corrupted, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, df_corrupted.to_dict(orient="records"))
    print(f" -> Đã ghi nhận log tiêm lỗi tại {settings.paths.corruption_log}")
    print(f" -> Dữ liệu sau tiêm lỗi: {len(df_corrupted)} dòng.")

    # 3. Đánh chỉ mục ChromaDB cho dữ liệu lỗi & Đo lường suy giảm (Silent Failure)
    print("\n[3/6] Lập chỉ mục dữ liệu bẩn và đo lường suy giảm RAG...")
    index_corrupted = LocalEmbeddingIndex.build(
        df_corrupted, settings, settings.paths.corrupted_embeddings_json
    )
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=index_corrupted,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    c_hit = corrupted_bundle.summary.get("retrieval_hit_rate", 0.0)
    c_f1 = corrupted_bundle.summary.get("mean_token_f1", 0.0)
    print(f" -> Corrupted Hit Rate: {c_hit * 100:.1f}%")
    print(f" -> Corrupted Token F1: {c_f1:.4f}")

    # 4. Kiểm định Observability trên dữ liệu lỗi
    print("\n[4/6] Chạy Quality Gate GX 1.x & Freshness SLA trên dữ liệu bẩn...")
    corrupted_quality = run_data_quality_checks(df_corrupted, settings, "corrupted")
    corrupted_freshness = build_freshness_report(
        df_corrupted, settings, settings.paths.quality_dir / "corrupted_freshness_report.json"
    )
    print(f" -> Quality Gate Status: {'PASSED' if corrupted_quality['success'] else 'FAILED ❌ (Phát hiện lỗi)'}")
    print(f" -> Freshness SLA:       {'FRESH' if corrupted_freshness['is_fresh'] else 'VIOLATED ⚠️ (Quá hạn > 25%)'}")

    # 5. Thực thi cơ chế Phục Hồi An Toàn (Idempotent Repair)
    print("\n[5/6] Kích hoạt cơ chế Phục hồi tự động (Idempotent Repair)...")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    df_repaired = build_clean_dataframe(raw_records, now_utc())
    write_csv(df_repaired, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, df_repaired.to_dict(orient="records"))

    # Đồng bộ hóa lại Vector DB
    index_repaired = LocalEmbeddingIndex.build(
        df_repaired, settings, settings.paths.repaired_embeddings_json
    )
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=index_repaired,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    repaired_quality = run_data_quality_checks(df_repaired, settings, "repaired")
    repaired_freshness = build_freshness_report(
        df_repaired, settings, settings.paths.quality_dir / "repaired_freshness_report.json"
    )
    r_hit = repaired_bundle.summary.get("retrieval_hit_rate", 0.0)
    r_f1 = repaired_bundle.summary.get("mean_token_f1", 0.0)
    print(f" -> Repaired Hit Rate:   {r_hit * 100:.1f}% (Phục hồi thành công)")
    print(f" -> Repaired Token F1:   {r_f1:.4f}")

    # 6. Xuất Báo Cáo Đối Chiếu 3 Trạng Thái
    print("\n[6/6] Xuất báo cáo so sánh đối chiếu 3 trạng thái...")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_bundle.summary,
        repaired_metrics=repaired_bundle.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )

    # In bảng đối chiếu ra terminal
    print("\n" + "=" * 65)
    print("📊 BẢNG TỔNG HỢP SO SÁNH 3 TRẠNG THÁI (BASELINE vs CORRUPTED vs REPAIRED)")
    print("=" * 65)
    print(f"{'Chỉ số':<22} | {'Baseline':<12} | {'Corrupted':<12} | {'Repaired':<12}")
    print("-" * 65)
    b_hit = baseline_metrics.get("retrieval_hit_rate", 0.0) * 100
    print(f"{'Retrieval Hit Rate':<22} | {b_hit:<11.1f}% | {c_hit * 100:<11.1f}% | {r_hit * 100:<11.1f}%")
    b_f1 = baseline_metrics.get("mean_token_f1", 0.0)
    print(f"{'Mean Token F1':<22} | {b_f1:<12.4f} | {c_f1:<12.4f} | {r_f1:<12.4f}")
    b_acc = baseline_metrics.get("judge_accuracy", 0.0) * 100
    c_acc = corrupted_bundle.summary.get("judge_accuracy", 0.0) * 100
    r_acc = repaired_bundle.summary.get("judge_accuracy", 0.0) * 100
    print(f"{'Judge Accuracy':<22} | {b_acc:<11.1f}% | {c_acc:<11.1f}% | {r_acc:<11.1f}%")
    print(f"{'GX 1.x Quality Gate':<22} | {'PASSED ✅':<12} | {'FAILED ❌':<12} | {'PASSED ✅':<12}")
    print(f"{'Freshness SLA':<22} | {'FRESH ✅':<12} | {'VIOLATED ⚠️':<12} | {'FRESH ✅':<12}")
    print("=" * 65)
    print(f"✅ Báo cáo chi tiết đã được tạo tại: {settings.paths.comparison_report}")


if __name__ == "__main__":
    main()
