import datetime as dt
import json

import pytest

from pipeline.catalog import ASSETS
from pipeline.main import build_site
from pipeline.validate import ValidationError

TODAY = dt.date(2026, 10, 12)


def fake_fetch_factory(calls, override=None):
    def fetch(ticker):
        calls.append(ticker)
        if override and ticker in override:
            return override[ticker]
        return {"2026-07": 100.0, "2026-08": 110.0, "2026-09": 120.0, "2026-10": 130.0}

    return fetch


def test_build_site_writes_all_files(tmp_path):
    calls = []
    docs = build_site(tmp_path, fetch=fake_fetch_factory(calls), today=TODAY)

    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "2026-09"
    assert manifest["assets"] == [a.id for a in ASSETS]
    assert (tmp_path / "fx" / "usdkrw.json").exists()
    for a in ASSETS:
        doc = json.loads((tmp_path / "prices" / f"{a.id}.json").read_text(encoding="utf-8"))
        assert doc["prices"][-1] == ["2026-09", 120.0]
    assert "삼성전자" in (tmp_path / "prices" / "005930.json").read_text(encoding="utf-8")
    assert len(docs) == len(ASSETS) + 2
    assert calls.count("KRW=X") == 1


def test_build_site_writes_nothing_when_validation_fails(tmp_path):
    bad = {"AAPL": {"2026-08": 100.0, "2026-09": 300.0}}
    with pytest.raises(ValidationError, match="AAPL"):
        build_site(tmp_path, fetch=fake_fetch_factory([], bad), today=TODAY)
    assert list(tmp_path.iterdir()) == []


def test_build_site_rejects_stale_asset(tmp_path):
    stale = {"005930.KS": {"2026-07": 100.0, "2026-08": 110.0}}
    with pytest.raises(ValidationError, match="005930"):
        build_site(tmp_path, fetch=fake_fetch_factory([], stale), today=TODAY)
