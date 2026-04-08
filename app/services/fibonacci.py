from __future__ import annotations

import pandas as pd


def bullish_fib(df: pd.DataFrame, lookback: int = 80) -> dict:
    window = df.tail(lookback)
    low = float(window['low'].min())
    high = float(window['high'].max())
    diff = high - low
    fib_0618 = high - diff * 0.618
    fib_0786 = high - diff * 0.786
    return {
        'anchor_low': low,
        'anchor_high': high,
        'fib_0618': fib_0618,
        'fib_0786': fib_0786,
        'fib_1': low,
    }


def bearish_fib(df: pd.DataFrame, lookback: int = 80) -> dict:
    window = df.tail(lookback)
    low = float(window['low'].min())
    high = float(window['high'].max())
    diff = high - low
    fib_0618 = low + diff * 0.618
    fib_0786 = low + diff * 0.786
    return {
        'anchor_low': low,
        'anchor_high': high,
        'fib_0618': fib_0618,
        'fib_0786': fib_0786,
        'fib_1': high,
    }


def zone_status(price: float, fib_0618: float, fib_0786: float, tolerance_pct: float) -> str:
    lo = min(fib_0618, fib_0786)
    hi = max(fib_0618, fib_0786)
    tol = hi * tolerance_pct / 100.0
    if lo <= price <= hi:
        return 'in_zone'
    if (lo - tol) <= price <= (hi + tol):
        return 'near_zone'
    return 'out_zone'
