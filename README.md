# stock-farming-scanner v1.7

농사매매법 KRX 스캐너입니다.

## 반영사항
- seed_tickers를 코스피/코스닥 중대형·중소형 혼합으로 대폭 확장
- 최근 20일 평균 거래대금 기준 완화: main 10억, sub 5억, hot 3억 수준
- 224일선 하단 5% 이내 종목 우선 노출 보너스 적용
- 대형주는 `group=LARGE_CAP`, 중소형주는 `group=SMALL_MID`로 분리
- `/hot`, `/hot/tiny` 엔드포인트 추가

## 주요 엔드포인트
- `/main` : 엄격한 A타입 실매수 후보
- `/main/tiny` : main 요약
- `/sub` : 조건 근접 관찰 후보 TOP 랭킹
- `/sub/tiny` : sub 요약
- `/hot` : 224일선 하단 근접·수급 유입·섹터 중립 이상 빠른 후보
- `/hot/tiny` : hot 요약
- `/summary` : main/sub 요약
- `/health` : 서버 상태

## Render 명령어
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
