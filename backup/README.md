# 완전무결매매법 코인 검색기

PDF의 핵심 규칙을 최대한 기계적으로 옮긴 FastAPI 스캐너입니다.

## 핵심 해석 원칙
- 1시간봉 중심
- RSI 일반 다이버전스보다 **3개 이상 pivot 연계**를 우선
- 피보나치 0.618 ~ 0.786 구간을 핵심 되돌림 구간으로 사용
- 피보나치 1 이탈은 구조 무효
- 과도한 추격, 거래량 부족, 저항 근접은 제외

## 엔드포인트
- `GET /health`
- `GET /scan/main`
- `GET /scan/sub`
- `GET /analyze/{symbol}`
- `GET /openapi.json`

## main / sub 차이
- `main`: 1시간봉 3점 연계 다이버전스 + 피보나치 구간 + 실전 필터를 강하게 적용
- `sub`: 일반 다이버전스도 허용, 다만 점수와 실전성은 별도 표기

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

## 주의
이 스캐너는 확률 필터다. 신호 생성기이지 수익 보증기가 아니다.
