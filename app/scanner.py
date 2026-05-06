"""
주식단테 농사매매법 스캐너
- 기법 1: 이평 때리기 (112/224/448일선 역배열 돌파)
- 기법 2: 256 기법 (5일선 > 20일선 골든크로스 + 60일선 위)
- 기법 3: 밥그릇 3번 (5일선 > 224일선 골든크로스 + 112>224)
- 기법 4: 256 장기 (5일선 > 112일선 골든크로스)
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from app.fetcher import (
    get_all_tickers,
    fetch_stock_data,
    get_latest_row,
    get_prev_row,
    has_maengzip_bong,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Render disk mountPath 환경변수 우선, 없으면 로컬 data/
DATA_DIR = Path(os.environ.get("DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_FILE = DATA_DIR / "scan_results.json"


# ──────────────────────────────────────────────
# 스캔 조건 함수
# ──────────────────────────────────────────────

def _safe_get(series, key):
    val = series.get(key)
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    return float(val)


def check_ipyeong_teorigi(df, cur, prev):
    """이평 때리기: 역배열(112<224<448) + 오늘 112선 돌파"""
    try:
        ma112 = _safe_get(cur, "ma112")
        ma224 = _safe_get(cur, "ma224")
        ma448 = _safe_get(cur, "ma448")
        if any(v is None for v in [ma112, ma224, ma448]):
            return None

        if not (ma112 < ma224 < ma448):
            return None

        ma112_prev = _safe_get(prev, "ma112")
        if ma112_prev is None:
            return None

        close_now = float(cur["close"])
        close_prev = float(prev["close"])
        breakthrough = close_now > ma112 and close_prev <= ma112_prev
        if not breakthrough:
            return None

        vol_now = float(cur.get("volume", 0) or 0)
        vol_prev = float(prev.get("volume", 1) or 1)
        vol_surge = vol_prev > 0 and (vol_now / vol_prev) >= 1.5

        if close_now < ma224:
            target, target_val = "224일선", round(ma224)
        elif close_now < ma448:
            target, target_val = "448일선", round(ma448)
        else:
            target, target_val = "448일선 돌파완료", round(ma448)

        return {
            "signal": "이평때리기",
            "detail": f"112일선 돌파 | 역배열 {round(ma112):,}→{round(ma224):,}→{round(ma448):,}",
            "target": target,
            "target_price": target_val,
            "stopline": round(ma112 * 0.97),
            "vol_surge": vol_surge,
            "ma112": round(ma112),
            "ma224": round(ma224),
            "ma448": round(ma448),
        }
    except Exception as e:
        logger.debug(f"이평때리기 오류: {e}")
    return None


def check_256(df, cur, prev):
    """256기법: 5>20 골든크로스 + 현재가 60선 위"""
    try:
        ma5 = _safe_get(cur, "ma5")
        ma20 = _safe_get(cur, "ma20")
        ma60 = _safe_get(cur, "ma60")
        ma5_prev = _safe_get(prev, "ma5")
        ma20_prev = _safe_get(prev, "ma20")
        if any(v is None for v in [ma5, ma20, ma60, ma5_prev, ma20_prev]):
            return None

        golden_cross = ma5 > ma20 and ma5_prev <= ma20_prev
        above_ma60 = float(cur["close"]) > ma60
        if not (golden_cross and above_ma60):
            return None

        maengzip = has_maengzip_bong(df)
        return {
            "signal": "256기법",
            "detail": f"5일선 골든크로스 | MA5:{round(ma5):,} MA20:{round(ma20):,} MA60:{round(ma60):,}",
            "target": "60일선 이상 유지",
            "target_price": round(ma60 * 1.05),
            "stopline": round(ma20 * 0.98),
            "maengzip": maengzip,
            "ma5": round(ma5),
            "ma20": round(ma20),
            "ma60": round(ma60),
        }
    except Exception as e:
        logger.debug(f"256기법 오류: {e}")
    return None


def check_bab_geureot(df, cur, prev):
    """밥그릇 3번: 5>224 골든크로스 + 112>224"""
    try:
        ma5 = _safe_get(cur, "ma5")
        ma112 = _safe_get(cur, "ma112")
        ma224 = _safe_get(cur, "ma224")
        ma5_prev = _safe_get(prev, "ma5")
        ma224_prev = _safe_get(prev, "ma224")
        if any(v is None for v in [ma5, ma112, ma224, ma5_prev, ma224_prev]):
            return None

        golden_cross = ma5 > ma224 and ma5_prev <= ma224_prev
        ma112_above = ma112 > ma224
        if not (golden_cross and ma112_above):
            return None

        ma448 = _safe_get(cur, "ma448")
        return {
            "signal": "밥그릇3번",
            "detail": f"5일선 224일선 돌파 | MA112:{round(ma112):,} MA224:{round(ma224):,}",
            "target": "448일선",
            "target_price": round(ma448) if ma448 else 0,
            "stopline": round(ma224 * 0.97),
            "ma112": round(ma112),
            "ma224": round(ma224),
            "ma448": round(ma448) if ma448 else 0,
        }
    except Exception as e:
        logger.debug(f"밥그릇3번 오류: {e}")
    return None


def check_256_long(df, cur, prev):
    """256장기: 5>112 골든크로스 + 현재가 112선 위"""
    try:
        ma5 = _safe_get(cur, "ma5")
        ma112 = _safe_get(cur, "ma112")
        ma224 = _safe_get(cur, "ma224")
        ma5_prev = _safe_get(prev, "ma5")
        ma112_prev = _safe_get(prev, "ma112")
        if any(v is None for v in [ma5, ma112, ma5_prev, ma112_prev]):
            return None

        golden = ma5 > ma112 and ma5_prev <= ma112_prev
        above = float(cur["close"]) > ma112
        if not (golden and above):
            return None

        return {
            "signal": "256장기",
            "detail": f"5일선 112일선 골든크로스 | MA5:{round(ma5):,} MA112:{round(ma112):,}",
            "target": "224일선",
            "target_price": round(ma224) if ma224 else 0,
            "stopline": round(ma112 * 0.97),
            "ma5": round(ma5),
            "ma112": round(ma112),
            "ma224": round(ma224) if ma224 else 0,
        }
    except Exception as e:
        logger.debug(f"256장기 오류: {e}")
    return None


# ──────────────────────────────────────────────
# 단일 종목 스캔
# ──────────────────────────────────────────────

def scan_ticker(ticker: str, info: dict) -> list[dict]:
    results = []
    try:
        df = fetch_stock_data(ticker)
        if df.empty or len(df) < 60:
            return []

        cur = get_latest_row(df)
        prev = get_prev_row(df, 1)
        if cur is None or prev is None:
            return []

        base = {
            "ticker": ticker,
            "name": info["name"],
            "market": info["market"],
            "close": int(cur["close"]),
            "volume": int(cur.get("volume", 0) or 0),
            "vol_ratio": round(float(cur.get("vol_ratio", 0) or 0), 2),
            "date": str(df.index[-1].date()),
        }

        for fn in [check_ipyeong_teorigi, check_256, check_bab_geureot, check_256_long]:
            res = fn(df, cur, prev)
            if res:
                results.append({**base, **res})

    except Exception as e:
        logger.debug(f"[{ticker}] 스캔 실패: {e}")
    return results


# ──────────────────────────────────────────────
# 전체 스캔
# ──────────────────────────────────────────────

_scan_status = {"running": False, "progress": 0, "total": 0, "last_run": None, "found": 0}


def get_scan_status() -> dict:
    return _scan_status.copy()


def get_latest_results() -> dict:
    if RESULTS_FILE.exists():
        try:
            return json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"scanned_at": None, "results": [], "total_scanned": 0, "found": 0}


def run_scan():
    global _scan_status
    if _scan_status["running"]:
        logger.info("이미 스캔 중")
        return

    _scan_status.update({"running": True, "progress": 0, "found": 0})
    start_time = datetime.now()
    logger.info("=== 농사매매 스캔 시작 ===")

    try:
        tickers = get_all_tickers()
        if not tickers:
            logger.error("종목 목록이 비어있습니다. 장중이거나 KRX 서버 오류일 수 있습니다.")
            return

        ticker_list = list(tickers.items())
        _scan_status["total"] = len(ticker_list)
        all_results = []
        done = 0

        # pykrx KRX API rate limit 고려 → max_workers=3
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(scan_ticker, t, info): t for t, info in ticker_list}
            for future in as_completed(futures):
                done += 1
                _scan_status["progress"] = done
                try:
                    res = future.result()
                    if res:
                        all_results.extend(res)
                        _scan_status["found"] = len(all_results)
                except Exception as e:
                    logger.debug(f"Future 오류: {e}")

                if done % 100 == 0:
                    logger.info(f"진행: {done}/{len(ticker_list)} | 발견: {len(all_results)}")
                    time.sleep(1)  # rate limit 방지

        signal_order = {"이평때리기": 0, "밥그릇3번": 1, "256기법": 2, "256장기": 3}
        all_results.sort(key=lambda x: (signal_order.get(x["signal"], 9), -x.get("vol_ratio", 0)))

        elapsed = (datetime.now() - start_time).seconds
        output = {
            "scanned_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed_sec": elapsed,
            "total_scanned": len(ticker_list),
            "found": len(all_results),
            "results": all_results,
        }
        RESULTS_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"=== 스캔 완료: {len(all_results)}개 발견 ({elapsed}초) ===")

    except Exception as e:
        logger.error(f"스캔 중 오류: {e}", exc_info=True)
    finally:
        _scan_status["running"] = False
        _scan_status["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
