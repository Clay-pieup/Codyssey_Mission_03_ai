"""
요약보다 자세한 통계(보너스): A 연도별·월별 합계, B 그룹 점유율과 변화, C 계절성.

- summary_service의 기억(원본 데이터)을 그대로 쓴다 → Firestore 추가 읽기 없음.
- 월별 합계는 '주 시작일이 속한 달'로 넣는 근사치다(Firestore에는 주 단위로만 저장돼 있다).
  정확한 월 합계는 data_pipeline/output/monthly_group.csv에 따로 있다.
"""
import datetime as dt
from collections import defaultdict
from typing import get_args

from app.schemas.data import GroupName
from app.services import summary_service

ONE_YEAR = dt.timedelta(weeks=52)


def _ordered_groups(names) -> list[str]:
    return [name for name in get_args(GroupName) if name in names]


def _period_totals(rows: list[dict], key) -> list[dict]:
    """rows를 key(날짜 → '2021' 또는 '2021-01')로 묶어 전체·그룹별 합계를 낸다."""
    totals = defaultdict(lambda: defaultdict(int))
    for row in rows:
        totals[key(row["date"])][row["memo"]] += row["value"]
    result = []
    for period in sorted(totals):
        groups = totals[period]
        result.append({"period": period, "total": sum(groups.values()),
                       "groups": {name: groups[name] for name in _ordered_groups(groups)}})
    return result


def _shares(rows: list[dict], start: dt.date | None, end: dt.date) -> dict:
    """start 초과 ~ end 이하 기간의 그룹별 점유율(%)."""
    sums = defaultdict(int)
    for row in rows:
        date = dt.date.fromisoformat(row["date"])
        if (start is None or date > start) and date <= end:
            sums[row["memo"]] += row["value"]
    whole = sum(sums.values())
    return {name: (round(value / whole * 100, 1) if whole else 0.0) for name, value in sums.items()}


def _seasonality(weekly: dict) -> dict:
    """{월요일 날짜: 값} → 달(1~12)별 주평균."""
    by_month = defaultdict(list)
    for date, value in weekly.items():
        by_month[date.month].append(value)
    return {month: sum(values) / len(values) for month, values in by_month.items()}


def build_statistics(rows: list[dict], computed_at: dt.datetime) -> dict:
    if not rows:
        return {"yearly": [], "monthly": [], "share": [], "seasonality": {"overall": [], "groups": []},
                "computed_at": computed_at}
    dates = [dt.date.fromisoformat(row["date"]) for row in rows]
    last = max(dates)

    # A. 연도별·월별 합계 — 12달이 다 있지 않은 해는 partial로 표시
    yearly = _period_totals(rows, key=lambda d: d[:4])
    months_in_year = defaultdict(set)
    for date in dates:
        months_in_year[str(date.year)].add(date.month)
    for item in yearly:
        item["partial"] = len(months_in_year[item["period"]]) < 12
    monthly = _period_totals(rows, key=lambda d: d[:7])

    # B. 점유율: 전체 기간 / 직전 52주 / 최근 52주
    all_time = _shares(rows, None, last)
    previous = _shares(rows, last - 2 * ONE_YEAR, last - ONE_YEAR)
    recent = _shares(rows, last - ONE_YEAR, last)
    share = [{"name": name, "all_time_pct": all_time.get(name, 0.0), "previous_52w_pct": previous.get(name, 0.0),
              "recent_52w_pct": recent.get(name, 0.0),
              "change_pt": round(recent.get(name, 0.0) - previous.get(name, 0.0), 1)}
             for name in _ordered_groups(all_time)]

    # C. 계절성: 전체는 달별 주평균 순위, 그룹은 성수기·비수기·배율
    total_weekly, group_weekly = defaultdict(int), defaultdict(lambda: defaultdict(int))
    for row, date in zip(rows, dates):
        total_weekly[date] += row["value"]
        group_weekly[row["memo"]][date] += row["value"]
    overall = _seasonality(total_weekly)
    overall_rank = [{"month": month, "weekly_average": round(avg)}
                    for month, avg in sorted(overall.items(), key=lambda item: item[1], reverse=True)]
    group_season = []
    for name in _ordered_groups(group_weekly):
        season = _seasonality(group_weekly[name])
        peak, low = max(season, key=season.get), min(season, key=season.get)
        group_season.append({"name": name, "peak_month": peak, "low_month": low,
                             "peak_to_low_ratio": round(season[peak] / season[low], 1) if season[low] else None})

    return {"yearly": yearly, "monthly": monthly, "share": share,
            "seasonality": {"overall": overall_rank, "groups": group_season},
            "computed_at": computed_at}


def get_statistics() -> dict:
    cache = summary_service.snapshot()
    if cache["statistics"] is None:
        cache["statistics"] = build_statistics(cache["rows"], cache["loaded_at"])
    return cache["statistics"]
