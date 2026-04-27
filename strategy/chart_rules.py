from __future__ import annotations
import numpy as np
import pandas as pd


def moving_average_status(df: pd.DataFrame, window: int = 224) -> dict:
    if len(df) < window or "close" not in df:
        return {"pass": False, "ma": None, "reason": "not_enough_data"}
    ma = float(df["close"].rolling(window).mean().iloc[-1])
    close = float(df["close"].iloc[-1])
    return {"pass": close < ma, "ma": round(ma, 2), "close": close}


def double_bottom_status(df: pd.DataFrame, lookback: int = 80, tolerance: float = 0.08) -> dict:
    if len(df) < lookback or "low" not in df:
        return {"pass": False, "reason": "not_enough_data"}
    lows = df["low"].tail(lookback).astype(float)
    # rolling local minima approximation
    local_min = lows[(lows.shift(1) > lows) & (lows.shift(-1) > lows)]
    if len(local_min) < 2:
        return {"pass": False, "reason": "not_enough_local_lows"}
    first_idx = local_min.index[-2]
    second_idx = local_min.index[-1]
    first = float(local_min.iloc[-2])
    second = float(local_min.iloc[-1])
    similar = abs(second - first) / max(first, 1) <= tolerance
    higher_or_similar = second >= first * (1 - tolerance)
    return {
        "pass": bool(similar and higher_or_similar),
        "first_low": round(first, 2),
        "second_low": round(second, 2),
        "first_low_date": str(first_idx.date()) if hasattr(first_idx, "date") else str(first_idx),
        "second_low_date": str(second_idx.date()) if hasattr(second_idx, "date") else str(second_idx),
    }


def concrete_support_status(df: pd.DataFrame, lookback: int = 60) -> dict:
    if len(df) < lookback or not {"close", "high", "low"}.issubset(df.columns):
        return {"pass": False, "reason": "not_enough_data"}
    recent = df.tail(lookback).copy()
    # 공구리: 최근 20일 이전의 단기 고점 돌파 후, 돌파선 부근에서 종가가 버티는 구조
    prior = recent.iloc[:-10]
    last10 = recent.iloc[-10:]
    if prior.empty or last10.empty:
        return {"pass": False, "reason": "insufficient_window"}
    breakout_line = float(prior["high"].max())
    broke = bool((last10["close"] > breakout_line).any())
    current_close = float(recent["close"].iloc[-1])
    support = current_close >= breakout_line * 0.97
    return {
        "pass": bool(broke and support),
        "breakout_line": round(breakout_line, 2),
        "current_close": round(current_close, 2),
        "support_gap_pct": round((current_close / breakout_line - 1) * 100, 2) if breakout_line else None,
    }


def resistance_gap_status(df: pd.DataFrame, target_return: float = 0.10, lookback: int = 120) -> dict:
    if len(df) < 30 or not {"close", "high"}.issubset(df.columns):
        return {"pass": False, "reason": "not_enough_data"}
    recent = df.tail(lookback)
    current = float(df["close"].iloc[-1])
    resistance = float(recent["high"].max())
    gap = resistance / current - 1 if current else 0
    return {
        "pass": bool(gap >= target_return),
        "resistance": round(resistance, 2),
        "gap_pct": round(gap * 100, 2)
    }
