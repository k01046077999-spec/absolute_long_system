from __future__ import annotations

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

from app.config import settings
from app.models import ScanResponse, SignalResponse, TopPicksResponse
from app.services.upbit_client import close_client, get_client, normalize_market_symbol
from app.services.scanner import analyze_symbol, scan_symbols

app = FastAPI(
    title="제이드 코인 스캐너",
    version=settings.version,
    description="업비트 KRW 마켓 전용 | 제이드 파동 심화 이론 기반 RSI 다이버전스 연계 + Fibonacci 스캐너",
)


@app.on_event("startup")
async def startup_event():
    await get_client()


@app.on_event("shutdown")
async def shutdown_event():
    await close_client()


# ─────────────────────────────────────────────────────────────
#  HTML 대시보드 (메인 페이지)
# ─────────────────────────────────────────────────────────────
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>제이드 코인 스캐너 v{version}</title>
<style>
  :root {{
    --bg: #0d1117; --surface: #161b22; --border: #30363d;
    --text: #e6edf3; --muted: #8b949e; --green: #3fb950;
    --red: #f85149; --blue: #58a6ff; --orange: #d29922;
    --purple: #bc8cff; --cyan: #39d353;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif; padding: 20px; }}
  h1 {{ font-size: 1.8rem; color: var(--blue); margin-bottom: 6px; }}
  .subtitle {{ color: var(--muted); font-size: 0.9rem; margin-bottom: 24px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; margin-bottom: 24px; }}
  .card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 18px; }}
  .card h2 {{ font-size: 1rem; color: var(--blue); margin-bottom: 12px; }}
  .btn {{ display: inline-block; padding: 10px 22px; border-radius: 8px; border: none; cursor: pointer;
          font-size: 0.95rem; font-weight: 600; text-decoration: none; transition: opacity 0.2s; }}
  .btn:hover {{ opacity: 0.85; }}
  .btn-green {{ background: var(--green); color: #000; }}
  .btn-blue  {{ background: var(--blue); color: #000; }}
  .btn-orange {{ background: var(--orange); color: #000; }}
  .btn-purple {{ background: var(--purple); color: #000; }}
  .endpoint {{ display: flex; flex-direction: column; gap: 8px; }}
  .ep-row {{ display: flex; align-items: center; gap: 10px; }}
  .badge {{ padding: 3px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; }}
  .get {{ background: #1f6feb; color: #fff; }}
  code {{ background: #1c2128; padding: 4px 8px; border-radius: 4px; font-size: 0.85rem; color: var(--cyan); }}
  .desc {{ font-size: 0.82rem; color: var(--muted); margin-left: 42px; }}
  .rule-list {{ list-style: none; }}
  .rule-list li {{ padding: 6px 0; border-bottom: 1px solid var(--border); font-size: 0.88rem; line-height: 1.5; }}
  .rule-list li:last-child {{ border-bottom: none; }}
  .tag {{ font-size: 0.75rem; padding: 2px 6px; border-radius: 4px; font-weight: 700; margin-right: 6px; }}
  .tag-green {{ background: #1a3c28; color: var(--green); }}
  .tag-blue  {{ background: #1a2f47; color: var(--blue); }}
  .tag-red   {{ background: #3c1a1a; color: var(--red); }}
  .tag-orange {{ background: #3c2a10; color: var(--orange); }}
  footer {{ text-align: center; color: var(--muted); font-size: 0.8rem; margin-top: 32px; }}
</style>
</head>
<body>
<h1>📊 제이드 코인 스캐너 <small style="font-size:1rem; color:var(--muted)">v{version}</small></h1>
<p class="subtitle">업비트 KRW 마켓 전용 | 제이드 파동 심화 이론 | RSI 다이버전스 연계 + Fibonacci 0.618~0.786</p>

<div class="grid">
  <div class="card">
    <h2>🚀 스캔 실행</h2>
    <div class="endpoint">
      <div class="ep-row"><span class="badge get">GET</span><code>/scan/main</code></div>
      <p class="desc">메인 스캔 — 엄격한 기준 (RR ≥ 2.0)</p>
      <div class="ep-row" style="margin-top:6px">
        <a href="/scan/main" class="btn btn-green">▶ Main 스캔</a>
        <a href="/scan/main/top" class="btn btn-blue">★ Top Picks</a>
      </div>
    </div>
  </div>

  <div class="card">
    <h2>🔍 서브 스캔</h2>
    <div class="endpoint">
      <div class="ep-row"><span class="badge get">GET</span><code>/scan/sub</code></div>
      <p class="desc">서브 스캔 — 유연한 기준 (RR ≥ 1.8)</p>
      <div class="ep-row" style="margin-top:6px">
        <a href="/scan/sub" class="btn btn-orange">▶ Sub 스캔</a>
        <a href="/scan/sub/top" class="btn btn-purple">★ Top Picks</a>
      </div>
    </div>
  </div>

  <div class="card">
    <h2>🔎 단일 심볼 분석</h2>
    <div class="endpoint">
      <div class="ep-row"><span class="badge get">GET</span><code>/scan/symbol/{{symbol}}</code></div>
      <p class="desc">예: <a href="/scan/symbol/KRW-BTC" style="color:var(--blue)">/scan/symbol/KRW-BTC</a></p>
      <div class="ep-row" style="margin-top:6px">
        <a href="/docs" class="btn btn-blue">📖 API 문서</a>
        <a href="/health" class="btn btn-green">💚 상태 확인</a>
      </div>
    </div>
  </div>
</div>

<div class="grid">
  <div class="card">
    <h2>📖 제이드 파동 심화 이론 핵심 규칙</h2>
    <ul class="rule-list">
      <li><span class="tag tag-blue">파동 정의</span>상승 파동: 전저점 미이탈 + 전고점 돌파 목적</li>
      <li><span class="tag tag-red">파동 정의</span>하락 파동: 전고점 미갱신 + 전저점 하향 목적</li>
      <li><span class="tag tag-green">다이버전스</span>RSI 과매도/과매수 구간("쾅") 에서만 유효</li>
      <li><span class="tag tag-green">연계</span>3개 꼭지점 연계 = 가장 강력한 신호</li>
      <li><span class="tag tag-blue">피보나치</span>0.618~0.786 구간 = 핵심 진입 대기 구간</li>
      <li><span class="tag tag-red">손절</span>피보나치 1 이탈 = 절대 손절 라인</li>
      <li><span class="tag tag-orange">목표</span>TP1=1.272, TP2=1.618 (피보 확장)</li>
      <li><span class="tag tag-blue">주기</span>1시간봉 중심 | 30m(보조) | 4h(상위확인)</li>
    </ul>
  </div>

  <div class="card">
    <h2>📐 스캔 설정</h2>
    <ul class="rule-list">
      <li><span class="tag tag-blue">Universe</span>업비트 KRW 상위 {universe_size}개 종목</li>
      <li><span class="tag tag-green">Prefilter</span>빠른 점수로 상위 {prefilter_size}개 선별</li>
      <li><span class="tag tag-blue">Full</span>Main {full_main}개 / Sub {full_sub}개 상세 분석</li>
      <li><span class="tag tag-orange">Main RR</span>최소 2.0 | TP1 ≥ 3% | TP2 ≥ 5%</li>
      <li><span class="tag tag-purple">Sub RR</span>최소 1.8 | TP1 ≥ 2.4% | TP2 ≥ 4.5%</li>
      <li><span class="tag tag-green">Top Picks</span>최대 {top_picks}개 추천 종목</li>
      <li><span class="tag tag-blue">API</span><a href="/docs" style="color:var(--blue)">Swagger UI</a> / <a href="/redoc" style="color:var(--blue)">ReDoc</a></li>
    </ul>
  </div>
</div>

<footer>제이드 코인 스캐너 v{version} | 업비트 KRW 마켓 전용 | 투자 판단은 본인 책임입니다</footer>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def root():
    return DASHBOARD_HTML.format(
        version=settings.version,
        universe_size=settings.universe_size,
        prefilter_size=settings.prefilter_size,
        full_main=settings.full_analysis_main_limit,
        full_sub=settings.full_analysis_sub_limit,
        top_picks=settings.top_pick_count,
    )


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": settings.service_name,
        "version": settings.version,
    }


@app.get("/ready")
async def ready():
    await get_client()
    return {
        "status": "ready",
        "service": settings.service_name,
        "version": settings.version,
        "universe_size": settings.universe_size,
        "prefilter_size": settings.prefilter_size,
        "scan_concurrency": settings.scan_concurrency,
    }


# ─────────────────────────────────────────────────────────────
#  스캔 엔드포인트
# ─────────────────────────────────────────────────────────────
@app.get("/scan/main", response_model=ScanResponse)
async def scan_main(symbols: str | None = Query(default=None, description="쉼표 구분 심볼 (예: KRW-BTC,KRW-ETH)")):
    symbol_list = [s.strip().upper() for s in symbols.split(",")] if symbols else None
    if symbol_list is not None and not symbol_list:
        symbol_list = settings.default_symbols
    results, watchlist, diagnostics, top_picks = await scan_symbols(symbol_list, mode="main")
    return ScanResponse(mode="main", count=len(results), results=results, watchlist=watchlist, top_picks=top_picks, diagnostics=diagnostics)


@app.get("/scan/main/top", response_model=TopPicksResponse)
async def scan_main_top(symbols: str | None = Query(default=None)):
    symbol_list = [s.strip().upper() for s in symbols.split(",")] if symbols else None
    results, watchlist, diagnostics, top_picks = await scan_symbols(symbol_list, mode="main")
    return TopPicksResponse(mode="main", count=len(top_picks), top_picks=top_picks, diagnostics=diagnostics)


@app.get("/scan/sub", response_model=ScanResponse)
async def scan_sub(symbols: str | None = Query(default=None)):
    symbol_list = [s.strip().upper() for s in symbols.split(",")] if symbols else None
    if symbol_list is not None and not symbol_list:
        symbol_list = settings.default_symbols
    results, watchlist, diagnostics, top_picks = await scan_symbols(symbol_list, mode="sub")
    return ScanResponse(mode="sub", count=len(results), results=results, watchlist=watchlist, top_picks=top_picks, diagnostics=diagnostics)


@app.get("/scan/sub/top", response_model=TopPicksResponse)
async def scan_sub_top(symbols: str | None = Query(default=None)):
    symbol_list = [s.strip().upper() for s in symbols.split(",")] if symbols else None
    results, watchlist, diagnostics, top_picks = await scan_symbols(symbol_list, mode="sub")
    return TopPicksResponse(mode="sub", count=len(top_picks), top_picks=top_picks, diagnostics=diagnostics)


@app.get("/scan/symbol/{symbol}", response_model=SignalResponse)
async def scan_symbol(symbol: str, mode: str = Query("main", pattern="^(main|sub)$")):
    return await analyze_symbol(normalize_market_symbol(symbol), mode=mode)  # type: ignore
