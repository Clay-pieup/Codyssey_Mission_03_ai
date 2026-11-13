"""
대화 기록 API 창구: 저장 / 목록 / 불러오기 / 삭제.

창구는 ① 입력을 받아(검증은 스키마가) ② 서비스 함수에 넘기고 ③ 서비스의 예외를 HTTP 상태 코드로 바꾼다.
"""
from fastapi import APIRouter, HTTPException, Query, Response

from app.schemas.conversation import ConversationDetail, ConversationIn, ConversationListItem
from app.services import conversation_service
from app.services.conversation_service import ConversationNotFoundError

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("", response_model=ConversationDetail, status_code=201, summary="새 대화 저장")
def create_conversation(item: ConversationIn):
    """항상 새 대화를 만든다. 제목을 생략하면 첫 질문 앞 30자로 정한다."""
    return conversation_service.create_conversation(item)


@router.get("", response_model=list[ConversationListItem], summary="대화 목록(최근에 바뀐 순, 메시지 제외)")
def list_conversations(limit: int = Query(20, ge=1, le=100, description="최대 건수(1~100)")):
    """제목·메시지 수·시각만 돌려준다. 메시지 전체는 대화 하나 불러오기로 받는다."""
    return conversation_service.list_conversations(limit)


@router.get("/{conversation_id}", response_model=ConversationDetail, summary="대화 하나 불러오기(메시지 전체)")
def get_conversation(conversation_id: str):
    try:
        return conversation_service.get_conversation(conversation_id)
    except ConversationNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))


@router.delete("/{conversation_id}", status_code=204, summary="대화 삭제")
def delete_conversation(conversation_id: str):
    try:
        conversation_service.delete_conversation(conversation_id)
    except ConversationNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))
    return Response(status_code=204)   # 성공: 돌려줄 내용 없음
