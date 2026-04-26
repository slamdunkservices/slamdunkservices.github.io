# Agents Guide — Slam Dunk Bets Site

## What this is

Marketing + blog site for **Slam Dunk Bets**, an NBA/WNBA prop & first-basket picks service. Quarto website published to GitHub Pages at <https://slamdunk.bet> (custom domain set via the `CNAME` file).

## Tech

- **Quarto website** — see `_quarto.yml`
- **Theme:** `litera` (Bootstrap 5-based)
- **Authoring:** RStudio with the visual editor (see `slamdunkservices.github.io.Rproj`)
- **R:** system-installed R — no `renv`, no virtualenv, no lockfile
- **Quarto binary:** bundled with RStudio at `/Applications/RStudio.app`. `quarto` is not on the default shell `PATH`; run Quarto commands from RStudio's Build pane or its embedded terminal.

## Repo tour

| Path | Purpose |
|---|---|
| `_quarto.yml` | Site config — navbar, theme, render whitelist |
| `index.qmd` | Homepage |
| `subscribe.qmd` | Subscription landing page |
| `articles.qmd` | Blog listing page (reads `posts/`) |
| `faq.qmd` | FAQ page |
| `contact.qmd` | Contact info |
| `posts/YYYY-MM/*.qmd` | Blog posts, grouped by year-month folders |
| `images/` | All assets — hero, favicon, post images |
| `styles.css` | Site-wide CSS overrides |
| `CNAME` | `slamdunk.bet` — GitHub Pages custom domain |
| `_site/`, `.quarto/` | Build output (gitignored) |

## Branches

- `jk-main` — source/working branch and **main branch**, edit here
- `gh-pages` — built site, **do not edit directly**

## Publishing

Publishing uses the Quarto `publish` command, which renders locally and pushes the built `_site/` to the `gh-pages` branch. Full docs: <https://quarto.org/docs/publishing/github-pages.html>.

No GitHub Actions workflow — all publishing happens from the author's machine. On first publish, Quarto writes a `_publish.yml` file recording the target; commit it when it appears.

Environment note: this project appears to use `r-reticulate`. Keep that set in the root `slamdunkservices.github.io.Rproj` file.

Typical flow:

1. Edit on `jk-main`
2. `quarto preview` — live local preview
3. Commit + push `jk-main`
4. Switch to any branch that is **not** `gh-pages`
5. `quarto publish gh-pages` from the repo root (run from RStudio's terminal, or any shell where `quarto` is on `PATH`)

## Common tasks

**Add a blog post.** Create `posts/YYYY-MM/slug.qmd` with this frontmatter:

```yaml
---
title: "Post Title"
author: Slam Dunk Bets
date: YYYY-MM-DD
categories: [nba, wnba]
draft: false
---
```

The post appears automatically on `articles.qmd` (a Quarto listing page).

**Edit a page.** Edit the `.qmd` at repo root, preview, commit, publish.

**Images.** Drop into `/images/`. Reference as `images/foo.jpg` from root-level pages or `../../images/foo.jpg` from `posts/YYYY-MM/`.

## Brand voice

Casual, confident, and clean. Use plain-spoken copy with selective emphasis; do not rely on emoji for tone. Prefer **Sharpduel** over Whop for subscription CTAs.

## Do not render

`agents.md` and `claude.md` are excluded from the site via the `project.render` whitelist in `_quarto.yml`. If you add more agent/doc markdown at the repo root, they'll stay out automatically since the whitelist only renders `.qmd`. Keep it that way.
