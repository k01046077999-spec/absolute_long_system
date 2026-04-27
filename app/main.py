from __future__ import annotations

import traceback
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.utils import to_builtin
from strategy.scanner import scan, scan_single

app = FastAPI(
    title="Stock Farming Scanner",
    version="1.1.0",
    description="농사매매법 기반 국내 주식 후보 스캐너"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def safe_response(payload, status_code: int = 200):
    return JSONResponse(content=to_builtin(payload), status_code=status_code)


@app.get("/")
def root():
    return safe_response({
        "service": "stock-farming-scanner",
        "strategy": "농사매매법",
        "version": "1.1.0",
        "endpoints": ["/health", "/main", "/sub", "/scan", "/ticker/{ticker}", "/debug"]
    })


@app.get("/health")
def health():
    return safe_response({
        "status": "ok",
        "strategy": "농사매매법",
        "target_return": f"{int(settings.target_return * 100)}%",
        "scan_market": settings.scan_market,
        "scan_limit": settings.scan_limit,
        "min_avg_trading_value": settings.min_avg_trading_value,
        "version": "1.1.0"
    })


@app.get("/main")
def main_scan(limit: int = Query(default=settings.scan_limit, ge=1, le=500)):
    try:
        return safe_response(scan(mode="main", limit=limit))
    except Exception as e:
        return safe_response({
            "status": "error",
            "endpoint": "/main",
            "message": str(e),
            "trace_tail": traceback.format_exc().splitlines()[-8:],
            "hint": "Render 로그와 pykrx/KRX 응답 상태를 확인하세요. v1.1은 500 대신 진단 JSON을 반환합니다."
        }, status_code=200)


@app.get("/sub")
def sub_scan(limit: int = Query(default=settings.scan_limit, ge=1, le=500)):
    try:
        return safe_response(scan(mode="sub", limit=limit))
    except Exception as e:
        return safe_response({
            "status": "error",
            "endpoint": "/sub",
            "message": str(e),
            "trace_tail": traceback.format_exc().splitlines()[-8:],
            "hint": "Render 로그와 pykrx/KRX 응답 상태를 확인하세요. v1.1은 500 대신 진단 JSON을 반환합니다."
        }, status_code=200)


@app.get("/scan")
def scan_endpoint(mode: str = Query(default="main", pattern="^(main|sub)$"), limit: int = Query(default=settings.scan_limit, ge=1, le=500)):
    try:
        return safe_response(scan(mode=mode, limit=limit))
    except Exception as e:
        return safe_response({
            "status": "error",
            "endpoint": "/scan",
            "mode": mode,
            "message": str(e),
            "trace_tail": traceback.format_exc().splitlines()[-8:]
        }, status_code=200)


@app.get("/ticker/{ticker}")
def ticker_scan(ticker: str):
    try:
        return safe_response(scan_single(ticker.zfill(6)))
    except Exception as e:
        return safe_response({
            "status": "error",
            "endpoint": "/ticker/{ticker}",
            "ticker": ticker.zfill(6),
            "message": str(e),
            "trace_tail": traceback.format_exc().splitlines()[-8:]
        }, status_code=200)


@app.get("/debug")
def debug(limit: int = Query(default=10, ge=1, le=50)):
    try:
        result = scan(mode="sub", limit=limit)
        return safe_response({
            "status": "ok",
            "debug_limit": limit,
            "result_summary": {
                "count": result.get("count"),
                "warnings": result.get("warnings", []),
                "errors": result.get("errors", [])[:10]
            },
            "sample_candidates": result.get("candidates", [])[:3]
        })
    except Exception as e:
        return safe_response({
            "status": "error",
            "message": str(e),
            "trace_tail": traceback.format_exc().splitlines()[-12:]
        }, status_code=200)
