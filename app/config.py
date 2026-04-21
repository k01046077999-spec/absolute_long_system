from __future__ import annotations
from pydantic import BaseModel


class Settings(BaseModel):
    # ── 기본 심볼 ──────────────────────────────────────────────
    default_symbols: list[str] = [
        "KRW-BTC", "KRW-ETH", "KRW-XRP", "KRW-SOL", "KRW-DOGE",
        "KRW-ADA", "KRW-SUI", "KRW-LINK", "KRW-AVAX", "KRW-TRX",
        "KRW-HBAR", "KRW-XLM", "KRW-DOT", "KRW-MATIC", "KRW-ATOM",
    ]

    # ── 캔들 수 ───────────────────────────────────────────────
    default_limit: int = 240
    prefilter_limit: int = 160

    # ── 기술 지표 ─────────────────────────────────────────────
    rsi_period: int = 14
    swing_window: int = 2

    # ── 스캔 범위 ─────────────────────────────────────────────
    max_symbols_per_scan: int = 80
    universe_size: int = 120
    prefilter_size: int = 60
    scan_concurrency: int = 3
    request_timeout: float = 20.0
    top_pick_count: int = 5

    # ── 분석 깊이 ─────────────────────────────────────────────
    full_analysis_main_limit: int = 15
    full_analysis_sub_limit: int = 20
    quick_score_main_floor: float = 20.0
    quick_score_sub_floor: float = 14.0
    main_threshold: float = 48.0
    sub_threshold: float = 26.0

    # ── 버전 ──────────────────────────────────────────────────
    version: str = "1.0.0"
    service_name: str = "제이드 코인 스캐너"


settings = Settings()
