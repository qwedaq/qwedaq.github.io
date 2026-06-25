#!/usr/bin/env python3
from __future__ import annotations
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def normalize(value: str) -> str:
    value = unicodedata.normalize('NFKD', value.lower())
    value = ''.join(ch for ch in value if not unicodedata.combining(ch))
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', value).split())

errors = []
pub_path = ROOT / 'src/data/publications.json'
data = json.loads(pub_path.read_text(encoding='utf-8'))
seen = {}
for index, item in enumerate(data.get('publications', [])):
    for required in ('title', 'authors', 'venue', 'year'):
        if not item.get(required):
            errors.append(f'Publication {index} is missing {required}.')
    key = normalize(item.get('title', ''))
    if key in seen:
        errors.append(f'Duplicate normalized title: {item.get("title")} and {seen[key]}')
    seen[key] = item.get('title')

news = json.loads((ROOT / 'src/data/news.json').read_text(encoding='utf-8'))
for index, item in enumerate(news):
    if not re.fullmatch(r'\d{2}/\d{4}', item.get('date', '')):
        errors.append(f'News item {index} has invalid date format: {item.get("date")}')

for required in ['public/Aveen_Dayal_CV.pdf', 'public/images/headshot.jpg']:
    if not (ROOT / required).exists():
        errors.append(f'Missing required asset: {required}')

if errors:
    print('\n'.join(f'ERROR: {error}' for error in errors), file=sys.stderr)
    raise SystemExit(1)
print(f'Validated {len(data["publications"])} unique publications and {len(news)} news items.')
