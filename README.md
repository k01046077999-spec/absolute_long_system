# Absolute Long System - Upbit Edition

업비트 전용 롱 스캐너입니다.

이번 버전은 기존 통합 전략의 핵심은 유지하되, **거래소를 업비트로 고정**하고 `KRW` 마켓만 스캔하도록 바꾼 버전입니다.

핵심은 그대로입니다.
- 파동 방향
- RSI 다이버전스
- 피보나치 0.618~0.786 눌림
- Fib 1 이탈 시 무효
- 손절/익절은 퍼센트 표시

## 이번 업비트 버전에서 바뀐 점

- 기본 거래소: `upbit`
- 기본 마켓: `KRW`
- 단일 종목 조회 시 `BTC`, `XRP`, `BTC/KRW`, `XRP/KRW` 형태 모두 허용
- 심볼 정규화 로직 추가
- 업비트 24시간 거래대금 기준 정렬 대응

## API

### 헬스체크
`GET /health`

### 전체 롱 스캔
`GET /scan/long`

예시:
```bash
curl "http://localhost:8000/scan/long?symbol_limit=40&timeframes=1h,4h"
```

### 단일 종목 스캔
`GET /scan/single`

예시:
```bash
curl "http://localhost:8000/scan/single?symbol=BTC&timeframe=1h"
curl "http://localhost:8000/scan/single?symbol=XRP/KRW&timeframe=4h"
```

## Render 배포

1. 이 폴더 전체를 GitHub 새 레포에 업로드
2. Render에서 New Web Service 생성
3. GitHub 레포 연결
4. `render.yaml` 자동 인식 확인
5. 배포 후 아래 경로 확인
   - `/health`
   - `/scan/long`
   - `/scan/single?symbol=BTC&timeframe=1h`

## 주의

- 업비트 기준이므로 해외 USDT 마켓과 결과가 다를 수 있습니다.
- KRW 마켓 특성상 거래대금/유동성 순위가 바이낸스와 다릅니다.
- 전략 논리는 같아도, 시장 풀 자체가 달라져 후보 종목이 달라지는 건 정상입니다.

## Render 안정 배포 설정

이 프로젝트는 Render에서 **Python 3.11.9** 기준으로 배포하도록 맞춰져 있습니다.

- `runtime.txt` 포함
- 빌드 커맨드: `pip install -r requirements.txt`
- 스타트 커맨드: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

만약 Render에서 기본 최신 Python으로 잡히면 `pydantic-core` 설치 오류가 날 수 있으니, 반드시 이 프로젝트 루트의 `runtime.txt`가 함께 올라가야 합니다.
