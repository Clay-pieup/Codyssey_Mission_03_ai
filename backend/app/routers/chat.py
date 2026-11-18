"""
AI 대화 API 창구. (U7-2: 시스템 프롬프트 미리보기 / U7-3: POST /api/chat 추가 예정)
"""
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from app.services import prompt_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.get("/system-prompt", response_class=PlainTextResponse, summary="시스템 프롬프트 미리보기(GPT에 들어가는 글)")
def get_system_prompt():
    """지금의 데이터 요약으로 만든 시스템 프롬프트를 그대로 보여 준다. 줄바꿈이 보이도록 일반 글(text)로 돌려준다."""
    return prompt_service.get_system_prompt()
