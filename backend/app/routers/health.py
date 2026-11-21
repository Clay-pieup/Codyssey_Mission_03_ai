"""
서버 상태 확인 창구.

Render 무료 서버는 한동안 요청이 없으면 잠든다. 프론트는 이 주소로 "깨어났는지"를 먼저 확인하고,
응답이 늦으면 '서버를 깨우는 중' 안내를 띄운다(U9~U11). 배포 직후 동작 확인에도 쓴다(U5).
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health():
    """서버가 살아 있으면 {"status": "ok"}를 돌려준다."""
    return {"status": "ok"}
