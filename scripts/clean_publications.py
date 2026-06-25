#!/usr/bin/env python3
"""One-time cleanup of the currently committed publication file."""
from __future__ import annotations

import json
from pathlib import Path

from sync_scholar import deduplicate, has_complete_bibliographic_metadata

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "src" / "data" / "publications.json"

data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
before = list(data.get("publications", []))
after = [item for item in deduplicate(before) if has_complete_bibliographic_metadata(item)]
data["publications"] = after
DATA_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

print(f"Publication cleanup: {len(before)} records -> {len(after)} unique complete papers.")
for item in before:
    if not has_complete_bibliographic_metadata(item):
        print(f"Skipped incomplete record: {item.get('title')}")
