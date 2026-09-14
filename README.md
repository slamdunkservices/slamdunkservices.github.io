# Slam Dunk Bets Website

This repo contains the Quarto source for <https://slamdunk.bet>.

Requires Quarto 1.9 or newer (`quarto --version`). See `agents.md` for the repo tour, the post checklist, and how the SEO/structured-data pieces fit together.

## Publishing

Publish from the repo root while checked out to any branch that is **not** `gh-pages`:

```bash
quarto publish gh-pages
```

The command renders locally and pushes the built site to the `gh-pages` branch.
