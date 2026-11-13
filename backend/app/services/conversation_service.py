"""
conversations 컬렉션을 실제로 다루는 '일하는 함수'들.

- data_service와 같은 원칙: HTTP를 모르고, 같은 함수를 U7 채팅·U8 AI 도구에서도 그대로 쓴다.
- 대화 1개 = 문서 1개. 메시지는 문서 안의 목록(messages)으로 저장한다(U6 결정 '가').
- 시각은 Firestore 시각 형식으로 저장하고(정렬·비교가 정확), 내보낼 때 한국 시간(KST)으로 바꾼다.
- 목록은 Firestore에서 메시지 칸을 빼고 필요한 칸만 받아온다(U6 결정 A).
  그래서 메시지 수(message_count)를 문서에 따로 적어 둔다.
"""
import datetime as dt

from google.cloud.firestore_v1 import Query

from app.core.firebase import get_db
from app.schemas.conversation import ConversationDetail, ConversationIn, ConversationListItem

COLLECTION = "conversations"
KST = dt.timezone(dt.timedelta(hours=9), "KST")
TITLE_LENGTH = 30
DEFAULT_TITLE = "새 대화"
LIST_FIELDS = ["title", "message_count", "created_at", "updated_at"]   # 목록에서 받아올 칸(messages 제외)


class ConversationNotFoundError(Exception):
    """해당 ID의 대화가 없다."""


def make_title(item: ConversationIn) -> str:
    """보낸 제목 → 없으면 첫 user 메시지 앞 30자(넘으면 '…') → user 메시지도 없으면 '새 대화'."""
    if item.title:
        return item.title
    first_question = next((m.content for m in item.messages if m.role == "user"), None)
    if first_question is None:
        return DEFAULT_TITLE
    text = " ".join(first_question.split())   # 줄바꿈·연속 공백을 공백 1칸으로 → 목록에서 한 줄로 보이게
    return text if len(text) <= TITLE_LENGTH else text[:TITLE_LENGTH] + "…"


def _to_list_item(doc_id: str, document: dict) -> ConversationListItem:
    return ConversationListItem(
        id=doc_id,
        title=document["title"],
        message_count=document["message_count"],
        created_at=document["created_at"].astimezone(KST),   # Firestore는 UTC로 돌려준다(U3-1) → 한국 시간으로
        updated_at=document["updated_at"].astimezone(KST),
    )


def create_conversation(item: ConversationIn) -> ConversationDetail:
    """항상 새 대화 문서를 만든다. 이어 저장(기존 대화에 메시지 추가)은 U7에서 추가한다."""
    now = dt.datetime.now(dt.timezone.utc)   # 시간대가 붙은 현재 시각. 같은 값을 저장·응답에 써서 다시 읽을 필요가 없다
    document = {
        "title": make_title(item),
        "messages": [message.model_dump() for message in item.messages],   # 모델 → {"role", "content"} 사전
        "message_count": len(item.messages),
        "created_at": now,
        "updated_at": now,
    }
    ref = get_db().collection(COLLECTION).document()   # 문서 ID는 Firestore가 자동 생성
    ref.set(document)
    return ConversationDetail(**_to_list_item(ref.id, document).model_dump(), messages=document["messages"])


def list_conversations(limit: int) -> list[ConversationListItem]:
    """최근에 바뀐 대화부터 최대 limit건. 읽기 비용 = 돌려준 건수(메시지를 빼도 1건 = 1읽기)."""
    query = (
        get_db().collection(COLLECTION)
        .select(LIST_FIELDS)   # 필요한 칸만 받아온다 → 메시지가 쌓여도 서버로 오는 양이 늘지 않는다
        .order_by("updated_at", direction=Query.DESCENDING)
        .limit(limit)
    )
    return [_to_list_item(doc.id, doc.to_dict()) for doc in query.stream()]


def get_conversation(conversation_id: str) -> ConversationDetail:
    """대화 하나 + 메시지 전체(U6 결정 A의 '따로 조회'). 읽기 비용 1."""
    snapshot = get_db().collection(COLLECTION).document(conversation_id).get()
    if not snapshot.exists:
        raise ConversationNotFoundError(f"ID {conversation_id} 대화가 없습니다.")
    document = snapshot.to_dict()
    return ConversationDetail(**_to_list_item(snapshot.id, document).model_dump(), messages=document["messages"])


def delete_conversation(conversation_id: str) -> None:
    ref = get_db().collection(COLLECTION).document(conversation_id)
    if not ref.get().exists:   # Firestore는 없는 문서를 지워도 오류가 없어서 직접 확인한다(U3-2와 같은 이유)
        raise ConversationNotFoundError(f"ID {conversation_id} 대화가 없습니다.")
    ref.delete()   # 메시지가 문서 안에 있으므로 문서 1개만 지우면 대화 전체가 사라진다(U6 결정 '가')
