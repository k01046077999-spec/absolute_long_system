from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.utils import to_builtin
from strategy.scanner import scan

app = FastAPI(
    title="Stock Farming Scanner - Main Only",
    version="1.8-main-only",
    description="농사매매법 기반 국내 주식 메인 실매수 후보 스캐너",
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


def tiny_main_payload():
    result = scan("main")
    candidates = result.get("candidates", []) or []
    return {
        "strategy": "농사매매법",
        "version": "1.8-main-only",
        "mode": "main_tiny",
        "count": len(candidates),
        "meaning": "실매수 후보만 반환합니다. count 0이면 현재 A타입 없음.",
        "candidates": [
            {
                "type": c.get("type"),
                "ticker": c.get("ticker"),
                "name": c.get("name"),
                "price": c.get("current_price"),
                "target_price": c.get("target_price"),
                "score": c.get("score"),
                "decision": c.get("decision"),
                "sector": c.get("sector"),
                "sector_status": (c.get("key_metrics") or {}).get("sector_status"),
                "ma224_gap_pct": (c.get("key_metrics") or {}).get("ma224_gap_pct"),
                "value_ratio": (c.get("key_metrics") or {}).get("value_ratio"),
                "avg_trading_value_20d": (c.get("key_metrics") or {}).get("avg_trading_value_20d"),
                "resistance_gap_pct": (c.get("key_metrics") or {}).get("resistance_gap_pct"),
                "conditions": c.get("conditions", []),
                "risks": c.get("risks", []),
            }
            for c in candidates[:5]
        ],
        "warnings": result.get("warnings", []),
        "errors": result.get("errors", []),
    }


@app.get("/")
def root():
    return safe_response({
        "service": "stock-farming-scanner",
        "version": "1.8-main-only",
        "primary_endpoint": "/main/tiny",
        "rule": "정확한 메인 A타입 실매수 후보만 사용. sub/hot은 의사결정에서 제외.",
    })


@app.get("/health")
def health():
    return safe_response({"ok": True, "version": "1.8-main-only"})


@app.get("/main")
def main_scan():
    return safe_response(scan("main"))


@app.get("/main/tiny")
def main_tiny():
    return safe_response(tiny_main_payload())


@app.get("/summary")
def summary():
    payload = tiny_main_payload()
    payload["interpretation"] = "count가 0이면 현재 농사매매법 A타입 실매수 후보가 없는 상태입니다. 억지 매수 금지."
    return safe_response(payload)


@app.get("/simple")
def simple_alias():
    return safe_response(tiny_main_payload())


@app.get("/scan")
def scan_alias():
    return safe_response(scan("main"))


@app.get("/sub")
def sub_disabled():
    return safe_response({"disabled": True, "message": "v1.8부터 sub는 사용하지 않습니다. 정확한 판단은 /main/tiny만 사용하세요."})


@app.get("/sub/tiny")
def sub_tiny_disabled():
    return safe_response({"disabled": True, "message": "v1.8부터 sub_tiny는 사용하지 않습니다. 정확한 판단은 /main/tiny만 사용하세요."})


@app.get("/hot/tiny")
def hot_tiny_disabled():
    return safe_response({"disabled": True, "message": "v1.8부터 hot_tiny는 사용하지 않습니다. 정확한 판단은 /main/tiny만 사용하세요."})
