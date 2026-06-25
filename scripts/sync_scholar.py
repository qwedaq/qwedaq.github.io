#!/usr/bin/env python3
"""Synchronize publications and Google Scholar metrics via SerpApi.

The canonical local list is preserved when the API is unavailable. Scholar results
are deduplicated by DOI when present and otherwise by a normalized title key.
No direct Google Scholar scraping is performed.
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
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "src" / "data" / "publications.json"
API_URL = "https://serpapi.com/search.json"
PAGE_SIZE = 100
MAX_RESULTS = 500
QUARTER_MONTHS = {1, 4, 7, 10}


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
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "AveenPortfolioScholarSync/1.0"})
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
            raw_value = values.get("all")
            try:
                value = int(raw_value)
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
    year = article.get("year")
    try:
        year_value = int(year)
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
        "title": str(article.get("title") or "Untitled publication").strip(),
        "authors": str(article.get("authors") or "").strip(),
        "venue": publication,
        "year": year_value,
        "type": inferred_type,
        "citations": int(cited.get("value", 0) or 0),
        "scholar": article.get("link") or scholar_url,
        "citedBy": cited.get("link"),
        "citationId": article.get("citation_id"),
    }


def richer(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """Merge two duplicate records while preserving curated local fields."""
    preferred = a if int(a.get("citations") or 0) >= int(b.get("citations") or 0) else b
    other = b if preferred is a else a
    merged = dict(other)
    merged.update(preferred)
    curated_keys = ("doi", "paper", "code", "project", "abstract", "image", "type")
    for key in curated_keys:
        if a.get(key):
            merged[key] = a[key]
        elif b.get(key):
            merged[key] = b[key]
    for key in ("authors", "venue", "scholar", "citedBy", "citationId"):
        if not merged.get(key):
            merged[key] = other.get(key)
    return merged


def deduplicate(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate primarily by normalized title and secondarily by DOI.

    Title matching is primary because Scholar author responses do not reliably
    expose DOI values. DOI matching still merges records whose titles differ.
    """
    by_title: dict[str, dict[str, Any]] = {}
    doi_to_title: dict[str, str] = {}

    for record in records:
        title_key = normalize_title(str(record.get("title", "")))
        if not title_key:
            continue
        doi = normalize_doi(record.get("doi"))

        existing_key = title_key if title_key in by_title else doi_to_title.get(doi, "") if doi else ""
        if existing_key:
            by_title[existing_key] = richer(by_title[existing_key], record)
            merged_doi = normalize_doi(by_title[existing_key].get("doi"))
            if merged_doi:
                doi_to_title[merged_doi] = existing_key
        else:
            by_title[title_key] = dict(record)
            if doi:
                doi_to_title[doi] = title_key

    return sorted(
        by_title.values(),
        key=lambda item: (-int(item.get("year") or 0), -int(item.get("citations") or -1), normalize_title(str(item.get("title", "")))),
    )


def merge_with_local(local_records: list[dict[str, Any]], scholar_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scholar_unique = deduplicate(scholar_records)
    scholar_by_title = {normalize_title(str(item.get("title", ""))): item for item in scholar_unique}
    scholar_by_doi = {
        normalize_doi(item.get("doi")): item
        for item in scholar_unique
        if normalize_doi(item.get("doi"))
    }

    merged: list[dict[str, Any]] = []
    used_titles: set[str] = set()
    for local in deduplicate(local_records):
        title_key = normalize_title(str(local.get("title", "")))
        doi_key = normalize_doi(local.get("doi"))
        remote = scholar_by_title.get(title_key) or (scholar_by_doi.get(doi_key) if doi_key else None)
        if remote:
            merged.append(richer(local, remote))
            used_titles.add(normalize_title(str(remote.get("title", ""))))
        else:
            merged.append(local)

    for remote in scholar_unique:
        remote_title = normalize_title(str(remote.get("title", "")))
        if remote_title not in used_titles:
            merged.append(remote)
    return deduplicate(merged)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Run outside the configured quarterly months.")
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
        raise RuntimeError("The Scholar API returned zero publications; refusing to overwrite the existing list.")

    output = {
        "profile": {
            **current.get("profile", {}),
            "lastSynced": now.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "source": "Google Scholar via SerpApi; curated local links and metadata are preserved during merging.",
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
