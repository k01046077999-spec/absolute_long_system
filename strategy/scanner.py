from __future__ import annotations
from typing import Dict, List
import pandas as pd

from app.config import settings
from data_sources.krx_loader import get_market_cap_rank, get_ohlcv
from strategy.sector_strength import calc_sector_strength
from strategy.scoring import evaluate_ticker


def _sort_key(item: dict):
    km = item.get("key_metrics", {})
    ma_gap = km.get("ma224_gap_pct")
    near_ma_bonus = 0
    if ma_gap is not None and -5 <= ma_gap < 0:
        near_ma_bonus = 30
    small_mid_bonus = 10 if item.get("group") == "SMALL_MID" else 0
    value_ratio = km.get("value_ratio") or 0
    return (item.get("score", 0) + near_ma_bonus + small_mid_bonus, value_ratio)


def scan(mode: str = "main", limit: int | None = None) -> dict:
    mode = mode.lower()
    if mode not in ["main", "sub", "hot"]:
        mode = "main"
    limit = limit or settings.scan_limit

    warnings: List[str] = []
    errors: List[dict] = []

    try:
        tickers = get_market_cap_rank(settings.scan_market, limit)
    except Exception as e:
        return {"strategy": "농사매매법", "mode": mode, "count": 0, "candidates": [], "warnings": ["종목 리스트/거래대금 순위 데이터를 불러오지 못했습니다."], "errors": [{"stage": "get_market_cap_rank", "message": str(e)}]}

    if not tickers:
        return {"strategy": "농사매매법", "mode": mode, "count": 0, "candidates": [], "warnings": ["pykrx 데이터를 불러오지 못했습니다. Render 네트워크, pykrx 설치 상태, KRX 응답 상태를 확인하세요."], "errors": []}

    frames: Dict[str, pd.DataFrame] = {}
    for ticker in tickers:
        try:
            df = get_ohlcv(ticker, settings.ohlcv_days)
            if df is not None and not df.empty:
                frames[ticker] = df
        except Exception as e:
            errors.append({"stage": "get_ohlcv", "ticker": ticker, "message": str(e)})

    if not frames:
        return {"strategy": "농사매매법", "mode": mode, "count": 0, "candidates": [], "scanned_tickers": len(tickers), "loaded_ohlcv": 0, "warnings": ["종목 리스트는 불러왔지만 OHLCV 데이터가 비어 있습니다."], "errors": errors[:20]}

    try:
        sector_map = calc_sector_strength(frames)
    except Exception as e:
        sector_map = {}
        warnings.append("섹터 강도 계산 실패: 섹터 점수 없이 계속 스캔합니다.")
        errors.append({"stage": "calc_sector_strength", "message": str(e)})

    candidates: List[dict] = []
    for ticker, df in frames.items():
        try:
            item = evaluate_ticker(ticker, df, sector_map, mode=mode)
            if item:
                candidates.append(item)
        except Exception as e:
            errors.append({"stage": "evaluate_ticker", "ticker": ticker, "message": str(e)})

    candidates = sorted(candidates, key=_sort_key, reverse=True)
    if mode in ["sub", "hot"]:
        candidates = candidates[:20]

    note = {
        "main": "main은 엄격한 A타입 실매수 후보만 반환합니다.",
        "sub": "sub는 조건 근접 관찰 후보 TOP 랭킹입니다. 224일선 하단 5% 이내와 중소형주를 우선 노출합니다.",
        "hot": "hot은 224일선 하단 근접·수급 유입·섹터 중립 이상 후보를 빠르게 보는 요약 랭킹입니다.",
    }[mode]
    return {"strategy": "농사매매법", "mode": mode, "count": len(candidates), "note": note, "scanned_tickers": len(tickers), "loaded_ohlcv": len(frames), "candidates": candidates, "warnings": warnings, "errors": errors[:30]}


def scan_single(ticker: str) -> dict:
    df = get_ohlcv(ticker, settings.ohlcv_days)
    if df is None or df.empty:
        return {"error": "no_data", "ticker": ticker}
    frames = {ticker: df}
    try:
        sector_map = calc_sector_strength(frames)
    except Exception:
        sector_map = {}
    item = evaluate_ticker(ticker, df, sector_map, mode="sub")
    return item or {"ticker": ticker, "decision": "조건 미충족", "loaded_ohlcv": len(df)}
