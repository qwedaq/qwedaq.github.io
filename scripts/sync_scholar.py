#!/usr/bin/env python3
"""Synchronize publications and Google Scholar metrics via SerpApi.

Deduplication policy:
- exact DOI match always means the same work;
- exact normalized title match means the same work;
- conservative near-title matching handles Scholar variants such as acronym prefixes,
  hyphenation, light/lightweight spelling, or publication/preprint wording changes;
- only complete records are allowed into the public list;
- duplicate citation counts are NOT summed because Scholar duplicate records can
  share citing papers. The maximum count is retained instead.

The canonical local bibliography remains authoritative for title, authors, venue,
year, type, DOI, paper, code, and project links. Scholar enriches it with live
citation counts and Scholar links.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "src" / "data" / "publications.json"
API_URL = "https://serpapi.com/search.json"
PAGE_SIZE = 100
MAX_RESULTS = 500
QUARTER_MONTHS = {1, 4, 7, 10}

# A deliberately high threshold. Lower values can merge genuinely different papers
# whose titles differ by only one technical term.
FUZZY_SEQUENCE_THRESHOLD = 0.955
FUZZY_TOKEN_OVERLAP_THRESHOLD = 0.82


def normalize_title(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def normalize_doi(value: str | None) -> str:
    if not value:
        return ""
    value = value.strip().lower()
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value)
    return value.rstrip(" .")


def _year_value(record: dict[str, Any]) -> int:
    try:
        return int(record.get("year") or 0)
    except (TypeError, ValueError):
        return 0


def has_complete_bibliographic_metadata(record: dict[str, Any]) -> bool:
    return bool(
        normalize_title(str(record.get("title", "")))
        and str(record.get("authors") or "").strip()
        and str(record.get("venue") or "").strip()
        and _year_value(record) > 0
    )


def _title_tokens(value: str) -> set[str]:
    return set(normalize_title(value).split())


def title_similarity(title_a: str, title_b: str) -> tuple[float, float]:
    """Return sequence similarity and symmetric token-overlap score."""
    a = normalize_title(title_a)
    b = normalize_title(title_b)
    if not a or not b:
        return 0.0, 0.0
    sequence = SequenceMatcher(None, a, b).ratio()
    tokens_a = set(a.split())
    tokens_b = set(b.split())
    if not tokens_a or not tokens_b:
        return sequence, 0.0
    intersection = len(tokens_a & tokens_b)
    overlap = min(intersection / len(tokens_a), intersection / len(tokens_b))
    return sequence, overlap


def years_compatible(a: dict[str, Any], b: dict[str, Any]) -> bool:
    year_a = _year_value(a)
    year_b = _year_value(b)
    if not year_a or not year_b:
        return True
    # Preprint and proceedings metadata can differ by one calendar year.
    return abs(year_a - year_b) <= 1


def titles_equivalent(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """Conservatively decide whether two records describe the same paper."""
    title_a = normalize_title(str(a.get("title", "")))
    title_b = normalize_title(str(b.get("title", "")))
    if not title_a or not title_b:
        return False
    if title_a == title_b:
        return True

    doi_a = normalize_doi(a.get("doi"))
    doi_b = normalize_doi(b.get("doi"))
    if doi_a and doi_b and doi_a == doi_b:
        return True

    if not years_compatible(a, b):
        return False

    sequence, overlap = title_similarity(title_a, title_b)
    return sequence >= FUZZY_SEQUENCE_THRESHOLD and overlap >= FUZZY_TOKEN_OVERLAP_THRESHOLD


def record_quality(record: dict[str, Any]) -> tuple[int, int, int, int, int]:
    """Rank metadata completeness, then citation count."""
    complete = int(has_complete_bibliographic_metadata(record))
    curated = sum(bool(record.get(k)) for k in ("doi", "paper", "code", "project"))
    specific_type = int(str(record.get("type") or "") in {"journal", "conference", "workshop", "preprint"})
    title_cleanliness = int("doi:" not in str(record.get("title", "")).lower())
    citations = int(record.get("citations") or 0)
    return complete, curated, specific_type, title_cleanliness, citations


def merge_duplicate_records(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """Merge duplicate records without double-counting citations."""
    preferred, other = (a, b) if record_quality(a) >= record_quality(b) else (b, a)
    merged = dict(other)
    merged.update(preferred)

    # Never sum duplicate citation counts: Scholar duplicates can overlap.
    merged["citations"] = max(int(a.get("citations") or 0), int(b.get("citations") or 0))

    # Keep the Scholar/cited-by link belonging to the largest citation count.
    citation_source = a if int(a.get("citations") or 0) >= int(b.get("citations") or 0) else b
    for key in ("scholar", "citedBy", "citationId"):
        if citation_source.get(key):
            merged[key] = citation_source[key]
        elif not merged.get(key):
            merged[key] = other.get(key)

    for key in ("doi", "paper", "code", "project", "abstract", "image"):
        if a.get(key):
            merged[key] = a[key]
        elif b.get(key):
            merged[key] = b[key]

    for key in ("title", "authors", "venue", "year", "type"):
        if not merged.get(key):
            merged[key] = other.get(key)
    return merged


def deduplicate(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return one complete record per unique paper title/DOI."""
    unique: list[dict[str, Any]] = []
    for raw_record in records:
        record = dict(raw_record)
        if not normalize_title(str(record.get("title", ""))):
            continue

        match_index: int | None = None
        for index, existing in enumerate(unique):
            if titles_equivalent(existing, record):
                match_index = index
                break

        if match_index is None:
            unique.append(record)
        else:
            unique[match_index] = merge_duplicate_records(unique[match_index], record)

    return sorted(
        unique,
        key=lambda item: (
            -_year_value(item),
            -int(item.get("citations") or -1),
            normalize_title(str(item.get("title", ""))),
        ),
    )


def merge_local_and_remote(local: dict[str, Any], remote: dict[str, Any]) -> dict[str, Any]:
    """Preserve verified local bibliography and apply Scholar metrics/links."""
    merged = dict(remote)
    for key in (
        "title", "authors", "venue", "year", "type", "doi", "paper",
        "code", "project", "abstract", "image",
    ):
        value = local.get(key)
        if value not in (None, "", 0):
            merged[key] = value

    merged["citations"] = max(
        int(local.get("citations") or 0),
        int(remote.get("citations") or 0),
    )
    for key in ("scholar", "citedBy", "citationId"):
        if remote.get(key):
            merged[key] = remote[key]
        elif local.get(key):
            merged[key] = local[key]
    return merged


def request_page(api_key: str, author_id: str, start: int) -> dict[str, Any]:
    params = {
        "engine": "google_scholar_author",
        "author_id": author_id,
        "hl": "en",
        "sort": "pubdate",
        "num": str(PAGE_SIZE),
        "start": str(start),
        "api_key": api_key,
    }
    url = API_URL + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "AveenPortfolioScholarSync/2.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            payload = json.load(response)
    except Exception as exc:
        raise RuntimeError(f"Scholar API request failed at offset {start}: {exc}") from exc
    if payload.get("error"):
        raise RuntimeError(str(payload["error"]))
    return payload


def parse_metrics(cited_by: dict[str, Any]) -> dict[str, int | None]:
    result = {"citations": None, "hIndex": None, "i10Index": None}
    for row in cited_by.get("table", []) or []:
        if not isinstance(row, dict):
            continue
        for raw_key, values in row.items():
            if not isinstance(values, dict):
                continue
            key = normalize_title(raw_key).replace(" ", "_")
            try:
                value = int(values.get("all"))
            except (TypeError, ValueError):
                continue
            if "i10" in key:
                result["i10Index"] = value
            elif key in {"h_index", "hindex", "indice_h"} or (key.startswith("h_") and "index" in key):
                result["hIndex"] = value
            elif "citation" in key:
                result["citations"] = value
    return result


def article_to_record(article: dict[str, Any], scholar_url: str) -> dict[str, Any]:
    cited = article.get("cited_by") or {}
    try:
        year_value = int(article.get("year"))
    except (TypeError, ValueError):
        matches = re.findall(r"\b(?:19|20)\d{2}\b", str(article.get("publication", "")))
        year_value = int(matches[-1]) if matches else 0

    publication = str(article.get("publication") or "").strip()
    lower = publication.lower()
    conference_hints = (
        "conference", "proceedings", "symposium", "workshop", "cvpr", "iccv",
        "eccv", "wacv", "neurips", "icml", "iclr", "aaai", "ijcai",
        "icassp", "interspeech", "ieee-ises", "comsnets",
    )
    journal_hints = (
        "journal", "transactions", "letters", "review", "applied soft computing",
        "pattern recognition", "sādhanā", "sadhana", "acoustical society",
    )
    if any(token in lower for token in conference_hints):
        inferred_type = "conference"
    elif any(token in lower for token in journal_hints):
        inferred_type = "journal"
    else:
        inferred_type = "publication"

    return {
        "title": str(article.get("title") or "").strip(),
        "authors": str(article.get("authors") or "").strip(),
        "venue": publication,
        "year": year_value,
        "type": inferred_type,
        "citations": int(cited.get("value", 0) or 0),
        "scholar": article.get("link") or scholar_url,
        "citedBy": cited.get("link"),
        "citationId": article.get("citation_id"),
    }


def find_equivalent(record: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    matches = [candidate for candidate in candidates if titles_equivalent(record, candidate)]
    if not matches:
        return None
    # If Scholar exposes multiple variants, collapse them first and use the richest.
    return deduplicate(matches)[0]


def merge_with_local(local_records: list[dict[str, Any]], scholar_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Existing local duplicates are also cleaned. Incomplete previously committed
    # Scholar-only records are discarded here.
    local_unique = [item for item in deduplicate(local_records) if has_complete_bibliographic_metadata(item)]
    scholar_unique = deduplicate(scholar_records)

    merged: list[dict[str, Any]] = []
    used_remote_ids: set[int] = set()

    for local in local_unique:
        equivalent = [remote for remote in scholar_unique if titles_equivalent(local, remote)]
        if equivalent:
            remote_merged = deduplicate(equivalent)[0]
            merged.append(merge_local_and_remote(local, remote_merged))
            used_remote_ids.update(id(remote) for remote in equivalent)
        else:
            merged.append(local)

    for remote in scholar_unique:
        if id(remote) in used_remote_ids:
            continue
        if not has_complete_bibliographic_metadata(remote):
            print(f"Skipping incomplete Scholar-only record: {remote.get('title') or 'Untitled'}", file=sys.stderr)
            continue
        merged.append(remote)

    final = deduplicate(merged)
    invalid = [item.get("title", "Untitled") for item in final if not has_complete_bibliographic_metadata(item)]
    if invalid:
        raise RuntimeError("Refusing to write incomplete records: " + "; ".join(invalid))
    return final


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Run outside quarterly months.")
    args = parser.parse_args()

    now = dt.datetime.now(dt.timezone.utc)
    if not args.force and now.month not in QUARTER_MONTHS:
        print(f"Month {now.month} is not a quarterly sync month; no Scholar request made.")
        return 0

    api_key = os.environ.get("SERPAPI_KEY", "").strip()
    if not api_key:
        print("SERPAPI_KEY is not set. Existing publication data was left unchanged.", file=sys.stderr)
        return 2

    current = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    author_id = current["profile"]["authorId"]
    scholar_url = current["profile"]["scholarUrl"]

    first_page: dict[str, Any] | None = None
    articles: list[dict[str, Any]] = []
    for start in range(0, MAX_RESULTS, PAGE_SIZE):
        page = request_page(api_key, author_id, start)
        first_page = first_page or page
        page_articles = page.get("articles") or []
        if not isinstance(page_articles, list):
            raise RuntimeError("The Scholar API returned an invalid articles field.")
        articles.extend(article_to_record(article, scholar_url) for article in page_articles)
        if len(page_articles) < PAGE_SIZE:
            break

    if not articles:
        raise RuntimeError("Scholar returned zero publications; refusing to overwrite existing data.")

    output = {
        "profile": {
            **current.get("profile", {}),
            "lastSynced": now.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "source": "Google Scholar via SerpApi; verified local bibliography is preserved and duplicate title variants are merged.",
        },
        "metrics": {
            key: value if value is not None else current.get("metrics", {}).get(key)
            for key, value in parse_metrics((first_page or {}).get("cited_by") or {}).items()
        },
        "publications": merge_with_local(current.get("publications", []), articles),
    }

    DATA_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Synchronized {len(output['publications'])} unique publications.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
