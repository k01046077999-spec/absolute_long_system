# Presidential Gilsu Long System Upbit

업비트 KRW 현물 전용 롱 스캐너다.

핵심 구조
- Main: 엄격 필터. RSI 다이버전스 + Fib 0.618~0.786 + 상승파동 + BTC 시장필터
- Sub: 완화 필터. 후보군 탐색용
- 밈코인/저유동성 코인 제외
- 손절/익절은 퍼센트로 반환

## Endpoints
- `GET /health`
- `GET /scan/main`
- `GET /scan/sub`
- `GET /scan/single?symbol=BTC&timeframe=1h&mode=main`

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


## v2.1 sub 완화 변경
- main 로직은 유지
- sub는 0.5~0.786 완화 피보 구간 허용
- sub는 다이버전스/3꼭지/wave 중 하나만 성립해도 후보 검토
- sub는 EMA20 또는 EMA60 위면 추세 조건 통과
- sub 최소 점수 하향 및 손절 상한 완화


## v2.2 sub score mode
- main 로직은 유지
- sub는 필터형이 아니라 점수형 후보 생성기로 완화
- sub 최소 점수 34점
- sub는 완화 피보/거래량/상승파동/RSI 범위 중 다수 조합으로 후보 출력
