"""
FastAPI 앱의 시작점.

실행(로컬, backend 폴더에서): uvicorn app.main:app --reload
실행(Render): uvicorn app.main:app --host 0.0.0.0 --port $PORT
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import ALLOWED_ORIGINS
from app.routers import health

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
