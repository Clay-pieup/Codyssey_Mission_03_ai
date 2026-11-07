"""
data 전체를 요약한다(전체 + 6그룹). 결과는 서버가 기억(캐시)해 두고 재사용한다.

- 비용: 요약 1번 계산 = 문서 1,794개 읽기. 채팅마다 계산하면 무료 한도(하루 읽기 5만)가 금방 찬다.
- 기억을 버리는 조건: ① 데이터가 바뀜(번호표가 달라짐) ② 1시간이 지남(서버 밖에서 바뀐 데이터 대비)
- 추세: 계절성이 강한 데이터라 '직전 기간'이 아니라 '전년 같은 기간'과 비교한다(최근 4주, 최근 12주).
"""
import datetime as dt
import time
from collections import defaultdict
from typing import get_args

from app.schemas.data import GroupName
from app.services import data_service

CACHE_SECONDS = 3600          # 최대 1시간 기억
STEADY_BAND_PCT = 5.0         # 변화가 ±5% 안이면 '유지'
ONE_YEAR = dt.timedelta(weeks=52)   # 52주 = 364일 → 요일(월요일)이 그대로 맞는다
KST = dt.timezone(dt.timedelta(hours=9), "KST")
TOTAL_NAME = "전체(6그룹 합계)"

_cache = {"summary": None, "version": None, "at": 0.0}


def _pct_change(recent: int, before: int) -> float | None:
    if before == 0:
        return None   # 작년 값이 없으면 비율을 낼 수 없다
    return round((recent - before) / before * 100, 1)


def _label(pct: float | None) -> str:
    if pct is None:
        return "비교 불가"
    if abs(pct) < STEADY_BAND_PCT:
        return "유지"
    return "증가" if pct > 0 else "감소"


def _window_sum(weekly: dict, end: dt.date, weeks: int) -> int:
    """end 주를 포함해 거꾸로 weeks주 동안의 합계."""
    start = end - dt.timedelta(weeks=weeks - 1)
    return sum(value for date, value in weekly.items() if start <= date <= end)


def summarize_series(name: str, weekly: dict, count: int) -> dict:
    """주별 값 {월요일 날짜: 값} 하나를 요약한다. (DB를 모르는 순수 계산 → 따로 시험하기 쉽다)"""
    if not weekly:
        return {"name": name, "period": "-", "count": 0, "weeks": 0, "metrics": None,
                "trend": "데이터 없음", "changes": {"recent_4w_vs_last_year_pct": None, "recent_12w_vs_last_year_pct": None}}
    first, last = min(weekly), max(weekly)
    total = sum(weekly.values())
    max_date = max(weekly, key=weekly.get)
    min_date = min(weekly, key=weekly.get)

    pct_4w = _pct_change(_window_sum(weekly, last, 4), _window_sum(weekly, last - ONE_YEAR, 4))
    pct_12w = _pct_change(_window_sum(weekly, last, 12), _window_sum(weekly, last - ONE_YEAR, 12))

    def fmt(pct):
        return "" if pct is None else f"({pct:+.1f}%)"

    return {
        "name": name,
        "period": f"{first} ~ {last + dt.timedelta(days=6)}",   # 마지막 주의 끝(일요일)까지
        "count": count,
        "weeks": len(weekly),
        "metrics": {
            "total": total,
            "average": round(total / len(weekly)),
            "max": {"date": max_date, "value": weekly[max_date]},
            "min": {"date": min_date, "value": weekly[min_date]},
        },
        "trend": f"최근 4주 {_label(pct_4w)}{fmt(pct_4w)}, 최근 12주 {_label(pct_12w)}{fmt(pct_12w)} — 전년 같은 기간 대비",
        "changes": {"recent_4w_vs_last_year_pct": pct_4w, "recent_12w_vs_last_year_pct": pct_12w},
    }


def build_summary(rows: list[dict]) -> dict:
    """data 문서 목록 → 전체 + 그룹별 요약."""
    total_weekly = defaultdict(int)                        # 날짜 → 6그룹 합계
    group_weekly = defaultdict(lambda: defaultdict(int))   # 그룹 → (날짜 → 값)
    group_count = defaultdict(int)
    for row in rows:
        date = dt.date.fromisoformat(row["date"])
        total_weekly[date] += row["value"]
        group_weekly[row["memo"]][date] += row["value"]
        group_count[row["memo"]] += 1

    summary = summarize_series(TOTAL_NAME, total_weekly, len(rows))
    # 그룹 순서를 정해 둔 6그룹 순서로 고정(Firestore는 무작위 ID 순서로 돌려주므로 그대로 두면 매번 순서가 바뀐다)
    order = [name for name in get_args(GroupName) if name in group_weekly]
    summary["groups"] = [summarize_series(name, group_weekly[name], group_count[name]) for name in order]
    summary["computed_at"] = dt.datetime.now(KST)
    return summary


def get_summary() -> dict:
    """기억이 쓸 만하면 그대로, 아니면 data 전체를 읽어 새로 계산한다."""
    version = data_service.data_version()   # 읽기 '전'의 번호표를 기억해야, 계산 도중 바뀐 것도 다음에 잡아낸다
    fresh = (
        _cache["summary"] is not None
        and _cache["version"] == version
        and time.monotonic() - _cache["at"] < CACHE_SECONDS
    )
    if fresh:
        return _cache["summary"]
    summary = build_summary(data_service.read_all())
    _cache.update(summary=summary, version=version, at=time.monotonic())
    return summary
