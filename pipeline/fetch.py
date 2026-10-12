import time

import pandas as pd


def closes_from_history(df: pd.DataFrame) -> dict[str, float]:
    """yfinance 월봉 DataFrame → {"YYYY-MM": 그 달 종가}. 같은 달 행이 여럿이면 마지막 값."""
    out: dict[str, float] = {}
    for ts, close in df["Close"].sort_index().items():
        if pd.isna(close):
            continue
        out[f"{ts.year:04d}-{ts.month:02d}"] = float(close)
    return out


def _download(ticker: str, start: str) -> pd.DataFrame:
    import yfinance as yf

    return yf.Ticker(ticker).history(start=start, interval="1mo", auto_adjust=False)


def fetch_monthly_closes(
    ticker: str, start: str = "2000-01-01", attempts: int = 3, sleep=time.sleep
) -> dict[str, float]:
    """예외나 빈 결과는 실패로 보고 2초, 4초, … 쉬며 재시도. 끝내 실패하면 RuntimeError."""
    last_error: Exception | None = None
    for attempt in range(attempts):
        if attempt:
            sleep(2**attempt)
        try:
            closes = closes_from_history(_download(ticker, start))
        except Exception as e:  # noqa: BLE001 - 네트워크·파싱 오류 모두 재시도
            last_error = e
            continue
        if closes:
            return closes
    raise RuntimeError(f"{ticker}: no data after {attempts} attempts") from last_error
