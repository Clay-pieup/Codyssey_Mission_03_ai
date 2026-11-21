"""
통계(GET /api/data/statistics)의 응답 모양 — 보너스.
"""
import datetime as dt

from pydantic import BaseModel, Field


class PeriodTotal(BaseModel):
    period: str = Field(description="'2021' 또는 '2021-01'")
    total: int
    groups: dict[str, int] = Field(description="그룹명 → 합계")
    partial: bool | None = Field(None, description="연도별에만: 12달이 다 있지 않은 해(예: 2026년은 9월까지)")


class Share(BaseModel):
    name: str
    all_time_pct: float
    previous_52w_pct: float
    recent_52w_pct: float
    change_pt: float = Field(description="최근 52주 - 직전 52주 (%p)")


class MonthAverage(BaseModel):
    month: int = Field(description="1~12월")
    weekly_average: int = Field(description="그 달에 시작하는 주들의 평균(6그룹 합계)")


class GroupSeason(BaseModel):
    name: str
    peak_month: int
    low_month: int
    peak_to_low_ratio: float | None = Field(description="성수기 주평균 ÷ 비수기 주평균")


class Seasonality(BaseModel):
    overall: list[MonthAverage] = Field(description="주평균이 높은 달부터")
    groups: list[GroupSeason]


class DataStatistics(BaseModel):
    yearly: list[PeriodTotal]
    monthly: list[PeriodTotal] = Field(description="주 시작일이 속한 달 기준 근사 합계")
    share: list[Share]
    seasonality: Seasonality
    computed_at: dt.datetime
