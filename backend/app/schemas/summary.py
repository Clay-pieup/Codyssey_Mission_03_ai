"""
요약(GET /api/data/summary)의 응답 모양.

이 요약은 U7에서 AI의 시스템 프롬프트에 그대로 들어간다 → 여기 담긴 것이 곧 AI가 답할 수 있는 범위다.
"""
import datetime as dt

from pydantic import BaseModel, Field


class Extreme(BaseModel):
    """최대·최소 주: 값만이 아니라 '언제'인지도 함께 준다."""

    date: dt.date = Field(description="그 주의 시작일(월요일)")
    value: int


class Metrics(BaseModel):
    total: int = Field(description="기간 전체 합계(회)")
    average: int = Field(description="주 평균(회)")
    max: Extreme
    min: Extreme


class Changes(BaseModel):
    """전년 같은 기간 대비 변화율(%). 비교할 작년 값이 없으면 null."""

    recent_4w_vs_last_year_pct: float | None
    recent_12w_vs_last_year_pct: float | None


class SeriesSummary(BaseModel):
    name: str = Field(description="'전체(6그룹 합계)' 또는 그룹명")
    period: str = Field(description="첫 주 시작일 ~ 마지막 주 끝(일요일)")
    count: int = Field(description="레코드 수")
    weeks: int = Field(description="주 수")
    metrics: Metrics | None
    trend: str = Field(description="예: '최근 4주 유지(-2.2%), 최근 12주 증가(+6.2%) — 전년 같은 기간 대비'")
    changes: Changes


class DataSummary(SeriesSummary):
    groups: list[SeriesSummary] = Field(description="6개 그룹 각각의 요약")
    computed_at: dt.datetime = Field(description="이 요약을 계산한 시각(한국 시간). 같은 값이 반복되면 기억(캐시)에서 꺼낸 것")
