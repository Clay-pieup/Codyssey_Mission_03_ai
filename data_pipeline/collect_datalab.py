"""
U1-b. 네이버 데이터랩 검색어트렌드 API로 '일간 검색 지수'를 받아 저장한다.

- 키워드 65개 + 그룹 6개를 각각 '따로' 요청한다(총 71회).
  따로 받으면 시리즈마다 자기 최대값이 100이 되어 작은 키워드 숫자가 뭉개지지 않는다.
  100 기준이 서로 달라도 U1-c에서 시리즈마다 배율을 따로 구하므로 문제없다.
- 기간: 2021-01-01 ~ 실행 전날. 9/30 이후는 배율 계산용이며, 저장용 자르기는 U1-c에서 한다.

실행: (레포 폴더에서) python data_pipeline\\collect_datalab.py
입력: data_pipeline/keywords.csv, data_pipeline/.env (둘 다 비공개)
출력: data_pipeline/raw/datalab_daily_YYYYMMDD.json (원본), .csv (긴 표) — 비공개
"""
import csv
import json
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
KEYWORDS_PATH = BASE_DIR / "keywords.csv"
RAW_DIR = BASE_DIR / "raw"

API_URL = "https://naverapihub.apigw.ntruss.com/search-trend/v1/search"  # A3-01과 같은 주소
START_DATE = "2021-01-01"
WAIT_SECONDS = 0.2   # 연속 요청 사이 쉬는 시간(초)


def load_keywords(path):
    """keywords.csv를 읽어 [{group_id, group_name, keyword}, ...] 목록으로 돌려준다."""
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_series(rows):
    """요청할 시리즈 71개를 만든다: (종류, 이름, 키워드 목록)."""
    series = [("keyword", row["keyword"], [row["keyword"]]) for row in rows]
    groups = {}   # 그룹명 → 그 그룹의 키워드들 (csv에 적힌 순서 유지)
    for row in rows:
        groups.setdefault(row["group_name"], []).append(row["keyword"])
    series += [("group", name, keywords) for name, keywords in groups.items()]
    return series


def request_trend(name, keywords, start, end, key_id, key):
    """시리즈 하나를 일간 단위로 요청한다. 실패하면 멈춘다."""
    headers = {
        "X-NCP-APIGW-API-KEY-ID": key_id,
        "X-NCP-APIGW-API-KEY": key,
        "Content-Type": "application/json",
    }
    body = {
        "startDate": start,
        "endDate": end,
        "timeUnit": "date",
        "keywordGroups": [{"groupName": name, "keywords": keywords}],
    }
    res = requests.post(API_URL, headers=headers, json=body, timeout=30)
    if res.status_code != 200:
        sys.exit(f"[실패] {name}: HTTP {res.status_code}\n{res.text[:500]}")
    return res.json()


def main():
    load_dotenv(BASE_DIR / ".env")
    key_id = os.getenv("NAVER_API_KEY_ID", "").strip()
    key = os.getenv("NAVER_API_KEY", "").strip()
    if not key_id or not key:
        sys.exit("[중단] data_pipeline/.env 에 NAVER_API_KEY_ID / NAVER_API_KEY 값이 비어 있습니다.")

    end_date = (date.today() - timedelta(days=1)).isoformat()   # 실행 전날까지
    total_days = (date.fromisoformat(end_date) - date.fromisoformat(START_DATE)).days + 1
    series = build_series(load_keywords(KEYWORDS_PATH))
    print(f"요청: {START_DATE} ~ {end_date} ({total_days}일), 일간, 시리즈 {len(series)}개")

    raw_results = []   # 원본 응답 보관용
    lines = []         # 긴 표의 줄들: [날짜, 종류, 이름, 지수]
    summary = []       # 시리즈별 요약
    for i, (kind, name, keywords) in enumerate(series, start=1):
        result = request_trend(name, keywords, START_DATE, end_date, key_id, key)
        data = result["results"][0]["data"]   # 이번 요청은 시리즈 1개라 results도 1개
        raw_results.append({"kind": kind, "name": name, "keywords": keywords, "response": result})
        for point in data:
            lines.append([point["period"], kind, name, point["ratio"]])
        peak = max(data, key=lambda p: p["ratio"])["period"] if data else "-"
        last = data[-1]["period"] if data else "-"
        summary.append((kind, name, len(data), total_days - len(data), peak, last))
        print(f"{i}/{len(series)} 완료")
        time.sleep(WAIT_SECONDS)

    RAW_DIR.mkdir(exist_ok=True)
    stamp = date.today().strftime("%Y%m%d")
    json_path = RAW_DIR / f"datalab_daily_{stamp}.json"
    csv_path = RAW_DIR / f"datalab_daily_{stamp}.csv"
    meta = {"collected_date": date.today().isoformat(), "start": START_DATE, "end": end_date}
    json_path.write_text(json.dumps({"meta": meta, "series": raw_results}, ensure_ascii=False), encoding="utf-8")
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "kind", "name", "ratio"])
        writer.writerows(lines)

    print(f"\n저장: {json_path.name}, {csv_path.name} ({len(lines):,}줄)")
    print(f"\n{'종류':<8}{'받은 날':>8}{'빠진 날':>8}  {'최대(100)인 날':<12}  {'마지막 날':<12}  이름")
    for kind, name, got, missing, peak, last in summary:
        print(f"{kind:<8}{got:>8}{missing:>8}  {peak:<12}  {last:<12}  {name}")


if __name__ == "__main__":
    main()
