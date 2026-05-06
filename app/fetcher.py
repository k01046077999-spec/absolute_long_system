"""
pykrx를 이용한 한국 주식 데이터 수집 모듈
- KOSPI / KOSDAQ 전 종목 일봉 데이터 수집
- 이동평균선 계산 (5, 20, 60, 112, 224, 448일)
"""

import pandas as pd
import numpy as np
from pykrx import stock
from datetime import datetime, timedelta
import time
import logging

logger = logging.getLogger(__name__)

# 스캔에 필요한 최대 일수 (448일 + 버퍼)
REQUIRED_DAYS = 500
MA_PERIODS = [5, 20, 60, 112, 224, 448]


def get_market_date(offset_days: int = 0) -> str:
    """영업일 기준 날짜 반환 (YYYYMMDD)"""
    d = datetime.today() - timedelta(days=offset_days)
    return d.strftime("%Y%m%d")


def get_all_tickers() -> dict:
    """KOSPI + KOSDAQ 전 종목 티커 및 종목명 반환"""
    today = get_market_date()
    try:
        kospi = stock.get_market_ticker_list(today, market="KOSPI")
        kosdaq = stock.get_market_ticker_list(today, market="KOSDAQ")
        all_tickers = {}
        for t in kospi:
            name = stock.get_market_ticker_name(t)
            all_tickers[t] = {"name": name, "market": "KOSPI"}
        for t in kosdaq:
            name = stock.get_market_ticker_name(t)
            all_tickers[t] = {"name": name, "market": "KOSDAQ"}
        logger.info(f"전체 종목 수: {len(all_tickers)}")
        return all_tickers
    except Exception as e:
        logger.error(f"종목 목록 조회 실패: {e}")
        return {}


def fetch_ohlcv(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """단일 종목 OHLCV 데이터 조회"""
    try:
        df = stock.get_market_ohlcv(start_date, end_date, ticker)
        if df is None or df.empty:
            return pd.DataFrame()
        df.index = pd.to_datetime(df.index)
        df.columns = ["open", "high", "low", "close", "volume", "trading_value", "price_change_sign", "price_change"]
        # 필요한 컬럼만
        df = df[["open", "high", "low", "close", "volume"]].copy()
        df = df[df["close"] > 0]  # 거래 정지 종목 제거
        return df
    except Exception as e:
        logger.debug(f"[{ticker}] OHLCV 조회 실패: {e}")
        return pd.DataFrame()


def calculate_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    """이동평균선 계산"""
    for p in MA_PERIODS:
        df[f"ma{p}"] = df["close"].rolling(window=p, min_periods=p).mean()
    return df


def calculate_volume_ratio(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """거래량 비율 계산 (현재 거래량 / 20일 평균 거래량)"""
    df["vol_avg20"] = df["volume"].rolling(window=period, min_periods=period).mean()
    df["vol_ratio"] = df["volume"] / df["vol_avg20"]
    return df


def fetch_stock_data(ticker: str) -> pd.DataFrame:
    """
    단일 종목 전체 데이터 수집 및 지표 계산
    - 448일선 계산을 위해 충분한 과거 데이터 요청
    """
    end_date = get_market_date()
    # 충분한 영업일 확보를 위해 2.5배 달력일 요청
    start_date = get_market_date(int(REQUIRED_DAYS * 2.5))

    df = fetch_ohlcv(ticker, start_date, end_date)
    if df.empty or len(df) < 60:
        return pd.DataFrame()

    df = calculate_moving_averages(df)
    df = calculate_volume_ratio(df)
    return df


def get_latest_row(df: pd.DataFrame) -> pd.Series | None:
    """데이터프레임의 최신 행 반환 (NaN 없는 행)"""
    valid = df.dropna(subset=["ma5", "ma20", "ma60"])
    if valid.empty:
        return None
    return valid.iloc[-1]


def get_prev_row(df: pd.DataFrame, n: int = 1) -> pd.Series | None:
    """n번째 이전 행 반환"""
    valid = df.dropna(subset=["ma5", "ma20", "ma60"])
    if len(valid) < n + 1:
        return None
    return valid.iloc[-(n + 1)]


def has_maengzip_bong(df: pd.DataFrame, lookback: int = 15) -> bool:
    """
    매집봉 존재 여부 확인
    - 양봉 + 거래량 급증(vol_ratio >= 2.0) + 장대양봉(몸통 >= 3%)
    """
    recent = df.dropna(subset=["vol_ratio"]).tail(lookback)
    for _, row in recent.iterrows():
        is_yang = row["close"] > row["open"]
        body_pct = (row["close"] - row["open"]) / row["open"] * 100 if row["open"] > 0 else 0
        is_big = body_pct >= 3.0
        is_vol = row.get("vol_ratio", 0) >= 2.0
        if is_yang and is_big and is_vol:
            return True
    return False
