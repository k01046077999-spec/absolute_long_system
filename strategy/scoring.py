from __future__ import annotations
from typing import Dict
import pandas as pd

from app.config import settings
from data_sources.krx_loader import get_ticker_name
from data_sources.theme_loader import get_sector_info
from data_sources.dart_loader import financial_health_filter
from strategy.chart_rules import moving_average_status, double_bottom_status, concrete_support_status, resistance_gap_status
from strategy.money_flow import money_flow_status

LARGE_CAP_NAMES = {"삼성전자", "SK하이닉스", "NAVER", "카카오", "현대차", "기아", "셀트리온", "LG에너지솔루션", "삼성바이오로직스", "POSCO홀딩스"}


def _ma224_gap_pct(ma: dict) -> float | None:
    if not ma.get("ma") or not ma.get("close"):
        return None
    return round((float(ma["close"]) / float(ma["ma"]) - 1) * 100, 2)


def evaluate_ticker(ticker: str, df: pd.DataFrame, sector_map: Dict[str, dict], mode: str = "main") -> dict | None:
    """main=A타입 실매수 후보, sub=관찰 후보, hot=224일선 근접·수급 우선 후보."""
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
        "sample_size": 0,
    })

    ma = moving_average_status(df)
    db = double_bottom_status(df)
    concrete = concrete_support_status(df)
    resistance = resistance_gap_status(df, target_return=settings.target_return)
    money = money_flow_status(df, min_avg_trading_value=settings.min_avg_trading_value, mode=mode)
    ma_gap_pct = _ma224_gap_pct(ma)

    name = get_ticker_name(ticker)
    is_large_cap = name in LARGE_CAP_NAMES

    score = 0
    conditions, risks, reject_flags = [], [], []

    if ma["pass"]:
        score += 15; conditions.append("224일선 아래")
        if ma_gap_pct is not None and -5 <= ma_gap_pct < 0:
            score += 10; conditions.append("224일선 하단 5% 이내 우선권")
    else:
        reject_flags.append("224일선 아래 미충족"); risks.append("농사매매법 핵심 조건인 224일선 아래 미충족")

    if db["pass"]:
        score += 20; conditions.append("쌍바닥 확인")
    else:
        reject_flags.append("쌍바닥 미충족"); risks.append("쌍바닥 구조 미흡")

    if concrete["pass"]:
        score += 20; conditions.append("공구리 확인")
    else:
        reject_flags.append("공구리 미충족"); risks.append("공구리 구조 미흡")

    if money["pass"]:
        score += 20; conditions.append("거래량/거래대금 증가")
    else:
        reject_flags.append("거래대금/거래량 기준 미충족"); risks.append("수급 유입 약함 또는 평균 거래대금 부족")

    if sector_strength["sector_status"] == "STRONG":
        score += 20; conditions.append("섹터 수급 강함")
    elif sector_strength["sector_status"] == "NEUTRAL":
        score += 10; conditions.append("섹터 수급 중립")
    else:
        reject_flags.append("섹터 수급 약함/미확인"); risks.append("섹터 수급 약함 또는 섹터 샘플 부족")

    if resistance["pass"]:
        score += 5; conditions.append("상단 저항까지 10% 이상 여유")
    else:
        reject_flags.append("10% 상승 여력 부족"); risks.append("상단 저항까지 목표수익률 여유 부족")

    # 대형주는 별도 그룹으로 분리. main 실매수 후보에서는 배제하지 않되 우선순위 감점.
    if is_large_cap:
        score -= 10
        risks.append("대형주 그룹: 농사매매법 단기 10% 회전 속도는 중소형주보다 느릴 수 있음")

    is_a = (
        ma["pass"] and db["pass"] and concrete["pass"] and money["pass"]
        and resistance["pass"] and sector_strength["sector_status"] == "STRONG" and score >= 85
    )
    is_b = (
        ma["pass"] and (db["pass"] or concrete["pass"])
        and (money["pass"] or sector_strength["sector_status"] in ["STRONG", "NEUTRAL"])
        and score >= 55
    )

    if mode == "main" and not is_a:
        return None
    if mode == "sub" and score < 25:
        return None
    if mode == "hot":
        near_ma = ma_gap_pct is not None and -7 <= ma_gap_pct < 0
        if not (near_ma or money["pass"] or sector_strength["sector_status"] in ["STRONG", "NEUTRAL"]):
            return None

    current = float(df["close"].iloc[-1])
    if is_a:
        candidate_type, decision = "A", "A타입 매수 후보"
    elif is_b:
        candidate_type, decision = "B", "B타입 관찰/탐색 후보"
    else:
        candidate_type, decision = "WATCH", "관찰 후보: 조건 일부 근접, 즉시 매수 후보 아님"

    return {
        "strategy": "농사매매법",
        "type": candidate_type,
        "ticker": ticker,
        "name": name,
        "market": "KRX",
        "group": "LARGE_CAP" if is_large_cap else "SMALL_MID",
        "sector": sector,
        "themes": sector_info["themes"],
        "current_price": round(current, 2),
        "target_price": round(current * (1 + settings.target_return), 2),
        "target_return": f"{int(settings.target_return * 100)}%",
        "score": int(score),
        "decision": decision,
        "conditions": conditions,
        "risks": risks[:6],
        "reject_flags": reject_flags[:8],
        "key_metrics": {
            "ma224_gap_pct": ma_gap_pct,
            "value_ratio": money.get("value_ratio"),
            "avg_trading_value_20d": money.get("avg_trading_value_20d"),
            "sector_status": sector_strength.get("sector_status"),
            "resistance_gap_pct": resistance.get("gap_pct"),
        },
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
