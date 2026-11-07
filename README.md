# Codyssey_Mission_03_ai — 검색 데이터 기반 AI 비서

코디세이 AI 네이티브 경남 1기 — AI 응용 학습 미션 「AI Agent 개발: 나만의 AI 비서 구축」 저장소입니다.
설계 메모와 단위별 해설은 [docs/작업기록.md](docs/작업기록.md)에 있습니다.

## 1. 실행 환경
| 항목 | 버전/내용 |
|---|---|
| OS | Windows 11 (개발) / Linux (Render 서버) |
| Python | 3.14 (로컬 3.14.7, Render 3.14) |
| Git | 필수 |

## 2. 준비할 계정·키
| 서비스 | 용도 | 필요한 값 |
|---|---|---|
| NAVER API HUB (데이터랩) | 주간 검색 지수 수집 | Client ID, Client Secret |
| 네이버 검색광고 API | 최근 30일 실제 검색수 | CUSTOMER_ID, 액세스라이선스, 비밀키 |
| OpenAI | GPT 채팅 | API Key |
| Firebase (Firestore) | 데이터·대화 저장 | 서비스 계정 키(.json) — **레포 밖에 보관** |
| Render / Vercel | 백엔드 / 프론트 배포 | 계정 |

> 네이버 키 5개는 `data_pipeline/.env`, OpenAI·Firebase 키 경로는 `backend/.env`(U3)에 둡니다. 각 폴더의 `.env.example`을 복사해 값을 채웁니다.

## 3. 처음 설치 (PowerShell)
```
git clone https://github.com/Clay-pieup/Codyssey_Mission_03_ai.git
cd Codyssey_Mission_03_ai
python -m venv .venv
.venv\Scripts\Activate.ps1
```
> 패키지 설치는 단위별로 추가합니다.

## 4. 폴더 구조
```
data_pipeline/  수집·보정 (로컬 전용, 배포 안 함)
backend/        FastAPI 서버 → Render
frontend/       HTML/CSS/JS → Vercel
docs/           설계 메모, 작업기록, 스크린샷
```

## 5. 공개하지 않는 것과 재현 범위
- 실제 키워드 목록(`data_pipeline/keywords.csv`)과 키워드별 수집 원본(`data_pipeline/raw/`)은 브랜드명이 포함되어 비공개입니다.
- 대신 형식 견본(`keywords.example.csv`)과 그룹 단위 결과(`data_pipeline/output/`의 CSV 2개와 검증 그래프)를 공개합니다.
  → 제3자는 **결과 CSV부터** 그대로 재현할 수 있습니다.

## 6. 데이터 수집 실행 (data_pipeline)
### 6-1. 준비
```
pip install -r data_pipeline\requirements.txt
Copy-Item data_pipeline\.env.example data_pipeline\.env
```
- 복사한 `data_pipeline\.env`에 값을 채웁니다.
- `data_pipeline\keywords.csv`를 준비합니다. 형식(`group_id, group_name, keyword`)은 `keywords.example.csv`를 참고합니다.

### 6-2. 검색광고 최근 30일 검색수 (U1-a)
```
python data_pipeline\collect_searchad.py
```
→ `data_pipeline\raw\searchad_30d_YYYYMMDD.csv`
- 조회일 기준 최근 30일 합계(PC/모바일)입니다. 조회일이 바뀌면 값도 바뀝니다.
- `< 10`은 검색수가 10 미만이라는 네이버 표기이며 원본 그대로 저장합니다.

### 6-3. 데이터랩 일간 검색 지수 (U1-b)
```
python data_pipeline\collect_datalab.py
```
→ `data_pipeline\raw\datalab_daily_YYYYMMDD.json` (원본), `.csv` (긴 표: `date, kind, name, ratio`)
- 2021-01-01 ~ 실행 전날. 키워드 65개 + 그룹 6개를 각각 따로 요청합니다(71회, 약 1분).
- `ratio`는 시리즈마다 최대값을 100으로 둔 상대 지수입니다.
- 검색이 매우 적은 날은 데이터랩이 그 날짜를 빼고 보냅니다.
- ⚠️ 6-2(검색광고)와 **같은 날** 실행해야 "최근 30일" 구간이 맞습니다.

### 6-4. 환산 배율 계산·검증 (U1-c-1)
```
python data_pipeline\calibrate.py
```
→ `data_pipeline\raw\calibration_YYYYMMDD.csv`
- `raw/`에서 6-2·6-3을 같은 날 수집한 파일 쌍 중 가장 최근 날짜를 자동으로 고릅니다.
- 배율 = 30일 실제 검색수 ÷ 같은 30일의 지수 합계 (30일 = 수집일 전날까지)
- `< 10`은 5로 계산합니다.
- 출력: 그룹 배율·민감도, 키워드 신뢰도 등급, 검증 A(1키워드 그룹 일치)·B(키워드 합산 vs 그룹)

### 6-5. 추정 검색량 결과물 (U1-c-2)
```
python data_pipeline\build_outputs.py
```
| 파일 | 공개 | 내용 |
|---|---|---|
| `output\weekly_group.csv` | 공개 | 서비스용. `date`(주 시작 월요일), `value`(추정 검색량), `memo`(그룹명) — 1,794건 |
| `output\monthly_group.csv` | 공개 | 보기용. 행=월(2021-01~2026-09), 열=6그룹 |
| `output\validation_tongyeong.png` | 공개 | 검증 그래프(통영가볼만한곳: 우리 추정 vs 외부 화면) |
| `raw\keyword_monthly_YYYYMMDD.csv` | 비공개 | 키워드 월별 + 신뢰도 등급 |

- 실행 순서: 6-2 → 6-3 (같은 날) → 6-4 → 6-5
- `value`는 실제 검색수가 아니라 **추정치**입니다. 환산 근거와 오차 범위는 [docs/작업기록.md](docs/작업기록.md)의 U1-c를 참고합니다.

## 7. 백엔드 실행 (backend)
```
pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
```
- 복사한 `backend\.env`의 `ALLOWED_ORIGINS=` 뒤에 허용할 프론트 주소를 씁니다(로컬 예: `http://localhost:5500,http://127.0.0.1:5500`).

```
cd backend
uvicorn app.main:app --reload
```
- http://127.0.0.1:8000/docs → API 설명서, `GET /api/health` → `{"status": "ok"}`
- 끄기: 터미널에서 **Ctrl+C**
- uvicorn은 **backend 폴더 안에서** 실행해야 `app.main`을 찾습니다.
- `backend\.env`에 `FIREBASE_SERVICE_ACCOUNT_PATH=`(레포 밖 서비스 계정 키 파일의 전체 경로)를 씁니다.
- Firestore 연결 시험(backend 폴더에서): `python -m scripts.check_firestore` → 1) 쓰기 2) 읽기 3) 삭제 성공이 나오면 정상

## 8. 데이터 API (U3-2)
| 요청 | 설명 | 성공 | 실패 |
|---|---|---|---|
| `POST /api/data` | 추가 `{date(월요일), value(0 이상 정수), memo(6그룹)}` | 201 | 409 중복, 422 규칙 위반 |
| `GET /api/data` | 목록(최신순). `memo`·`date_from`·`date_to`·`limit`(1~500, 기본 50) | 200 | 422 |
| `PUT /api/data/{id}` | 통째로 교체 | 200 | 404 없음, 409 중복, 422 |
| `DELETE /api/data/{id}` | 삭제 | 204 | 404 |
| `GET /api/data/summary` | 전체+6그룹 요약(AI 프롬프트 주입용). 서버가 최대 1시간 기억, 데이터가 바뀌면 다시 계산 | 200 | — |
| `GET /api/data/statistics` | ★ 연도·월별 합계, 그룹 점유율 변화(최근 52주 vs 직전 52주), 계절성. summary와 같은 기억 사용(추가 읽기 없음) | 200 | — |

- 그룹(`memo`) 거르기에는 Firestore 복합 색인(`data`: `memo` 오름차순, `date` 내림차순)이 필요합니다. 처음 호출 때 서버 터미널에 나오는 링크로 만들거나, Firebase 콘솔 [색인] 탭에서 직접 추가합니다.

## 9. 데이터 적재 (U3-3)
```
cd backend
python -m scripts.seed_data
```
- `data_pipeline/output/weekly_group.csv`(1,794건)를 Firestore `data` 컬렉션에 넣습니다.
- `data` 컬렉션이 **비어 있을 때만** 실행됩니다(중복 방지).
- 실행 순서: 6-5(CSV 생성) → 7(`backend/.env` 설정) → 9
