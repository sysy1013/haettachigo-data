import datetime as dt

import pandas as pd
import pytest

from pipeline.build import asset_json, last_complete_month, manifest_json, month_end
from pipeline.catalog import Asset
from pipeline import fetch as fetch_mod
from pipeline.fetch import closes_from_history

SAMPLE = Asset("aaa", "에이", "kr_stock", "KRW", "aaa.KS")


def test_closes_from_history_maps_months_and_skips_nan():
    idx = pd.to_datetime(["2020-01-01", "2020-02-01", "2020-03-01", "2020-03-15"]).tz_localize("Asia/Seoul")
    df = pd.DataFrame({"Close": [100.0, float("nan"), 120.0, 125.5]}, index=idx)
    assert closes_from_history(df) == {"2020-01": 100.0, "2020-03": 125.5}


def test_last_complete_month():
    assert last_complete_month(dt.date(2026, 10, 12)) == "2026-09"
    assert last_complete_month(dt.date(2026, 1, 1)) == "2025-12"


def test_month_end():
    assert month_end("2026-09") == "2026-09-30"
    assert month_end("2024-02") == "2024-02-29"


def test_asset_json_trims_incomplete_month_and_sorts():
    closes = {"2026-10": 999.0, "2026-08": 110.1234567, "2026-09": 120.0}
    doc = asset_json(SAMPLE, closes, "2026-09")
    assert doc == {
        "id": "aaa",
        "name": "에이",
        "category": "kr_stock",
        "currency": "KRW",
        "listedFrom": "2026-08",
        "prices": [["2026-08", 110.123457], ["2026-09", 120.0]],
    }


def test_asset_json_without_data_raises():
    with pytest.raises(ValueError):
        asset_json(SAMPLE, {"2026-10": 1.0}, "2026-09")


def test_manifest_json():
    assert manifest_json("2026-09", ["a", "b"]) == {
        "version": "2026-09",
        "baseDate": "2026-09-30",
        "assets": ["a", "b"],
    }


def _history(*closes):
    idx = pd.to_datetime([f"2020-{i + 1:02d}-01" for i in range(len(closes))])
    return pd.DataFrame({"Close": list(closes)}, index=idx)


def _scripted_download(monkeypatch, outcomes):
    calls = []

    def download(ticker, start):
        calls.append((ticker, start))
        outcome = outcomes[len(calls) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(fetch_mod, "_download", download)
    return calls


def test_fetch_retries_until_third_attempt(monkeypatch):
    calls = _scripted_download(monkeypatch, [_history(), ConnectionError("boom"), _history(100.0, 110.0)])
    sleeps = []
    closes = fetch_mod.fetch_monthly_closes("AAPL", sleep=sleeps.append)
    assert closes == {"2020-01": 100.0, "2020-02": 110.0}
    assert sleeps == [2, 4]
    assert calls == [("AAPL", "2000-01-01")] * 3


def test_fetch_empty_every_time_raises(monkeypatch):
    _scripted_download(monkeypatch, [_history(), _history(), _history()])
    sleeps = []
    with pytest.raises(RuntimeError, match="AAPL: no data after 3 attempts"):
        fetch_mod.fetch_monthly_closes("AAPL", sleep=sleeps.append)
    assert sleeps == [2, 4]


def test_fetch_last_exception_is_chained(monkeypatch):
    err = ConnectionError("down")
    _scripted_download(monkeypatch, [_history(), _history(), err])
    with pytest.raises(RuntimeError) as info:
        fetch_mod.fetch_monthly_closes("AAPL", sleep=lambda s: None)
    assert info.value.__cause__ is err


def test_fetch_exception_then_success(monkeypatch):
    _scripted_download(monkeypatch, [TimeoutError("slow"), _history(100.0)])
    sleeps = []
    assert fetch_mod.fetch_monthly_closes("AAPL", sleep=sleeps.append) == {"2020-01": 100.0}
    assert sleeps == [2]
