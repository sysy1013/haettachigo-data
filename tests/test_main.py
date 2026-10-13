import datetime as dt
import json

import pytest

from pipeline.catalog import ASSETS
from pipeline import main as main_mod
from pipeline.main import build_site
from pipeline.validate import ValidationError

TODAY = dt.date(2026, 10, 12)


def fake_fetch_factory(calls, override=None):
    def fetch(ticker):
        calls.append(ticker)
        if override and ticker in override:
            return override[ticker]
        if ticker == "KRW=X":
            return {"2026-07": 1300.0, "2026-08": 1310.0, "2026-09": 1320.0, "2026-10": 1330.0}
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
        assert doc["prices"][-1] == ["2026-09", 1320.0 if a.ticker == "KRW=X" else 120.0]
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


GLITCHY_KRW = {
    "2015-01": 1101.0,
    "2015-02": 0.110254,
    "2015-03": 1105.5,
    "2015-09": 1194.16,
    "2015-10": 0.114273,
    "2015-11": 1154.83,
    "2026-08": 1310.0,
    "2026-09": 1320.0,
    "2026-10": 1330.0,
}


def test_build_site_removes_isolated_spikes_and_reports_drops(tmp_path):
    dropped = {}
    docs = build_site(
        tmp_path, fetch=fake_fetch_factory([], {"KRW=X": GLITCHY_KRW}), today=TODAY, dropped=dropped
    )
    months = [m for m, _ in docs["fx/usdkrw.json"]["prices"]]
    assert "2015-02" not in months and "2015-10" not in months
    assert all(v >= 500 for _, v in docs["prices/usd.json"]["prices"])
    assert dropped == {"usd": ["2015-02", "2015-10"], "usdkrw": ["2015-02", "2015-10"]}


def test_build_site_spike_check_ignores_incomplete_month(tmp_path):
    # 마지막 완결 달(2026-09)은 미완결 달(2026-10)과 비교해 제거되지 않는다
    series = {"2026-07": 100.0, "2026-08": 101.0, "2026-09": 160.0, "2026-10": 102.0}
    dropped = {}
    docs = build_site(tmp_path, fetch=fake_fetch_factory([], {"AAPL": series}), today=TODAY, dropped=dropped)
    assert docs["prices/AAPL.json"]["prices"][-1] == ["2026-09", 160.0]
    assert dropped == {}


def test_cli_prints_dropped_months(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(main_mod, "fetch_monthly_closes", fake_fetch_factory([], {"KRW=X": GLITCHY_KRW}))
    monkeypatch.setattr(main_mod, "_today", lambda: TODAY)
    main_mod.main(["--out", str(tmp_path)])
    out = capsys.readouterr().out
    assert "usdkrw: dropped 2015-02, 2015-10" in out
    assert "usd: dropped 2015-02, 2015-10" in out


def latest_fetch(ticker):
    if ticker == "KRW=X":
        return ("2026-10-10", 1335.0)
    if ticker == "AAPL":
        raise RuntimeError("down")
    return ("2026-10-10", 125.0)


def test_build_site_with_latest_writes_latest_json(tmp_path):
    docs = build_site(tmp_path, fetch=fake_fetch_factory([]), today=TODAY, latest_fetch=latest_fetch)
    latest = json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))
    assert latest == docs["latest.json"]
    assert latest["asOf"] == "2026-10-10"
    assert latest["usdkrw"] == 1335.0
    assert "AAPL" not in latest["prices"]
    assert latest["prices"]["005930"] == 125.0
    assert latest["prices"]["usd"] == 1335.0
    assert len(latest["prices"]) == len(ASSETS) - 1


def test_build_site_without_latest_fetch_skips_latest(tmp_path):
    docs = build_site(tmp_path, fetch=fake_fetch_factory([]), today=TODAY)
    assert "latest.json" not in docs
    assert not (tmp_path / "latest.json").exists()


def test_build_site_skips_latest_when_fx_fails(tmp_path):
    def fx_down(ticker):
        if ticker == "KRW=X":
            raise RuntimeError("down")
        return ("2026-10-10", 125.0)

    docs = build_site(tmp_path, fetch=fake_fetch_factory([]), today=TODAY, latest_fetch=fx_down)
    assert "latest.json" not in docs
    assert (tmp_path / "manifest.json").exists()


def test_cli_with_latest(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(main_mod, "fetch_monthly_closes", fake_fetch_factory([]))
    monkeypatch.setattr(main_mod, "fetch_latest_close", latest_fetch)
    monkeypatch.setattr(main_mod, "_today", lambda: TODAY)
    main_mod.main(["--out", str(tmp_path), "--with-latest"])
    assert (tmp_path / "latest.json").exists()
    assert "latest 2026-10-10" in capsys.readouterr().out
