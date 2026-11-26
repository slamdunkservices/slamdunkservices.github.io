"""Offline tests for the parts of the fulfillment function that need no network.

    cd _store/fulfillment && TOKEN_SECRET=test-secret-test-secret-test python3 -m pytest -q

Stripe and GCS are stubbed at import time, so this runs with pytest alone.
"""
import os
import sys
import types

os.environ.setdefault("TOKEN_SECRET", "test-secret-test-secret-test")


def _stub(name, **attrs):
    mod = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(mod, key, value)
    sys.modules[name] = mod
    return mod


class _Err(Exception):
    pass


_stub("functions_framework", http=lambda fn: fn)
_stub("stripe", api_key="", max_network_retries=0,
      error=types.SimpleNamespace(StripeError=_Err, InvalidRequestError=_Err))
_stub("google")
_stub("google.auth", default=lambda: (None, None))
_stub("google.auth.transport")
_stub("google.auth.transport.requests", Request=object)
_stub("google.cloud")
_stub("google.cloud.storage", Client=object)

import pytest  # noqa: E402

import main  # noqa: E402


def test_token_round_trip():
    token = main.make_token("cus_abc123")
    assert main.read_token(token) == "cus_abc123"


def test_token_tamper_and_expiry():
    token = main.make_token("cus_abc123", now=0)          # expired in 1971
    with pytest.raises(main.Refused) as err:
        main.read_token(token)
    assert err.value.status == 401
    body, sig = main.make_token("cus_abc123").split(".")
    forged = main._b64(b"cus_other.9999999999") + "." + sig
    with pytest.raises(main.Refused):
        main.read_token(forged)
    with pytest.raises(main.Refused):
        main.read_token("garbage")


def test_blocked_customer(monkeypatch):
    monkeypatch.setattr(main, "BLOCKED", {"cus_bad"})
    with pytest.raises(main.Refused) as err:
        main.read_token(main.make_token("cus_bad"))
    assert err.value.status == 403


def test_parse_grants_drops_junk():
    assert main.parse_grants("nba/2025-26/player-logs, NBA/2024-25/* ,../etc, a/b, nba/*/x") == [
        "nba/2025-26/player-logs", "nba/2024-25/*"]
    assert main.parse_grants(None) == []


def test_grants_round_trip_through_metadata():
    grants = [f"nba/{y}-{str(y + 1)[2:]}/*" for y in range(1980, 2060)]
    packed = main.pack_grants(grants)
    assert len(packed) > 1 and all(len(v) <= 500 for v in packed.values())
    assert sorted(main.unpack_grants({**packed, "other": "nba/2025-26/*"})) == sorted(grants)


def test_allowed_matches_folder_only():
    grants = ["nba/2025-26/player-logs", "wnba/2026/*"]
    assert main.allowed("files/nba/2025-26/player-logs/nba_2025-26_player-logs.csv", grants)
    assert not main.allowed("files/nba/2024-25/player-logs/x.csv", grants)
    assert not main.allowed("files/nba/2025-26/play-by-play/x.csv", grants)
    assert main.allowed("files/wnba/2026/first-events/x.csv", grants)
    assert not main.allowed("files/wnba/2025/first-events/x.csv", grants)
    # nothing outside files/<league>/<season>/<dataset>/<name> is ever downloadable
    assert not main.allowed("samples/nba/x.csv", ["nba/2025-26/*"])
    assert not main.allowed("files/nba/2025-26/player-logs/deeper/x.csv", ["nba/2025-26/*"])
    assert not main.allowed("files/nba/2025-26/x.csv", ["nba/2025-26/*"])


def test_parse_lookup():
    assert main.parse_lookup("sdb_nba_player-logs_pass") == ("nba", "player-logs", "pass")
    assert main.parse_lookup("sdb_wnba_all_season") == ("wnba", "all", "season")
    assert main.parse_lookup("sdb_nfl_archive") == ("nfl", "all", "archive")
    assert main.parse_lookup("something_else") is None
    assert main.parse_lookup(None) is None


PRICES = {
    ("nba", "player-logs", "pass"): {"id": "p_pl_pass", "amount": 4900, "currency": "usd", "season": "2026-27"},
    ("nba", "player-logs", "season"): {"id": "p_pl_season", "amount": 1200, "currency": "usd", "season": None},
    ("nba", "all", "pass"): {"id": "p_all_pass", "amount": 12900, "currency": "usd", "season": "2026-27"},
    ("nba", "all", "season"): {"id": "p_all_season", "amount": 3900, "currency": "usd", "season": None},
    ("nba", "all", "archive"): {"id": "p_archive", "amount": 24900, "currency": "usd", "season": None},
    ("wnba", "player-logs", "season"): {"id": "p_w_season", "amount": 1000, "currency": "usd", "season": None},
}
STOCK = {
    "nba": {"player-logs": ["2024-25", "2025-26", "2026-27"], "play-by-play": ["2025-26", "2026-27"]},
    "wnba": {"player-logs": ["2025", "2026"]},
}


def cart(*items):
    return [dict(zip(("league", "dataset", "season"), i)) for i in items]


def test_price_cart_picks_pass_or_season_price():
    lines, grants, labels = main.price_cart(
        cart(("nba", "player-logs", "2026-27"), ("nba", "player-logs", "2025-26"),
             ("nba", "player-logs", "2024-25"), ("nba", "player-logs", "2024-25")),
        PRICES, STOCK)
    assert lines == [{"price": "p_pl_pass", "quantity": 1}, {"price": "p_pl_season", "quantity": 2}]
    assert sorted(grants) == ["nba/2024-25/player-logs", "nba/2025-26/player-logs", "nba/2026-27/player-logs"]
    assert len(labels) == 3


def test_price_cart_bundles_and_archive():
    lines, grants, _ = main.price_cart(
        cart(("nba", "all", "2026-27"), ("nba", "all", "archive")), PRICES, STOCK)
    assert lines == [{"price": "p_all_pass", "quantity": 1}, {"price": "p_archive", "quantity": 1}]
    # the archive is every completed season, never the one in progress
    assert sorted(grants) == ["nba/2024-25/*", "nba/2025-26/*", "nba/2026-27/*"]
    _, only_archive, _ = main.price_cart(cart(("nba", "all", "archive")), PRICES, STOCK)
    assert sorted(only_archive) == ["nba/2024-25/*", "nba/2025-26/*"]


def test_price_cart_off_season_league_has_no_pass():
    lines, grants, _ = main.price_cart(cart(("wnba", "player-logs", "2026")), PRICES, STOCK)
    assert lines == [{"price": "p_w_season", "quantity": 1}] and grants == ["wnba/2026/player-logs"]


@pytest.mark.parametrize("items,status", [
    ([], 400),
    ("nope", 400),
    (cart(("nba", "player-logs", "2019-20")), 409),          # season not in the bucket
    (cart(("nba", "play-by-play", "2025-26")), 409),         # in the bucket, no price
    (cart(("mlb", "player-logs", "2026")), 409),             # league not on sale
    (cart(("nba", "player-logs", "archive")), 400),          # archive is league-wide
    (cart(("nba", "../x", "2025-26")), 400),
    ([{"league": "nba"}], 400),
])
def test_price_cart_refuses(items, status):
    with pytest.raises(main.Refused) as err:
        main.price_cart(items, PRICES, STOCK)
    assert err.value.status == status


def test_inventory():
    files = [{"league": "nba", "dataset": "player-logs", "season": s} for s in ("2025-26", "2024-25", "2025-26")]
    assert main.inventory(files) == {"nba": {"player-logs": ["2024-25", "2025-26"]}}


def test_throttle(monkeypatch):
    monkeypatch.setattr(main, "DOWNLOADS_PER_HOUR", 2)
    main._downloads.clear()
    main.throttle("cus_a")
    main.throttle("cus_a")
    with pytest.raises(main.Refused) as err:
        main.throttle("cus_a")
    assert err.value.status == 429
    main.throttle("cus_b")
