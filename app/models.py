from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class Candidate(BaseModel):
    strategy: str
    type: str
    ticker: str
    name: str
    market: str
    sector: str
    themes: List[str]
    current_price: float
    target_price: float
    target_return: str
    score: int
    decision: str
    conditions: List[str]
    risks: List[str]
    metrics: Dict[str, Any]
    financial_health: Dict[str, Any]

class ScanResponse(BaseModel):
    strategy: str
    mode: str
    count: int
    candidates: List[Candidate]
    warnings: List[str] = []
