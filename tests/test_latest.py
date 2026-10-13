import json
import math

import pandas as pd
import pytest

from pipeline import latest as latest_mod
from pipeline.catalog import Asset
from pipeline.latest import build_latest, fetch_latest_close, last_close_from_history

KR = Asset("005930", "삼성전자", "kr_stock", "KRW", "005930.KS")
US = Asset("AAPL", "애플", "us_stock", "USD", "AAPL")
BTC = Asset("btc", "비트코인", "crypto", "USD", "BTC-USD")
FX = Asset("usdkrw", "원/달러 환율", "fx", "KRW", "KRW=X")
MONTH_END = {"005930": 70000.0, "AAPL": 200.0, "btc": 60000.0, "usdkrw": 1300.0}


def fetch_from(table):
    def fetch(ticker):
        v = table[ticker]
        if isinstance(v, Exception):
            raise v
        return v

    return fetch


GOOD = {
    "005930.KS": ("2026-10-12", 71000.0),
    "AAPL": ("2026-10-12", 210.5),
    "BTC-USD": ("2026-10-13", 62000.0),
    "KRW=X": ("2026-10-13", 1350.25),
}


def test_last_close_from_history_takes_latest_non_nan_row():
    idx = pd.to_datetime(["2026-10-09", "2026-10-10", "2026-10-13"]).tz_localize("America/New_York")
    df = pd.DataFrame({"Close": [100.0, 101.5, float("nan")]}, index=idx)
    assert last_close_from_history(df) == ("2026-10-10", 101.5)


def test_last_close_from_history_empty_returns_none():
    assert last_close_from_history(pd.DataFrame({"Close": []})) is None


def test_fetch_latest_close_retries_three_times_then_fails(monkeypatch):
    calls = []

    def boom(ticker):
        calls.append(ticker)
        raise ConnectionError("down")

    monkeypatch.setattr(latest_mod, "_download_daily", boom)
    with pytest.raises(RuntimeError, match="AAPL"):
        fetch_latest_close("AAPL", sleep=lambda s: None)
    assert len(calls) == 3


def test_fetch_latest_close_recovers_after_empty_result(monkeypatch):
    idx = pd.to_datetime(["2026-10-12"])
    frames = iter([pd.DataFrame({"Close": []}), pd.DataFrame({"Close": [5.0]}, index=idx)])
    monkeypatch.setattr(latest_mod, "_download_daily", lambda t: next(frames))
    assert fetch_latest_close("X", sleep=lambda s: None) == ("2026-10-12", 5.0)


def test_build_latest_format():
    doc = build_latest([KR, US, BTC], FX, MONTH_END, fetch_from(GOOD))
    assert doc == {
        "asOf": "2026-10-13",
        "prices": {"005930": 71000.0, "AAPL": 210.5, "btc": 62000.0},
        "usdkrw": 1350.25,
    }
    json.dumps(doc, allow_nan=False)


@pytest.mark.parametrize(
    "bad",
    [
        RuntimeError("no data"),
        ("2026-10-12", float("nan")),
        ("2026-10-12", math.inf),
        ("2026-10-12", 0.0),
        ("2026-10-12", -5.0),
        ("2026-10-12", 301.0),  # 월말 200 대비 +50.5%
        ("2026-10-12", 99.0),  # 월말 200 대비 -50.5%
    ],
)
def test_build_latest_omits_failed_or_invalid_asset(bad):
    doc = build_latest([KR, US], FX, MONTH_END, fetch_from({**GOOD, "AAPL": bad}))
    assert "AAPL" not in doc["prices"]
    assert doc["prices"]["005930"] == 71000.0


def test_build_latest_allows_exactly_50_percent():
    doc = build_latest([US], FX, MONTH_END, fetch_from({**GOOD, "AAPL": ("2026-10-12", 300.0)}))
    assert doc["prices"]["AAPL"] == 300.0


def test_build_latest_omits_asset_without_month_end_reference():
    doc = build_latest([US], FX, {"usdkrw": 1300.0}, fetch_from(GOOD))
    assert doc["prices"] == {}


@pytest.mark.parametrize("rate", [499.0, 3001.0, float("nan")])
def test_build_latest_returns_none_when_fx_invalid(rate):
    me = {**MONTH_END, "usdkrw": 1300.0}
    assert build_latest([KR], FX, me, fetch_from({**GOOD, "KRW=X": ("2026-10-13", rate)})) is None


def test_build_latest_returns_none_when_fx_fetch_fails():
    assert build_latest([KR], FX, MONTH_END, fetch_from({**GOOD, "KRW=X": RuntimeError("x")})) is None


def test_build_latest_fetches_each_ticker_once():
    calls = []
    usd = Asset("usd", "달러", "fx", "KRW", "KRW=X")

    def fetch(t):
        calls.append(t)
        return GOOD[t]

    doc = build_latest([usd, KR], FX, {**MONTH_END, "usd": 1300.0}, fetch)
    assert doc["prices"]["usd"] == 1350.25
    assert calls.count("KRW=X") == 1
