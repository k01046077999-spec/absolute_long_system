from __future__ import annotations

from datetime import datetime, timedelta
from functools import lru_cache
from typing import List
import pandas as pd

try:
    from pykrx import stock
except Exception:  # pragma: no cover
    stock = None


def _yyyymmdd(dt: datetime) -> str:
    return dt.strftime("%Y%m%d")


def _today_yyyymmdd() -> str:
    return _yyyymmdd(datetime.now())


def _start_yyyymmdd(days: int) -> str:
    return _yyyymmdd(datetime.now() - timedelta(days=max(days * 2, days + 30)))


def _recent_dates(max_back_days: int = 14) -> list[str]:
    now = datetime.now()
    return [_yyyymmdd(now - timedelta(days=i)) for i in range(max_back_days + 1)]


@lru_cache(maxsize=4)
def get_tickers(market: str = "ALL") -> List[str]:
    if stock is None:
        return []
    market = market.upper()
    try:
        if market == "ALL":
            kospi = stock.get_market_ticker_list(market="KOSPI")
            kosdaq = stock.get_market_ticker_list(market="KOSDAQ")
            return sorted(set(kospi + kosdaq))
        return stock.get_market_ticker_list(market=market)
    except Exception:
        return []


@lru_cache(maxsize=4096)
def get_ticker_name(ticker: str) -> str:
    if stock is None:
        return ticker
    try:
        return stock.get_market_ticker_name(ticker)
    except Exception:
        return ticker


@lru_cache(maxsize=16)
def get_market_cap_rank(market: str = "ALL", limit: int = 250) -> List[str]:
    if stock is None:
        return []
    frames = []
    markets = ["KOSPI", "KOSDAQ"] if market.upper() == "ALL" else [market.upper()]
    for date in _recent_dates(14):
        frames.clear()
        for m in markets:
            try:
                df = stock.get_market_cap_by_ticker(date, market=m)
                if df is not None and not df.empty:
                    df = df.copy()
                    df["market"] = m
                    frames.append(df)
            except Exception:
                continue
        if frames:
            break
    if not frames:
        tickers = get_tickers(market)
        return tickers[:limit]
    cap = pd.concat(frames)
    sort_col = "거래대금" if "거래대금" in cap.columns else "시가총액" if "시가총액" in cap.columns else None
    if sort_col:
        cap[sort_col] = pd.to_numeric(cap[sort_col], errors="coerce").fillna(0)
        cap = cap.sort_values(sort_col, ascending=False)
    return cap.head(limit).index.astype(str).tolist()


@lru_cache(maxsize=4096)
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
        required = ["open", "high", "low", "close", "volume"]
        if not set(required).issubset(df.columns):
            return pd.DataFrame()
        for col in ["open", "high", "low", "close", "volume", "trading_value", "change_rate"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        if "trading_value" not in df.columns:
            df["trading_value"] = df["close"] * df["volume"]
        keep = ["open", "high", "low", "close", "volume", "trading_value", "change_rate"]
        return df[[c for c in keep if c in df.columns]].dropna(subset=["open", "high", "low", "close", "volume"])
    except Exception:
        return pd.DataFrame()
