import pandas as pd


def closes_from_history(df: pd.DataFrame) -> dict[str, float]:
    """yfinance 월봉 DataFrame → {"YYYY-MM": 그 달 종가}. 같은 달 행이 여럿이면 마지막 값."""
    out: dict[str, float] = {}
    for ts, close in df["Close"].sort_index().items():
        if pd.isna(close):
            continue
        out[f"{ts.year:04d}-{ts.month:02d}"] = float(close)
    return out


def fetch_monthly_closes(ticker: str, start: str = "2000-01-01") -> dict[str, float]:
    import yfinance as yf

    df = yf.Ticker(ticker).history(start=start, interval="1mo", auto_adjust=False)
    return closes_from_history(df)
