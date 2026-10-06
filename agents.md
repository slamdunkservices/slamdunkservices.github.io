# Agents Guide — Slam Dunk Bets Site

## What this is

Marketing + blog site for **Slam Dunk Bets**, an NBA, WNBA & MLB prop picks service — first baskets for basketball, home runs and NRFI/YRFI for baseball. Quarto website published to GitHub Pages at <https://slamdunk.bet> (custom domain set via the `CNAME` file).

## Tech

- **Quarto website** — see `_quarto.yml`. Theme: `litera` (Bootstrap 5-based) with `custom.scss` and `styles.css` overrides.
- **Content is plain markdown** — no R or Python code chunks in any `.qmd`, so rendering needs only Quarto itself. Build-time logic lives in one Lua filter (`_filters/seo-schema.lua`), which also needs only Quarto.
- **Quarto binary: 1.9 or newer is required** (`canonical-url`, `draft-mode`, `body-classes`, listing feeds). Installed at `~/.local/bin/quarto` (1.10.18, tarball install) and symlinked from `/usr/local/bin/quarto`, so `quarto` on `PATH` is the right one. An old root-owned 1.3.361 still sits in `/Applications/quarto`; never use it — it regresses Open Graph tags and every feature above. Check `quarto --version` before publishing.
- **Authoring:** RStudio with the visual editor (`slamdunkservices.github.io.Rproj`). Keep `PythonType: r-reticulate` set in the `.Rproj`.

## Commands

- `quarto preview` — live local preview with hot reload
- `quarto render` — build the site into `_site/` (gitignored)
- `quarto publish gh-pages` — render and push the built site to `gh-pages` (see Publishing)

There are no tests or linters. The verification greps in the SEO section below are the closest thing.

## Repo tour

| Path | Purpose |
|---|---|
| `_quarto.yml` | Site config — `site-url`, site description/image, navbar, footer, Open Graph/Twitter, `canonical-url`, includes, filter, render whitelist, `resources` |
| `index.qmd` | Homepage — hero (H1 tagline + one-paragraph lede), feature list, "Hall of Fame" carousel |
| `subscribe.qmd` | Subscription landing page — what's included, **pricing table**, `schema-offers` frontmatter |
| `apps.qmd` | Slam Dunk Dashboard page (carousel of screenshots) |
| `data.qmd` | Data products teaser page |
| `articles.qmd` | Blog listing page (reads `posts/`) and generates the RSS feed `articles.xml` |
| `faq.qmd` | FAQ as open `::: {.faq-item}` sections (see SEO) |
| `about.qmd`, `privacy.qmd`, `terms.qmd` | Trust pages, linked from the footer. Plain-language drafts, not legal advice; keep effective dates current |
| `contact.qmd`, `404.qmd` | Contact page; custom not-found page (GitHub Pages serves `404.html` automatically) |
| `posts/YYYY-MM/*.qmd` | Blog posts, grouped by year-month folders |
| `_drafts/` | Unfinished posts. Underscore prefix keeps the folder out of the render entirely (see its README) |
| `_filters/seo-schema.lua` | Emits JSON-LD structured data into every page's `<head>`, plus the Open Graph extras Quarto lacks (`og:url`, `og:type`, `article:*`) and intrinsic `width`/`height` on body images |
| `_scripts/post-render.sh` | Quarto `post-render` hook: rewrites the homepage `<loc>` in `sitemap.xml` from `/index.html` to `/` so it matches the canonical URL |
| `_includes/head.html` | Extra `<head>` markup: RSS link, search-engine verification meta tags (placeholders), preconnect |
| `_includes/after-body.html` | Loads `scripts/site-analytics.js` on every page |
| `_og/*.html` | Source compositions for the raster brand images (see Images). Not rendered |
| `robots.txt` | Copied verbatim to `_site/`. Explicitly allows search and AI crawlers and carries the `Sitemap:` line (Quarto does not add it when a source `robots.txt` exists) |
| `llms.txt` | Plain-text summary of the business and site for AI agents, per llmstxt.org. Shipped via `resources` |
| `images/` | All assets, organized by the page that uses them (see Images below) |
| `scripts/hof-carousel.js` | Homepage carousel; loads images from a JSON manifest |
| `scripts/site-analytics.js` | GA4 events: `cta_click` on Sharpduel/Whop/Dashboard links, `ai_referral` for AI-assistant referrers |
| `styles.css`, `custom.scss` | Site-wide styling overrides |
| `CNAME` | `slamdunk.bet` — GitHub Pages custom domain |
| `.claude/launch.json` | Dev-server config for the Claude Code browser preview (`quarto preview` on port 4321) |
| `_site/`, `.quarto/` | Build output (gitignored) |

## Branches

- `main` — source/working branch, edit here
- `gh-pages` — built site, and the repo's default branch on GitHub — **do not edit directly**

## Publishing

Publishing uses the Quarto `publish` command, which renders locally and pushes the built `_site/` to the `gh-pages` branch. Full docs: <https://quarto.org/docs/publishing/github-pages.html>.

No GitHub Actions workflow — all publishing happens from the author's machine. On first publish, Quarto writes a `_publish.yml` file recording the target; commit it when it appears.

Typical flow:

1. Edit on `main`
2. `quarto --version` — must be 1.9+
3. `quarto preview` — check locally
4. Commit + push `main`
5. `quarto publish gh-pages` from the repo root (must be on a branch that is **not** `gh-pages`)
6. After publish, spot-check `https://slamdunk.bet/robots.txt`, `/llms.txt`, `/sitemap.xml`, `/articles.xml`

## Common tasks

**Add a blog post.** Create `posts/YYYY-MM/slug.qmd` with this frontmatter (every key matters for search and social cards):

```yaml
---
title: "Post Title"
subtitle: "Optional kicker"
author: Slam Dunk Bets
date: YYYY-MM-DD
categories: [nba, first-basket, methodology]
draft: false
description: "One or two plain sentences, 120-220 characters, that say what the post covers. Becomes the meta description, the OG description, the listing blurb, and the JSON-LD description."
image: "/images/posts/slug-image.jpg"
image-alt: "What the image shows"
---
```

- **Category vocabulary** (use only these): `nba`, `wnba`, `mlb`, `first-basket`, `home-runs`, `methodology`, `roi-recap`, `strategy`.
- Every body image needs alt text: `![What it shows](/images/posts/foo.jpg)`.
- Put the topic in the `title` itself ("How Do We Predict Home Runs? Part 1: Pitch Data"), not in `subtitle`: the title is the `<title>`, the H1, the JSON-LD headline, and what search and AI answer engines cite.
- Break the body into `## ` sections every few paragraphs with headings that read as answers ("What counts as a playable edge"). Answer engines and featured snippets extract headed sections; a wall of paragraphs gets skipped.
- Link to at least one other page on the site (the FAQ, a series part, a recap) and, for a multi-part series, end every part with the shared `::: {.series-nav}` block listing all parts (styled in `styles.css`). Link forward to the next part in the closing paragraph.
- Keep images at or under 1600px on the long edge and roughly 300 KB (`sips -Z 1600 -s formatOptions 45 in.jpg --out in.jpg` works; `sips` upscales smaller images with `-Z`, so skip the flag for anything already smaller). Oversized photos were the single biggest Core Web Vitals problem on the site.
- Link subscribe CTAs to `https://sharpduel.com/slam_dunk_bets` (preferred) and Whop only as `https://whop.com/slam-dunk-bets` (no `www`, no trailing slash).
- Add a bullet for the post under the matching section of `llms.txt`.
- The post appears automatically on `articles.qmd` and in `articles.xml`. `draft: true` keeps it off the listing but still renders an empty page; park truly unfinished posts in `_drafts/` instead.

**Edit a page.** Edit the `.qmd` at repo root, preview, commit, publish. Every root page has `title`, `pagetitle` (browser/search title; Quarto appends " – Slam Dunk Bets"), and `description` in its frontmatter. Keep them when editing; write them for any new page.

**Change pricing.** Prices live in four places and must match: the table and `schema-offers` block in `subscribe.qmd`, the "How much does it cost?" answer in `faq.qmd`, and the key-facts paragraph in `llms.txt`.

**Update the ROI numbers.** The FAQ "What kind of ROI" answer, the `## Track record` line in `llms.txt`, and the headline claim ("8,000+ units", in `index.qmd`, `about.qmd`, `faq.qmd`, `_quarto.yml` description, `SITE_DESC` in `_filters/seo-schema.lua`, and `_og/og-default.html` → regenerate the PNG) all come from the graded ledgers, not from memory. Sources and method:

- NBA and WNBA season snapshots: `~/Code/adhoc/bet_tracking/<LEAGUE>/<season>/bet_tracking_consolidated.csv` (registry: `slam_dunk_tracking.R` there). Net = sum of `units_standardized_net`; ROI = net / sum of `units_standardized_bet` (voids excluded from the denominator). 2021-22 and 2022-23 are spreadsheets at flat stakes (`Win`/`Loss` outcomes, American `Odds`, `Units` staked); 2021-22 computes to +572 net on 3,349 staked (17.1%), which is what the FAQ and `llms.txt` show. By decision (2026-09-14) the site keeps 2022-23 at +1,610 with its Kelly footnote even though the spreadsheet computes to about +929.
- The homepage chart `images/home/cumulative_total.png` is built by `_scripts/roi-chart/build.sh` (Python reads the ledgers above, R draws the chart). It covers NBA, WNBA, and MLB home runs plus NRFI/YRFI, and it prints every season's net and ROI as it runs. 2022-23 is scaled to the +1,610 basis so the line agrees with the headline; on the raw spreadsheet basis the all-time total is about 680 units lower. Rebuild it whenever the FAQ numbers change, and update the date in its caption in `index.qmd`. Last built 2026-10-06, through 2026-10-05: 8,579 units.
- Live WNBA season: `$WNBA_DATA_ROOT/02_curated/wnba_first_to_score/tracking/ledger/*.csv` (exchanges already excluded). The adhoc snapshot of the current season goes stale; prefer the ledger.
- MLB: `$MLB_DATA_ROOT/02_curated/bet_tracking/<product>/roi_daily.csv`; use only rows where `market == "ALL"` (per-market rows would double-count). Net = sum of `net_units_std`, staked = sum of `staked_units_std`.
- Read CSVs with `/Users/jim/Code/jobs/mlb/.venv/bin/python` (pandas); the two `.xlsx` seasons need `/Users/jim/Code/jobs/atp/.venv/bin/python` (openpyxl). Data roots are defined in `~/.<league>_jobs.env`; NBA has no local root (history is in the adhoc tree and `gs://sdbs_nba`).

**Update the FAQ.** Each question is a block:

```markdown
::: {.faq-item}
### The question, phrased the way someone would ask it?

One to three plain sentences. First sentence should stand alone.
:::
```

The Lua filter turns these into `FAQPage` structured data; anything outside a `.faq-item` block is ignored by it.

**Images.** `images/` is organized by the page that consumes each asset:

| Folder | Used by |
|---|---|
| `images/brand/` | Site-wide — favicon (`_quarto.yml`), logos (`styles.css`, `index.qmd`), `og-default.png` (social card, `website.image`) and `logo-square.png` (JSON-LD logo) |
| `images/home/` | `index.qmd` |
| `images/apps/` | `apps.qmd` |
| `images/posts/` | `posts/**/*.qmd` |
| `images/hof-carousel/` | Homepage carousel (see below) |
| `images/_unused/` | Not referenced anywhere on the site — staging area for review, not published (the square SVG here is the source for `logo-square.png`) |

Drop new assets into the folder for the page that uses them. Reference as `images/<folder>/foo.jpg` from root-level pages, or `/images/<folder>/foo.jpg` from posts (root-absolute is preferred in posts because it also works as `image:` frontmatter and in the JSON-LD).

Quarto only copies images that are actually referenced into `_site/`, so an unreferenced file costs nothing at publish time — but keep `images/_unused/` for anything not on the site so the page folders stay a true inventory. The leading underscore also keeps the folder out of Quarto's input scan.

**Regenerate the social card or square logo.** Edit `_og/og-default.html` or `_og/logo-square.html`, then screenshot with headless Chrome (the only rasterizer on this machine; no Pillow/rsvg):

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 --user-data-dir=/tmp/sdb-chrome --window-size=1200,630 --screenshot="$PWD/images/brand/og-default.png" "file://$PWD/_og/og-default.html"
```

Chrome sometimes hangs after writing the file; kill it, the PNG is already there. Use `--window-size=512,512` for the square logo.

**Homepage carousel.** `scripts/hof-carousel.js` reads `images/hof-carousel/manifest.json` — adding an image to `images/hof-carousel/` does nothing until its filename is added to the manifest. Store receipts as JPEG (`sips -s format jpeg -s formatOptions 60 in.png --out in.jpg`); quality 60 keeps the text crisp at about a quarter of the PNG size. Both paths are shipped via the `resources` list in `_quarto.yml`.

## SEO and AI discoverability

What the build produces, and where each piece comes from:

- `<title>`, `<meta name="description">`, Open Graph and Twitter cards — from each page's `pagetitle`/`title`, `description`, `image`, `image-alt`, with site-wide fallbacks in `_quarto.yml` (`website.description`, `website.image`). Quarto builds these from YAML, so a description must be written in frontmatter; the Lua filter cannot backfill it.
- `<link rel="canonical">` — `canonical-url: true` plus `site-url`.
- `sitemap.xml` — automatic from `site-url`; drafts excluded.
- `robots.txt`, `llms.txt` — source files at repo root.
- `articles.xml` — the `feed:` block on `articles.qmd` (full-text RSS).
- JSON-LD — `_filters/seo-schema.lua`: `Organization` + `WebSite` on every page; `BlogPosting` + `BreadcrumbList` on posts; `FAQPage` on `faq.qmd`; `WebPage` (+ `Product`/`Offer` from `schema-offers`) elsewhere. Set `schema-type: none` in frontmatter to skip a page (the 404 does).
- `og:url`, `og:type` (`article` on posts, `website` elsewhere), `article:published_time`/`modified_time`/`tag` — same filter, from `date`, `date-modified`, `categories`.
- `width`/`height` on body images — same filter, read from the PNG/JPEG file header. An explicit `width=600` on an image is kept and the height is scaled to match. SVGs and remote images are left alone.

The site description is duplicated in three places on purpose (`_quarto.yml`, `SITE_DESC` in the Lua filter, the summary in `llms.txt`); change all three together. Brand facts in the filter's `Organization` node (legal name, founding year, email, `sameAs` profiles) are the canonical entity description — update there first.

Verification after `quarto render` (all counts should equal the number of pages, 24 excluding the 404):

```bash
grep -rl 'name="description"' _site --include='*.html' | grep -v site_libs | wc -l
grep -rl 'rel="canonical"' _site --include='*.html' | grep -v site_libs | wc -l
grep -rl 'application/ld+json' _site --include='*.html' | grep -v site_libs | wc -l
grep -rl 'property="og:url"' _site --include='*.html' | grep -v site_libs | wc -l
grep -c 'slamdunk.bet/</loc>' _site/sitemap.xml   # 1: post-render hook rewrote the homepage entry
tail -1 _site/robots.txt   # Sitemap line
ls _site/llms.txt _site/articles.xml _site/sitemap.xml _site/404.html
```

## Analytics

- GA4 property `G-66MCY7L0V7` via `website.google-analytics`.
- `scripts/site-analytics.js` sends `cta_click` (params: `cta_destination`, `cta_text`, `cta_location`, `link_url`, `page_path`) and `ai_referral` (`referrer_host`). Register those as custom dimensions and mark `cta_click` a key event in the GA4 admin UI; create an "AI Search" channel group on the same referrer list that's in the script.
- Google Search Console: verified by DNS TXT (the `google-site-verification` record is on `slamdunk.bet`). Bing Webmaster Tools is not verified yet (no Bing TXT record as of 2026-10-06); it can import the property from Search Console in one step. Submit `https://slamdunk.bet/sitemap.xml` to both. Bing's index feeds ChatGPT search and Copilot.

## Ads

None on the site. If ads or affiliate links are ever added: article pages only, never the homepage/subscribe/apps funnel; update the "Advertising and affiliate links" section of `privacy.qmd`; disclose affiliate links on the page itself; DFS operators need no state affiliate license, sportsbook affiliates do in many states.

## Brand voice

Casual, confident, and clean. Use plain-spoken copy with selective emphasis; do not rely on emoji for tone. Prefer **Sharpduel** over Whop for subscription CTAs (Sharpduel is the primary button; Whop is the secondary option). The brand account is `@slam_dunk_bets` on X; `@jimtheflash` is the founder/support handle.

## Do not render

`agents.md`, `CLAUDE.md`, and `README.md` are excluded from the site because the `project.render` whitelist in `_quarto.yml` only renders `.qmd`. Underscore-prefixed folders (`_includes`, `_filters`, `_scripts`, `_og`, `_drafts`) are excluded by Quarto convention. Keep it that way.
