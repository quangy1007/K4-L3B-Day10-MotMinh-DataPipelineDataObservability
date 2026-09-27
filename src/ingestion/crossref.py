from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload thanh list PaperRecord."""
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        paper_id = str(item.get("DOI", "")).strip()
        titles = item.get("title", [])
        if isinstance(titles, list) and titles:
            title = normalize_whitespace(str(titles[0]))
        else:
            title = normalize_whitespace(str(titles or ""))

        abstract_raw = str(item.get("abstract", ""))
        # Loai bo tat ca tag HTML/XML nhu <jats:p>, <jats:italic>, etc.
        cleaned_abstract = re.sub(r"<[^>]+>", " ", abstract_raw)
        summary = normalize_whitespace(cleaned_abstract)

        authors: list[str] = []
        for author in item.get("author", []):
            given = author.get("given", "").strip()
            family = author.get("family", "").strip()
            name = f"{given} {family}".strip() if (given or family) else author.get("name", "").strip()
            if name:
                authors.append(name)

        categories = [normalize_whitespace(str(c)) for c in item.get("subject", []) if str(c).strip()]
        primary_category = categories[0] if categories else "General"

        date_parts = item.get("published", {}).get("date-parts", [[]])
        if date_parts and date_parts[0]:
            parts = date_parts[0]
            year = int(parts[0]) if len(parts) > 0 else 2026
            month = int(parts[1]) if len(parts) > 1 else 1
            day = int(parts[2]) if len(parts) > 2 else 1
            published = f"{year:04d}-{month:02d}-{day:02d}"
        else:
            created = item.get("created", {}).get("date-time", "")
            published = created[:10] if len(created) >= 10 else "2026-01-01"

        updated = published
        url = item.get("URL", f"https://doi.org/{paper_id}")
        comment = f"Crossref record {paper_id}"

        if not paper_id or not title:
            continue

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=url,
                pdf_url=url,
                comment=comment,
            )
        )

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi source API, luu raw response, parse thanh records co fallback offline."""
    if settings.refresh_source:
        try:
            params = {
                "query": settings.source_query,
                "filter": settings.source_filter,
                "rows": settings.max_results,
            }
            headers = {"User-Agent": "DataObservabilityLab/1.0 (mailto:lab-day10@vinuni.edu.vn)"}
            resp = requests.get("https://api.crossref.org/works", params=params, headers=headers, timeout=12)
            if resp.status_code == 200:
                payload = resp.json()
                write_json(settings.paths.raw_api_response, payload)
                records = parse_crossref_payload(payload)
                if records:
                    write_json(settings.paths.raw_records_json, [asdict(r) for r in records])
                    return records
        except Exception:
            # Fallback to local snapshot when network fails or 429/503 occurs
            pass

    # Doc tu snapshot offline
    if settings.paths.raw_records_json.exists():
        records = load_raw_records(settings.paths.raw_records_json)
        if records:
            return records

    if settings.paths.raw_api_response.exists():
        payload = read_json(settings.paths.raw_api_response)
        records = parse_crossref_payload(payload)
        if records:
            write_json(settings.paths.raw_records_json, [asdict(r) for r in records])
            return records

    raise FileNotFoundError(
        f"Khong tim thay du lieu raw tai {settings.paths.raw_records_json} hoac {settings.paths.raw_api_response}"
    )


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh list PaperRecord."""
    raw_list = read_json(path)
    records: list[PaperRecord] = []
    for item in raw_list:
        records.append(
            PaperRecord(
                paper_id=str(item["paper_id"]).strip(),
                title=normalize_whitespace(str(item["title"])),
                summary=normalize_whitespace(str(item.get("summary", ""))),
                authors=[normalize_whitespace(str(a)) for a in item.get("authors", [])],
                categories=[normalize_whitespace(str(c)) for c in item.get("categories", [])],
                primary_category=str(item.get("primary_category", "General")),
                published=str(item.get("published", "2026-01-01")),
                updated=str(item.get("updated", item.get("published", "2026-01-01"))),
                abs_url=str(item.get("abs_url", "")),
                pdf_url=str(item.get("pdf_url", "")),
                comment=str(item.get("comment", "")),
            )
        )
    return records
