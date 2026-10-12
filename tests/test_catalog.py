from pipeline.catalog import ASSETS, FX

CATEGORIES = {"kr_stock", "us_stock", "crypto", "commodity", "fx"}
CURRENCIES = {"KRW", "USD"}


def test_counts_per_category():
    by_cat = {}
    for a in ASSETS:
        by_cat[a.category] = by_cat.get(a.category, 0) + 1
    assert by_cat == {"kr_stock": 20, "us_stock": 20, "crypto": 2, "commodity": 1, "fx": 1}


def test_ids_unique_and_fx_separate():
    ids = [a.id for a in ASSETS]
    assert len(ids) == len(set(ids))
    assert FX.id == "usdkrw" and FX.id not in ids


def test_fields_valid():
    for a in ASSETS + [FX]:
        assert a.category in CATEGORIES
        assert a.currency in CURRENCIES
        assert a.name and a.ticker


def test_currency_rules():
    for a in ASSETS:
        if a.category == "kr_stock":
            assert a.currency == "KRW" and a.ticker == f"{a.id}.KS"
        if a.category == "us_stock":
            assert a.currency == "USD" and a.ticker == a.id
    by_id = {a.id: a for a in ASSETS}
    assert by_id["btc"].ticker == "BTC-USD" and by_id["btc"].currency == "USD"
    assert by_id["gold"].ticker == "GC=F"
    assert by_id["usd"].ticker == "KRW=X" and by_id["usd"].currency == "KRW"
    assert FX.ticker == "KRW=X" and FX.currency == "KRW"
