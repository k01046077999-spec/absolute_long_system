from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query

from app.core.config import settings
from app.core.schemas import HealthResponse, ScanResponse
from app.services.engine import ScannerEngine

app = FastAPI(title=settings.app_name, version=settings.app_version)
engine = ScannerEngine()


@app.get('/health', response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status='ok', version=settings.app_version)


@app.get('/scan/main', response_model=ScanResponse)
async def scan_main() -> ScanResponse:
    return await engine.scan('main')


@app.get('/scan/sub', response_model=ScanResponse)
async def scan_sub() -> ScanResponse:
    return await engine.scan('sub')


@app.get('/analyze/{symbol}')
async def analyze_symbol(symbol: str, mode: str = Query('main', pattern='^(main|sub)$')):
    normalized = symbol.upper().replace('/', '').replace('_', '-')
    if not normalized.startswith('KRW-'):
        normalized = f'KRW-{normalized.replace("KRW", "").replace("-", "")}'
    result = await engine.analyze_symbol(normalized, mode)
    if result is None:
        raise HTTPException(status_code=404, detail='signal_not_found')
    return result
