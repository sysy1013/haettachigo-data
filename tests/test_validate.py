import copy

import pytest

from pipeline.validate import ValidationError, validate_asset, validate_manifest

GOOD = {
    "id": "aaa",
    "name": "에이",
    "category": "kr_stock",
    "currency": "KRW",
    "listedFrom": "2026-07",
    "prices": [["2026-07", 100.0], ["2026-08", 110.0], ["2026-09", 120.0]],
}


def mutated(**changes):
    doc = copy.deepcopy(GOOD)
    doc.update(changes)
    return doc


def test_good_asset_passes():
    validate_asset(GOOD, "2026-09")


@pytest.mark.parametrize(
    "doc",
    [
        {k: v for k, v in GOOD.items() if k != "name"},
        mutated(category="stock"),
        mutated(currency="JPY"),
        mutated(prices=[["2026-09", 120.0]], listedFrom="2026-09"),
        mutated(prices=[["2026-7", 100.0], ["2026-09", 120.0]], listedFrom="2026-7"),
        mutated(prices=[["2026-09", 100.0], ["2026-08", 110.0]], listedFrom="2026-09"),
        mutated(prices=[["2026-08", 100.0], ["2026-08", 110.0]], listedFrom="2026-08"),
        mutated(listedFrom="2026-08"),
        mutated(prices=[["2026-08", 0], ["2026-09", 120.0]], listedFrom="2026-08"),
        mutated(prices=[["2026-08", -1.0], ["2026-09", 120.0]], listedFrom="2026-08"),
        mutated(prices=[["2026-08", float("nan")], ["2026-09", 120.0]], listedFrom="2026-08"),
        mutated(prices=[["2026-08", True], ["2026-09", 120.0]], listedFrom="2026-08"),
        mutated(prices=[["2026-08", "100"], ["2026-09", 120.0]], listedFrom="2026-08"),
    ],
)
def test_bad_assets_rejected(doc):
    with pytest.raises(ValidationError):
        validate_asset(doc, "2026-09")


def test_stale_latest_month_rejected():
    with pytest.raises(ValidationError, match="aaa"):
        validate_asset(GOOD, "2026-10")


def test_jump_limit():
    ok = mutated(prices=[["2026-08", 100.0], ["2026-09", 190.0]], listedFrom="2026-08")
    validate_asset(ok, "2026-09")
    up = mutated(prices=[["2026-08", 100.0], ["2026-09", 191.0]], listedFrom="2026-08")
    down = mutated(prices=[["2026-08", 100.0], ["2026-09", 9.0]], listedFrom="2026-08")
    for doc in (up, down):
        with pytest.raises(ValidationError, match="aaa"):
            validate_asset(doc, "2026-09")


def test_manifest():
    good = {"version": "2026-09", "baseDate": "2026-09-30", "assets": ["a", "b"]}
    validate_manifest(good, ["a", "b"])
    for bad in (
        dict(good, version="2026-9"),
        dict(good, baseDate="2026-09-31"),
        dict(good, assets=["a"]),
    ):
        with pytest.raises(ValidationError):
            validate_manifest(bad, ["a", "b"])
