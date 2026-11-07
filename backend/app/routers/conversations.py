"""
대화 기록 API 창구: 저장 / 목록. (불러오기·삭제는 U6-2)

창구는 ① 입력을 받아(검증은 스키마가) ② 서비스 함수에 넘긴다.
"""
from fastapi import APIRouter, Query

from app.schemas.conversation import ConversationDetail, ConversationIn, ConversationListItem
from app.services import conversation_service

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("", response_model=ConversationDetail, status_code=201, summary="새 대화 저장")
def create_conversation(item: ConversationIn):
    """항상 새 대화를 만든다. 제목을 생략하면 첫 질문 앞 30자로 정한다."""
    return conversation_service.create_conversation(item)


@router.get("", response_model=list[ConversationListItem], summary="대화 목록(최근에 바뀐 순, 메시지 제외)")
def list_conversations(limit: int = Query(20, ge=1, le=100, description="최대 건수(1~100)")):
    """제목·메시지 수·시각만 돌려준다. 메시지 전체는 대화 하나 조회(U6-2)로 받는다."""
    return conversation_service.list_conversations(limit)
