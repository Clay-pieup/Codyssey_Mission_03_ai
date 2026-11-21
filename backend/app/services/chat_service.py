"""
AI 대화의 흐름(미션 4-7): 하루 횟수 확인 → 이전 메시지 읽기 → 요약 쪽지 + 메시지로 GPT 호출 → 대화 자동 저장.

- HTTP를 모른다. 문제는 이 파일·conversation_service의 예외로 알리고, 상태 코드로 바꾸는 일은 라우터가 한다.
- 비용 안전장치 3겹: ① 답 길이 상한(MAX_REPLY_TOKENS) ② GPT에 보내는 이전 메시지 수(HISTORY_SIZE)
  ③ 서버 하루 호출 상한(DAILY_LIMIT). 마지막 안전장치는 OpenAI 대시보드의 월 한도다.
- U8(Function Calling)은 _ask_gpt에 '도구'를 붙이는 식으로 이 파일을 확장한다.
"""
import datetime as dt

from openai import OpenAIError

from app.core.config import OPENAI_MODEL
from app.core.openai_client import get_client
from app.schemas.chat import ChatIn, ChatOut, Usage
from app.schemas.conversation import ConversationIn
from app.services import conversation_service, prompt_service

HISTORY_SIZE = 10        # GPT에 함께 보낼 이전 메시지 수(5번 주고받기). 저장은 전부 한다
MAX_REPLY_TOKENS = 500   # 답 길이 상한 = 1회 답변 비용 상한(미션 제약: max_tokens)
TEMPERATURE = 0.3        # 낮을수록 같은 질문에 비슷하고 숫자에 충실한 답(0~2, 기본 1)
DAILY_LIMIT = 200        # 서버 하루 GPT 호출 상한. 서버 메모리에 세므로 서버가 다시 켜지면 0부터(느슨한 상한)
KST = dt.timezone(dt.timedelta(hours=9), "KST")

_usage_today = {"day": None, "count": 0}   # 오늘 날짜(한국 시간)와 그날 호출 수


class DailyLimitError(Exception):
    """오늘 GPT 호출 횟수를 다 썼다."""


class ChatUnavailableError(Exception):
    """서버 설정 문제로 GPT를 부를 수 없다(키 없음)."""


class ChatFailedError(Exception):
    """GPT 호출이 실패했다(시간 초과, 한도 초과, 키 오류 등)."""


def _take_daily_slot() -> None:
    """GPT를 부르기 '전에' 하루 횟수를 1 쓴다 → 실패한 호출도 세어 비용을 확실히 묶는다."""
    today = dt.datetime.now(KST).date()
    if _usage_today["day"] != today:   # 한국 시간으로 날짜가 바뀌었으면 0부터
        _usage_today.update(day=today, count=0)
    if _usage_today["count"] >= DAILY_LIMIT:
        raise DailyLimitError(f"오늘 AI 대화 사용량({DAILY_LIMIT}회)을 다 썼습니다. 내일 다시 이용하세요.")
    _usage_today["count"] += 1


def _ask_gpt(messages: list[dict]) -> tuple[str, Usage]:
    try:
        client = get_client()
    except RuntimeError as error:   # 키가 비어 있음 → 서버 설정 문제
        raise ChatUnavailableError(str(error))
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            max_tokens=MAX_REPLY_TOKENS,
            temperature=TEMPERATURE,
        )
    except OpenAIError as error:   # openai 패키지의 모든 오류(키·한도·시간 초과·연결)의 공통 부모
        print(f"[chat] GPT 호출 실패: {type(error).__name__}: {error}")   # Render 로그에서 원인 확인용
        raise ChatFailedError(f"AI 답을 받지 못했습니다({type(error).__name__}). 잠시 후 다시 시도하세요.")
    reply = (response.choices[0].message.content or "").strip()
    if not reply:
        raise ChatFailedError("AI가 빈 답을 보냈습니다. 다시 시도하세요.")
    usage = Usage(prompt_tokens=response.usage.prompt_tokens,
                  completion_tokens=response.usage.completion_tokens,
                  total_tokens=response.usage.total_tokens)
    return reply, usage


def chat(item: ChatIn) -> ChatOut:
    # 1) 이어 대화면 이전 메시지를 읽고, 자리가 있는지 GPT를 부르기 전에 확인한다(없으면 404 / 409)
    conversation = None
    previous: list[dict] = []
    if item.conversation_id:
        conversation = conversation_service.get_conversation(item.conversation_id)
        conversation_service.check_room(conversation.message_count, adding=2)
        previous = [message.model_dump() for message in conversation.messages]

    # 2) 하루 횟수 확인(넘으면 429)
    _take_daily_slot()

    # 3) GPT에 보낼 목록 = [요약 쪽지] + 최근 10개 + 새 질문
    messages = [
        {"role": "system", "content": prompt_service.get_system_prompt()},
        *previous[-HISTORY_SIZE:],
        {"role": "user", "content": item.message},
    ]
    reply, usage = _ask_gpt(messages)   # 실패하면 여기서 예외 → 아래 저장까지 가지 않는다(결정 3)

    # 4) 성공했을 때만 질문·답을 함께 저장한다
    new_messages = [{"role": "user", "content": item.message}, {"role": "assistant", "content": reply}]
    if conversation is None:
        saved = conversation_service.create_conversation(ConversationIn(messages=new_messages))
        conversation_id, title = saved.id, saved.title
    else:
        conversation_service.append_messages(conversation.id, previous, new_messages)
        conversation_id, title = conversation.id, conversation.title

    return ChatOut(conversation_id=conversation_id, title=title, reply=reply, usage=usage)
