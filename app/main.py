from fastapi import FastAPI, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from pathlib import Path

from app.scanner import run_scan, get_latest_results, get_scan_status

app = FastAPI(title="주식단테 농사매매 스캐너", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent.parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    html_path = BASE_DIR / "templates" / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.post("/api/scan")
async def trigger_scan(background_tasks: BackgroundTasks):
    """전 종목 스캔 트리거 (백그라운드 실행)"""
    background_tasks.add_task(run_scan)
    return {"message": "스캔을 시작했습니다.", "status": "running"}


@app.get("/api/status")
async def scan_status():
    """스캔 진행 상태 확인"""
    return get_scan_status()


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/results")
async def get_results():
    """전체 스캔 결과 반환"""
    return JSONResponse(content=get_latest_results())


@app.get("/api/summary")
async def get_summary():
    """스캔 요약 통계 - GPT 브리핑용"""
    data = get_latest_results()
    results = data.get("results", [])
    signal_counts: dict = {}
    for r in results:
        sig = r.get("signal", "기타")
        signal_counts[sig] = signal_counts.get(sig, 0) + 1
    kospi = [r for r in results if r.get("market") == "KOSPI"]
    kosdaq = [r for r in results if r.get("market") == "KOSDAQ"]
    top_vol = sorted(results, key=lambda x: x.get("vol_ratio", 0), reverse=True)[:5]
    total = len(results)
    return {
        "scanned_at": data.get("scanned_at"),
        "total_scanned": data.get("total_scanned", 0),
        "total_found": total,
        "by_signal": signal_counts,
        "by_market": {"KOSPI": len(kospi), "KOSDAQ": len(kosdaq)},
        "market_sentiment": "강세" if total >= 30 else "중립" if total >= 10 else "약세",
        "top_volume_ratio": [
            {"ticker": r.get("ticker"), "name": r.get("name"),
             "signal": r.get("signal"), "vol_ratio": r.get("vol_ratio"),
             "close": r.get("close")} for r in top_vol
        ],
    }


@app.get("/api/results/signal/{signal_type}")
async def get_results_by_signal(signal_type: str):
    """신호 유형별 필터 - signal_type: 이평때리기|256기법|밥그릇3번|256장기"""
    data = get_latest_results()
    results = data.get("results", [])
    filtered = [r for r in results if r.get("signal") == signal_type]
    return {"signal": signal_type, "count": len(filtered),
            "scanned_at": data.get("scanned_at"), "results": filtered}


@app.get("/api/results/market/{market}")
async def get_results_by_market(market: str):
    """시장별 필터 - market: KOSPI|KOSDAQ"""
    data = get_latest_results()
    results = data.get("results", [])
    filtered = [r for r in results if r.get("market", "").upper() == market.upper()]
    return {"market": market.upper(), "count": len(filtered),
            "scanned_at": data.get("scanned_at"), "results": filtered}


@app.get("/api/results/ticker/{ticker}")
async def get_result_by_ticker(ticker: str):
    """종목 코드로 신호 조회 - ticker: 6자리 코드 (예: 005930)"""
    data = get_latest_results()
    results = data.get("results", [])
    matched = [r for r in results if r.get("ticker") == ticker]
    return {"ticker": ticker, "found": len(matched) > 0,
            "signals": matched, "scanned_at": data.get("scanned_at")}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
