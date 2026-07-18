# Agents Guide — Slam Dunk Bets Site

## What this is

Marketing + blog site for **Slam Dunk Bets**, an NBA, WNBA & MLB prop picks service — first baskets for basketball, home runs and NRFI/YRFI for baseball. Quarto website published to GitHub Pages at <https://slamdunk.bet> (custom domain set via the `CNAME` file).

## Tech

- **Quarto website** — see `_quarto.yml`. Theme: `litera` (Bootstrap 5-based) with `custom.scss` and `styles.css` overrides.
- **Content is plain markdown** — no R or Python code chunks in any `.qmd`, so rendering needs only Quarto itself.
- **Quarto binary:** standalone install, on `PATH` at `/usr/local/bin/quarto` (symlink to `/Applications/quarto`). Run Quarto commands from any shell.
- **Authoring:** RStudio with the visual editor (`slamdunkservices.github.io.Rproj`). Keep `PythonType: r-reticulate` set in the `.Rproj`.

## Commands

- `quarto preview` — live local preview with hot reload
- `quarto render` — build the site into `_site/` (gitignored)
- `quarto publish gh-pages` — render and push the built site to `gh-pages` (see Publishing)

There are no tests or linters.

## Repo tour

| Path | Purpose |
|---|---|
| `_quarto.yml` | Site config — navbar, theme, render whitelist, extra `resources` |
| `index.qmd` | Homepage — hero, feature list, "Hall of Fame" carousel |
| `subscribe.qmd` | Subscription landing page |
| `data.qmd` | Data products teaser page |
| `articles.qmd` | Blog listing page (reads `posts/`) |
| `faq.qmd`, `contact.qmd` | FAQ and contact pages |
| `posts/YYYY-MM/*.qmd` | Blog posts, grouped by year-month folders |
| `images/` | All assets — brand, hero, post images, carousel receipts |
| `scripts/hof-carousel.js` | Homepage carousel; loads images from a JSON manifest |
| `styles.css`, `custom.scss` | Site-wide styling overrides |
| `CNAME` | `slamdunk.bet` — GitHub Pages custom domain |
| `_site/`, `.quarto/` | Build output (gitignored) |

## Branches

- `main` — source/working branch, edit here
- `gh-pages` — built site, and the repo's default branch on GitHub — **do not edit directly**

## Publishing

Publishing uses the Quarto `publish` command, which renders locally and pushes the built `_site/` to the `gh-pages` branch. Full docs: <https://quarto.org/docs/publishing/github-pages.html>.

No GitHub Actions workflow — all publishing happens from the author's machine. On first publish, Quarto writes a `_publish.yml` file recording the target; commit it when it appears.

Typical flow:

1. Edit on `main`
2. `quarto preview` — check locally
3. Commit + push `main`
4. `quarto publish gh-pages` from the repo root (must be on a branch that is **not** `gh-pages`)

## Common tasks

**Add a blog post.** Create `posts/YYYY-MM/slug.qmd` with this frontmatter:

```yaml
---
title: "Post Title"
author: Slam Dunk Bets
date: YYYY-MM-DD
categories: [nba, wnba, mlb]
draft: false
---
```

The post appears automatically on `articles.qmd` (a Quarto listing page). `draft: true` keeps it off the listing.

**Edit a page.** Edit the `.qmd` at repo root, preview, commit, publish.

**Images.** Drop into `images/`. Reference as `images/foo.jpg` from root-level pages or `../../images/foo.jpg` from `posts/YYYY-MM/`.

**Homepage carousel.** `scripts/hof-carousel.js` reads `images/hof-carousel/manifest.json` — adding an image to `images/hof-carousel/` does nothing until its filename is added to the manifest. Both paths are shipped via the `resources` list in `_quarto.yml`.

## Brand voice

Casual, confident, and clean. Use plain-spoken copy with selective emphasis; do not rely on emoji for tone. Prefer **Sharpduel** over Whop for subscription CTAs (Sharpduel is the primary button; Whop is the secondary option).

## Do not render

`agents.md` and `CLAUDE.md` are excluded from the site because the `project.render` whitelist in `_quarto.yml` only renders `.qmd`. Any agent/doc markdown added at the repo root stays out automatically. Keep it that way.
