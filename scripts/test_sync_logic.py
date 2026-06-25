#!/usr/bin/env python3
from sync_scholar import deduplicate, merge_with_local, normalize_title, titles_equivalent


def rec(title, year=2024, citations=0, **extra):
    return {
        "title": title,
        "authors": "A Dayal, B Author",
        "venue": "Example Venue",
        "year": year,
        "type": "conference",
        "citations": citations,
        **extra,
    }


# Exact normalized title and DOI variants collapse.
records = [
    rec("A Paper: With Punctuation", citations=2, doi="10.1/test"),
    rec("A paper with punctuation", citations=5),
    rec("Different display title", citations=1, doi="https://doi.org/10.1/test"),
]
unique = deduplicate(records)
assert len(unique) == 1, unique
assert unique[0]["citations"] == 5
assert unique[0]["doi"] == "10.1/test"

# Known Scholar title variants collapse conservatively.
madg = deduplicate([
    rec("MADG: margin-based adversarial learning for domain generalization", year=2023, citations=78),
    rec("Margin-based Adversarial Learning for Domain Generalization", year=2023, citations=32),
])
assert len(madg) == 1, madg
assert madg[0]["citations"] == 78

lightweight = deduplicate([
    rec("Lightweight deep convolutional neural network for background sound classification in speech signals", year=2022, citations=17),
    rec("Lightweight deep convolution neural network for background sound classification in speech signals", year=2022, citations=0, doi="10.1121/10.0010257"),
])
assert len(lightweight) == 1, lightweight
assert lightweight[0]["citations"] == 17
assert lightweight[0]["doi"] == "10.1121/10.0010257"

mini = deduplicate([
    rec("Mini-COVIDNet: efficient lightweight deep neural network for ultrasound based point-of-care detection of COVID-19", year=2021, citations=91),
    rec("Mini-COVIDNet: Efficient Light Weight Deep Neural Network for Ultrasound based Point-of-Care Testing of COVID-19", year=2021, citations=0, doi="10.1109/TUFFC.2021.3068190"),
])
assert len(mini) == 1, mini
assert mini[0]["citations"] == 91

# Related but distinct titles must not merge.
related = [
    rec("Foundation Model Priors Enhance Object Focus in Feature Space for Source-Free Object Detection", year=2026),
    rec("Foreground Confusion under Domain Shift: The Hidden Bottleneck in Source-Free Domain Adaptive Object Detection", year=2026),
]
assert not titles_equivalent(related[0], related[1])
assert len(deduplicate(related)) == 2

# Local metadata remains canonical, Scholar updates citations and links.
local = [rec("Local Title", year=2025, citations=0, venue="Verified Venue", paper="https://example.test/paper")]
remote = [rec("local title", year=2025, citations=9, venue="Remote Venue", scholar="https://example.test/scholar")]
merged = merge_with_local(local, remote)
assert len(merged) == 1
assert merged[0]["citations"] == 9
assert merged[0]["venue"] == "Verified Venue"
assert merged[0]["paper"] == "https://example.test/paper"
assert normalize_title("A & B") == "a and b"

print("Scholar synchronization and title-deduplication tests passed.")
