"""
AI 대화 API 창구: 질문하기(POST /api/chat) / 시스템 프롬프트 미리보기.

창구는 ① 입력을 받아(검증은 스키마가) ② 서비스에 넘기고 ③ 서비스의 예외를 HTTP 상태 코드로 바꾼다.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from app.schemas.chat import ChatIn, ChatOut
from app.services import chat_service, prompt_service
from app.services.chat_service import ChatFailedError, ChatUnavailableError, DailyLimitError
from app.services.conversation_service import ConversationFullError, ConversationNotFoundError

router = APIRouter(prefix="/api/chat", tags=["chat"])

# 설명서(/docs)에 실패 경우를 표시하기 위한 안내. 실제 상태 코드는 아래 except가 만든다.
CHAT_ERRORS = {
    404: {"description": "conversation_id의 대화가 없음"},
    409: {"description": "대화 하나의 메시지 상한(100개) 초과 → 새 대화 필요"},
    429: {"description": "오늘 AI 대화 사용량(200회) 초과"},
    502: {"description": "GPT 호출 실패(시간 초과·한도·키 오류) — 저장하지 않음"},
    503: {"description": "서버에 OpenAI 키가 설정되지 않음"},
}


@router.post("", response_model=ChatOut, summary="AI에게 질문하기(요약 주입 + 대화 자동 저장)", responses=CHAT_ERRORS)
def chat(item: ChatIn):
    """conversation_id를 생략하면 새 대화, 보내면 그 대화에 이어서 묻고 저장한다."""
    try:
        return chat_service.chat(item)
    except ConversationNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except ConversationFullError as error:
        raise HTTPException(status_code=409, detail=str(error))
    except DailyLimitError as error:
        raise HTTPException(status_code=429, detail=str(error))
    except ChatFailedError as error:
        raise HTTPException(status_code=502, detail=str(error))
    except ChatUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error))


@router.get("/system-prompt", response_class=PlainTextResponse, summary="시스템 프롬프트 미리보기(GPT에 들어가는 글)")
def get_system_prompt():
    """지금의 데이터 요약으로 만든 시스템 프롬프트를 그대로 보여 준다. 줄바꿈이 보이도록 일반 글(text)로 돌려준다."""
    return prompt_service.get_system_prompt()
