import datetime as dt

from pipeline.catalog import Asset
from pipeline.daily import build_daily, remove_daily_spikes

KR = Asset("005930", "삼성전자", "kr_stock", "KRW", "005930.KS")
BTC = Asset("btc", "비트코인", "crypto", "USD", "BTC-USD")
FX = Asset("usdkrw", "원/달러 환율", "fx", "KRW", "KRW=X")
TODAY = dt.date(2026, 10, 14)


def day(n):  # TODAY 기준 n일 전
    return (TODAY - dt.timedelta(days=n)).isoformat()


def table_fetch(table):
    def fetch(ticker, start):
        v = table[ticker]
        if isinstance(v, Exception):
            raise v
        return v

    return fetch


def good():
    return {
        "005930.KS": [(day(500), 69000.0), (day(5), 70000.1234567), (day(1), 71000.0), (day(0), 72000.0)],
        "BTC-USD": [(day(400), 100000.0), (day(1), 101000.0), (day(0), 102000.0)],
        "KRW=X": [(day(3), 1380.0), (day(0), 1390.0)],
    }


def test_format_base_offsets_range_rounding():
    failed = []
    doc = build_daily([KR, BTC], FX, table_fetch(good()), failed, TODAY)
    assert failed == []
    assert doc["version"] == 1
    assert doc["asOf"] == "2026-10-14"
    assert doc["base"] == day(400)  # 500일 전 점은 제외
    for rows in doc["series"].values():
        offsets = [r[0] for r in rows]
        assert offsets == sorted(set(offsets))
    assert doc["series"]["005930"][0] == [395, 70000.123457]
    assert doc["series"]["btc"][0] == [0, 100000.0]
    assert doc["series"]["usdkrw"][-1] == [400, 1390.0]
    assert all(r[0] <= 400 for rows in doc["series"].values() for r in rows)


def test_spike_removed():
    rows = [("a", 100.0), ("b", 300.0), ("c", 110.0), ("d", 40.0), ("e", 112.0)]
    assert remove_daily_spikes(rows) == [("a", 100.0), ("c", 110.0), ("e", 112.0)]


def test_bad_values_removed():
    rows = [("a", 100.0), ("b", float("nan")), ("c", -5.0), ("d", 0.0), ("e", float("inf")), ("f", 101.0)]
    assert remove_daily_spikes(rows) == [("a", 100.0), ("f", 101.0)]


def test_fx_out_of_range_dropped():
    t = good()
    t["KRW=X"] = [(day(3), 1380.0), (day(2), 3500.0), (day(0), 1390.0)]
    doc = build_daily([KR], FX, table_fetch(t), None, TODAY)
    assert [r[1] for r in doc["series"]["usdkrw"]] == [1380.0, 1390.0]


def test_fx_failure_returns_none():
    t = good()
    t["KRW=X"] = RuntimeError("boom")
    failed = []
    assert build_daily([KR, BTC], FX, table_fetch(t), failed, TODAY) is None
    assert "usdkrw" in failed


def test_failed_asset_excluded():
    t = good()
    t["BTC-USD"] = RuntimeError("boom")
    failed = []
    doc = build_daily([KR, BTC], FX, table_fetch(t), failed, TODAY)
    assert failed == ["btc"]
    assert set(doc["series"]) == {"005930", "usdkrw"}
