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
- 대신 형식 견본(`keywords.example.csv`)과 그룹 단위 결과 CSV를 공개합니다.
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
