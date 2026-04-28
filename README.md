# stock-farming-scanner v1.8 main-only

농사매매법 전용 KRX 주식 스캐너입니다.

## 핵심 변경

v1.8은 `정확한 메인만 받는 구조`입니다.

- `/main/tiny` : Custom GPT 연결용 최우선 엔드포인트
- `/main` : 상세 디버그/검토용 엔드포인트
- `/summary` : main-only 요약
- `/simple`, `/scan` : 기존 연결 호환용 alias
- `/sub`, `/sub/tiny`, `/hot/tiny` : 비활성화 안내만 반환

## 판단 원칙

`/main/tiny`는 A타입 실매수 후보만 반환합니다.

A타입 기준:

1. 224일선 아래
2. 쌍바닥 확인
3. 공구리 확인
4. 거래량/거래대금 증가
5. 섹터 수급 STRONG
6. 상단 저항까지 목표수익률 10% 이상 여유
7. 재무건전성 FAIL 종목 제외

`count: 0`이면 오류가 아니라 현재 실매수 후보가 없다는 뜻입니다. 억지 매수하지 않습니다.

## Render 설정

Build Command

```bash
pip install -r requirements.txt
```

Start Command

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Custom GPT Action 권장 URL

```text
https://absolute-long-system.onrender.com/main/tiny
```

## 운영 원칙

이 버전부터 sub/watch 후보는 실제 매수 판단에 사용하지 않습니다. 후보가 많이 나오는 것보다, 틀린 후보를 줄이는 것을 우선합니다.
