from __future__ import annotations
from typing import Dict, List
import pandas as pd

from app.config import settings
from data_sources.krx_loader import get_market_cap_rank, get_ohlcv
from strategy.sector_strength import calc_sector_strength
from strategy.scoring import evaluate_ticker


def scan(mode: str = "main", limit: int | None = None) -> dict:
    mode = mode.lower()
    if mode not in ["main", "sub"]:
        mode = "main"
    limit = limit or settings.scan_limit

    warnings: List[str] = []
    errors: List[dict] = []

    try:
        tickers = get_market_cap_rank(settings.scan_market, limit)
    except Exception as e:
        return {
            "strategy": "농사매매법",
            "mode": mode,
            "count": 0,
            "candidates": [],
            "warnings": ["종목 리스트/거래대금 순위 데이터를 불러오지 못했습니다."],
            "errors": [{"stage": "get_market_cap_rank", "message": str(e)}]
        }

    if not tickers:
        return {
            "strategy": "농사매매법",
            "mode": mode,
            "count": 0,
            "candidates": [],
            "warnings": ["pykrx 데이터를 불러오지 못했습니다. Render 네트워크, pykrx 설치 상태, KRX 응답 상태를 확인하세요."],
            "errors": []
        }

    frames: Dict[str, pd.DataFrame] = {}
    for ticker in tickers:
        try:
            df = get_ohlcv(ticker, settings.ohlcv_days)
            if df is not None and not df.empty:
                frames[ticker] = df
        except Exception as e:
            errors.append({"stage": "get_ohlcv", "ticker": ticker, "message": str(e)})
            continue

    if not frames:
        return {
            "strategy": "농사매매법",
            "mode": mode,
            "count": 0,
            "candidates": [],
            "scanned_tickers": len(tickers),
            "loaded_ohlcv": 0,
            "warnings": ["종목 리스트는 불러왔지만 OHLCV 데이터가 비어 있습니다."],
            "errors": errors[:20]
        }

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
            continue

    candidates = sorted(candidates, key=lambda x: x.get("score", 0), reverse=True)
    if mode == "sub":
        candidates = candidates[:20]
    return {
        "strategy": "농사매매법",
        "mode": mode,
        "count": len(candidates),
        "note": "main은 엄격한 실매수 후보, sub는 조건 근접 관찰 후보 TOP 랭킹입니다." if mode == "sub" else "main은 엄격한 A타입 실매수 후보만 반환합니다.",
        "scanned_tickers": len(tickers),
        "loaded_ohlcv": len(frames),
        "candidates": candidates,
        "warnings": warnings,
        "errors": errors[:30]
    }


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
