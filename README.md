# 🌾 주식단테 농사매매 스캐너

주식단테 유튜버의 농사매매법을 자동으로 스캔하는 웹 스캐너입니다.
KOSPI·KOSDAQ 전 종목을 분석하여 매수 시그널을 탐지합니다.

## 📐 지원 기법

| 기법 | 조건 | 목표 |
|---|---|---|
| **이평 때리기** | 112<224<448 역배열 + 112일선 돌파 | 224 → 448일선 |
| **256 기법** | 5일선 > 20일선 골든크로스 + 60일선 위 | 60일선 유지 |
| **밥그릇 3번** | 5일선 > 224일선 골든크로스 + 112>224 | 448일선 |
| **256 장기** | 5일선 > 112일선 골든크로스 | 224일선 |

## 🚀 로컬 실행

```bash
# 1. 패키지 설치
pip install -r requirements.txt

# 2. 서버 실행
uvicorn app.main:app --reload --port 8000

# 3. 브라우저에서 접속
open http://localhost:8000

# 4. 수동 스캔 (CLI)
python cron_scan.py
```

## ☁️ Render 배포

### 방법 1: render.yaml 사용 (권장)

1. GitHub에 이 레포를 push
2. [Render Dashboard](https://dashboard.render.com) → **New → Blueprint**
3. GitHub 레포 선택
4. `render.yaml`이 자동으로 Web Service + Cron Job 생성

### 방법 2: 수동 설정

**Web Service:**
- Runtime: Python 3
- Build Command: `pip install -r requirements.txt`
- Start Command: `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health Check: `/api/health`
- Disk: 1GB @ `/app/data`

**Cron Job (자동 스캔):**
- Schedule: `40 6 * * 1-5` (평일 15:40 KST)
- Command: `python cron_scan.py`
- Disk: Web Service와 동일한 디스크 마운트

## 📁 프로젝트 구조

```
dante_scanner/
├── app/
│   ├── main.py        # FastAPI 앱 & 라우터
│   ├── scanner.py     # 스캔 로직 (이평때리기·256·밥그릇)
│   └── fetcher.py     # pykrx 데이터 수집
├── templates/
│   └── index.html     # 프론트엔드 대시보드
├── static/            # 정적 파일 (CSS·JS)
├── data/              # 스캔 결과 JSON 저장
├── cron_scan.py       # 자동 스캔 스크립트
├── render.yaml        # Render 배포 설정
└── requirements.txt
```

## ⚠️ 주의사항

- **투자 책임**: 이 스캐너는 참고용입니다. 투자 결과에 대한 책임은 본인에게 있습니다.
- **API 제한**: pykrx는 KRX 공식 데이터를 사용합니다. 너무 빠른 반복 호출은 제한될 수 있습니다.
- **무료 플랜**: Render 무료 플랜은 15분 비활성 시 슬립됩니다. Cron Job은 starter 플랜 이상 필요.
- **스캔 시간**: 전 종목(약 2,500개) 스캔에 15~30분 소요됩니다.
- **장 마감 후 실행**: pykrx는 당일 데이터를 장 마감(15:30) 후 조회 가능합니다.

## 🔧 커스터마이징

`app/scanner.py`에서 조건 수정 가능:

```python
# 이평 때리기: 거래량 조건 완화
vol_surge = vol_prev > 0 and (vol_now / vol_prev) >= 1.2  # 1.5 → 1.2

# 256기법: 60일선 조건 제거 (주가 아래여도 허용)
if golden_cross:  # and above_ma60 제거
```

## 📊 API 엔드포인트

| Method | Path | 설명 |
|---|---|---|
| `GET` | `/` | 대시보드 |
| `POST` | `/api/scan` | 전체 스캔 시작 |
| `GET` | `/api/results` | 최신 결과 조회 |
| `GET` | `/api/status` | 스캔 진행 상태 |
| `GET` | `/api/health` | 헬스체크 |
