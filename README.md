# Stock Farming Scanner v1 — 농사매매법 주식 스캐너

국내 주식 대상 `농사매매법` 후보를 찾기 위한 FastAPI 기반 스캐너입니다.

## 전략 정의

농사매매법 v1은 다음 목적을 가집니다.

> 장기 하락/소외 구간에 있는 종목 중, 쌍바닥과 공구리로 구조가 잡히고, 현재 돈이 들어오는 섹터에 속하며, 상폐 리스크가 낮은 종목만 골라 +10% 수익 실현을 노리는 전략.

## 핵심 조건

### 하드 제외 필터

- 관리종목/거래정지/상장폐지 위험 종목 제외
- 자본잠식/감사의견 비적정/한정/거절 종목 제외
- 거래대금 부족 종목 제외
- 섹터 약세 종목 제외
- 상단 저항까지 +10% 여유가 없는 종목 제외

### A타입

- 224일선 아래
- 쌍바닥 확인
- 공구리 확인
- 거래량/거래대금 증가
- 섹터 강도 양호
- 재무/상폐 리스크 PASS
- 목표수익률 +10%

### B타입

- 224일선 아래
- 쌍바닥 또는 공구리 중 하나 충족
- 거래량/거래대금 증가
- 섹터 최소 중립 이상
- 재무/상폐 리스크 PASS

## API

```bash
GET /health
GET /main?limit=250
GET /sub?limit=250
GET /scan?mode=main&limit=250
GET /ticker/{ticker}
```

## 로컬 실행

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Render 배포

- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

## 데이터 소스

- 주가/거래량/거래대금: `pykrx`
- 재무/상폐 하드필터: `data/exclude_list.json`, 추후 DART/KRX/KIND 연동 확장
- 섹터/테마: `data/sector_theme_map.json`

## 주의

이 스캐너는 투자 조언이나 자동매매 도구가 아니라 후보 선별 도구입니다. 실제 매수 전 공시, 거래정지, 관리종목 여부, 재무제표, 뉴스, 수급을 반드시 재확인해야 합니다.


## v1.3 변경사항

- `/main`: 기존처럼 엄격한 A타입 실매수 후보만 반환합니다.
- `/sub`: 조건 전체 통과가 아니라 농사매매법에 가까운 관찰 후보 TOP 20을 점수순으로 반환합니다.
- 후보가 왜 매수 후보가 아닌지 확인할 수 있도록 `reject_flags`를 추가했습니다.
- Render에서 정상 로딩되지만 `/sub`도 0개만 나오는 문제를 완화했습니다.
