"""매일 최신가: 각 자산·환율의 최근 일봉 종가 1개 → latest.json."""
import math
import time

import pandas as pd

from .catalog import Asset
from .validate import FX_MAX, FX_MIN

MAX_DRIFT = 0.5  # 직전 월말 대비 허용 변동 (±50%)


def last_close_from_history(df: pd.DataFrame) -> tuple[str, float] | None:
    """일봉 DataFrame → 마지막 유효 행의 ("YYYY-MM-DD", 종가). 없으면 None."""
    for ts, close in reversed(list(df["Close"].sort_index().items())):
        if pd.isna(close):
            continue
        return f"{ts.year:04d}-{ts.month:02d}-{ts.day:02d}", float(close)
    return None


def _download_daily(ticker: str) -> pd.DataFrame:
    import yfinance as yf

    return yf.Ticker(ticker).history(period="7d", interval="1d", auto_adjust=False)


def fetch_latest_close(ticker: str, attempts: int = 3, sleep=time.sleep) -> tuple[str, float]:
    """예외나 빈 결과는 실패로 보고 재시도. 끝내 실패하면 RuntimeError."""
    last_error: Exception | None = None
    for attempt in range(attempts):
        if attempt:
            sleep(2**attempt)
        try:
            result = last_close_from_history(_download_daily(ticker))
        except Exception as e:  # noqa: BLE001 - 네트워크·파싱 오류 모두 재시도
            last_error = e
            continue
        if result:
            return result
    raise RuntimeError(f"{ticker}: no daily data after {attempts} attempts") from last_error


def _valid(value, reference: float | None) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    if not math.isfinite(value) or value <= 0 or not reference:
        return False
    return abs(value / reference - 1) <= MAX_DRIFT


def build_latest(
    assets: list[Asset],
    fx: Asset,
    month_end: dict[str, float],
    fetch=fetch_latest_close,
    failed: list[str] | None = None,
) -> dict | None:
    """month_end는 id → 직전 월말가. 실패·검증 탈락 종목은 제외(failed에 기록).
    환율이 없거나 범위 밖이면 None (latest.json을 쓰지 않음)."""
    cache: dict[str, tuple[str, float] | None] = {}

    def get(ticker: str):
        if ticker not in cache:
            try:
                cache[ticker] = fetch(ticker)
            except Exception:  # noqa: BLE001 - 실패 종목은 제외
                cache[ticker] = None
        return cache[ticker]

    fx_row = get(fx.ticker)
    if fx_row is None or not _valid(fx_row[1], month_end.get(fx.id)) or not FX_MIN <= fx_row[1] <= FX_MAX:
        if failed is not None:
            failed.append(fx.id)
        return None

    prices: dict[str, float] = {}
    dates = [fx_row[0]]
    for asset in assets:
        row = get(asset.ticker)
        if row is None or not _valid(row[1], month_end.get(asset.id)):
            if failed is not None:
                failed.append(asset.id)
            continue
        prices[asset.id] = round(row[1], 6)
        dates.append(row[0])
    return {"asOf": max(dates), "prices": prices, "usdkrw": round(fx_row[1], 6)}
