"""
AI 대화(POST /api/chat)의 입력·출력 모양.

입력 규칙: 질문은 U6 메시지와 같은 규칙(1~4,000자, 공백뿐이면 거절), 모르는 칸 거절.
conversation_id를 보내면 그 대화에 이어서, 안 보내면 새 대화로 저장한다.
"""
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatIn(BaseModel):
    # json_schema_extra: 설명서(/docs) 입력 칸의 예시를 '질문 한 줄'로 고정한다.
    # 없으면 Swagger가 칸마다 예시를 지어내 "conversation_id": "string"이 들어가고, 그대로 보내면 404가 난다.
    model_config = ConfigDict(extra="forbid", json_schema_extra={"examples": [{"message": "최근 4주 검색량 추세 알려줘"}]})

    message: str = Field(min_length=1, max_length=4000, description="사용자 질문(1~4,000자)",
                         examples=["최근 4주 검색량 추세 알려줘"])
    conversation_id: str | None = Field(None, min_length=1,
                                        description="이어서 대화할 대화 ID. 생략하면 새 대화")

    @field_validator("message")
    @classmethod
    def must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message가 공백뿐입니다.")
        return value


class Usage(BaseModel):
    """이번 GPT 호출에 쓴 토큰 수(= 요금 계산 기준)."""

    prompt_tokens: int = Field(description="입력(시스템 프롬프트 + 이전 메시지 + 질문)")
    completion_tokens: int = Field(description="출력(답)")
    total_tokens: int


class ChatOut(BaseModel):
    conversation_id: str = Field(description="저장된 대화 ID. 이어서 물을 때 그대로 보낸다")
    title: str
    reply: str = Field(description="AI 답")
    usage: Usage
