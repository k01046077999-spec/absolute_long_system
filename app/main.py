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
    version="1.7.0",
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


def compact_candidate(item: dict) -> dict:
    metrics = item.get("metrics", {}) or {}
    money = metrics.get("money_flow", {}) or {}
    sector_strength = metrics.get("sector_strength", {}) or {}
    resistance = metrics.get("resistance_gap", {}) or {}
    ma224 = metrics.get("ma224", {}) or {}
    db = metrics.get("double_bottom", {}) or {}
    concrete = metrics.get("concrete_support", {}) or {}
    fin = item.get("financial_health", {}) or {}
    conditions = item.get("conditions", []) or []
    risks = item.get("risks", []) or []
    reject_flags = item.get("reject_flags", []) or []
    pass_flags = []
    if ma224.get("pass"):
        pass_flags.append("224일선 아래")
    if db.get("pass"):
        pass_flags.append("쌍바닥")
    if concrete.get("pass"):
        pass_flags.append("공구리")
    if money.get("pass"):
        pass_flags.append("거래대금/거래량")
    if sector_strength.get("sector_status") == "STRONG":
        pass_flags.append("섹터 강함")
    if resistance.get("pass"):
        pass_flags.append("상단 10% 여유")
    fail_reason = (reject_flags or risks or conditions or [None])[0]
    return {
        "type": item.get("type"),
        "ticker": item.get("ticker"),
        "name": item.get("name"),
        "price": item.get("current_price"),
        "target_price": item.get("target_price"),
        "target_return": item.get("target_return"),
        "score": item.get("score"),
        "decision": item.get("decision"),
        "sector": item.get("sector"),
        "themes": item.get("themes", [])[:3],
        "pass_flags": pass_flags,
        "fail_reason": fail_reason,
        "key_metrics": {
            "value_ratio": money.get("value_ratio"),
            "avg_trading_value_20d": money.get("avg_trading_value_20d"),
            "sector_status": sector_strength.get("sector_status"),
            "sector_score": sector_strength.get("sector_score"),
            "resistance_gap_pct": resistance.get("gap_pct"),
            "financial_status": fin.get("status"),
            "financial_risk_grade": fin.get("risk_grade"),
        },
    }


def tiny_candidate(item: dict) -> dict:
    metrics = item.get("metrics", {}) or {}
    money = metrics.get("money_flow", {}) or {}
    resistance = metrics.get("resistance_gap", {}) or {}
    sector_strength = metrics.get("sector_strength", {}) or {}
    ma224 = metrics.get("ma224", {}) or {}
    db = metrics.get("double_bottom", {}) or {}
    concrete = metrics.get("concrete_support", {}) or {}
    return {
        "type": item.get("type"),
        "ticker": item.get("ticker"),
        "name": item.get("name"),
        "price": item.get("current_price"),
        "target_price": item.get("target_price"),
        "score": item.get("score"),
        "decision": item.get("decision"),
        "sector": item.get("sector"),
        "sector_status": sector_strength.get("sector_status"),
        "ma224_pass": ma224.get("pass"),
        "double_bottom_pass": db.get("pass"),
        "concrete_pass": concrete.get("pass"),
        "money_flow_pass": money.get("pass"),
        "value_ratio": money.get("value_ratio"),
        "avg_trading_value_20d": money.get("avg_trading_value_20d"),
        "resistance_gap_pct": resistance.get("gap_pct"),
        "reason": (item.get("reject_flags", []) or item.get("risks", []) or item.get("conditions", []) or [None])[0],
    }


def split_candidates(candidates: list[dict]) -> dict:
    buy = [x for x in candidates if x.get("type") in ["A", "B"]]
    watch = [x for x in candidates if x.get("type") == "WATCH"]
    return {"buy": buy, "watch": watch}


def compact_scan(mode: str, limit: int) -> dict:
    result = scan(mode=mode, limit=limit)
    candidates = result.get("candidates", [])
    return {
        "strategy": result.get("strategy"),
        "mode": mode,
        "count": len(candidates),
        "note": "simple은 브라우저/Custom GPT용 요약 응답입니다. 상세 지표는 /main 또는 /sub에서 확인하세요.",
        "scanned_tickers": result.get("scanned_tickers"),
        "loaded_ohlcv": result.get("loaded_ohlcv"),
        "candidates": [compact_candidate(x) for x in candidates],
        "warnings": result.get("warnings", []),
        "errors": result.get("errors", []),
    }


@app.get("/")
def root():
    return safe_response({
        "service": "stock-farming-scanner",
        "strategy": "농사매매법",
        "version": "1.7.0",
        "endpoints": ["/health", "/summary", "/simple", "/buy/tiny", "/watch/tiny", "/hot", "/hot/tiny", "/main", "/sub", "/main/simple", "/sub/simple", "/main/tiny", "/sub/tiny", "/scan", "/ticker/{ticker}", "/debug"]
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
        "version": "1.7.0"
    })


@app.get("/main")
def main_scan(limit: int = Query(default=settings.scan_limit, ge=1, le=500)):
    try:
        return safe_response(scan(mode="main", limit=limit))
    except Exception as e:
        return safe_response({"status": "error", "endpoint": "/main", "message": str(e), "trace_tail": traceback.format_exc().splitlines()[-8:]}, status_code=200)


@app.get("/hot")
def hot_scan(limit: int = Query(default=settings.scan_limit, ge=1, le=500)):
    try:
        return safe_response(scan(mode="hot", limit=limit))
    except Exception as e:
        return safe_response({"status": "error", "endpoint": "/hot", "message": str(e), "trace_tail": traceback.format_exc().splitlines()[-8:]}, status_code=200)

@app.get("/sub")
def sub_scan(limit: int = Query(default=settings.scan_limit, ge=1, le=500)):
    try:
        return safe_response(scan(mode="sub", limit=limit))
    except Exception as e:
        return safe_response({"status": "error", "endpoint": "/sub", "message": str(e), "trace_tail": traceback.format_exc().splitlines()[-8:]}, status_code=200)


@app.get("/main/simple")
def main_simple(limit: int = Query(default=settings.scan_limit, ge=1, le=500)):
    try:
        return safe_response(compact_scan(mode="main", limit=limit))
    except Exception as e:
        return safe_response({"status": "error", "endpoint": "/main/simple", "message": str(e), "trace_tail": traceback.format_exc().splitlines()[-8:]}, status_code=200)


@app.get("/sub/simple")
def sub_simple(limit: int = Query(default=settings.scan_limit, ge=1, le=500)):
    try:
        return safe_response(compact_scan(mode="sub", limit=limit))
    except Exception as e:
        return safe_response({"status": "error", "endpoint": "/sub/simple", "message": str(e), "trace_tail": traceback.format_exc().splitlines()[-8:]}, status_code=200)


@app.get("/simple")
def simple(limit: int = Query(default=settings.scan_limit, ge=1, le=500)):
    return summary(limit=limit)


@app.get("/buy/tiny")
def buy_tiny(limit: int = Query(default=settings.scan_limit, ge=1, le=500)):
    try:
        result = scan(mode="sub", limit=limit)
        split = split_candidates(result.get("candidates", []))
        return safe_response({
            "strategy": "농사매매법",
            "mode": "buy_tiny",
            "count": len(split["buy"]),
            "meaning": "A/B 타입만 매수 검토 대상입니다. count 0이면 오늘은 매수보다 대기입니다.",
            "candidates": [tiny_candidate(x) for x in split["buy"][:10]],
        })
    except Exception as e:
        return safe_response({"status": "error", "endpoint": "/buy/tiny", "message": str(e), "trace_tail": traceback.format_exc().splitlines()[-8:]}, status_code=200)


@app.get("/watch/tiny")
def watch_tiny(limit: int = Query(default=settings.scan_limit, ge=1, le=500)):
    try:
        result = scan(mode="sub", limit=limit)
        split = split_candidates(result.get("candidates", []))
        return safe_response({
            "strategy": "농사매매법",
            "mode": "watch_tiny",
            "count": len(split["watch"]),
            "meaning": "WATCH는 관찰 후보입니다. 매수는 A/B 전환 후 검토합니다.",
            "candidates": [tiny_candidate(x) for x in split["watch"][:20]],
        })
    except Exception as e:
        return safe_response({"status": "error", "endpoint": "/watch/tiny", "message": str(e), "trace_tail": traceback.format_exc().splitlines()[-8:]}, status_code=200)


@app.get("/hot/tiny")
def hot_tiny(limit: int = Query(default=50, ge=1, le=500)):
    try:
        result = scan(mode="hot", limit=limit)
        candidates = result.get("candidates", [])
        return safe_response({
            "strategy": "농사매매법",
            "mode": "hot_tiny",
            "count": len(candidates),
            "meaning": "224일선 하단 근접·수급 유입·섹터 중립 이상 후보를 빠르게 보는 요약입니다.",
            "candidates": [tiny_candidate(x) for x in candidates],
        })
    except Exception as e:
        return safe_response({"status": "error", "endpoint": "/hot/tiny", "message": str(e), "trace_tail": traceback.format_exc().splitlines()[-8:]}, status_code=200)

@app.get("/sub/tiny")
def sub_tiny(limit: int = Query(default=30, ge=1, le=500)):
    try:
        result = scan(mode="sub", limit=limit)
        candidates = result.get("candidates", [])
        return safe_response({
            "strategy": "농사매매법",
            "mode": "sub_tiny",
            "count": len(candidates),
            "meaning": "관찰 후보 요약입니다. A/B만 매수 검토, WATCH는 관찰만.",
            "candidates": [tiny_candidate(x) for x in candidates],
        })
    except Exception as e:
        return safe_response({"status": "error", "endpoint": "/sub/tiny", "message": str(e), "trace_tail": traceback.format_exc().splitlines()[-8:]}, status_code=200)


@app.get("/main/tiny")
def main_tiny(limit: int = Query(default=30, ge=1, le=500)):
    try:
        result = scan(mode="main", limit=limit)
        candidates = result.get("candidates", [])
        return safe_response({
            "strategy": "농사매매법",
            "mode": "main_tiny",
            "count": len(candidates),
            "meaning": "실매수 후보 요약입니다. count 0이면 현재 A타입 없음.",
            "candidates": [tiny_candidate(x) for x in candidates],
        })
    except Exception as e:
        return safe_response({"status": "error", "endpoint": "/main/tiny", "message": str(e), "trace_tail": traceback.format_exc().splitlines()[-8:]}, status_code=200)


@app.get("/summary")
def summary(limit: int = Query(default=settings.scan_limit, ge=1, le=500)):
    try:
        main_result = scan(mode="main", limit=limit)
        sub_result = scan(mode="sub", limit=limit)
        sub_candidates = sub_result.get("candidates", [])
        counts_by_type = {"A": 0, "B": 0, "WATCH": 0}
        for item in sub_candidates:
            t = item.get("type")
            counts_by_type[t] = counts_by_type.get(t, 0) + 1
        split = split_candidates(sub_candidates)
        return safe_response({
            "strategy": "농사매매법",
            "target_return": f"{int(settings.target_return * 100)}%",
            "main_count": len(main_result.get("candidates", [])),
            "sub_count": len(sub_candidates),
            "buy_count": len(split["buy"]),
            "watch_count": len(split["watch"]),
            "counts_by_type": counts_by_type,
            "top_buy": [compact_candidate(x) for x in split["buy"][:5]],
            "top_watch": [compact_candidate(x) for x in split["watch"][:5]],
            "warnings": list(set(main_result.get("warnings", []) + sub_result.get("warnings", []))),
            "errors": (main_result.get("errors", []) + sub_result.get("errors", []))[:10],
            "interpretation": "main_count/buy_count가 0이면 오류가 아니라 현재 실매수 후보가 없다는 뜻입니다. WATCH는 관찰 후보입니다."
        })
    except Exception as e:
        return safe_response({"status": "error", "endpoint": "/summary", "message": str(e), "trace_tail": traceback.format_exc().splitlines()[-8:]}, status_code=200)


@app.get("/scan")
def scan_endpoint(mode: str = Query(default="main", pattern="^(main|sub|hot)$"), limit: int = Query(default=settings.scan_limit, ge=1, le=500)):
    try:
        return safe_response(scan(mode=mode, limit=limit))
    except Exception as e:
        return safe_response({"status": "error", "endpoint": "/scan", "mode": mode, "message": str(e), "trace_tail": traceback.format_exc().splitlines()[-8:]}, status_code=200)


@app.get("/ticker/{ticker}")
def ticker_scan(ticker: str):
    try:
        return safe_response(scan_single(ticker.zfill(6)))
    except Exception as e:
        return safe_response({"status": "error", "endpoint": "/ticker/{ticker}", "ticker": ticker.zfill(6), "message": str(e), "trace_tail": traceback.format_exc().splitlines()[-8:]}, status_code=200)


@app.get("/debug")
def debug(limit: int = Query(default=10, ge=1, le=50)):
    try:
        result = scan(mode="sub", limit=limit)
        return safe_response({
            "status": "ok",
            "debug_limit": limit,
            "result_summary": {"count": result.get("count"), "warnings": result.get("warnings", []), "errors": result.get("errors", [])[:10]},
            "sample_candidates": result.get("candidates", [])[:3]
        })
    except Exception as e:
        return safe_response({"status": "error", "message": str(e), "trace_tail": traceback.format_exc().splitlines()[-12:]}, status_code=200)
