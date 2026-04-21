# 📊 제이드 코인 스캐너 v1.0.0

> **업비트 KRW 마켓 전용** — 제이드 파동 심화 이론 기반 RSI 다이버전스 연계 + Fibonacci 스캐너

---

## 🎯 핵심 분석 이론 (PDF 기반)

### 파동의 정의
| 파동 | 특징 | 목적 |
|------|------|------|
| 상승 파동 | 전저점 미이탈, 저점 상승 | 전고점 돌파 |
| 하락 파동 | 전고점 미갱신, 고점 하락 | 전저점 갱신 |
| 잔 파동 | 횡보 (박스권) | 방향 전환 준비 |

### RSI 다이버전스 연계 (핵심)
```
상승 다이버전스: 지수 저점 하락 + RSI 저점 상승 → 롱 신호
하락 다이버전스: 지수 고점 상승 + RSI 고점 하락 → 숏 신호
```

**중요**: RSI가 과매도/과매수 구간을 **"쾅" 하며 돌파**하는 시점에서만 유효  
(점선 = 70/30 기준선, 중간 구간 다이버전스는 확률 낮음)

**3점 연계 = 최강 신호** (PDF 강조)

### 피보나치 되돌림
```
진입 대기: 0.618 ~ 0.786 구간
손절 라인: 피보나치 1 (절대 방어선, 이탈 시 더 큰 파동 고려)
TP1:       1.272 연장선
TP2:       1.618 연장선
```

### 매매 원칙
1. **근거 있는 자리만 진입** (다이버전스 연계 + 피보나치 구간)
2. **역지정(손절) 없는 매매 금지** → 피보나치 1 자리
3. **분할 매수** 습관화
4. 애매할 때 → 주기 한 단계 축소 (1h → 30m)
5. 피보나치 1 이탈 시 → 더 큰 파동으로 재계산

---

## 🚀 빠른 시작

### 로컬 실행
```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 서버 시작
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 3. 브라우저에서 확인
open http://localhost:8000
```

### Docker 실행
```bash
docker build -t jade-scanner .
docker run -p 8000:8000 jade-scanner
```

---

## 📡 API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/` | 대시보드 (HTML) |
| GET | `/health` | 서비스 상태 |
| GET | `/scan/main` | 메인 스캔 (엄격한 기준) |
| GET | `/scan/main/top` | 메인 Top Picks |
| GET | `/scan/sub` | 서브 스캔 (유연한 기준) |
| GET | `/scan/sub/top` | 서브 Top Picks |
| GET | `/scan/symbol/{symbol}` | 단일 종목 분석 |
| GET | `/docs` | Swagger UI |

### 쿼리 파라미터
```
/scan/main?symbols=KRW-BTC,KRW-ETH,KRW-XRP
/scan/symbol/KRW-BTC?mode=sub
```

---

## 🏗️ 분석 파이프라인

```
1. Universe 수집    : 업비트 KRW 상위 거래량 120개
        ↓
2. Prefilter        : 1h RSI 다이버전스 빠른 점수 → 상위 60개
        ↓
3. Quick Gate       : bull_rank 기준 Full 분석 대상 선별
        ↓
4. Full Analysis    : 1h + 30m + 4h 다이버전스 + Fib + 진입 확인
        ↓
5. Practical Filter : RR / TP% / SL% 실전 기준 적용
        ↓
6. Top Picks        : 최종 상위 랭킹 (최대 5개)
```

### 스코어링 기준
| 조건 | 점수 |
|------|------|
| 1h 다이버전스 연계 (3점) | +34~52 |
| 30m 다이버전스 연계 | +14 |
| 4h 방향 확인 | +10 |
| Fib 0.618~0.786 진입 구간 | +18 |
| Fib 핵심 구간 인접 | +9~14 |
| RSI 극단 구간 | +8~12 |
| 거래량 증가 | +8 |
| 목표 방향 공간 | +5 |

---

## ⚙️ 실전 필터 기준

### Main 스캔
| 지표 | 기준 |
|------|------|
| R:R (TP2) | ≥ 2.0 |
| SL 폭 | ≥ 1.2% |
| TP1 | ≥ 3.0% |
| TP2 | ≥ 5.0% |

### Sub 스캔
| 지표 | 기준 |
|------|------|
| R:R (TP2) | ≥ 1.8 |
| SL 폭 | ≥ 1.0% |
| TP1 | ≥ 2.4% |
| TP2 | ≥ 4.5% |

---

## 🌐 Render 배포

### 1. GitHub에 올리기
```bash
git init
git add .
git commit -m "feat: jade scanner v1.0.0"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/jade-scanner.git
git push -u origin main
```

### 2. Render 설정
1. [render.com](https://render.com) → New Web Service
2. GitHub 저장소 연결
3. 설정:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Region**: Singapore (업비트 API 레이턴시 최적)
4. Deploy

---

## 📁 프로젝트 구조

```
jade_scanner_v1/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI 앱 + 대시보드
│   ├── config.py        # 설정값
│   ├── models.py        # Pydantic 모델
│   └── services/
│       ├── __init__.py
│       ├── upbit_client.py   # 업비트 API 클라이언트
│       ├── indicators.py     # RSI 등 기술 지표
│       ├── swings.py         # 스윙 고점/저점 감지
│       ├── divergence.py     # 다이버전스 연계 감지
│       ├── fibonacci.py      # 피보나치 되돌림
│       └── scanner.py        # 핵심 스캔 엔진
├── requirements.txt
├── render.yaml
├── Procfile
├── runtime.txt
├── .gitignore
└── README.md
```

---

## ⚠️ 주의사항

- 이 스캐너는 **투자 보조 도구**입니다
- 모든 투자 판단은 **본인 책임**입니다
- **역지정(손절) 없는 매매는 절대 금지**
- 차트에 100%는 없습니다 — 반드시 분할 매수 + 손절 설정

---

*제이드 파동 심화 이론 기반 | 차트로 먹고살기 (coinfolio.kr)*
