# Build and validation report

Validation date: 25 June 2026

## Passed checks

- `scripts/validate_data.py`
  - 20 unique seeded publication titles
  - 26 news entries
  - every news date follows `MM/YYYY`
  - required CV and uploaded headshot assets exist
- `scripts/test_sync_logic.py`
  - normalized-title deduplication
  - DOI fallback deduplication
  - preservation of curated paper links during Scholar merging
  - higher citation count retained for duplicate records
- Full Astro production build
  - 6 static pages generated
  - sitemap generated successfully
  - no Astro build errors
- Headshot integrated as a 5:4 landscape desktop image with a square mobile crop
- Publications metrics moved to a responsive side column
- Academic Service sections aligned to one shared grid
- Footer reduced to email, Google Scholar, GitHub, and LinkedIn

## Dependency versions

- Astro `7.0.2`
- `@astrojs/sitemap` `3.7.3`
- Node.js requirement: `>=22.12.0`

## Build commands used

```bash
npm install --no-audit --no-fund
npm run validate
npm run build
```

The delivery ZIP excludes `node_modules`, `dist`, and the environment-generated
`package-lock.json`. Running `npm install` locally will create a clean lockfile
using the public npm registry configured in `.npmrc`.
