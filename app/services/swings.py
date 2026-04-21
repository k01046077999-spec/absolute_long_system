from __future__ import annotations

import pandas as pd


def find_swings(df: pd.DataFrame, window: int = 2) -> pd.DataFrame:
    """스윙 고점/저점 마킹 (좌우 window개 봉 대비 극값)"""
    out = df.copy()
    out["swing_high"] = False
    out["swing_low"]  = False
    highs = out["high"]
    lows  = out["low"]

    for i in range(window, len(out) - window):
        local_highs = highs.iloc[i - window: i + window + 1]
        local_lows  = lows.iloc[i - window: i + window + 1]
        if highs.iloc[i] == local_highs.max():
            out.iloc[i, out.columns.get_loc("swing_high")] = True
        if lows.iloc[i] == local_lows.min():
            out.iloc[i, out.columns.get_loc("swing_low")] = True
    return out


def latest_swing_lows(df: pd.DataFrame, count: int = 4) -> pd.DataFrame:
    return df[df["swing_low"]].tail(count).copy()


def latest_swing_highs(df: pd.DataFrame, count: int = 4) -> pd.DataFrame:
    return df[df["swing_high"]].tail(count).copy()
