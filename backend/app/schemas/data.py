"""
data 컬렉션의 입력·출력 모양(Pydantic 스키마).

입력 규칙(엄격): 이 데이터는 "주간 × 6그룹" 추정 검색량이므로 그 성격을 규칙으로 못 박는다.
- date : 실제 날짜이면서 월요일(주 시작일)
- value: 0 이상의 정수(그 주의 추정 검색 횟수)
- memo : 6개 키워드 그룹 중 하나
규칙에 어긋나면 FastAPI가 서비스 코드를 실행하기 전에 422로 돌려보낸다 → 잘못된 값이 DB에 들어가지 못한다.
"""
import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# 6개 그룹 이름 — U1 결과(weekly_group.csv)의 memo 값과 정확히 같아야 한다
GroupName = Literal["브랜드 키워드", "핵심 키워드", "일반숙박", "펜션/풀빌라", "주변명소", "대형 키워드"]


class DataIn(BaseModel):
    """추가(POST)·수정(PUT) 때 받는 데이터."""

    model_config = ConfigDict(extra="forbid")   # 정해지지 않은 칸이 섞여 오면 거절

    date: dt.date = Field(description="주 시작일(월요일), YYYY-MM-DD", examples=["2026-09-21"])
    value: int = Field(ge=0, strict=True, description="그 주의 추정 검색량(회)", examples=[19406])  # strict: true·"123" 같은 숫자 아닌 값은 거절
    memo: GroupName = Field(description="키워드 그룹", examples=["대형 키워드"])

    @field_validator("date")
    @classmethod
    def must_be_monday(cls, value: dt.date) -> dt.date:
        if value.weekday() != 0:   # 월=0 … 일=6
            raise ValueError("date는 주 시작일(월요일)이어야 합니다.")
        return value


class DataOut(BaseModel):
    """돌려줄 때의 모양: 저장된 값 + 문서 ID. (출력은 검사하지 않고 그대로 보여 준다)"""

    id: str = Field(description="Firestore 문서 ID")
    date: dt.date
    value: int
    memo: str
