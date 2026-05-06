"""
pykrx 1.2.x 기반 한국 주식 데이터 수집 모듈
- KOSPI / KOSDAQ 전 종목 일봉 데이터 수집
- 이동평균선 계산 (5, 20, 60, 112, 224, 448일)
"""

import pandas as pd
import numpy as np
from pykrx import stock
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

REQUIRED_DAYS = 500
MA_PERIODS = [5, 20, 60, 112, 224, 448]


def get_market_date(offset_days: int = 0) -> str:
    """달력일 기준 날짜 반환 (YYYYMMDD)"""
    d = datetime.today() - timedelta(days=offset_days)
    return d.strftime("%Y%m%d")


def get_all_tickers() -> dict:
    """
    KOSPI + KOSDAQ 전 종목 티커 및 종목명 반환
    pykrx 1.2.x: get_market_ticker_list 날짜를 가장 최근 영업일로 fallback
    """
    today = get_market_date()
    all_tickers = {}
    try:
        for market in ["KOSPI", "KOSDAQ"]:
            tickers = stock.get_market_ticker_list(today, market=market)
            if not tickers:
                # 오늘 데이터 없으면 전일 시도 (주말/공휴일)
                tickers = stock.get_market_ticker_list(get_market_date(1), market=market)
            if not tickers:
                tickers = stock.get_market_ticker_list(get_market_date(3), market=market)
            for t in tickers:
                try:
                    name = stock.get_market_ticker_name(t)
                except Exception:
                    name = t
                all_tickers[t] = {"name": name, "market": market}
        logger.info(f"전체 종목 수: {len(all_tickers)}")
    except Exception as e:
        logger.error(f"종목 목록 조회 실패: {e}")
    return all_tickers


def fetch_ohlcv(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    단일 종목 OHLCV 데이터 조회
    pykrx 1.2.x 컬럼: 시가/고가/저가/종가/거래량/거래대금/등락률
    """
    try:
        df = stock.get_market_ohlcv(start_date, end_date, ticker)
        if df is None or df.empty:
            return pd.DataFrame()

        df.index = pd.to_datetime(df.index)

        # pykrx 버전별 컬럼 정규화
        col_map = {}
        for col in df.columns:
            c = str(col)
            if "시가" in c:   col_map[col] = "open"
            elif "고가" in c: col_map[col] = "high"
            elif "저가" in c: col_map[col] = "low"
            elif "종가" in c: col_map[col] = "close"
            elif "거래량" in c: col_map[col] = "volume"
        df = df.rename(columns=col_map)

        needed = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
        if "close" not in needed or "volume" not in needed:
            return pd.DataFrame()

        df = df[needed].copy()
        df = df[df["close"] > 0]
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
    """단일 종목 전체 데이터 수집 및 지표 계산"""
    end_date = get_market_date()
    start_date = get_market_date(int(REQUIRED_DAYS * 2.5))

    df = fetch_ohlcv(ticker, start_date, end_date)
    if df.empty or len(df) < 60:
        return pd.DataFrame()

    df = calculate_moving_averages(df)
    df = calculate_volume_ratio(df)
    return df


def get_latest_row(df: pd.DataFrame) -> pd.Series | None:
    """최신 유효 행 반환"""
    valid = df.dropna(subset=["ma5", "ma20", "ma60"])
    if valid.empty:
        return None
    return valid.iloc[-1]


def get_prev_row(df: pd.DataFrame, n: int = 1) -> pd.Series | None:
    """n번째 이전 유효 행 반환"""
    valid = df.dropna(subset=["ma5", "ma20", "ma60"])
    if len(valid) < n + 1:
        return None
    return valid.iloc[-(n + 1)]


def has_maengzip_bong(df: pd.DataFrame, lookback: int = 15) -> bool:
    """
    매집봉 존재 여부 확인
    - 양봉 + 거래량 급증(vol_ratio >= 2.0) + 장대양봉(몸통 >= 3%)
    """
    if "open" not in df.columns:
        return False
    recent = df.dropna(subset=["vol_ratio"]).tail(lookback)
    for _, row in recent.iterrows():
        open_p = row.get("open", 0)
        close_p = row.get("close", 0)
        if open_p <= 0:
            continue
        is_yang = close_p > open_p
        body_pct = (close_p - open_p) / open_p * 100
        is_big = body_pct >= 3.0
        is_vol = float(row.get("vol_ratio", 0) or 0) >= 2.0
        if is_yang and is_big and is_vol:
            return True
    return False
