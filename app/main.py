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
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    html_path = BASE_DIR / "templates" / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.post("/api/scan")
async def trigger_scan(background_tasks: BackgroundTasks):
    """장 마감 후 전 종목 스캔 트리거"""
    background_tasks.add_task(run_scan)
    return {"message": "스캔을 시작했습니다. 수분 내 완료됩니다.", "status": "running"}


@app.get("/api/results")
async def get_results():
    """최신 스캔 결과 반환"""
    results = get_latest_results()
    return JSONResponse(content=results)


@app.get("/api/status")
async def scan_status():
    """스캔 진행 상태 확인"""
    return get_scan_status()


@app.get("/api/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
