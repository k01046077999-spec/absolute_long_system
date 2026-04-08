from typing import Literal
from pydantic import BaseModel, Field

Mode = Literal['main', 'sub']
Side = Literal['bullish', 'bearish']


class RiskPlan(BaseModel):
    entry_reference: float
    fib_0618: float | None = None
    fib_0786: float | None = None
    invalidation_price: float
    invalidation_rule: str
    stop_loss_pct: float
    tp1_price: float
    tp1_pct: float
    tp2_price: float
    tp2_pct: float
    rr_tp1: float
    rr_tp2: float


class ScanSignal(BaseModel):
    symbol: str
    mode: Mode
    side: Side
    score: float
    grade: str
    state: str
    current_price: float
    reason_summary: str
    divergence_kind: str
    chain_points: int = 0
    fib_zone_status: str
    volume_ratio: float
    rsi_1h: float
    rsi_15m: float
    resistance_room_pct: float
    risk: RiskPlan
    filters_passed: bool
    rejected_reasons: list[str] = Field(default_factory=list)


class ScanResponse(BaseModel):
    mode: Mode
    scanned_symbols: int
    matched_symbols: int
    elapsed_seconds: float
    top_picks: list[ScanSignal]
    signals: list[ScanSignal]


class HealthResponse(BaseModel):
    status: str
    version: str
