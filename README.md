# Presidential Gilsu Long System Upbit

업비트 KRW 현물 전용 롱 스캐너다.

핵심 구조
- Main: 엄격 필터. RSI 다이버전스 + Fib 0.618~0.786 + 상승파동 + BTC 시장필터
- Sub: 점수형 후보 생성기
- 밈코인/저유동성 코인 제외
- 손절/익절은 퍼센트로 반환
- 3단계 스캔 구조 적용
  - 1단계: KRW 유동성 상위 유니버스 선별
  - 2단계: 1h 경량 스코어링으로 shortlist 압축
  - 3단계: shortlist만 정밀 분석

## Endpoints
- `GET /health`
- `GET /scan/main`
- `GET /scan/sub`
- `GET /scan/single?symbol=BTC&timeframe=1h&mode=main`

## 추천 파라미터
- Main: `universe_limit=70&shortlist_limit=14`
- Sub: `universe_limit=70&shortlist_limit=20`

즉, 모수는 넓게 가져가되 정밀 판정 대상만 압축한다.

## Render
Build Command
```bash
pip install -r requirements.txt
```

Start Command
```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Python version on Render
환경변수에 아래 값을 추가하는 것을 권장한다.

```txt
PYTHON_VERSION=3.11.9
```

또는 루트 `.python-version` 파일 사용.

## 환경변수
- `REQUEST_SLEEP=0.18` 업비트 요청 간 최소 간격
- `SCAN_UNIVERSE_LIMIT=70`
- `SCAN_SHORTLIST_LIMIT_MAIN=14`
- `SCAN_SHORTLIST_LIMIT_SUB=20`


## v2.4.2 final
- Main logic preserved
- Sub logic relaxed: score threshold lowered to 14
- Sub stop anchor uses recent pivot/last 30 bars instead of 120-bar swing low
- Sub max stop widened to 45%


## Stable defaults in this build
- universe_limit default: 50
- shortlist_limit main: 12
- shortlist_limit sub: 15
- request sleep default: 0.28s
- OHLCV cache TTL: 25s

For safer operation on Render, first test:
- /scan/main?universe_limit=40&shortlist_limit=10
- /scan/sub?universe_limit=40&shortlist_limit=12
