#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from sync_scholar import (
    has_complete_bibliographic_metadata,
    normalize_doi,
    titles_equivalent,
)

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []

pub_path = ROOT / "src" / "data" / "publications.json"
data = json.loads(pub_path.read_text(encoding="utf-8"))
publications = data.get("publications", [])

for index, item in enumerate(publications):
    if not has_complete_bibliographic_metadata(item):
        errors.append(f"Publication {index} has incomplete title/authors/venue/year: {item.get('title')}")

for left in range(len(publications)):
    for right in range(left + 1, len(publications)):
        a = publications[left]
        b = publications[right]
        if titles_equivalent(a, b):
            errors.append(f"Duplicate paper titles: '{a.get('title')}' and '{b.get('title')}'")

seen_dois: dict[str, str] = {}
for item in publications:
    doi = normalize_doi(item.get("doi"))
    if not doi:
        continue
    if doi in seen_dois:
        errors.append(f"Duplicate DOI {doi}: '{seen_dois[doi]}' and '{item.get('title')}'")
    seen_dois[doi] = item.get("title", "")

news = json.loads((ROOT / "src/data/news.json").read_text(encoding="utf-8"))
for index, item in enumerate(news):
    if not re.fullmatch(r"\d{2}/\d{4}", item.get("date", "")):
        errors.append(f"News item {index} has invalid date format: {item.get('date')}")

for required in ["public/Aveen_Dayal_CV.pdf", "public/images/headshot.jpg"]:
    if not (ROOT / required).exists():
        errors.append(f"Missing required asset: {required}")

if errors:
    print("\n".join(f"ERROR: {error}" for error in errors), file=sys.stderr)
    raise SystemExit(1)

print(f"Validated {len(publications)} unique publications and {len(news)} news items.")
