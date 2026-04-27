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

    tickers = get_market_cap_rank(settings.scan_market, limit)
    warnings = []
    if not tickers:
        return {
            "strategy": "농사매매법",
            "mode": mode,
            "count": 0,
            "candidates": [],
            "warnings": ["pykrx 데이터를 불러오지 못했습니다. 로컬/Render 네트워크 또는 pykrx 설치 상태를 확인하세요."]
        }

    frames: Dict[str, pd.DataFrame] = {}
    for ticker in tickers:
        df = get_ohlcv(ticker, settings.ohlcv_days)
        if df is not None and not df.empty:
            frames[ticker] = df

    sector_map = calc_sector_strength(frames)
    candidates: List[dict] = []
    for ticker, df in frames.items():
        item = evaluate_ticker(ticker, df, sector_map, mode=mode)
        if item:
            candidates.append(item)

    candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)
    return {
        "strategy": "농사매매법",
        "mode": mode,
        "count": len(candidates),
        "candidates": candidates,
        "warnings": warnings
    }


def scan_single(ticker: str) -> dict:
    df = get_ohlcv(ticker, settings.ohlcv_days)
    if df is None or df.empty:
        return {"error": "no_data", "ticker": ticker}
    frames = {ticker: df}
    sector_map = calc_sector_strength(frames)
    item = evaluate_ticker(ticker, df, sector_map, mode="sub")
    return item or {"ticker": ticker, "decision": "조건 미충족"}
