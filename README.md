# 완전무결매매법 코인 검색기 (업비트 KRW / 롱 전용)

이번 최종본은 **업비트 기준**, **롱 포지션만 탐색**하도록 다시 정리한 FastAPI 스캐너입니다.

## 핵심 해석 원칙
- 업비트 **KRW 마켓**만 스캔
- **롱 포지션만** 탐색
- 1시간봉 중심
- RSI 일반 다이버전스보다 **3개 이상 pivot 연계**를 main에서 우선
- 피보나치 **0.618 ~ 0.786** 구간을 핵심 되돌림 구간으로 사용
- **피보나치 1 이탈은 구조 무효**
- 과도한 추격, 거래량 부족, 저항 근접, RR 부족은 제외
- 손절/익절은 **가격 + 퍼센트** 둘 다 반환

## 엔드포인트
- `GET /health`
- `GET /scan/main`
- `GET /scan/sub`
- `GET /analyze/{symbol}`
- `GET /openapi.json`

## main / sub 차이
- `main`: 1시간봉 **연계 다이버전스(chain)** 필수 + 피보나치 구간 + 실전 필터 강하게 적용
- `sub`: 일반 상승 다이버전스도 허용, 탐색 후보용

## 응답에서 바로 볼 포인트
- `risk.stop_loss_pct` → 손절 퍼센트
- `risk.tp1_pct` → 1차 익절 퍼센트
- `risk.tp2_pct` → 2차 익절 퍼센트
- `reason_summary` 안에도 `%` 표기로 같이 노출

## 심화 검토 포인트
- 업비트는 USDT 마켓보다 유동성 구조가 달라서 **KRW 24시간 거래대금 하한**을 둠
- 롱만 남기기 위해 하락 다이버전스/숏 로직은 제거
- `main_requires_chain_divergence`로 메인은 PDF 핵심인 **연계형 구조**를 강제
- `invalid_stop_structure`를 넣어 손절 구조가 비정상인 후보를 제거

## 로컬 실행
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Render 배포
- 새 Web Service 생성
- 이 프로젝트 업로드
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

## Render env 예시
- `UPBIT_BASE_URL=https://api.upbit.com`
- `SCAN_MARKET_LIMIT_MAIN=60`
- `SCAN_MARKET_LIMIT_SUB=120`
- `TOP_PICK_COUNT=8`

## analyze 예시
- `/analyze/BTC`
- `/analyze/KRW-BTC`
- `/analyze/XRP?mode=sub`

## 주의
이 스캐너는 **신호 생성기**다. 승률을 높이는 구조물이지, 수익 보장기는 아니다.
