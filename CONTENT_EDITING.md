# Content editing guide

## Profile and links

Edit `src/data/profile.ts`.

## Research framework

Edit `src/data/research.ts`. Keep the five-pillar structure unless the overall
research framing changes.

## News

Edit `src/data/news.json`. Dates must use `MM/YYYY`. The validation script rejects
other formats.

## Publications

The canonical data lives in `src/data/publications.json`. The quarterly Scholar
sync enriches this file and preserves curated links.

Add optional fields only when verified:

```json
{
  "doi": "10.xxxx/example",
  "paper": "https://...",
  "code": "https://...",
  "project": "https://..."
}
```

Do not manually enter citation or h-index values; let the synchronization update
them.

## Academic service

Edit `src/data/service.json`.

## Replace or recrop the headshot

The active photograph is `public/images/headshot.jpg` and is referenced from
`src/data/profile.ts`.

- Desktop/laptop uses a 5:4 landscape frame.
- Mobile uses a square frame.
- CSS cropping is controlled by `.portrait` in `src/styles/global.css`.

Replace the image while keeping the same filename, or update `headshot` in
`src/data/profile.ts`.

## Add gallery photographs

Copy images into `public/images/gallery/`, then replace each
`gallery-placeholder` block in `src/pages/about.astro` with an `<img>` and a
caption. Keep descriptive `alt` text.

## Replace the CV

Replace `public/Aveen_Dayal_CV.pdf` while keeping the filename unchanged.
