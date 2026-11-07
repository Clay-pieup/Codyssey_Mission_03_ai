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

> 키를 어느 `.env`에 둘지는 U1-a·U3에서 확정 후 추가합니다.

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
