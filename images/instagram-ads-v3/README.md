# Instagram ads — V3

Ten evergreen 4:5 (1080×1350) ads for Slam Dunk Bets. Nothing is tied to a date, a
season, a specific game, or a promo window, so the whole set stays postable
indefinitely.

## Rebuilding

```bash
./render.sh
```

Renders every `.ad` section in `source.html` to `ad-NN.png` + `ad-NN.jpg`, then builds
`contact-sheet.jpg`. Needs Google Chrome and network access (Barlow Condensed loads from
Google Fonts). Edit `source.html` and re-run — there is no other build step.

`source.html?only=ad-04` isolates one ad in the browser, which is how `render.sh` gets a
pixel-exact 1080×1350 capture.

## Design system

Taken straight from the brand SVGs:

| Token | Value | Use |
|---|---|---|
| Black | `#0a0a0a` | dark backgrounds |
| Paper | `#f0f0ee` | light backgrounds |
| Neon green | `#39ff14` | accent **on dark only** |
| Forest green | `#1a9f00` | accent **on light only** |
| Type | Barlow Condensed 400/500/700 | all copy |

The logo's dashed trajectory arcs and its basketball/baseball marks are reused as a
graphic system across the set. Both lockups are inline `<symbol>`s in `source.html`
(`#logo-dark`, `#logo-light`) — transparent, and inline so they pick up the loaded
webfont. An `<img>`-referenced SVG can't reach the page's webfonts and silently falls
back to a system face, which is worth remembering if you add more layouts.

Every ad carries `21+ · Play responsibly`. Ad 02 also carries a past-results
disclaimer, since it's the one making a performance claim. Both are additions on my
part — pull them if they conflict with how you'd rather present the brand.

## The set

Mixed on purpose: two light backgrounds against eight dark, three photo-led against
seven typographic, and a spread of jobs from awareness to direct response.

| # | Job | Headline |
|---|---|---|
| 01 | Brand hero | Modeled. Tracked. Posted. |
| 02 | Track record | 7,000+ units of ROI |
| 03 | Freshness | Picks refresh every 30 minutes. |
| 04 | Coverage | Every slate, covered. |
| 05 | First basket | Who scores first? |
| 06 | Home runs | Who goes deep tonight? |
| 07 | NRFI / YRFI | The first inning is its own bet. |
| 08 | Accountability | Every pick logged. Wins and losses. |
| 09 | Explainer | Three steps. |
| 10 | Offer | First month free |

Ads 01, 04, 09 and 10 also work as a four-card carousel in that order: what we do →
what's covered → how it works → the offer.

All claims trace to copy already on slamdunk.bet (7,000+ units since 2021–22, 30-minute
refresh, Discord ROI receipts, free first month). If any of those change on the site,
they need to change here too.

## Draft captions

Starting points, not finished copy — trim to taste.

**01** — Projections for every NBA, WNBA and MLB game. Updated all day. Every pick logged where you can see it. That's the whole pitch. → slamdunk.bet

**02** — 7,000+ units of ROI tracked since the 2021–22 season, and the chart is still climbing. Every pick logged, win or lose. → slamdunk.bet

**03** — Lines move all day. Picks that were set this morning aren't picks anymore. Ours refresh every 30 minutes, automatically.

**04** — One subscription. First baskets and the full opening-possession board for NBA and WNBA, home runs and NRFI/YRFI for MLB.

**05** — The first bucket isn't a coin flip. Rotations, matchups and opening sets, run before the ball goes up. → slamdunk.bet

**06** — Batter, pitcher, park, weather. Home run projections for every game on the board.

**07** — The first inning is its own bet. Starting pitchers, top-of-the-order splits and park factors — a daily NRFI/YRFI call on every game.

**08** — Anyone can post the winners. We post all of it — daily ROI on Discord since 2021–22, nothing quietly deleted when it misses.

**09** — Model the slate. Refresh every 30 minutes. Post in Discord. That's it. → slamdunk.bet

**10** — First month free. Daily NBA, WNBA and MLB picks delivered on Discord. Subscribe on Sharpduel → slamdunk.bet
