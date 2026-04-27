from __future__ import annotations
from collections import defaultdict
from typing import Dict, List
import pandas as pd

from data_sources.theme_loader import get_sector_info


def calc_sector_strength(symbol_frames: Dict[str, pd.DataFrame]) -> Dict[str, dict]:
    groups = defaultdict(list)
    for ticker, df in symbol_frames.items():
        sector = get_sector_info(ticker)["sector"]
        if sector == "UNKNOWN" or len(df) < 6:
            continue
        try:
            close = df["close"].astype(float)
            value = df["trading_value"].astype(float)
            ret3 = close.iloc[-1] / close.iloc[-4] - 1
            avg20 = value.tail(20).mean() if len(value) >= 20 else value.mean()
            val_ratio = value.tail(3).mean() / avg20 if avg20 else 0
            up = close.iloc[-1] > close.iloc[-2]
            groups[sector].append((ret3, val_ratio, up))
        except Exception:
            continue

    result = {}
    for sector, rows in groups.items():
        if not rows:
            continue
        ret3 = sum(r[0] for r in rows) / len(rows)
        val_ratio = sum(r[1] for r in rows) / len(rows)
        rising_ratio = sum(1 for r in rows if r[2]) / len(rows)
        score = 0
        score += 35 if ret3 > 0.03 else 25 if ret3 > 0 else 10
        score += 35 if val_ratio > 1.5 else 25 if val_ratio > 1.1 else 10
        score += 30 if rising_ratio >= 0.6 else 20 if rising_ratio >= 0.45 else 5
        status = "STRONG" if score >= 75 else "NEUTRAL" if score >= 55 else "WEAK"
        result[sector] = {
            "sector_score": int(score),
            "sector_status": status,
            "sector_return_3d_pct": round(ret3 * 100, 2),
            "sector_trading_value_ratio": round(val_ratio, 2),
            "sector_rising_ratio_pct": round(rising_ratio * 100, 2),
            "sample_size": len(rows)
        }
    return result
