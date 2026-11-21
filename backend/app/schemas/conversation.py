"""
conversations 컬렉션의 입력·출력 모양(Pydantic 스키마).

입력 규칙(엄격): 대화 1개를 Firestore 문서 1개에 담으므로(문서 크기 한도 1MB) 크기에 상한을 둔다.
- role    : user(사용자) 또는 assistant(AI)만. AI에게 주는 지시문(system)은 요약으로 매번 새로 만들므로 저장하지 않는다.
- content : 1~4,000자, 공백만 있으면 거절
- messages: 한 번에 1~100개
- title   : 보내면 1~100자. 안 보내면 서비스가 첫 질문으로 만든다.
규칙에 어긋나면 서비스 코드를 실행하기 전에 422로 돌려보낸다.
"""
import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Role = Literal["user", "assistant"]


class MessageIn(BaseModel):
    """메시지 1개: 누가(role) 무엇을(content) 말했는지."""

    model_config = ConfigDict(extra="forbid")   # 정해지지 않은 칸이 섞여 오면 거절

    role: Role = Field(description="user(사용자) 또는 assistant(AI)", examples=["user"])
    content: str = Field(min_length=1, max_length=4000, description="메시지 내용(1~4,000자)",
                         examples=["최근 4주 검색량 추세 알려줘"])

    @field_validator("content")
    @classmethod
    def must_not_be_blank(cls, value: str) -> str:
        if not value.strip():   # strip(): 앞뒤 공백·줄바꿈을 지운 결과가 비었으면 공백뿐인 내용
            raise ValueError("content가 공백뿐입니다.")
        return value


class ConversationIn(BaseModel):
    """대화 저장(POST) 때 받는 데이터."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(None, min_length=1, max_length=100,
                              description="대화 제목(1~100자). 생략하면 첫 질문 앞 30자로 자동")
    messages: list[MessageIn] = Field(min_length=1, max_length=100, description="메시지 목록(1~100개)")

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("title이 공백뿐입니다. 자동 제목을 원하면 title 칸을 빼고 보내세요.")
        return value.strip()


class MessageOut(BaseModel):
    """돌려줄 때의 메시지 모양(출력은 검사하지 않고 그대로 보여 준다)."""

    role: str
    content: str


class ConversationListItem(BaseModel):
    """목록용: 메시지 내용은 빼고 가벼운 칸만(U6 결정 A)."""

    id: str = Field(description="Firestore 문서 ID")
    title: str
    message_count: int
    created_at: dt.datetime = Field(description="만든 시각(한국 시간)")
    updated_at: dt.datetime = Field(description="마지막으로 바뀐 시각(한국 시간)")


class ConversationDetail(ConversationListItem):
    """대화 하나 전체: 목록 칸 + 메시지 전체."""

    messages: list[MessageOut]
