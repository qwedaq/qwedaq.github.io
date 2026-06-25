# Deploy to GitHub Pages

The project is configured for the GitHub username `qwedaq` and a user-site
repository named `qwedaq.github.io`. That repository name publishes at:

`https://qwedaq.github.io`

## 1. Install and test locally

Install Node.js 22.12 or newer, open a terminal in this directory, and run:

```bash
npm install --no-audit --no-fund
npm run validate
npm run build
npm run dev
```

The first `npm install` creates `package-lock.json`. Commit that file to make
future installations deterministic.

## 2. Create the repository

On GitHub, create a **public** repository named exactly:

`qwedaq.github.io`

Do not initialize it with a README or license.

## 3. Push the project

```bash
git init
git add .
git commit -m "Launch personal research portfolio"
git branch -M main
git remote add origin https://github.com/qwedaq/qwedaq.github.io.git
git push -u origin main
```

## 4. Enable Pages

1. Open the repository on GitHub.
2. Go to **Settings → Pages**.
3. Under **Build and deployment**, choose **GitHub Actions** as the source.
4. Open the **Actions** tab and inspect **Deploy Astro site to GitHub Pages**.
5. After the workflow completes, open `https://qwedaq.github.io`.

The included deployment follows Astro's official GitHub Pages workflow with
`actions/checkout@v6`, `withastro/action@v6`, and `actions/deploy-pages@v5`.

## 5. Configure quarterly Scholar updates

Google Scholar does not provide an official public author API for this use case.
The repository therefore uses the SerpApi Google Scholar Author endpoint. The
private key is read only inside GitHub Actions and is never sent to website
visitors.

1. Create a SerpApi account and copy its API key.
2. In GitHub, open **Settings → Secrets and variables → Actions**.
3. Choose **New repository secret**.
4. Name the secret exactly `SERPAPI_KEY`.
5. Paste the key and save.
6. Open **Actions → Quarterly Google Scholar sync**.
7. Choose **Run workflow** to test the first synchronization manually.

The API is queried on the first day of January, April, July, and October. The
workflow wakes monthly and makes a small heartbeat commit in intervening months,
because GitHub automatically disables scheduled workflows in inactive public
repositories after 60 days. The heartbeat does not query Scholar.

The synchronization script:

- retrieves all paginated Scholar results;
- updates total citations and h-index;
- deduplicates by normalized title, using DOI where present;
- keeps the record with the larger Scholar citation count when duplicates collide;
- preserves manually curated DOI, paper, code, project, abstract, and image links;
- refuses to overwrite the site when the API fails or returns zero articles.

## 6. Add the headshot

Copy the photograph to:

`public/images/headshot.jpg`

Then edit `src/data/profile.ts`:

```ts
headshot: '/images/headshot.jpg'
```

Run `npm run build` before committing.

## 7. Optional custom domain

After the GitHub Pages URL works:

1. Purchase a domain.
2. Configure its DNS according to GitHub Pages documentation.
3. Add `public/CNAME` containing the domain, for example `www.aveendayal.com`.
4. Change `site` in `astro.config.mjs` to the custom HTTPS URL.
5. Add the custom domain under **Settings → Pages** on GitHub.
