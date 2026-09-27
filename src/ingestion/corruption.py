from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path | str) -> pd.DataFrame:
    """Tiêm 6 kịch bản dữ liệu lỗi (Synthetic Data Corruption) vào cleaned dataframe.

    Các kịch bản:
    1. Drop latest: Loại bỏ 20% bản ghi mới nhất.
    2. Blank summary: Xóa rỗng summary ở một số dòng (vi phạm độ dài tối thiểu).
    3. Inject noise: Chèn chuỗi rác ngẫu nhiên vào summary.
    4. Truncate title: Cắt ngắn tiêu đề bài báo xuống dưới 8 ký tự.
    5. Stale date: Lùi ngày xuất bản về năm 1990, đẩy tỷ lệ bài cũ > 25% để vi phạm Freshness SLA.
    6. Duplicate rows: Nhân bản dữ liệu tạo duplicate paper_id (vi phạm tính duy nhất của GX 1.x).
    """
    out_path = Path(output_log_path)
    corrupted = df.copy()

    log_entries: list[dict[str, Any]] = []

    # 1. Drop 20% bản ghi mới nhất
    drop_count = max(1, int(len(corrupted) * 0.20))
    corrupted = corrupted.sort_values(by="published", ascending=False).iloc[drop_count:].copy().reset_index(drop=True)
    log_entries.append(
        {
            "corruption": "drop_latest_records",
            "impacted_count": drop_count,
            "description": f"Đã loại bỏ {drop_count} bản ghi mới nhất (20% dữ liệu).",
        }
    )

    # 2. Blank summary ở 2 dòng đầu
    blank_indices = [0, 1] if len(corrupted) > 1 else [0]
    blanked_ids = []
    for idx in blank_indices:
        corrupted.at[idx, "summary"] = ""
        corrupted.at[idx, "summary_chars"] = 0
        blanked_ids.append(corrupted.at[idx, "paper_id"])
    log_entries.append(
        {
            "corruption": "blank_summary",
            "impacted_ids": blanked_ids,
            "description": f"Xóa rỗng trường summary trên {len(blanked_ids)} bản ghi.",
        }
    )

    # 3. Inject noise vào summary ở dòng kế tiếp
    noise_indices = [2, 3] if len(corrupted) > 3 else []
    noise_ids = []
    for idx in noise_indices:
        corrupted.at[idx, "summary"] = "### CORRUPTED NOISE %%% !!! INVALID UNREADABLE DATA ###"
        noise_ids.append(corrupted.at[idx, "paper_id"])
    if noise_ids:
        log_entries.append(
            {
                "corruption": "inject_noise",
                "impacted_ids": noise_ids,
                "description": f"Chèn ký tự nhiễu rác vào summary trên {len(noise_ids)} bản ghi.",
            }
        )

    # 4. Truncate title xuống dưới 8 ký tự
    trunc_indices = [4, 5] if len(corrupted) > 5 else []
    trunc_ids = []
    for idx in trunc_indices:
        corrupted.at[idx, "title"] = "Data"
        trunc_ids.append(corrupted.at[idx, "paper_id"])
    if trunc_ids:
        log_entries.append(
            {
                "corruption": "truncate_title",
                "impacted_ids": trunc_ids,
                "description": f"Cắt ngắn title xuống '< 8 ký tự' trên {len(trunc_ids)} bản ghi.",
            }
        )

    # 5. Stale date: Đưa ngày xuất bản về 1990 trên 35% bản ghi để phá vỡ Freshness SLA (>25%)
    stale_count = max(2, int(len(corrupted) * 0.35))
    stale_ids = []
    for idx in range(len(corrupted) - stale_count, len(corrupted)):
        corrupted.at[idx, "published"] = "1990-01-01"
        corrupted.at[idx, "age_days"] = 13000
        stale_ids.append(corrupted.at[idx, "paper_id"])
    log_entries.append(
        {
            "corruption": "stale_date",
            "impacted_count": len(stale_ids),
            "description": f"Lùi ngày xuất bản về 1990-01-01 trên {len(stale_ids)} bài báo, kích hoạt cảnh báo Freshness SLA.",
        }
    )

    # 6. Duplicate rows: Nhân bản 2 dòng tạo trùng lặp paper_id
    dup_rows = corrupted.iloc[:2].copy()
    corrupted = pd.concat([corrupted, dup_rows], ignore_index=True)
    log_entries.append(
        {
            "corruption": "duplicate_rows",
            "impacted_count": len(dup_rows),
            "description": f"Nhân bản {len(dup_rows)} dòng dữ liệu, vi phạm tính duy nhất (ExpectColumnValuesToBeUnique).",
        }
    )

    # 7. Tái tạo lại text_for_embedding và summary_chars
    for idx in range(len(corrupted)):
        title = corrupted.at[idx, "title"]
        authors = corrupted.at[idx, "authors_joined"]
        cats = corrupted.at[idx, "categories_joined"]
        pub = corrupted.at[idx, "published"]
        summ = corrupted.at[idx, "summary"]
        corrupted.at[idx, "summary_chars"] = len(str(summ))
        corrupted.at[idx, "text_for_embedding"] = (
            f"Title: {title}\n"
            f"Authors: {authors}\n"
            f"Categories: {cats}\n"
            f"Published: {pub}\n"
            f"Summary: {summ}"
        )

    # 8. Ghi log corruption
    payload = {
        "total_records_before": len(df),
        "total_records_after": len(corrupted),
        "corruptions_applied": log_entries,
    }
    write_json(out_path, payload)

    return corrupted
