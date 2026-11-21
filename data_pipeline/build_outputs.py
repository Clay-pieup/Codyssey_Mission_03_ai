"""
U1-c-2. 환산 배율을 일간 지수에 곱해 '추정 검색량'을 만들고, 결과물을 저장한다.

    일간 추정 검색량 = 그날의 데이터랩 지수 × 시리즈 배율(calibration)

- 저장 기간: 2021-01-01 ~ 2026-09-30 (그 뒤 데이터는 배율 계산에만 사용)
- 주간: 월~일 7일이 다 찬 주만 사용 (양 끝 3일짜리 주는 제외)
- 서비스용은 그룹 직접 추정, 키워드 단위는 신뢰도 등급과 함께 비공개로 보관

실행: (레포 폴더에서) python data_pipeline\\build_outputs.py
입력: raw/datalab_daily_YYYYMMDD.csv, raw/calibration_YYYYMMDD.csv (calibrate.py 결과)
출력(공개): output/weekly_group.csv, output/monthly_group.csv, output/validation_tongyeong.png
출력(비공개): raw/keyword_monthly_YYYYMMDD.csv
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")   # 창을 띄우지 않고 파일로만 그린다
import matplotlib.pyplot as plt
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "raw"
OUT_DIR = BASE_DIR / "output"

STORE_START = pd.Timestamp("2021-01-01")
STORE_END = pd.Timestamp("2026-09-30")
VALIDATION_GROUP = "대형 키워드"   # 키워드가 '통영가볼만한곳' 하나뿐인 그룹

# 검증용 비교값 — 2026-11-07 화면에서 읽은 값.
# 정확값은 2개뿐(아이템스카우트 2026-10 = 66,620, 네이버 모바일 2026-10 = 60,300)이고
# 나머지는 그래프 눈금을 보고 읽은 '판독 근사값'(±2~3천)이다.
ITEMSCOUT_APPROX = {
    "2025-10": 78000, "2025-11": 71500, "2025-12": 85500, "2026-01": 82000,
    "2026-02": 82500, "2026-03": 68000, "2026-04": 94500, "2026-05": 107000,
    "2026-06": 75000, "2026-07": 101500, "2026-08": 100000, "2026-09": 61000,
    "2026-10": 66620,
}
NAVER_PC_MOBILE_APPROX = {   # 네이버 키워드도구 상세 창 '월별 검색수 추이' (PC + 모바일)
    "2025-11": 72500, "2025-12": 88500, "2026-01": 86500, "2026-02": 89500,
    "2026-03": 73000, "2026-04": 96000, "2026-05": 108500, "2026-06": 75500,
    "2026-07": 104000, "2026-08": 100500, "2026-09": 61000, "2026-10": 67100,
}

# 그래프 색: 차트 설계 지침의 검증된 기본 팔레트 앞 3칸 (색약 구분 검사 통과)
COLOR_OURS, COLOR_ITEMSCOUT, COLOR_NAVER = "#2a78d6", "#eb6834", "#1baf7a"
SURFACE, TEXT, TEXT_MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1"


def latest_stamp():
    """calibrate.py 결과가 있는 가장 최근 날짜(YYYYMMDD)를 고른다."""
    stamps = sorted(p.stem.split("_")[-1] for p in RAW_DIR.glob("calibration_*.csv"))
    if not stamps:
        sys.exit("[중단] raw/에 calibration 파일이 없습니다. calibrate.py를 먼저 실행하세요.")
    return stamps[-1]


def daily_estimate(daily, calib):
    """시리즈마다 '일간 지수 × 배율'을 계산해 긴 표에 estimate 열을 붙인다."""
    factors = calib.set_index(["kind", "name"])["factor"]
    merged = daily.join(factors, on=["kind", "name"])
    merged["estimate"] = merged["ratio"] * merged["factor"]
    return merged.dropna(subset=["estimate"])   # 배율이 없는(계산 불가) 시리즈는 뺀다


def weekly_group(est, group_order):
    """그룹 일간 추정치 → 월~일 7일이 다 찬 주만 합산 → date, value, memo."""
    groups = est[(est["kind"] == "group") & est["date"].between(STORE_START, STORE_END)].copy()
    groups["week_start"] = groups["date"] - pd.to_timedelta(groups["date"].dt.day_of_week, unit="D")  # 월=0 … 일=6
    weekly = groups.groupby(["week_start", "name"]).agg(value=("estimate", "sum"), days=("date", "nunique"))
    weekly = weekly[weekly["days"] == 7].reset_index()   # 3일짜리 양 끝 주 제외
    weekly["value"] = weekly["value"].round().astype(int)
    weekly["memo"] = pd.Categorical(weekly["name"], categories=group_order, ordered=True)
    weekly = weekly.sort_values(["week_start", "memo"])
    return pd.DataFrame({
        "date": weekly["week_start"].dt.strftime("%Y-%m-%d"),
        "value": weekly["value"],
        "memo": weekly["name"],
    })


def monthly_table(est, kind, start, end):
    """일간 추정치 → 달력 월 합계, 행=월, 열=시리즈 이름의 넓은 표."""
    part = est[(est["kind"] == kind) & est["date"].between(start, end)].copy()
    part["month"] = part["date"].dt.strftime("%Y-%m")
    table = part.pivot_table(index="month", columns="name", values="estimate", aggfunc="sum", fill_value=0)
    return table.round().astype(int)   # 한 달 내내 값이 없던 키워드는 0


def draw_validation(est, path):
    """통영가볼만한곳(대형 키워드 그룹) 최근 월별: 우리 추정 vs 아이템스카우트·네이버 판독값."""
    ours = monthly_table(est, "group", pd.Timestamp("2025-10-01"), pd.Timestamp("2026-10-31"))[VALIDATION_GROUP]
    months = list(ours.index)
    x = range(len(months))
    item = [ITEMSCOUT_APPROX.get(m) for m in months]
    naver = [NAVER_PC_MOBILE_APPROX.get(m) for m in months]

    plt.rcParams["font.family"] = ["Malgun Gothic", "Noto Sans CJK KR", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(10, 5), dpi=150, facecolor=SURFACE)
    ax.set_facecolor(SURFACE)

    ax.plot(x, ours.values, color=COLOR_OURS, lw=2, marker="o", ms=5, label="우리 추정 (데이터랩 × 배율)")
    ax.plot(x, item, color=COLOR_ITEMSCOUT, lw=2, ls="--", marker="s", ms=5, label="아이템스카우트 (판독 근사)")
    ax.plot(x, naver, color=COLOR_NAVER, lw=2, ls=":", marker="^", ms=5, label="네이버 PC+모바일 (판독 근사)")
    last = len(months) - 1   # 정확값 강조: 아이템스카우트 2026-10
    ax.plot([last], [ITEMSCOUT_APPROX["2026-10"]], marker="*", ms=14, color=COLOR_ITEMSCOUT, mec=SURFACE, mew=1.5, zorder=5)
    ax.annotate("정확값 66,620\n(우리 66,629)", (last, ITEMSCOUT_APPROX["2026-10"]), xytext=(-70, -38),
                textcoords="offset points", fontsize=9, color=TEXT_MUTED,
                arrowprops={"arrowstyle": "-", "color": TEXT_MUTED, "lw": 0.8})

    ax.set_xticks(list(x), [m[2:].replace("-", ".") for m in months], color=TEXT_MUTED, fontsize=9)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v / 1000:.0f}K"))
    ax.tick_params(axis="y", colors=TEXT_MUTED, labelsize=9)
    ax.grid(axis="y", color=GRID, lw=1)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.set_ylim(0, max(ours.max(), max(v for v in item if v)) * 1.15)
    ax.set_title("통영가볼만한곳 월별 검색량 — 우리 추정 vs 외부 화면", loc="left", color=TEXT, fontsize=13, pad=22)
    ax.text(0, 1.02, "점선 = 화면 그래프를 눈으로 읽은 근사값(±2~3천). ★ = 마우스로 확인한 정확값. 2025-10은 네이버 화면 범위 밖",
            transform=ax.transAxes, color=TEXT_MUTED, fontsize=9)
    ax.legend(loc="lower left", frameon=False, fontsize=9, labelcolor=TEXT)
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)
    return ours


def main():
    stamp = latest_stamp()
    daily = pd.read_csv(RAW_DIR / f"datalab_daily_{stamp}.csv", encoding="utf-8-sig", parse_dates=["date"])
    calib = pd.read_csv(RAW_DIR / f"calibration_{stamp}.csv", encoding="utf-8-sig")
    est = daily_estimate(daily, calib)
    group_order = list(calib.loc[calib["kind"] == "group", "name"])
    OUT_DIR.mkdir(exist_ok=True)

    # 1) 서비스용: 그룹 주간 (과제 데이터 형식 date, value, memo)
    weekly = weekly_group(est, group_order)
    weekly.to_csv(OUT_DIR / "weekly_group.csv", index=False, encoding="utf-8-sig")
    print(f"weekly_group.csv: {len(weekly):,}건, {weekly['date'].min()} ~ {weekly['date'].max()}, "
          f"그룹당 {len(weekly) // len(group_order)}주")

    # 2) 보기용: 그룹 월별 넓은 표
    monthly = monthly_table(est, "group", STORE_START, STORE_END)[group_order]
    monthly.to_csv(OUT_DIR / "monthly_group.csv", encoding="utf-8-sig")
    print(f"monthly_group.csv: {len(monthly)}개월 × {len(group_order)}그룹")

    # 3) 비공개: 키워드 월별 + 신뢰도 등급
    kw = monthly_table(est, "keyword", STORE_START, STORE_END).stack().rename("value").reset_index()
    info = calib[calib["kind"] == "keyword"][["name", "group", "grade"]]
    kw = kw.merge(info, on="name")[["month", "group", "name", "grade", "value"]]
    kw.to_csv(RAW_DIR / f"keyword_monthly_{stamp}.csv", index=False, encoding="utf-8-sig")
    print(f"keyword_monthly_{stamp}.csv: 키워드 {kw['name'].nunique()}개 (계산 불가 제외), 비공개")

    # 4) 검증 그래프
    ours = draw_validation(est, OUT_DIR / "validation_tongyeong.png")
    print("validation_tongyeong.png 저장\n")

    # 5) 요약: 그룹별 연도 합계 (2026년은 9월까지)
    yearly = monthly.groupby(monthly.index.str[:4]).sum()
    print("[그룹별 연도 합계 — 추정 검색량, 2026년은 1~9월]")
    print(yearly.to_string(), "\n")
    print("[검증] 통영가볼만한곳 월별: 우리 추정 / 아이템스카우트(판독)")
    for month, value in ours.items():
        ref = ITEMSCOUT_APPROX.get(month)
        print(f"  {month}: {value:>9,.0f} / {ref:>9,}  ({value / ref:.2f})")


if __name__ == "__main__":
    main()
