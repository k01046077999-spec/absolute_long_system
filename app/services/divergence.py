from __future__ import annotations

"""
제이드 파동 심화 이론 — 다이버전스 감지 엔진
================================================
PDF 핵심 규칙:
  - RSI 지표가 과매수(상단 점선) / 과매도(하단 점선) 구간을 돌파하는 시점에서만 다이버전스 판단
  - 최소 3개 꼭지점 연계(chain)가 가장 강력한 신호
  - 지수 고점 상승 + RSI 고점 하락 → 하락 다이버전스 (숏)
  - 지수 저점 하락 + RSI 저점 상승 → 상승 다이버전스 (롱)
"""

import pandas as pd

# RSI 임계값 (PDF 기준: 점선 = 과매수/과매도 영역)
EXTREME_OVERSOLD   = 38   # 1차 과매도 경계
STRONG_OVERSOLD    = 30   # 2차 강 과매도 경계 (쾅 구간)
EXTREME_OVERBOUGHT = 62   # 1차 과매수 경계
STRONG_OVERBOUGHT  = 70   # 2차 강 과매수 경계 (쾅 구간)

# 다이버전스 최소 요건
MIN_PRICE_MOVE_PCT = 0.15   # 가격 최소 이동 %
MIN_RSI_MOVE       = 1.0    # RSI 최소 이동폭
MIN_BAR_GAP        = 1      # 꼭지점 간 최소 봉 거리


def _bar_gap_ok(swings: pd.DataFrame) -> bool:
    """꼭지점 간 최소 봉 간격 확인"""
    if len(swings) < 2:
        return False
    idx = list(swings.index)
    return all((idx[i] - idx[i - 1]) >= MIN_BAR_GAP for i in range(1, len(idx)))


def _pct_change(a: float, b: float) -> float:
    if a == 0:
        return 0.0
    return abs((b - a) / a) * 100.0


# ─────────────────────────────────────────────────────────────
#  상승 다이버전스 감지 (롱 신호)
#  지수 저점 하락 + RSI 저점 상승
# ─────────────────────────────────────────────────────────────
def detect_bullish_divergence_chain(swings: pd.DataFrame) -> dict:
    """
    PDF 핵심 규칙:
      - RSI가 과매도 구간('쾅' 하락)에서 형성된 저점에서만 판단
      - 2점 다이버전스: general
      - 3점 연계 다이버전스: chain (가장 강력)
    """
    if len(swings) < 2:
        return {
            "found": False, "general": False, "chain": False,
            "extreme": False, "strong_extreme": False, "strength": 0.0,
        }

    last2 = swings.tail(2).copy()
    last3 = swings.tail(3).copy()

    p2 = last2["low"].tolist()
    r2 = last2["rsi"].tolist()
    price_move_2 = _pct_change(p2[0], p2[-1])
    rsi_move_2   = r2[-1] - r2[0]

    # 2점 일반 다이버전스
    general = (
        p2[-1] < p2[-2]            # 지수 저점 하락
        and r2[-1] > r2[-2]        # RSI 저점 상승
        and price_move_2 >= MIN_PRICE_MOVE_PCT
        and rsi_move_2 >= MIN_RSI_MOVE
        and _bar_gap_ok(last2)
    )

    # 3점 연계 다이버전스 (PDF에서 가장 강조)
    chain = False
    chain_strength = 0.0
    if len(last3) >= 3:
        p3 = last3["low"].tolist()
        r3 = last3["rsi"].tolist()
        price_move_3 = _pct_change(p3[0], p3[-1])
        rsi_move_3   = r3[-1] - r3[0]
        chain = (
            p3[-1] <= p3[-2] <= p3[-3]   # 3개 저점 순차 하락
            and r3[-1] >= r3[-2] >= r3[-3]  # 3개 RSI 순차 상승
            and price_move_3 >= MIN_PRICE_MOVE_PCT
            and rsi_move_3 >= MIN_RSI_MOVE
            and _bar_gap_ok(last3)
        )
        if chain:
            chain_strength += min(price_move_3 * 1.2, 8.0)
            chain_strength += min(rsi_move_3 * 0.8, 10.0)

    # 극단값 (RSI 점선 돌파 여부) — PDF에서 "쾅 하는 구간"
    extreme_rsi   = float(last3["rsi"].min()) if len(last3) >= 3 else float(last2["rsi"].min())
    extreme       = extreme_rsi <= EXTREME_OVERSOLD   # 점선 이하
    strong_extreme = extreme_rsi <= STRONG_OVERSOLD   # 강 과매도 (쾅)

    # 강도 계산
    strength = 0.0
    if general:
        strength += 12.0 + min(price_move_2, 6.0) + min(rsi_move_2, 8.0)
    if chain:
        strength += 20.0 + chain_strength
    if extreme:
        strength += 6.0
    if strong_extreme:
        strength += 5.0

    return {
        "found": general or chain,
        "general": general,
        "chain": chain,
        "extreme": extreme,
        "strong_extreme": strong_extreme,
        "strength": round(strength, 2),
        "price_points": last3["low"].tolist() if len(last3) >= 3 else last2["low"].tolist(),
        "rsi_points":   last3["rsi"].tolist() if len(last3) >= 3 else last2["rsi"].tolist(),
        "bar_indices":  list(last3.index) if len(last3) >= 3 else list(last2.index),
        "extreme_rsi":  round(extreme_rsi, 2),
    }


# ─────────────────────────────────────────────────────────────
#  하락 다이버전스 감지 (숏 신호)
#  지수 고점 상승 + RSI 고점 하락
# ─────────────────────────────────────────────────────────────
def detect_bearish_divergence_chain(swings: pd.DataFrame) -> dict:
    """
    PDF 핵심 규칙:
      - RSI가 과매수 구간('쾅' 상승)에서 형성된 고점에서만 판단
    """
    if len(swings) < 2:
        return {
            "found": False, "general": False, "chain": False,
            "extreme": False, "strong_extreme": False, "strength": 0.0,
        }

    last2 = swings.tail(2).copy()
    last3 = swings.tail(3).copy()

    p2 = last2["high"].tolist()
    r2 = last2["rsi"].tolist()
    price_move_2 = _pct_change(p2[0], p2[-1])
    rsi_move_2   = r2[0] - r2[-1]

    general = (
        p2[-1] > p2[-2]
        and r2[-1] < r2[-2]
        and price_move_2 >= MIN_PRICE_MOVE_PCT
        and rsi_move_2 >= MIN_RSI_MOVE
        and _bar_gap_ok(last2)
    )

    chain = False
    chain_strength = 0.0
    if len(last3) >= 3:
        p3 = last3["high"].tolist()
        r3 = last3["rsi"].tolist()
        price_move_3 = _pct_change(p3[0], p3[-1])
        rsi_move_3   = r3[0] - r3[-1]
        chain = (
            p3[-1] >= p3[-2] >= p3[-3]
            and r3[-1] <= r3[-2] <= r3[-3]
            and price_move_3 >= MIN_PRICE_MOVE_PCT
            and rsi_move_3 >= MIN_RSI_MOVE
            and _bar_gap_ok(last3)
        )
        if chain:
            chain_strength += min(price_move_3 * 1.2, 8.0)
            chain_strength += min(rsi_move_3 * 0.8, 10.0)

    extreme_rsi    = float(last3["rsi"].max()) if len(last3) >= 3 else float(last2["rsi"].max())
    extreme        = extreme_rsi >= EXTREME_OVERBOUGHT
    strong_extreme = extreme_rsi >= STRONG_OVERBOUGHT

    strength = 0.0
    if general:
        strength += 12.0 + min(price_move_2, 6.0) + min(rsi_move_2, 8.0)
    if chain:
        strength += 20.0 + chain_strength
    if extreme:
        strength += 6.0
    if strong_extreme:
        strength += 5.0

    return {
        "found": general or chain,
        "general": general,
        "chain": chain,
        "extreme": extreme,
        "strong_extreme": strong_extreme,
        "strength": round(strength, 2),
        "price_points": last3["high"].tolist() if len(last3) >= 3 else last2["high"].tolist(),
        "rsi_points":   last3["rsi"].tolist() if len(last3) >= 3 else last2["rsi"].tolist(),
        "bar_indices":  list(last3.index) if len(last3) >= 3 else list(last2.index),
        "extreme_rsi":  round(extreme_rsi, 2),
    }
