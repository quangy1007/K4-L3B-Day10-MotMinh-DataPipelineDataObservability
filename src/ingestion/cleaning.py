from __future__ import annotations

from datetime import datetime
import re

import pandas as pd

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord


def _clean_text(text: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", text)
    return normalize_whitespace(cleaned)


def _parse_date(date_str: str, default_date) -> datetime.date:
    try:
        clean_str = date_str.strip()[:10]
        return datetime.strptime(clean_str, "%Y-%m-%d").date()
    except Exception:
        return default_date


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thanh dataframe san sang de embed.

    1. Normalize title, summary, authors, categories.
    2. Parse published date va tinh age_days.
    3. Tao cot helper:
       - authors_joined
       - categories_joined
       - summary_chars
       - text_for_embedding (cau truc chuan 5 phan)
    4. Khử trùng lặp theo paper_id và lọc dòng rỗng.
    5. Trả về DataFrame sạch chuẩn hóa.
    """
    ref_date = run_date.date() if hasattr(run_date, "date") else run_date

    rows = []
    seen_ids = set()

    for r in records:
        pid = str(r.paper_id).strip()
        if not pid or pid in seen_ids:
            continue

        title = _clean_text(r.title)
        summary = _clean_text(r.summary)
        if not title:
            continue

        seen_ids.add(pid)

        authors = [normalize_whitespace(str(a)) for a in r.authors if str(a).strip()]
        categories = [normalize_whitespace(str(c)) for c in r.categories if str(c).strip()]
        authors_joined = ", ".join(authors) if authors else "Unknown"
        categories_joined = ", ".join(categories) if categories else "General"

        pub_date = _parse_date(r.published, ref_date)
        age_days = max(0, (ref_date - pub_date).days)

        summary_chars = len(summary)

        # Cấu trúc 5 phần chuẩn cho text_for_embedding
        text_for_embedding = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Categories: {categories_joined}\n"
            f"Published: {r.published}\n"
            f"Summary: {summary}"
        )

        rows.append(
            {
                "paper_id": pid,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": r.primary_category or (categories[0] if categories else "General"),
                "published": str(r.published),
                "updated": str(r.updated),
                "abs_url": str(r.abs_url),
                "pdf_url": str(r.pdf_url),
                "comment": str(r.comment),
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": summary_chars,
                "age_days": age_days,
                "text_for_embedding": text_for_embedding,
            }
        )

    df = pd.DataFrame(rows)
    return df
