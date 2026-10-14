"""최근 400일 일봉 종가: 자산·환율별 [dayOffset, close] → daily.json."""
import datetime as dt
import math
import time

import pandas as pd

from .catalog import Asset
from .validate import FX_MAX, FX_MIN

SPAN_DAYS = 400
MAX_DAILY_JUMP = 0.5  # 직전 유효점 대비 허용 변동 (±50%)


def rows_from_history(df: pd.DataFrame) -> list[tuple[str, float]]:
    """일봉 DataFrame → [("YYYY-MM-DD", 종가)] 날짜 오름차순. 결측 제외."""
    rows = []
    for ts, close in df["Close"].sort_index().items():
        if pd.isna(close):
            continue
        rows.append((f"{ts.year:04d}-{ts.month:02d}-{ts.day:02d}", float(close)))
    return rows


def _download_daily(ticker: str, start: dt.date) -> pd.DataFrame:
    import yfinance as yf

    return yf.Ticker(ticker).history(start=start.isoformat(), interval="1d", auto_adjust=False)


def fetch_daily_closes(
    ticker: str, start: dt.date, attempts: int = 3, sleep=time.sleep
) -> list[tuple[str, float]]:
    """예외나 빈 결과는 실패로 보고 재시도. 끝내 실패하면 RuntimeError."""
    last_error: Exception | None = None
    for attempt in range(attempts):
        if attempt:
            sleep(2**attempt)
        try:
            rows = rows_from_history(_download_daily(ticker, start))
        except Exception as e:  # noqa: BLE001 - 네트워크·파싱 오류 모두 재시도
            last_error = e
            continue
        if rows:
            return rows
    raise RuntimeError(f"{ticker}: no daily data after {attempts} attempts") from last_error


def remove_daily_spikes(rows: list[tuple[str, float]], lo: float = 0, hi: float = math.inf):
    """비유한·비양수·[lo,hi] 밖 점 제거, 직전 유효점 대비 ±50% 초과 점 제거."""
    kept: list[tuple[str, float]] = []
    for date, value in rows:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue
        if not math.isfinite(value) or value <= 0 or not lo <= value <= hi:
            continue
        if kept and abs(value / kept[-1][1] - 1) > MAX_DAILY_JUMP:
            continue
        kept.append((date, value))
    return kept


def build_daily(
    assets: list[Asset],
    fx: Asset,
    fetch=fetch_daily_closes,
    failed: list[str] | None = None,
    today: dt.date | None = None,
) -> dict | None:
    """실패·빈 자산은 제외(failed에 기록). 환율이 없으면 None (daily.json을 쓰지 않음)."""
    today = today or dt.date.today()
    start = today - dt.timedelta(days=SPAN_DAYS + 5)
    cache: dict[str, list[tuple[str, float]] | None] = {}

    def get(asset: Asset, lo: float = 0, hi: float = math.inf):
        if asset.ticker not in cache:
            try:
                cache[asset.ticker] = fetch(asset.ticker, start)
            except Exception:  # noqa: BLE001 - 실패 종목은 제외
                cache[asset.ticker] = None
        raw = cache[asset.ticker]
        return remove_daily_spikes(raw, lo, hi) if raw else []

    series_rows: dict[str, list[tuple[str, float]]] = {}
    fx_rows = get(fx, FX_MIN, FX_MAX)
    if not fx_rows:
        if failed is not None:
            failed.append(fx.id)
        return None
    series_rows[fx.id] = fx_rows
    for asset in assets:
        rows = get(asset)
        if not rows:
            if failed is not None:
                failed.append(asset.id)
            continue
        series_rows[asset.id] = rows

    as_of = dt.date.fromisoformat(max(r[-1][0] for r in series_rows.values()))
    floor = (as_of - dt.timedelta(days=SPAN_DAYS)).isoformat()
    trimmed = {k: [r for r in rows if r[0] >= floor] for k, rows in series_rows.items()}
    trimmed = {k: rows for k, rows in trimmed.items() if rows}
    if fx.id not in trimmed:
        return None
    base = dt.date.fromisoformat(min(rows[0][0] for rows in trimmed.values()))
    series = {
        k: [[(dt.date.fromisoformat(d) - base).days, round(v, 6)] for d, v in rows]
        for k, rows in trimmed.items()
    }
    return {"version": 1, "asOf": as_of.isoformat(), "base": base.isoformat(), "series": series}
