"""Data store backend: checkout and fulfillment for the static storefront at /data/.

One small HTTP function (Cloud Run functions, scales to zero). The storefront is a
static Quarto site, so this is the only compute it needs:

    GET  /catalog                        what is for sale right now (prices, seasons)
    POST /checkout  {items: [...]}       price a cart, open a Stripe Checkout Session
    GET  /claim?session_id=cs_...        after Stripe redirects back to /data/thanks.html;
                                         returns the buyer's library token
    POST /recover  {email, receipt}      the same token from the email and the receipt
                                         number on the buyer's Stripe receipt
    GET  /library?t=<token>              files this buyer may download (JSON)
    GET  /download?t=<token>&f=<path>    302 to a short-lived signed URL for one file
    GET  /healthz

How the pieces fit

  Files     gs://$BUCKET/files/<league>/<season>/<dataset>/<name>, written by the
            jobs repo (datastore/). A season is on sale when its folder has files.
  Prices    Stripe prices with lookup keys, one product per league and dataset:
              sdb_<league>_<dataset>_pass      the season in progress (daily updates);
                                               price metadata sdb_season names it
              sdb_<league>_<dataset>_season    any one completed season
              sdb_<league>_all_pass / _all_season   every dataset, one season
              sdb_<league>_archive             every dataset, every completed season
            Created by _store/stripe_sync.py from _store/catalog.yml.
  Cart      A cart item is {league, dataset, season}; dataset may be "all", season may
            be "archive". The price is always looked up here, never taken from the page.
  Grants    What a paid checkout unlocks is written on the Checkout Session itself as
            metadata (g0, g1, ...): comma-separated <league>/<season>/<dataset> folders,
            "*" allowed for the dataset. A file is downloadable when its folder matches
            a grant of one of the buyer's paid, unrefunded sessions. Nothing is stored
            here, so there is no database and nothing to back up.

Cost guards (see deploy.sh): the bucket is private; files leave only through signed
URLs that expire in SIGNED_URL_MINUTES; downloads are throttled per buyer; the service
runs with a low --max-instances; BLOCKED_CUSTOMERS cuts off a shared library link.

Environment
    STRIPE_API_KEY        restricted key (Secret Manager): write on Checkout Sessions,
                          read on Prices, Products, Customers, Charges, PaymentIntents
    TOKEN_SECRET          random string that signs library tokens (Secret Manager)
    BUCKET                bucket holding files/ (default sdbs_datastore)
    SITE_URL              where Stripe sends the buyer back (default https://slamdunk.bet)
    ALLOWED_ORIGINS       comma-separated origins for CORS
    AUTOMATIC_TAX         "1" turns on Stripe Tax at checkout (off by default)
    SIGNED_URL_MINUTES    default 5
    DOWNLOADS_PER_HOUR    per buyer per instance, default 40
    BLOCKED_CUSTOMERS     comma-separated Stripe customer ids
"""
from __future__ import annotations

import base64
import fnmatch
import hashlib
import hmac
import json
import os
import re
import time
from datetime import timedelta

import functions_framework
import google.auth
import stripe
from google.auth.transport import requests as google_requests
from google.cloud import storage

BUCKET = os.environ.get("BUCKET", "sdbs_datastore")
FILES_PREFIX = "files/"
SITE_URL = os.environ.get("SITE_URL", "https://slamdunk.bet").rstrip("/")
ALLOWED_ORIGINS = {
    o.strip() for o in os.environ.get(
        "ALLOWED_ORIGINS", "https://slamdunk.bet,http://localhost:4321").split(",") if o.strip()
}
AUTOMATIC_TAX = os.environ.get("AUTOMATIC_TAX", "") == "1"
SIGNED_URL_MINUTES = int(os.environ.get("SIGNED_URL_MINUTES", "5"))
DOWNLOADS_PER_HOUR = int(os.environ.get("DOWNLOADS_PER_HOUR", "40"))
BLOCKED = {c.strip() for c in os.environ.get("BLOCKED_CUSTOMERS", "").split(",") if c.strip()}
TOKEN_DAYS = 400          # a season pass outlives the season; entitlement is rechecked anyway
MAX_CART_ITEMS = 60
SEGMENT = r"[a-z0-9]+(?:-[a-z0-9]+)*"
SEGMENT_RE = re.compile(rf"^{SEGMENT}$")
GRANT_RE = re.compile(rf"^{SEGMENT}/{SEGMENT}/(?:{SEGMENT}|\*)$")
SESSION_RE = re.compile(r"^cs_(test|live)_[A-Za-z0-9]{10,}$")
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}$")
LOOKUP_RE = re.compile(rf"^sdb_({SEGMENT})_({SEGMENT})_(pass|season)$|^sdb_({SEGMENT})_(archive)$")

stripe.api_key = os.environ.get("STRIPE_API_KEY", "")
stripe.max_network_retries = 1

_storage = None
_cache: dict[str, tuple[float, object]] = {}
_downloads: dict[str, list[float]] = {}


class Refused(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


# ---------- small helpers ----------

def _cached(key: str, ttl: float, build):
    hit = _cache.get(key)
    now = time.time()
    if hit and now - hit[0] < ttl:
        return hit[1]
    value = build()
    _cache[key] = (now, value)
    if len(_cache) > 2000:                      # an instance never grows without bound
        for k in sorted(_cache, key=lambda k: _cache[k][0])[:1000]:
            _cache.pop(k, None)
    return value


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _secret() -> bytes:
    secret = os.environ.get("TOKEN_SECRET", "")
    if len(secret) < 24:
        raise Refused(503, "The store is not configured yet.")
    return secret.encode()


def make_token(customer: str, now: float | None = None) -> str:
    issued = time.time() if now is None else now
    body = f"{customer}.{int(issued + TOKEN_DAYS * 86400)}".encode()
    sig = hmac.new(_secret(), body, hashlib.sha256).digest()
    return f"{_b64(body)}.{_b64(sig)}"


def read_token(token: str, now: float | None = None) -> str:
    try:
        body_b64, sig_b64 = token.split(".")
        body = _unb64(body_b64)
        good = hmac.new(_secret(), body, hashlib.sha256).digest()
        if not hmac.compare_digest(good, _unb64(sig_b64)):
            raise ValueError
        customer, exp = body.decode().rsplit(".", 1)
        if int(exp) < (time.time() if now is None else now):
            raise Refused(401, "This library link has expired. Recover it with your receipt.")
    except Refused:
        raise
    except Exception:
        raise Refused(401, "That library link is not valid.") from None
    if customer in BLOCKED:
        raise Refused(403, "This library is on hold. Email us and we will sort it out.")
    return customer


# ---------- grants ----------

def parse_grants(text: str | None) -> list[str]:
    grants = []
    for part in (text or "").split(","):
        part = part.strip().lower()
        if part and GRANT_RE.match(part):
            grants.append(part)
    return grants


def pack_grants(grants: list[str]) -> dict[str, str]:
    """Stripe metadata values stop at 500 characters; spread the list over g0, g1, ..."""
    out: dict[str, str] = {}
    chunk: list[str] = []
    for grant in sorted(set(grants)):
        if chunk and len(",".join(chunk + [grant])) > 480:
            out[f"g{len(out)}"] = ",".join(chunk)
            chunk = []
        chunk.append(grant)
    if chunk:
        out[f"g{len(out)}"] = ",".join(chunk)
    if len(out) > 40:
        raise Refused(400, "That cart is too large for one checkout. Split it in two.")
    return out


def unpack_grants(metadata: dict | None) -> list[str]:
    grants: list[str] = []
    for key, value in (metadata or {}).items():
        if re.fullmatch(r"g\d+", key):
            grants.extend(parse_grants(value))
    return grants


def folder_of(object_name: str) -> str | None:
    """``files/nba/2025-26/player-logs/x.csv`` -> ``nba/2025-26/player-logs``."""
    if not object_name.startswith(FILES_PREFIX):
        return None
    parts = object_name[len(FILES_PREFIX):].split("/")
    if len(parts) != 4 or not parts[3]:
        return None
    return "/".join(parts[:3])


def allowed(object_name: str, grants: list[str]) -> bool:
    folder = folder_of(object_name)
    return bool(folder) and any(fnmatch.fnmatchcase(folder, g) for g in grants)


# ---------- storage ----------

def _client() -> storage.Client:
    global _storage
    if _storage is None:
        _storage = storage.Client()
    return _storage


def all_files() -> list[dict]:
    def build():
        out = []
        for blob in _client().list_blobs(BUCKET, prefix=FILES_PREFIX):
            if folder_of(blob.name) is None:
                continue
            league, season, dataset, name = blob.name[len(FILES_PREFIX):].split("/")
            out.append({
                "path": blob.name[len(FILES_PREFIX):], "league": league, "season": season,
                "dataset": dataset, "name": name, "bytes": blob.size,
                "updated": blob.updated.isoformat() if blob.updated else None,
            })
        return out
    return _cached("files", 300, build)


def inventory(files: list[dict]) -> dict[str, dict[str, list[str]]]:
    """league -> dataset -> seasons that have at least one file, ascending."""
    out: dict[str, dict[str, set]] = {}
    for f in files:
        out.setdefault(f["league"], {}).setdefault(f["dataset"], set()).add(f["season"])
    return {lg: {ds: sorted(seasons) for ds, seasons in sets.items()} for lg, sets in out.items()}


def signed_url(path: str) -> str:
    credentials, _ = google.auth.default()
    credentials.refresh(google_requests.Request())
    blob = _client().bucket(BUCKET).blob(FILES_PREFIX + path)
    return blob.generate_signed_url(
        version="v4", expiration=timedelta(minutes=SIGNED_URL_MINUTES), method="GET",
        service_account_email=credentials.service_account_email,
        access_token=credentials.token,
        response_disposition=f'attachment; filename="{path.rsplit("/", 1)[-1]}"')


def throttle(customer: str) -> None:
    now = time.time()
    recent = [t for t in _downloads.get(customer, []) if now - t < 3600]
    if len(recent) >= DOWNLOADS_PER_HOUR:
        raise Refused(429, "That is a lot of downloads. Try again in an hour.")
    recent.append(now)
    _downloads[customer] = recent


# ---------- prices ----------

def parse_lookup(key: str) -> tuple[str, str, str] | None:
    """``sdb_nba_player-logs_pass`` -> (nba, player-logs, pass); ``sdb_nba_archive`` -> (nba, all, archive)."""
    m = LOOKUP_RE.match(key or "")
    if not m:
        return None
    if m.group(5):
        return (m.group(4), "all", "archive")
    return (m.group(1), m.group(2), m.group(3))


def price_table() -> dict[tuple[str, str, str], dict]:
    """(league, dataset|all, pass|season|archive) -> {id, amount, currency, season}."""
    def build():
        table = {}
        prices = stripe.Price.list(active=True, type="one_time", limit=100)
        for price in prices.auto_paging_iter():
            parsed = parse_lookup(price.get("lookup_key"))
            if not parsed or price.get("unit_amount") is None:
                continue
            table[parsed] = {
                "id": price["id"], "amount": price["unit_amount"], "currency": price["currency"],
                "season": (price.get("metadata") or {}).get("sdb_season") or None,
            }
        return table
    return _cached("prices", 300, build)


def pass_season(prices: dict, league: str) -> str | None:
    """The season in progress for a league: named on any of its pass prices."""
    for (lg, _dataset, kind), price in prices.items():
        if lg == league and kind == "pass" and price["season"]:
            return price["season"]
    return None


def price_cart(items: list, prices: dict, stock: dict) -> tuple[list[dict], list[str], list[str]]:
    """Validate a cart against what exists. Returns (line items, grants, labels)."""
    if not isinstance(items, list) or not items:
        raise Refused(400, "The cart is empty.")
    if len(items) > MAX_CART_ITEMS:
        raise Refused(400, "That cart is too large for one checkout. Split it in two.")
    quantity: dict[str, int] = {}
    grants: list[str] = []
    labels: list[str] = []
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            raise Refused(400, "That cart is not readable. Empty it and add the files again.")
        league = str(item.get("league", ""))
        dataset = str(item.get("dataset", ""))
        season = str(item.get("season", ""))
        if not all(SEGMENT_RE.match(v) for v in (league, dataset, season)):
            raise Refused(400, "That cart is not readable. Empty it and add the files again.")
        if (league, dataset, season) in seen:
            continue
        seen.add((league, dataset, season))
        have = stock.get(league) or {}
        current = pass_season(prices, league)
        every = sorted({s for seasons in have.values() for s in seasons})
        if season == "archive":
            if dataset != "all":
                raise Refused(400, "The archive is sold for the whole league.")
            kind, seasons = "archive", [s for s in every if s != current]
        else:
            in_stock = every if dataset == "all" else have.get(dataset, [])
            if season not in in_stock:
                raise Refused(409, f"{league.upper()} {season} {dataset} is not available right now.")
            kind, seasons = ("pass" if season == current else "season"), [season]
        price = prices.get((league, dataset, kind))
        if not price or not seasons:
            raise Refused(409, f"{league.upper()} {dataset} {season} is not for sale right now.")
        quantity[price["id"]] = quantity.get(price["id"], 0) + 1
        grants.extend(f"{league}/{s}/{'*' if dataset == 'all' else dataset}" for s in seasons)
        labels.append(f"{league.upper()} {dataset.replace('-', ' ')} {season}")
    lines = [{"price": pid, "quantity": qty} for pid, qty in sorted(quantity.items())]
    return lines, grants, labels


def create_checkout(items: list, origin: str) -> str:
    prices = price_table()
    stock = inventory(all_files())
    lines, grants, labels = price_cart(items, prices, stock)
    site = origin if origin in ALLOWED_ORIGINS else SITE_URL
    summary = "You are buying: " + "; ".join(labels) + "."
    params = dict(
        mode="payment", line_items=lines, customer_creation="always",
        allow_promotion_codes=True, metadata=pack_grants(grants),
        success_url=f"{site}/data/thanks.html?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{site}/data/cart.html",
        custom_text={"submit": {"message": summary[:1150]}},
        payment_intent_data={"description": ("Slam Dunk data: " + "; ".join(labels))[:900]},
    )
    if AUTOMATIC_TAX:
        params["automatic_tax"] = {"enabled": True}
    session = stripe.checkout.Session.create(**params)
    return session["url"]


def catalog() -> dict:
    prices = price_table()
    stock = inventory(all_files())
    out = {}
    for (league, dataset, kind), price in sorted(prices.items()):
        row = out.setdefault(league, {"current": pass_season(prices, league), "datasets": {}, "prices": {}})
        row["prices"][f"{dataset}_{kind}"] = price["amount"]
    for league, datasets in stock.items():
        out.setdefault(league, {"current": None, "datasets": {}, "prices": {}})["datasets"] = datasets
    return out


# ---------- entitlement ----------

def _product_grants(product_id: str) -> list[str]:
    def build():
        product = stripe.Product.retrieve(product_id)
        return parse_grants((product.get("metadata") or {}).get("sdb_grants"))
    return _cached(f"product:{product_id}", 600, build)


def _session_paid(session) -> bool:
    if session.get("mode") != "payment" or session.get("status") != "complete":
        return False
    if session.get("payment_status") not in ("paid", "no_payment_required"):
        return False
    intent = session.get("payment_intent")
    charge = intent.get("latest_charge") if isinstance(intent, dict) else None
    if isinstance(charge, dict) and (charge.get("refunded") or charge.get("disputed")):
        return False
    return True


def _session_grants(session) -> list[str]:
    """Grants written at checkout; a session made elsewhere (a Payment Link, an invoice
    paid by hand) falls back to ``metadata.sdb_grants`` on the products it sold."""
    grants = unpack_grants(session.get("metadata"))
    if grants:
        return grants
    items = stripe.checkout.Session.list_line_items(session["id"], limit=100)
    for item in items.auto_paging_iter():
        product = (item.get("price") or {}).get("product")
        if product:
            grants.extend(_product_grants(product if isinstance(product, str) else product["id"]))
    return grants


def customer_grants(customer: str) -> list[str]:
    def build():
        grants: list[str] = []
        sessions = stripe.checkout.Session.list(
            customer=customer, status="complete", limit=100,
            expand=["data.payment_intent.latest_charge"])
        for session in sessions.auto_paging_iter():
            if _session_paid(session):
                grants.extend(_session_grants(session))
        return sorted(set(grants))
    return _cached(f"grants:{customer}", 60, build)


def claim(session_id: str) -> str:
    if not SESSION_RE.match(session_id or ""):
        raise Refused(400, "That checkout reference does not look right.")
    try:
        session = stripe.checkout.Session.retrieve(
            session_id, expand=["payment_intent.latest_charge"])
    except stripe.error.InvalidRequestError:
        raise Refused(404, "We could not find that checkout.") from None
    if not _session_paid(session):
        raise Refused(402, "That checkout has not been paid.")
    customer = session.get("customer")
    if not customer:
        raise Refused(409, "That checkout has no customer attached. Email us with your receipt.")
    customer = customer if isinstance(customer, str) else customer["id"]
    _cache.pop(f"grants:{customer}", None)
    return customer


def recover(email: str, receipt: str) -> str:
    """The receipt number on a Stripe receipt, plus the email it was sent to."""
    email = (email or "").strip().lower()
    receipt = (receipt or "").strip().lstrip("#")
    if not EMAIL_RE.match(email) or not re.fullmatch(r"[0-9]{4}-[0-9]{4}", receipt):
        raise Refused(400, "Enter the email you paid with and the receipt number (1234-5678).")
    time.sleep(0.4)                               # slows guessing; never a hot path
    for cust in stripe.Customer.list(email=email, limit=20).auto_paging_iter():
        for charge in stripe.Charge.list(customer=cust["id"], limit=100).auto_paging_iter():
            if charge.get("paid") and charge.get("receipt_number") == receipt:
                return cust["id"]
    raise Refused(404, "No purchase matches that email and receipt number.")


# ---------- HTTP ----------

def _respond(request, payload: dict, status: int = 200, cache: str = "no-store"):
    origin = request.headers.get("Origin", "")
    headers = {"Content-Type": "application/json", "Cache-Control": cache,
               "Vary": "Origin", "X-Robots-Tag": "noindex"}
    if origin in ALLOWED_ORIGINS:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Headers"] = "Content-Type"
        headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        headers["Access-Control-Max-Age"] = "3600"
    return (json.dumps(payload), status, headers)


@functions_framework.http
def store(request):
    if request.method == "OPTIONS":
        return _respond(request, {}, 204)
    route = request.path.rstrip("/").rsplit("/", 1)[-1]
    try:
        if route == "healthz":
            return _respond(request, {"ok": True})
        if not stripe.api_key:
            raise Refused(503, "The store is not configured yet.")

        if route == "catalog" and request.method == "GET":
            return _respond(request, catalog(), cache="public, max-age=300")

        if route == "checkout" and request.method == "POST":
            body = request.get_json(silent=True) or {}
            url = create_checkout(body.get("items"), request.headers.get("Origin", ""))
            return _respond(request, {"url": url})

        if route == "claim" and request.method == "GET":
            customer = claim(request.args.get("session_id", ""))
            return _respond(request, {"token": make_token(customer)})

        if route == "recover" and request.method == "POST":
            body = request.get_json(silent=True) or {}
            customer = recover(body.get("email", ""), body.get("receipt", ""))
            return _respond(request, {"token": make_token(customer)})

        if route == "library" and request.method == "GET":
            customer = read_token(request.args.get("t", ""))
            grants = customer_grants(customer)
            files = [f for f in all_files() if allowed(FILES_PREFIX + f["path"], grants)]
            files.sort(key=lambda f: (f["league"], f["season"], f["dataset"], f["name"]))
            return _respond(request, {"grants": grants, "files": files})

        if route == "download" and request.method == "GET":
            customer = read_token(request.args.get("t", ""))
            path = request.args.get("f", "")
            known = {f["path"] for f in all_files()}
            if path not in known or not allowed(FILES_PREFIX + path, customer_grants(customer)):
                raise Refused(404, "That file is not in your library.")
            throttle(customer)
            return ("", 302, {"Location": signed_url(path), "Cache-Control": "no-store",
                              "Referrer-Policy": "no-referrer"})

        raise Refused(404, "Not found.")
    except Refused as err:
        return _respond(request, {"error": err.message}, err.status)
    except stripe.error.StripeError:
        return _respond(request, {"error": "The payment system did not answer. Try again in a minute."}, 502)
