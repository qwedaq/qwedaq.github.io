# Aveen Dayal — Reliable AI Portfolio

A five-page Astro portfolio designed around a coherent reliable-AI research
framework.

## Pages

- Home
- About
- Publications
- Academic Service
- CV

## Local development

Requires Node.js 22.12 or newer.

```bash
npm install --no-audit --no-fund
npm run validate
npm run dev
```

Open the local URL printed by Astro, normally `http://localhost:4321`.

The included `.npmrc` uses the public npm registry and disables audit/funding
prompts. The repository intentionally does not include a generated lockfile from
the delivery environment.

For a production build:

```bash
npm run build
npm run preview
```

## Headshot

The supplied photograph is included as `public/images/headshot.jpg`. A landscape
crop is used on laptop and desktop layouts, while mobile uses a square crop through
responsive CSS.

The About-page gallery is intentionally composed of styled placeholders. See
`CONTENT_EDITING.md` for replacement instructions.

## Publication metrics

Total citations and h-index are sourced from the quarterly Google Scholar sync.
Until the first successful sync, the side panel clearly shows that live values are
pending rather than displaying invented values.

## Deployment

See `DEPLOYMENT.md` for GitHub Pages and Scholar-sync setup. See
`BUILD_VALIDATION.md` for completed checks and `CONTENT_PROVENANCE.md` for source
and accuracy notes.
