#!/usr/bin/env python3
"""Make Stripe's catalog match _store/pricing.toml. Standard library only.

    python3 _store/stripe_sync.py                 # dry run: print what would change
    STRIPE_API_KEY=sk_test_... python3 _store/stripe_sync.py --apply
    STRIPE_API_KEY=sk_live_... python3 _store/stripe_sync.py --apply --live

What it maintains (and nothing else in the account):

    Product  sdb_<league>_<dataset>         "NBA Player Game Logs (CSV)"
             sdb_<league>_all               "NBA Complete Data (CSV)"
    Price    lookup key sdb_<league>_<dataset>_pass     season in progress; metadata sdb_season
             lookup key sdb_<league>_<dataset>_season   one completed season
             lookup key sdb_<league>_all_pass / _all_season
             lookup key sdb_<league>_archive            every dataset, every completed season

The checkout function finds prices by lookup key, so the storefront never holds a
price id. Stripe prices cannot be edited: a changed amount creates a new price that
takes over the lookup key, and the old one is archived. A league with `current = ""`
has its pass prices archived (off sale) until the next season is set.

Idempotent: a second run with nothing changed prints "in sync" and writes nothing.
Without --apply it only reads. Without a key it prints the plan from the file alone.
A live key is refused unless --live is given.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
API = "https://api.stripe.com/v1"


def load_plan(path: Path) -> tuple[list[dict], list[dict]]:
    """pricing.toml -> (products, prices) as Stripe should hold them."""
    cfg = tomllib.loads(path.read_text())
    products, prices = [], []
    for league, lg in cfg["leagues"].items():
        name, current = lg["name"], (lg.get("current") or "").strip()
        for dataset, value in lg["prices"].items():
            if dataset == "archive":
                continue
            if dataset == "all":
                title = f"{name} Complete Data (CSV)"
                blurb = f"Every {name} dataset in the store, as documented flat files."
            else:
                meta = cfg["datasets"][dataset]
                title = f"{name} {meta['name']} (CSV)"
                blurb = meta["blurb"]
            pid = f"sdb_{league}_{dataset}"
            products.append({
                "id": pid, "name": title, "description": blurb,
                "metadata": {"sdb_league": league, "sdb_dataset": dataset},
            })
            prices.append({
                "lookup_key": f"sdb_{league}_{dataset}_season", "product": pid,
                "amount": int(value["season"]) * 100, "active": True,
                "nickname": "One completed season",
                "metadata": {"sdb_kind": "season", "sdb_league": league, "sdb_dataset": dataset},
            })
            prices.append({
                "lookup_key": f"sdb_{league}_{dataset}_pass", "product": pid,
                "amount": int(value["pass"]) * 100, "active": bool(current),
                "nickname": f"{current} season pass" if current else "Season pass (off sale)",
                "metadata": {"sdb_kind": "pass", "sdb_league": league, "sdb_dataset": dataset,
                             "sdb_season": current},
            })
        if "archive" in lg["prices"]:
            prices.append({
                "lookup_key": f"sdb_{league}_archive", "product": f"sdb_{league}_all",
                "amount": int(lg["prices"]["archive"]) * 100, "active": True,
                "nickname": "Complete archive: every completed season",
                "metadata": {"sdb_kind": "archive", "sdb_league": league, "sdb_dataset": "all"},
            })
    return products, prices


class Stripe:
    def __init__(self, key: str):
        self.auth = "Basic " + base64.b64encode((key + ":").encode()).decode()

    def call(self, method: str, path: str, params: list[tuple[str, str]] | None = None):
        url, data = API + path, None
        if params and method == "GET":
            url += "?" + urllib.parse.urlencode(params)
        elif params:
            data = urllib.parse.urlencode(params).encode()
        req = urllib.request.Request(url, data=data, method=method, headers={"Authorization": self.auth})
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                return json.load(res)
        except urllib.error.HTTPError as err:
            body = json.loads(err.read() or b"{}")
            if err.code == 404:
                return None
            raise SystemExit(f"Stripe said {err.code} on {method} {path}: "
                             f"{(body.get('error') or {}).get('message', body)}") from None


def flat(prefix: str, mapping: dict) -> list[tuple[str, str]]:
    return [(f"{prefix}[{k}]", str(v)) for k, v in mapping.items()]


def sync(stripe: Stripe | None, products: list[dict], prices: list[dict], apply: bool) -> int:
    changes = 0

    def act(label: str, method: str = "", path: str = "", params=None):
        nonlocal changes
        changes += 1
        print(("  did   " if apply else "  would ") + label)
        if apply and stripe is not None:
            return stripe.call(method, path, params)
        return None

    for want in products:
        have = stripe.call("GET", f"/products/{want['id']}") if stripe else None
        body = [("name", want["name"]), ("description", want["description"])] + flat("metadata", want["metadata"])
        if have is None:
            act(f"create product {want['id']}  \"{want['name']}\"", "POST", "/products",
                [("id", want["id"])] + body)
        elif (have["name"], have.get("description"), have.get("active")) != (want["name"], want["description"], True) \
                or any(have.get("metadata", {}).get(k) != v for k, v in want["metadata"].items()):
            act(f"update product {want['id']}", "POST", f"/products/{want['id']}", body + [("active", "true")])

    for want in prices:
        key = want["lookup_key"]
        found = stripe.call("GET", "/prices", [("lookup_keys[]", key), ("limit", "1")]) if stripe else None
        have = (found or {}).get("data", [None])[0] if found else None
        dollars = f"${want['amount'] / 100:,.0f}"
        if not want["active"]:
            if have and have.get("active"):
                act(f"archive price {key} (league is between seasons)", "POST", f"/prices/{have['id']}",
                    [("active", "false")])
            continue
        create = [("product", want["product"]), ("currency", "usd"), ("unit_amount", str(want["amount"])),
                  ("lookup_key", key), ("nickname", want["nickname"]), ("tax_behavior", "unspecified")] \
            + flat("metadata", want["metadata"])
        if have is None:
            act(f"create price {key}  {dollars}", "POST", "/prices", create)
        elif have["unit_amount"] != want["amount"] or have.get("product") != want["product"]:
            act(f"replace price {key}  ${have['unit_amount'] / 100:,.0f} -> {dollars}", "POST", "/prices",
                create + [("transfer_lookup_key", "true")])
            if apply and stripe is not None:
                stripe.call("POST", f"/prices/{have['id']}", [("active", "false")])
        elif not have.get("active") or have.get("nickname") != want["nickname"] \
                or any(have.get("metadata", {}).get(k) != v for k, v in want["metadata"].items()):
            act(f"update price {key} (season, nickname or metadata)", "POST", f"/prices/{have['id']}",
                [("active", "true"), ("nickname", want["nickname"])] + flat("metadata", want["metadata"]))
    return changes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true", help="write to Stripe (default: read and print)")
    ap.add_argument("--live", action="store_true", help="allow a live-mode key")
    ap.add_argument("--pricing", default=str(ROOT / "pricing.toml"))
    args = ap.parse_args()

    products, prices = load_plan(Path(args.pricing))
    key = os.environ.get("STRIPE_API_KEY", "").strip()
    if not key:
        if args.apply:
            sys.exit("set STRIPE_API_KEY to apply")
        print(f"No STRIPE_API_KEY: showing the plan from {Path(args.pricing).name} only.\n")
        for p in products:
            print(f"  product {p['id']:<28} {p['name']}")
        for p in prices:
            state = f"${p['amount'] / 100:>5,.0f}" if p["active"] else "  off"
            print(f"  price   {p['lookup_key']:<34} {state}  {p['nickname']}")
        print(f"\n{len(products)} products, {sum(p['active'] for p in prices)} prices on sale, "
              f"{sum(not p['active'] for p in prices)} off sale.")
        return 0
    if "_live_" in key and not args.live:
        sys.exit("that is a live-mode key; rerun with --live if you mean it")
    mode = "LIVE" if "_live_" in key else "test"
    print(f"Stripe {mode} mode, {'applying' if args.apply else 'dry run'}:")
    changes = sync(Stripe(key), products, prices, args.apply)
    print("in sync" if not changes else f"{changes} change(s) {'made' if args.apply else 'pending; rerun with --apply'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
