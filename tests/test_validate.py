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


FX_GOOD = {
    "id": "usdkrw",
    "name": "원/달러 환율",
    "category": "fx",
    "currency": "KRW",
    "listedFrom": "2015-01",
    "prices": [["2015-01", 1101.0], ["2015-02", 1105.0], ["2015-03", 1100.0], ["2026-09", 1320.0]],
}


def fx_doc(prices):
    return dict(FX_GOOD, prices=prices, listedFrom=prices[0][0])


def test_clean_fx_passes():
    validate_asset(FX_GOOD, "2026-09")


def test_fx_glitch_value_rejected_anywhere_in_history():
    doc = fx_doc([["2015-01", 1101.0], ["2015-02", 0.11], ["2015-03", 1105.0], ["2026-09", 1320.0]])
    with pytest.raises(ValidationError, match=r"usdkrw.*2015-02"):
        validate_asset(doc, "2026-09")


def test_fx_out_of_range_high_rejected():
    doc = fx_doc([["2015-01", 1101.0], ["2015-02", 3100.0], ["2026-09", 1320.0]])
    with pytest.raises(ValidationError, match=r"usdkrw.*2015-02"):
        validate_asset(doc, "2026-09")


def test_fx_large_monthly_jump_rejected():
    doc = fx_doc([["2015-01", 1000.0], ["2015-02", 1350.0], ["2015-03", 1340.0], ["2026-09", 1320.0]])
    with pytest.raises(ValidationError, match=r"usdkrw.*2015-02"):
        validate_asset(doc, "2026-09")


def test_non_fx_historical_jump_still_allowed():
    doc = mutated(
        prices=[["2026-06", 100.0], ["2026-07", 270.0], ["2026-08", 280.0], ["2026-09", 290.0]],
        listedFrom="2026-06",
    )
    validate_asset(doc, "2026-09")
