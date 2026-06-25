#!/usr/bin/env python3
from sync_scholar import deduplicate, merge_with_local, normalize_title

records = [
    {"title": "A Paper: With Punctuation", "authors": "A", "venue": "V", "year": 2024, "citations": 2, "doi": "10.1/test"},
    {"title": "A paper with punctuation", "authors": "A, B", "venue": "V", "year": 2024, "citations": 5},
    {"title": "Different display title", "authors": "A", "venue": "V", "year": 2024, "citations": 1, "doi": "https://doi.org/10.1/test"},
]
unique = deduplicate(records)
assert len(unique) == 1, unique
assert unique[0]["citations"] == 5
assert unique[0]["doi"] == "10.1/test"

local = [{"title": "Local Title", "authors": "A", "venue": "Local", "year": 2025, "citations": None, "paper": "https://example.test/paper"}]
remote = [{"title": "local title", "authors": "A, B", "venue": "Remote", "year": 2025, "citations": 9, "scholar": "https://example.test/scholar"}]
merged = merge_with_local(local, remote)
assert len(merged) == 1
assert merged[0]["citations"] == 9
assert merged[0]["paper"] == "https://example.test/paper"
assert normalize_title("A & B") == "a and b"
print("Scholar synchronization logic tests passed.")
