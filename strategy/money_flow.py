from __future__ import annotations
import pandas as pd


def money_flow_status(df: pd.DataFrame, min_avg_trading_value: int = 1_000_000_000, mode: str = "main") -> dict:
    if len(df) < 25 or not {"close", "open", "volume", "trading_value"}.issubset(df.columns):
        return {"pass": False, "reason": "not_enough_data"}
    recent = df.tail(20)
    avg_vol = float(recent["volume"].mean())
    avg_value = float(recent["trading_value"].mean())
    last = df.iloc[-1]
    last_vol = float(last["volume"])
    last_value = float(last["trading_value"])
    vol_ratio = last_vol / avg_vol if avg_vol else 0
    value_ratio = last_value / avg_value if avg_value else 0
    is_bullish = float(last["close"]) >= float(last["open"])
    last3_value_up = int((df["trading_value"].tail(3) > avg_value).sum())

    threshold = min_avg_trading_value
    if mode == "sub":
        threshold = int(min_avg_trading_value * 0.5)
    elif mode == "hot":
        threshold = int(min_avg_trading_value * 0.3)

    # 거래대금 기준을 지나치게 높게 잡으면 농사매매법 후보가 대형주 위주로 고착됨.
    # 따라서 main은 10억, sub는 5억, hot은 3억 수준으로 낮추고,
    # 최근 거래대금/거래량 증가 여부를 함께 본다.
    passed = avg_value >= threshold and value_ratio >= 1.05 and vol_ratio >= 1.05 and last3_value_up >= 1
    return {
        "pass": bool(passed),
        "threshold": int(threshold),
        "avg_trading_value_20d": int(avg_value),
        "last_trading_value": int(last_value),
        "value_ratio": round(value_ratio, 2),
        "volume_ratio": round(vol_ratio, 2),
        "bullish_candle": bool(is_bullish),
        "last3_value_above_avg_days": last3_value_up,
    }
