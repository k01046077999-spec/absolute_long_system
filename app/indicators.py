from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional


def sma(values: List[float], period: int) -> List[Optional[float]]:
    out: List[Optional[float]] = [None] * len(values)
    if period <= 0:
        raise ValueError('period must be positive')
    rolling = 0.0
    for i, v in enumerate(values):
        rolling += v
        if i >= period:
            rolling -= values[i - period]
        if i >= period - 1:
            out[i] = rolling / period
    return out


def ema(values: List[float], period: int) -> List[Optional[float]]:
    out: List[Optional[float]] = [None] * len(values)
    if not values:
        return out
    alpha = 2 / (period + 1)
    current = values[0]
    out[0] = current
    for i in range(1, len(values)):
        current = alpha * values[i] + (1 - alpha) * current
        out[i] = current
    return out


def rsi(closes: List[float], period: int = 14) -> List[Optional[float]]:
    if len(closes) < period + 1:
        return [None] * len(closes)
    gains = [0.0]
    losses = [0.0]
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(abs(min(delta, 0.0)))

    avg_gain = sum(gains[1: period + 1]) / period
    avg_loss = sum(losses[1: period + 1]) / period
    out: List[Optional[float]] = [None] * len(closes)

    if avg_loss == 0:
        out[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        out[period] = 100 - (100 / (1 + rs))

    for i in range(period + 1, len(closes)):
        avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
        avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period
        if avg_loss == 0:
            out[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            out[i] = 100 - (100 / (1 + rs))
    return out


@dataclass
class Pivot:
    index: int
    value: float


def pivot_lows(values: List[float], left: int = 3, right: int = 3) -> List[Pivot]:
    out: List[Pivot] = []
    if len(values) < left + right + 1:
        return out
    for i in range(left, len(values) - right):
        center = values[i]
        window = values[i - left: i + right + 1]
        if center == min(window) and window.count(center) == 1:
            out.append(Pivot(index=i, value=center))
    return out


def highest(values: List[float], start: int, end: int) -> float:
    return max(values[start:end])


def lowest(values: List[float], start: int, end: int) -> float:
    return min(values[start:end])


def pct_change(a: float, b: float) -> float:
    if a == 0:
        return 0.0
    return ((b - a) / a) * 100.0


def safe_round(value: Optional[float], digits: int = 4) -> Optional[float]:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return round(value, digits)
