#!/usr/bin/env python3
"""
장 마감 후 자동 스캔
Render Cron Job: 평일 15:40 KST → schedule: "40 6 * * 1-5"
"""
import sys
import os
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def main():
    # DATA_DIR 환경변수 확인
    data_dir = os.environ.get("DATA_DIR", "data")
    Path(data_dir).mkdir(parents=True, exist_ok=True)
    logger.info(f"=== 자동 스캔 시작 | DATA_DIR={data_dir} ===")

    try:
        from app.scanner import run_scan
        run_scan()
        logger.info("=== 자동 스캔 완료 ===")
        sys.exit(0)
    except Exception as e:
        logger.error(f"스캔 실패: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
