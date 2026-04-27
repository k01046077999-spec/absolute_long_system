from __future__ import annotations

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from strategy.scanner import scan, scan_single

app = FastAPI(
    title="Stock Farming Scanner",
    version="1.0.0",
    description="농사매매법 기반 국내 주식 후보 스캐너"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "service": "stock-farming-scanner",
        "strategy": "농사매매법",
        "version": "1.0.0",
        "endpoints": ["/health", "/main", "/sub", "/scan", "/ticker/{ticker}"]
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "strategy": "농사매매법",
        "target_return": f"{int(settings.target_return * 100)}%",
        "scan_market": settings.scan_market,
        "scan_limit": settings.scan_limit,
        "min_avg_trading_value": settings.min_avg_trading_value,
    }


@app.get("/main")
def main_scan(limit: int = Query(default=settings.scan_limit, ge=10, le=500)):
    return scan(mode="main", limit=limit)


@app.get("/sub")
def sub_scan(limit: int = Query(default=settings.scan_limit, ge=10, le=500)):
    return scan(mode="sub", limit=limit)


@app.get("/scan")
def scan_endpoint(mode: str = Query(default="main", pattern="^(main|sub)$"), limit: int = Query(default=settings.scan_limit, ge=10, le=500)):
    return scan(mode=mode, limit=limit)


@app.get("/ticker/{ticker}")
def ticker_scan(ticker: str):
    return scan_single(ticker.zfill(6))
