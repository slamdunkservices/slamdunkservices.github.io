# Data store

Everything behind `/data/`: the price list, the catalog snapshot the pages are generated from, the Stripe sync, and the one small function that takes payment and hands out downloads. Underscore-prefixed, so Quarto never renders this folder.

## How the pieces fit

| Piece | Lives in | Does |
|---|---|---|
| Export jobs | jobs repo, `datastore/` | Build the CSV files from the league data roots into `~/Desktop/files/sdbs_datastore/files/<league>/<season>/<dataset>/`, push them to `gs://sdbs_datastore`, and write `catalog/catalog.json` + samples |
| `pricing.toml` | here | The one hand-edited file: prices, which season each pass covers, the store API URL |
| `datasets.json`, `samples/` | here | Snapshot of the jobs repo's catalog (datasets, columns, seasons, rows, sizes). Committed, so the site builds without the data root |
| `_scripts/store/build.py` | site repo | Writes `data/index.qmd`, one page per league and per dataset, `data/_store-head.html` and `data/samples/` |
| `stripe_sync.py` | here | Makes Stripe's products and prices match `pricing.toml` (lookup keys `sdb_<league>_<dataset>_pass|season`, `sdb_<league>_archive`) |
| `fulfillment/` | here | Cloud Run function `datastore-fulfill`: prices a cart from Stripe, opens Checkout, and after payment lists the buyer's files and signs 5-minute download URLs |
| `scripts/data-store.js` | site repo | Cart, checkout redirect, thank-you and library pages |

Nothing stores customer data on our side. What a purchase unlocks is written on the Stripe Checkout Session as metadata (`g0`, `g1`, ...: `<league>/<season>/<dataset>` folders); the function reads it back from Stripe each time a buyer opens their library.

## Routine jobs

**Rebuild the pages** after the catalog or prices change:

```bash
python3 _scripts/store/build.py --sync      # --sync pulls datasets.json + samples from the jobs output
CARDS_TSV=_scripts/store/cards.tsv _scripts/og-cards/build.sh
```

**Change a price.** Edit `pricing.toml`, then `STRIPE_API_KEY=... python3 _store/stripe_sync.py --apply --live`, then rebuild the pages. Checkout always charges what Stripe holds, so run the sync before publishing the page.

**Season rollover.** When a season ends, set that league's `current = ""` in `pricing.toml` (the pass comes off sale; the finished season sells as a completed season). When the next season's first files exist, set `current` to the new season. Sync Stripe and rebuild the pages both times.

**Add a dataset.** Add it in the jobs repo (a `Dataset` spec and its `build`), run the backfill and `describe`, add its name and blurb under `[datasets]` and a price under each league in `pricing.toml`, sync Stripe, rebuild.

**Cut off a shared library link.** Add the Stripe customer id to `BLOCKED_CUSTOMERS` on the Cloud Run service (`gcloud run services update datastore-fulfill --update-env-vars BLOCKED_CUSTOMERS=cus_...`). A refund or a dispute removes access on its own.

## First-time setup

1. `_store/fulfillment/deploy.sh setup` creates the private bucket, the service account and the token secret.
2. In Stripe, create a restricted key (write: Checkout Sessions; read: Prices, Products, Customers, Charges, PaymentIntents) and put it in Secret Manager as `stripe-datastore-key` (the command is in the header of `deploy.sh`).
3. `STRIPE_API_KEY=sk_... python3 _store/stripe_sync.py --apply --live` creates the products and prices.
4. In the jobs repo, set `DATASTORE_SKIP_GCS=0` in `~/.datastore_jobs.env` and run `datastore/backfill.sh` to upload the files.
5. `_store/fulfillment/deploy.sh deploy`, then put the printed URL in `pricing.toml` (`[store] api`) and rebuild the pages.
6. Buy something in Stripe test mode end to end before pointing a live key at it.

## What it can cost

| Item | Rate | At this store's size |
|---|---|---|
| Storage, `gs://sdbs_datastore` (us-central1, Standard) | $0.020 per GB a month | The full catalog is a few GB or less: cents a month |
| Download egress | about $0.12 per GB | A league's complete season is tens of MB: under a cent a buyer |
| Cloud Run function | Free tier: 2M requests, 180k vCPU-seconds a month | Scales to zero; effectively free |
| Secret Manager | $0.06 per secret version a month | Two secrets |

The guards that keep it there are set in `fulfillment/deploy.sh` and `main.py`: the bucket has public access prevention on, files leave only through signed URLs that expire in 5 minutes, downloads are capped per buyer per hour, the service runs at most 2 instances, soft delete and versioning are off so a file rebuilt daily is stored once, and the export job uploads only files whose bytes changed. A Cloud Billing budget alert on the project is still worth setting; it is an alert, not a cap.

## Tests

```bash
cd _store/fulfillment && TOKEN_SECRET=test-secret-test-secret-test /Users/jim/Code/jobs/mlb/.venv/bin/python -m pytest -q -p no:cacheprovider
python3 _store/stripe_sync.py        # no key: prints the plan from pricing.toml
```
