from dataclasses import dataclass


@dataclass(frozen=True)
class Asset:
    id: str
    name: str
    category: str  # kr_stock | us_stock | crypto | commodity | fx
    currency: str  # KRW | USD
    ticker: str  # yfinance 티커


_KR = [
    ("005930", "삼성전자"),
    ("000660", "SK하이닉스"),
    ("373220", "LG에너지솔루션"),
    ("207940", "삼성바이오로직스"),
    ("005380", "현대차"),
    ("000270", "기아"),
    ("068270", "셀트리온"),
    ("035420", "NAVER"),
    ("035720", "카카오"),
    ("105560", "KB금융"),
    ("055550", "신한지주"),
    ("005490", "POSCO홀딩스"),
    ("006400", "삼성SDI"),
    ("051910", "LG화학"),
    ("012330", "현대모비스"),
    ("028260", "삼성물산"),
    ("012450", "한화에어로스페이스"),
    ("329180", "HD현대중공업"),
    ("323410", "카카오뱅크"),
    ("259960", "크래프톤"),
]

_US = [
    ("AAPL", "애플"),
    ("MSFT", "마이크로소프트"),
    ("NVDA", "엔비디아"),
    ("GOOGL", "알파벳(구글)"),
    ("AMZN", "아마존"),
    ("META", "메타"),
    ("TSLA", "테슬라"),
    ("NFLX", "넷플릭스"),
    ("AVGO", "브로드컴"),
    ("AMD", "AMD"),
    ("TSM", "TSMC"),
    ("INTC", "인텔"),
    ("KO", "코카콜라"),
    ("DIS", "디즈니"),
    ("NKE", "나이키"),
    ("SBUX", "스타벅스"),
    ("MCD", "맥도날드"),
    ("COST", "코스트코"),
    ("SPY", "S&P500 ETF (SPY)"),
    ("QQQ", "나스닥100 ETF (QQQ)"),
]

ASSETS: list[Asset] = (
    [Asset(code, name, "kr_stock", "KRW", f"{code}.KS") for code, name in _KR]
    + [Asset(t, name, "us_stock", "USD", t) for t, name in _US]
    + [
        Asset("btc", "비트코인", "crypto", "USD", "BTC-USD"),
        Asset("eth", "이더리움", "crypto", "USD", "ETH-USD"),
        Asset("gold", "금 (1온스)", "commodity", "USD", "GC=F"),
        Asset("usd", "달러", "fx", "KRW", "KRW=X"),
    ]
)

FX = Asset("usdkrw", "원/달러 환율", "fx", "KRW", "KRW=X")
