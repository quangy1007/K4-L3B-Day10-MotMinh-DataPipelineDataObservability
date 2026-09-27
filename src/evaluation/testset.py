from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path: Path | str) -> list[dict[str, Any]]:
    """Tạo bộ evaluation benchmark gồm 10 câu hỏi đa dạng qua 4 nhóm nghiệp vụ.

    Các nhóm nghiệp vụ:
    - summary: Yêu cầu tóm tắt câu đầu tiên của abstract
    - authors: Yêu cầu danh sách tác giả
    - date: Yêu cầu ngày xuất bản
    - categories: Yêu cầu các danh mục chủ đề
    """
    if len(df) < 4:
        raise ValueError(f"Dữ liệu quá ít ({len(df)} dòng), cần tối thiểu 4 bài báo để sinh test set.")

    out_p = Path(output_path)
    records = df.to_dict(orient="records")
    n = len(records)

    # Phân bổ 10 câu hỏi qua 4 nhóm: 3 summary, 3 authors, 2 date, 2 categories
    question_plan = [
        ("summary", "What is the summary of '{title}'?"),
        ("authors", "Who authored '{title}'?"),
        ("date", "When was '{title}' published?"),
        ("categories", "What categories does '{title}' belong to?"),
        ("summary", "What is the primary contribution in '{title}'?"),
        ("authors", "List the authors of '{title}'."),
        ("date", "What is the publication date of '{title}'?"),
        ("categories", "What subject categories are assigned to '{title}'?"),
        ("summary", "Give a summary of '{title}'."),
        ("authors", "Who wrote the paper '{title}'?"),
    ]

    test_set: list[dict[str, Any]] = []

    for idx, (q_type, template) in enumerate(question_plan, start=1):
        # Chọn paper luân phiên theo modulo
        paper = records[(idx - 1) % n]
        title = paper["title"]
        pid = paper["paper_id"]

        if q_type == "summary":
            gt = first_sentence(paper["summary"])
        elif q_type == "authors":
            gt = str(paper["authors_joined"])
        elif q_type == "date":
            gt = str(paper["published"])
        elif q_type == "categories":
            gt = str(paper["categories_joined"])
        else:
            gt = first_sentence(paper["summary"])

        question = template.format(title=title)

        test_set.append(
            {
                "id": f"eval-q{idx:02d}",
                "question_type": q_type,
                "question": question,
                "ground_truth": gt,
                "ground_truth_doc_ids": [pid],
            }
        )

    write_json(out_p, test_set)
    return test_set
