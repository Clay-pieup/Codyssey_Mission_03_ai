"""
FastAPI 앱의 시작점.

실행(로컬, backend 폴더에서): uvicorn app.main:app --reload
실행(Render): uvicorn app.main:app --host 0.0.0.0 --port $PORT
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.core.config import ALLOWED_ORIGINS
from app.routers import conversations, data, health

app = FastAPI(
    title="검색 데이터 AI 비서 API",
    description="그룹별 주간 추정 검색량을 관리하고, 그 요약을 바탕으로 AI와 대화하는 API",
    version="0.1.0",
)

# CORS: 브라우저가 '다른 주소의 화면'에서 온 요청의 응답을 넘겨줘도 되는지 판단하는 규칙.
# 허용 목록은 설정(.env / Render 환경변수)에서만 읽는다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "DELETE"],   # 과제 API가 쓰는 요청 종류만
    allow_headers=["Content-Type"],                    # 프론트가 JSON을 보낼 때 필요한 머리말만
)

# 라우터(창구) 연결 — 기능이 늘 때마다 여기에 한 줄씩 추가한다.
app.include_router(health.router)
app.include_router(data.router)
app.include_router(conversations.router)


# 맨 앞 주소(/)로 들어오면 API 설명서(/docs)로 보낸다.
# 배포 주소를 그대로 열었을 때 'Not Found' 대신 설명서가 보이게 하기 위함. 설명서 목록에는 넣지 않는다.
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")
