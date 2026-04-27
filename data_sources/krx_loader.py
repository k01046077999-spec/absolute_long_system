from __future__ import annotations

from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import List
import ast
import json
import re

import pandas as pd
import requests

try:
    from pykrx import stock
except Exception:  # pragma: no cover
    stock = None

BASE_DIR = Path(__file__).resolve().parents[1]
SEED_TICKER_PATH = BASE_DIR / "data" / "seed_tickers.json"


def _yyyymmdd(dt: datetime) -> str:
    return dt.strftime("%Y%m%d")


def _today_yyyymmdd() -> str:
    return _yyyymmdd(datetime.now())


def _start_yyyymmdd(days: int) -> str:
    return _yyyymmdd(datetime.now() - timedelta(days=max(days * 2, days + 30)))


def _recent_dates(max_back_days: int = 14) -> list[str]:
    now = datetime.now()
    return [_yyyymmdd(now - timedelta(days=i)) for i in range(max_back_days + 1)]


def _load_seed_tickers(limit: int | None = None) -> List[str]:
    try:
        payload = json.loads(SEED_TICKER_PATH.read_text(encoding="utf-8"))
        tickers = [str(t).zfill(6) for t in payload.get("tickers", [])]
        return tickers[:limit] if limit else tickers
    except Exception:
        return []


@lru_cache(maxsize=4)
def get_tickers(market: str = "ALL") -> List[str]:
    if stock is not None:
        market = market.upper()
        try:
            if market == "ALL":
                kospi = stock.get_market_ticker_list(market="KOSPI")
                kosdaq = stock.get_market_ticker_list(market="KOSDAQ")
                tickers = sorted(set(kospi + kosdaq))
            else:
                tickers = stock.get_market_ticker_list(market=market)
            if tickers:
                return [str(t).zfill(6) for t in tickers]
        except Exception:
            pass
    return _load_seed_tickers()


@lru_cache(maxsize=4096)
def get_ticker_name(ticker: str) -> str:
    ticker = str(ticker).zfill(6)
    if stock is not None:
        try:
            name = stock.get_market_ticker_name(ticker)
            if name:
                return name
        except Exception:
            pass
    return ticker


@lru_cache(maxsize=16)
def get_market_cap_rank(market: str = "ALL", limit: int = 250) -> List[str]:
    if stock is not None:
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
                try:
                    cap = pd.concat(frames)
                    sort_col = "거래대금" if "거래대금" in cap.columns else "시가총액" if "시가총액" in cap.columns else None
                    if sort_col:
                        cap[sort_col] = pd.to_numeric(cap[sort_col], errors="coerce").fillna(0)
                        cap = cap.sort_values(sort_col, ascending=False)
                    tickers = cap.head(limit).index.astype(str).str.zfill(6).tolist()
                    if tickers:
                        return tickers
                except Exception:
                    pass
    return _load_seed_tickers(limit)


def _parse_naver_sise_json(text: str) -> pd.DataFrame:
    text = text.strip()
    match = re.search(r"\[\s*\[.*\]\s*\]", text, flags=re.S)
    if not match:
        return pd.DataFrame()
    raw = match.group(0).replace("null", "None")
    try:
        rows = ast.literal_eval(raw)
    except Exception:
        return pd.DataFrame()
    if not rows or len(rows) < 2:
        return pd.DataFrame()
    header = rows[0]
    body = rows[1:]
    df = pd.DataFrame(body, columns=header)
    df = df.rename(columns={"날짜": "date", "시가": "open", "고가": "high", "저가": "low", "종가": "close", "거래량": "volume"})
    required = ["date", "open", "high", "low", "close", "volume"]
    if not set(required).issubset(df.columns):
        return pd.DataFrame()
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d", errors="coerce")
    df = df.dropna(subset=["date"]).set_index("date")
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["open", "high", "low", "close", "volume"])
    df["trading_value"] = df["close"] * df["volume"]
    df["change_rate"] = df["close"].pct_change() * 100
    return df[["open", "high", "low", "close", "volume", "trading_value", "change_rate"]]


def _get_ohlcv_from_naver(ticker: str, days: int = 320) -> pd.DataFrame:
    start = _start_yyyymmdd(days)
    end = _today_yyyymmdd()
    url = "https://api.finance.naver.com/siseJson.naver"
    params = {"symbol": str(ticker).zfill(6), "requestType": "1", "startTime": start, "endTime": end, "timeframe": "day"}
    headers = {"User-Agent": "Mozilla/5.0", "Referer": f"https://finance.naver.com/item/sise_day.naver?code={ticker}"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=12)
        if resp.status_code != 200 or not resp.text:
            return pd.DataFrame()
        return _parse_naver_sise_json(resp.text)
    except Exception:
        return pd.DataFrame()


@lru_cache(maxsize=4096)
def get_ohlcv(ticker: str, days: int = 320) -> pd.DataFrame:
    ticker = str(ticker).zfill(6)
    if stock is not None:
        start = _start_yyyymmdd(days)
        end = _today_yyyymmdd()
        try:
            df = stock.get_market_ohlcv_by_date(start, end, ticker)
            if df is not None and not df.empty:
                df = df.rename(columns={"시가": "open", "고가": "high", "저가": "low", "종가": "close", "거래량": "volume", "거래대금": "trading_value", "등락률": "change_rate"})
                required = ["open", "high", "low", "close", "volume"]
                if set(required).issubset(df.columns):
                    for col in ["open", "high", "low", "close", "volume", "trading_value", "change_rate"]:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors="coerce")
                    if "trading_value" not in df.columns:
                        df["trading_value"] = df["close"] * df["volume"]
                    keep = ["open", "high", "low", "close", "volume", "trading_value", "change_rate"]
                    out = df[[c for c in keep if c in df.columns]].dropna(subset=["open", "high", "low", "close", "volume"])
                    if not out.empty:
                        return out
        except Exception:
            pass
    return _get_ohlcv_from_naver(ticker, days)
