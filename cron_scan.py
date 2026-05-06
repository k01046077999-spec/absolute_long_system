#!/usr/bin/env python3
"""
장 마감 후 자동 스캔 실행 스크립트
- Render Cron Job 또는 로컬 crontab에서 실행
- 매일 15:40 KST (06:40 UTC) 실행 권장

crontab 예시:
  40 6 * * 1-5 /usr/bin/python3 /app/cron_scan.py >> /var/log/scan.log 2>&1

Render Cron Job:
  Schedule: 40 6 * * 1-5
  Command: python cron_scan.py
"""

import sys
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def main():
    logger.info("=== 자동 스캔 시작 (cron_scan.py) ===")

    # data 디렉토리 생성
    os.makedirs("data", exist_ok=True)

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
