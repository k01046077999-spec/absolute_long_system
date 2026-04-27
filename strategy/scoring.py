from __future__ import annotations
from typing import Dict, Any
import pandas as pd

from app.config import settings
from data_sources.krx_loader import get_ticker_name
from data_sources.theme_loader import get_sector_info
from data_sources.dart_loader import financial_health_filter
from strategy.chart_rules import moving_average_status, double_bottom_status, concrete_support_status, resistance_gap_status
from strategy.money_flow import money_flow_status


def evaluate_ticker(ticker: str, df: pd.DataFrame, sector_map: Dict[str, dict], mode: str = "main") -> dict | None:
    if df is None or df.empty or len(df) < 230:
        return None

    fin = financial_health_filter(ticker)
    if fin.get("status") == "FAIL":
        return None

    sector_info = get_sector_info(ticker)
    sector = sector_info["sector"]
    sector_strength = sector_map.get(sector, {
        "sector_score": 0,
        "sector_status": "UNKNOWN",
        "sector_return_3d_pct": None,
        "sector_trading_value_ratio": None,
        "sector_rising_ratio_pct": None,
        "sample_size": 0
    })

    ma = moving_average_status(df)
    db = double_bottom_status(df)
    concrete = concrete_support_status(df)
    resistance = resistance_gap_status(df, target_return=settings.target_return)
    money = money_flow_status(df, min_avg_trading_value=settings.min_avg_trading_value)

    # hard filters: 재무 fail, 거래대금 부족, 섹터 약세, 10% 여유 부족
    if not ma["pass"]:
        return None
    if not money["pass"]:
        return None
    if not resistance["pass"]:
        return None
    if sector_strength["sector_status"] in ["WEAK", "UNKNOWN"] and mode == "main":
        return None

    score = 0
    conditions = []
    risks = []

    if ma["pass"]:
        score += 15; conditions.append("224일선 아래")
    if db["pass"]:
        score += 20; conditions.append("쌍바닥 확인")
    else:
        risks.append("쌍바닥 구조 미흡")
    if concrete["pass"]:
        score += 20; conditions.append("공구리 확인")
    else:
        risks.append("공구리 구조 미흡")
    if money["pass"]:
        score += 20; conditions.append("거래량/거래대금 증가")
    if sector_strength["sector_status"] == "STRONG":
        score += 20; conditions.append("섹터 수급 강함")
    elif sector_strength["sector_status"] == "NEUTRAL":
        score += 10; conditions.append("섹터 수급 중립")
    if resistance["pass"]:
        score += 5; conditions.append("상단 저항까지 10% 이상 여유")

    is_a = db["pass"] and concrete["pass"] and sector_strength["sector_status"] == "STRONG" and score >= 85
    is_b = (db["pass"] or concrete["pass"]) and score >= 65

    if mode == "main" and not is_a:
        return None
    if mode == "sub" and not (is_a or is_b):
        return None

    current = float(df["close"].iloc[-1])
    candidate_type = "A" if is_a else "B"
    decision = "A타입 매수 후보" if candidate_type == "A" else "B타입 관찰/탐색 후보"

    return {
        "strategy": "농사매매법",
        "type": candidate_type,
        "ticker": ticker,
        "name": get_ticker_name(ticker),
        "market": "KRX",
        "sector": sector,
        "themes": sector_info["themes"],
        "current_price": round(current, 2),
        "target_price": round(current * (1 + settings.target_return), 2),
        "target_return": f"{int(settings.target_return * 100)}%",
        "score": int(score),
        "decision": decision,
        "conditions": conditions,
        "risks": risks,
        "metrics": {
            "ma224": ma,
            "double_bottom": db,
            "concrete_support": concrete,
            "money_flow": money,
            "sector_strength": sector_strength,
            "resistance_gap": resistance,
        },
        "financial_health": fin,
    }
