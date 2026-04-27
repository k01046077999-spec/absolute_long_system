from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
EXCLUDE_PATH = BASE_DIR / "data" / "exclude_list.json"

@lru_cache(maxsize=1)
def load_exclude_list() -> set[str]:
    if not EXCLUDE_PATH.exists():
        return set()
    with EXCLUDE_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return set(data.get("manual_exclude_tickers", []))


def financial_health_filter(ticker: str) -> dict:
    # v1: manual hard-exclude list. v2에서 DART Open API 재무제표/감사의견 자동 연동 예정.
    if ticker in load_exclude_list():
        return {
            "status": "FAIL",
            "risk_grade": "F",
            "delisting_risk": "HIGH",
            "reasons": ["manual_exclude_list"]
        }
    return {
        "status": "PASS",
        "risk_grade": "UNKNOWN",
        "delisting_risk": "UNKNOWN",
        "reasons": ["DART/KRX hard filter not connected yet; manual exclude list checked"]
    }
