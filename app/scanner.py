"""
주식단테 농사매매법 스캐너
- 기법 1: 이평 때리기 (112/224/448일선 역배열 돌파)
- 기법 2: 256 기법 (5일선 > 20일선 골든크로스 + 60일선 위)
- 기법 3: 밥그릇 3번 (224일선 골든크로스)
"""

import json
import logging
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

RESULTS_FILE = Path("data/scan_results.json")
STATUS_FILE = Path("data/scan_status.json")
RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────
# 스캔 조건 함수
# ──────────────────────────────────────────────

def check_ipyeong_teorigi(df: pd.DataFrame, cur: pd.Series, prev: pd.Series) -> dict | None:
    """
    이평 때리기 조건
    1. 112 < 224 < 448 (역배열)
    2. 오늘 종가 > 112일선 (돌파)
    3. 전일 종가 <= 112일선 (직전까지 아래)
    4. 거래량 전일 대비 150% 이상
    """
    try:
        ma112 = cur.get("ma112")
        ma224 = cur.get("ma224")
        ma448 = cur.get("ma448")

        if pd.isna(ma112) or pd.isna(ma224) or pd.isna(ma448):
            return None

        is_reverse = ma112 < ma224 < ma448
        if not is_reverse:
            return None

        close_now = cur["close"]
        close_prev = prev["close"]
        ma112_prev = prev.get("ma112")

        if pd.isna(ma112_prev):
            return None

        breakthrough = close_now > ma112 and close_prev <= ma112_prev

        vol_now = cur.get("volume", 0)
        vol_prev = prev.get("volume", 1)
        vol_surge = vol_prev > 0 and (vol_now / vol_prev) >= 1.5

        if breakthrough:
            # 다음 목표선
            if close_now < ma224:
                target = "224일선"
                target_val = round(ma224)
            elif close_now < ma448:
                target = "448일선"
                target_val = round(ma448)
            else:
                target = "448일선 돌파 완료"
                target_val = round(ma448)

            return {
                "signal": "이평때리기",
                "detail": f"112일선 돌파 | 역배열: {round(ma112):,}→{round(ma224):,}→{round(ma448):,}",
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


def check_256(df: pd.DataFrame, cur: pd.Series, prev: pd.Series) -> dict | None:
    """
    256 기법 조건
    1. 오늘 5일선 > 20일선 (골든크로스 발생)
    2. 전일 5일선 <= 20일선
    3. 현재가 > 60일선 (추세 우위)
    4. 매집봉 존재 여부 (보조 지표)
    """
    try:
        ma5 = cur.get("ma5")
        ma20 = cur.get("ma20")
        ma60 = cur.get("ma60")
        ma5_prev = prev.get("ma5")
        ma20_prev = prev.get("ma20")

        if any(pd.isna(x) for x in [ma5, ma20, ma60, ma5_prev, ma20_prev]):
            return None

        golden_cross = ma5 > ma20 and ma5_prev <= ma20_prev
        above_ma60 = cur["close"] > ma60

        if golden_cross and above_ma60:
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


def check_bab_geureot(df: pd.DataFrame, cur: pd.Series, prev: pd.Series) -> dict | None:
    """
    밥그릇 3번 자리 (256기법 장기 버전)
    - 5일선이 224일선을 상향 돌파
    - 112일선이 224일선 위에 위치 (정배열 전환 중)
    """
    try:
        ma5 = cur.get("ma5")
        ma112 = cur.get("ma112")
        ma224 = cur.get("ma224")
        ma5_prev = prev.get("ma5")
        ma224_prev = prev.get("ma224")

        if any(pd.isna(x) for x in [ma5, ma112, ma224, ma5_prev, ma224_prev]):
            return None

        golden_cross_224 = ma5 > ma224 and ma5_prev <= ma224_prev
        ma112_above_224 = ma112 > ma224

        if golden_cross_224 and ma112_above_224:
            return {
                "signal": "밥그릇3번",
                "detail": f"5일선 224일선 돌파 | MA112:{round(ma112):,} MA224:{round(ma224):,}",
                "target": "448일선",
                "target_price": round(cur.get("ma448", 0)) if not pd.isna(cur.get("ma448", float("nan"))) else 0,
                "stopline": round(ma224 * 0.97),
                "ma112": round(ma112),
                "ma224": round(ma224),
            }
    except Exception as e:
        logger.debug(f"밥그릇3번 오류: {e}")
    return None


def check_256_long(df: pd.DataFrame, cur: pd.Series, prev: pd.Series) -> dict | None:
    """
    256 기법 장기 버전 (112/224일선 활용)
    - 5일선이 112일선 골든크로스
    - 현재가 > 112일선
    """
    try:
        ma5 = cur.get("ma5")
        ma112 = cur.get("ma112")
        ma224 = cur.get("ma224")
        ma5_prev = prev.get("ma5")
        ma112_prev = prev.get("ma112")

        if any(pd.isna(x) for x in [ma5, ma112, ma5_prev, ma112_prev]):
            return None

        golden = ma5 > ma112 and ma5_prev <= ma112_prev
        above = cur["close"] > ma112

        if golden and above:
            return {
                "signal": "256장기",
                "detail": f"5일선 112일선 골든크로스 | MA5:{round(ma5):,} MA112:{round(ma112):,}",
                "target": "224일선",
                "target_price": round(ma224) if not pd.isna(ma224) else 0,
                "stopline": round(ma112 * 0.97),
                "ma5": round(ma5),
                "ma112": round(ma112),
                "ma224": round(ma224) if not pd.isna(ma224) else 0,
            }
    except Exception as e:
        logger.debug(f"256장기 오류: {e}")
    return None


# ──────────────────────────────────────────────
# 단일 종목 스캔
# ──────────────────────────────────────────────

def scan_ticker(ticker: str, info: dict) -> list[dict]:
    """단일 종목에 대해 모든 기법 적용"""
    results = []
    try:
        df = fetch_stock_data(ticker)
        if df.empty or len(df) < 60:
            return []

        cur = get_latest_row(df)
        prev = get_prev_row(df, 1)

        if cur is None or prev is None:
            return []

        close_price = int(cur["close"])
        volume = int(cur["volume"])
        date_str = str(df.index[-1].date())
        vol_ratio = round(float(cur.get("vol_ratio", 0) or 0), 2)

        base = {
            "ticker": ticker,
            "name": info["name"],
            "market": info["market"],
            "close": close_price,
            "volume": volume,
            "vol_ratio": vol_ratio,
            "date": date_str,
        }

        for check_fn in [check_ipyeong_teorigi, check_256, check_bab_geureot, check_256_long]:
            result = check_fn(df, cur, prev)
            if result:
                entry = {**base, **result}
                results.append(entry)

    except Exception as e:
        logger.debug(f"[{ticker}] 스캔 실패: {e}")

    return results


# ──────────────────────────────────────────────
# 전체 스캔 실행
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
    return {"scanned_at": None, "results": [], "total_scanned": 0}


def run_scan():
    """전 종목 스캔 메인 함수"""
    global _scan_status

    if _scan_status["running"]:
        logger.info("이미 스캔이 실행 중입니다.")
        return

    _scan_status["running"] = True
    _scan_status["progress"] = 0
    _scan_status["found"] = 0
    start_time = datetime.now()
    logger.info("=== 농사매매 스캔 시작 ===")

    try:
        tickers = get_all_tickers()
        ticker_list = list(tickers.items())
        _scan_status["total"] = len(ticker_list)

        all_results = []
        done = 0

        # 병렬 처리 (pykrx rate limit 고려 max_workers=5)
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(scan_ticker, t, info): t
                for t, info in ticker_list
            }
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

                # API 부하 분산
                if done % 50 == 0:
                    logger.info(f"진행: {done}/{len(ticker_list)} | 발견: {len(all_results)}")
                    time.sleep(0.5)

        elapsed = (datetime.now() - start_time).seconds
        scanned_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 결과 정렬: 신호 우선순위 → 거래량 비율
        signal_order = {"이평때리기": 0, "밥그릇3번": 1, "256기법": 2, "256장기": 3}
        all_results.sort(key=lambda x: (signal_order.get(x["signal"], 9), -x.get("vol_ratio", 0)))

        output = {
            "scanned_at": scanned_at,
            "elapsed_sec": elapsed,
            "total_scanned": len(ticker_list),
            "found": len(all_results),
            "results": all_results,
        }
        RESULTS_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"=== 스캔 완료: {len(all_results)}개 발견 ({elapsed}초) ===")

    except Exception as e:
        logger.error(f"스캔 중 오류: {e}")
    finally:
        _scan_status["running"] = False
        _scan_status["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
