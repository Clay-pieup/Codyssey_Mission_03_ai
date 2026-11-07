"""
U1-c-1. 시리즈별 환산 배율(지수 1 = 몇 회)을 구하고 검증한다.

    배율 = (검색광고 '최근 30일' 실제 검색수) ÷ (같은 30일의 데이터랩 지수 합계)

- 30일 구간: 검색광고 수집일의 '전날까지 30일'
- '< 10'은 5로 본다(0~9의 가운데)
- 키워드는 30일 구간 안에 데이터랩 값이 있는 날 수로 신뢰도 등급을 매긴다
- 민감도: 구간 끝을 1~3일 앞당겼을 때 배율이 몇 % 바뀌는지 함께 기록한다

실행: (레포 폴더에서) python data_pipeline\\calibrate.py
입력: raw/searchad_30d_YYYYMMDD.csv, raw/datalab_daily_YYYYMMDD.csv (같은 날짜 쌍)
출력: raw/calibration_YYYYMMDD.csv (시리즈 71개의 배율·등급·민감도) — 비공개
"""
import sys
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "raw"

SMALL_VALUE = 5       # '< 10' 을 이 값으로 본다
WINDOW_DAYS = 30      # 검색광고 '최근 30일'
SHIFTS = [1, 2, 3]    # 민감도: 구간 끝을 며칠 앞당겨 볼지


def latest_stamp():
    """raw/에서 검색광고·데이터랩 파일이 둘 다 있는 가장 최근 날짜(YYYYMMDD)를 고른다."""
    searchad = {p.stem.split("_")[-1] for p in RAW_DIR.glob("searchad_30d_*.csv")}
    datalab = {p.stem.split("_")[-1] for p in RAW_DIR.glob("datalab_daily_*.csv")}
    common = sorted(searchad & datalab)
    if not common:
        sys.exit("[중단] 같은 날짜에 수집한 searchad·datalab 파일 쌍이 raw/에 없습니다.")
    return common[-1]


def to_count(value):
    """'< 10' 같은 글자는 SMALL_VALUE로, 숫자 글자는 숫자로 바꾼다."""
    text = str(value).strip()
    return SMALL_VALUE if text.startswith("<") else float(text)


def window_sum(series, end):
    """한 시리즈에서 [end-29일, end] 30일 동안의 지수 합계와, 값이 있는 날 수를 돌려준다."""
    start = end - pd.Timedelta(days=WINDOW_DAYS - 1)
    in_window = series[(series["date"] >= start) & (series["date"] <= end)]
    return in_window["ratio"].sum(), len(in_window)


def grade(days):
    """30일 구간 안에 값이 있는 날 수 → 신뢰도 등급."""
    if days == WINDOW_DAYS:
        return "높음"
    if days >= 20:
        return "보통"
    if days >= 1:
        return "낮음"
    return "계산 불가"


def main():
    stamp = latest_stamp()

    # 1) 실제 검색수(검색광고): 키워드별, 그룹별(키워드 합)
    searchad = pd.read_csv(RAW_DIR / f"searchad_30d_{stamp}.csv", encoding="utf-8-sig", dtype=str)
    searchad["actual"] = searchad["pc_30d"].map(to_count) + searchad["mobile_30d"].map(to_count)
    keyword_actual = searchad.set_index("keyword")["actual"]
    group_actual = searchad.groupby("group_name", sort=False)["actual"].sum()
    group_of = searchad.set_index("keyword")["group_name"]

    # 2) 30일 구간: 수집일 전날까지 30일
    window_end = pd.Timestamp(searchad["collected_date"].iloc[0]) - pd.Timedelta(days=1)
    window_start = window_end - pd.Timedelta(days=WINDOW_DAYS - 1)
    print(f"30일 구간: {window_start.date()} ~ {window_end.date()}  ('< 10' = {SMALL_VALUE})")

    # 3) 일간 지수(데이터랩): (종류, 이름)별로 나눠 둔다
    daily = pd.read_csv(RAW_DIR / f"datalab_daily_{stamp}.csv", encoding="utf-8-sig", parse_dates=["date"])
    by_series = {key: part for key, part in daily.groupby(["kind", "name"], sort=False)}
    empty = daily.iloc[0:0]   # 데이터가 한 줄도 없는 시리즈용 빈 표

    # 4) 시리즈 71개의 배율 계산
    expected = [("keyword", k) for k in keyword_actual.index] + [("group", g) for g in group_actual.index]
    rows = []
    for kind, name in expected:
        series = by_series.get((kind, name), empty)
        actual = keyword_actual[name] if kind == "keyword" else group_actual[name]
        ratio_sum, days = window_sum(series, window_end)
        factor = actual / ratio_sum if ratio_sum > 0 else None
        row = {
            "kind": kind,
            "name": name,
            "group": group_of[name] if kind == "keyword" else name,
            "actual_30d": actual,
            "window_ratio_sum": round(ratio_sum, 5),
            "days_in_window": days,
            "grade": grade(days) if kind == "keyword" else "그룹",
            "factor": factor,
        }
        for shift in SHIFTS:   # 구간 끝을 shift일 앞당기면 배율이 몇 % 바뀌나
            shifted_sum, _ = window_sum(series, window_end - pd.Timedelta(days=shift))
            change = (actual / shifted_sum / factor - 1) * 100 if factor and shifted_sum > 0 else None
            row[f"change_end_minus_{shift}d_pct"] = change
        rows.append(row)
    calib = pd.DataFrame(rows)

    out_path = RAW_DIR / f"calibration_{stamp}.csv"
    calib.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"저장: {out_path.name}\n")

    # 5) 결과 요약: 그룹 배율과 민감도
    groups = calib[calib["kind"] == "group"]
    cols = ["name", "actual_30d", "window_ratio_sum", "factor"] + [f"change_end_minus_{s}d_pct" for s in SHIFTS]
    print("[그룹 배율] factor = 지수 1당 검색 횟수, change = 구간 끝을 n일 앞당길 때 배율 변화(%)")
    print(groups[cols].round(2).to_string(index=False), "\n")

    keywords = calib[calib["kind"] == "keyword"]
    print("[키워드 신뢰도 등급]", keywords["grade"].value_counts().to_dict(), "\n")

    # 6) 검증 A: 키워드가 1개뿐인 그룹은 그룹 배율 = 그 키워드 배율, 일간 지수도 완전히 같아야 한다
    print("[검증 A] 키워드 1개짜리 그룹 = 그 키워드")
    for group_name, members in searchad.groupby("group_name", sort=False)["keyword"]:
        if len(members) != 1:
            continue
        keyword = members.iloc[0]
        same_values = by_series[("group", group_name)]["ratio"].tolist() == by_series[("keyword", keyword)]["ratio"].tolist()
        f_group = groups.loc[groups["name"] == group_name, "factor"].iloc[0]
        f_keyword = keywords.loc[keywords["name"] == keyword, "factor"].iloc[0]
        print(f"  {group_name}: 지수 일치={same_values}, 배율 {f_group:.2f} vs {f_keyword:.2f}")

    # 7) 검증 B: 키워드별 추정을 그룹별로 더한 값 vs 그룹 직접 추정 (전체 기간 합계)
    print("\n[검증 B] 키워드 합산 vs 그룹 직접 추정 (전체 기간 합계, '계산 불가' 키워드 제외)")
    total = {key: part["ratio"].sum() for key, part in by_series.items()}   # 시리즈별 지수 총합
    for _, g in groups.iterrows():
        direct = total.get(("group", g["name"]), 0) * g["factor"]
        members = keywords[(keywords["group"] == g["name"]) & keywords["factor"].notna()]
        summed = sum(total.get(("keyword", m["name"]), 0) * m["factor"] for _, m in members.iterrows())
        grades = keywords[keywords["group"] == g["name"]]["grade"].value_counts().to_dict()
        print(f"  {g['name']}: 그룹 {direct:,.0f} / 키워드 합 {summed:,.0f} / 차이 {100 * (summed - direct) / direct:+.1f}%  {grades}")


if __name__ == "__main__":
    main()
