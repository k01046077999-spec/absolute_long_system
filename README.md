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
