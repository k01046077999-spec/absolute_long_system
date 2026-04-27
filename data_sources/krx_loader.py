from __future__ import annotations

from datetime import datetime, timedelta
from functools import lru_cache
from typing import List, Dict
import pandas as pd

try:
    from pykrx import stock
except Exception:  # pragma: no cover
    stock = None


def _today_yyyymmdd() -> str:
    return datetime.now().strftime("%Y%m%d")


def _start_yyyymmdd(days: int) -> str:
    return (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")


@lru_cache(maxsize=4)
def get_tickers(market: str = "ALL") -> List[str]:
    if stock is None:
        return []
    market = market.upper()
    if market == "ALL":
        return sorted(set(stock.get_market_ticker_list(market="KOSPI") + stock.get_market_ticker_list(market="KOSDAQ")))
    return stock.get_market_ticker_list(market=market)


@lru_cache(maxsize=4096)
def get_ticker_name(ticker: str) -> str:
    if stock is None:
        return ticker
    try:
        return stock.get_market_ticker_name(ticker)
    except Exception:
        return ticker


@lru_cache(maxsize=4)
def get_market_cap_rank(market: str = "ALL", limit: int = 250) -> List[str]:
    if stock is None:
        return []
    today = _today_yyyymmdd()
    frames = []
    for m in (["KOSPI", "KOSDAQ"] if market.upper() == "ALL" else [market.upper()]):
        try:
            df = stock.get_market_cap_by_ticker(today, market=m)
            if df is not None and not df.empty:
                frames.append(df)
        except Exception:
            continue
    if not frames:
        return get_tickers(market)[:limit]
    cap = pd.concat(frames)
    if "거래대금" in cap.columns:
        cap = cap.sort_values("거래대금", ascending=False)
    elif "시가총액" in cap.columns:
        cap = cap.sort_values("시가총액", ascending=False)
    return cap.head(limit).index.astype(str).tolist()


@lru_cache(maxsize=2048)
def get_ohlcv(ticker: str, days: int = 320) -> pd.DataFrame:
    if stock is None:
        return pd.DataFrame()
    start = _start_yyyymmdd(days)
    end = _today_yyyymmdd()
    try:
        df = stock.get_market_ohlcv_by_date(start, end, ticker)
        if df is None or df.empty:
            return pd.DataFrame()
        df = df.rename(columns={
            "시가": "open", "고가": "high", "저가": "low", "종가": "close",
            "거래량": "volume", "거래대금": "trading_value", "등락률": "change_rate"
        })
        return df[[c for c in ["open", "high", "low", "close", "volume", "trading_value", "change_rate"] if c in df.columns]].dropna()
    except Exception:
        return pd.DataFrame()
