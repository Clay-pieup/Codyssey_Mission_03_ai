"""
U1-a. 네이버 검색광고 API로 키워드별 '최근 30일 실제 검색수'를 받아 저장한다.

실행: (레포 폴더에서) python data_pipeline\\collect_searchad.py
입력: data_pipeline/keywords.csv (비공개), data_pipeline/.env (비공개)
출력: data_pipeline/raw/searchad_30d_YYYYMMDD.csv (비공개 — 키워드 단위라 브랜드명이 들어 있음)
"""
import base64
import csv
import hashlib
import hmac
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

# 이 파일이 있는 폴더(data_pipeline)를 기준으로 경로를 잡는다.
# 터미널을 어느 폴더에서 열고 실행하든 같은 파일을 찾게 하기 위해서다.
BASE_DIR = Path(__file__).resolve().parent
KEYWORDS_PATH = BASE_DIR / "keywords.csv"
RAW_DIR = BASE_DIR / "raw"

API_BASE = "https://api.searchad.naver.com"
URI = "/keywordstool"   # 서명에 들어가는 '주소' 부분. 물음표 뒤(검색 조건)는 넣지 않는다.
METHOD = "GET"
BATCH_SIZE = 5          # API가 한 번에 받는 키워드 최대 개수
WAIT_SECONDS = 0.5      # 호출 사이 쉬는 시간(초). 초당 3회를 넘기지 않기 위함


def load_keywords(path):
    """keywords.csv를 읽어 [{group_id, group_name, keyword}, ...] 목록으로 돌려준다."""
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def make_signature(timestamp, method, uri, secret_key):
    """'시각.요청종류.주소'를 비밀키로 섞어 일회용 도장(서명)을 만든다."""
    message = f"{timestamp}.{method}.{uri}"
    digest = hmac.new(secret_key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def fetch_batch(hint_keywords, customer_id, access_license, secret_key):
    """키워드 최대 5개를 보내고, API가 돌려준 키워드 목록을 받는다."""
    timestamp = str(int(time.time() * 1000))   # 지금 시각(1970년 이후 밀리초)
    headers = {
        "X-Timestamp": timestamp,
        "X-API-KEY": access_license,
        "X-Customer": customer_id,
        "X-Signature": make_signature(timestamp, METHOD, URI, secret_key),
    }
    params = {"hintKeywords": ",".join(hint_keywords), "showDetail": "1"}
    response = requests.get(API_BASE + URI, headers=headers, params=params, timeout=10)
    if response.status_code != 200:
        print(f"[오류] 상태 코드 {response.status_code}: {response.text[:300]}")
        sys.exit(1)
    return response.json()["keywordList"]


def normalize(text):
    """비교용으로 띄어쓰기를 없애고 영문을 대문자로 통일한다."""
    return text.replace(" ", "").upper()


def main():
    load_dotenv(BASE_DIR / ".env")
    customer_id = os.getenv("SEARCHAD_CUSTOMER_ID")
    access_license = os.getenv("SEARCHAD_ACCESS_LICENSE")
    secret_key = os.getenv("SEARCHAD_SECRET_KEY")
    if not (customer_id and access_license and secret_key):
        print("[오류] data_pipeline/.env 에 SEARCHAD_ 로 시작하는 값 3개를 채워 주세요.")
        sys.exit(1)

    keywords = load_keywords(KEYWORDS_PATH)
    collected_date = datetime.now().strftime("%Y-%m-%d")
    results = {}   # 비교용 키워드 → API가 준 항목

    for start in range(0, len(keywords), BATCH_SIZE):
        batch = [row["keyword"] for row in keywords[start:start + BATCH_SIZE]]
        items = fetch_batch(batch, customer_id, access_license, secret_key)
        wanted = {normalize(k) for k in batch}
        for item in items:   # 응답에는 연관 키워드 수백 개가 섞여 오므로, 보낸 것만 골라 담는다
            key = normalize(item["relKeyword"])
            if key in wanted:
                results[key] = item
        print(f"{start + len(batch)}/{len(keywords)} 완료")
        time.sleep(WAIT_SECONDS)

    RAW_DIR.mkdir(exist_ok=True)
    out_path = RAW_DIR / f"searchad_30d_{collected_date.replace('-', '')}.csv"
    missing = []
    small = 0   # '< 10'처럼 숫자가 아닌 글자로 온 키워드 수
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["collected_date", "group_id", "group_name", "keyword", "pc_30d", "mobile_30d"])
        for row in keywords:
            item = results.get(normalize(row["keyword"]))
            if item is None:
                missing.append(row["keyword"])
                pc, mobile = "", ""
            else:
                pc, mobile = item["monthlyPcQcCnt"], item["monthlyMobileQcCnt"]
                if isinstance(pc, str) or isinstance(mobile, str):
                    small += 1
            writer.writerow([collected_date, row["group_id"], row["group_name"], row["keyword"], pc, mobile])

    print(f"저장: {out_path}")
    print(f"찾은 키워드 {len(keywords) - len(missing)}개 / 못 찾은 키워드 {len(missing)}개")
    print(f"'< 10'처럼 글자로 온 값이 있는 키워드: {small}개")
    if missing:
        print("못 찾은 키워드:", ", ".join(missing))


if __name__ == "__main__":
    main()
