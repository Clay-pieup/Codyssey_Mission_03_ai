"""
U3-3. U1 결과(data_pipeline/output/weekly_group.csv) 1,794건을 Firestore data 컬렉션에 넣는다.

실행(backend 폴더에서): python -m scripts.seed_data

순서
1) CSV 전체를 API와 같은 입력 규칙표(DataIn)로 먼저 검사한다. 한 줄이라도 틀리면 아무것도 저장하지 않는다.
2) 안전장치: data 컬렉션이 비어 있을 때만 진행한다(두 번 실행해도 중복이 생기지 않게).
3) 500건씩 묶음 쓰기(batch). 묶음 하나는 전부 성공하거나 전부 실패한다.
4) 개수 세기(count)로 전체·그룹별 건수를 확인한다.
"""
import csv
import sys
from pathlib import Path
from typing import get_args

from google.cloud.firestore_v1 import FieldFilter
from pydantic import ValidationError

from app.core.firebase import get_db
from app.schemas.data import DataIn, GroupName
from app.services.data_service import COLLECTION, to_document

REPO_DIR = Path(__file__).resolve().parents[2]   # backend/scripts → backend → 레포 맨 위
CSV_PATH = REPO_DIR / "data_pipeline" / "output" / "weekly_group.csv"
BATCH_SIZE = 500   # Firestore 묶음 쓰기 한 번의 최대 건수


def load_and_validate(path):
    """CSV를 읽어 DataIn 목록으로 만든다. 틀린 줄과 중복(같은 날짜+그룹)은 오류 목록에 모은다."""
    items, errors, seen = [], [], set()
    with open(path, encoding="utf-8-sig", newline="") as f:
        for line_no, row in enumerate(csv.DictReader(f), start=2):   # 1행은 머리글
            try:
                # CSV는 모든 칸이 글자라, 규칙표(strict 정수)에 넣기 전에 value만 숫자로 바꾼다
                item = DataIn(date=row["date"], value=int(row["value"]), memo=row["memo"])
            except (ValidationError, ValueError) as error:
                errors.append(f"{line_no}행: {error}")
                continue
            key = (item.date, item.memo)
            if key in seen:
                errors.append(f"{line_no}행: {item.date} / {item.memo} 가 CSV 안에 두 번 있습니다.")
                continue
            seen.add(key)
            items.append(item)
    return items, errors


def main():
    if not CSV_PATH.is_file():
        sys.exit(f"[중단] CSV가 없습니다: {CSV_PATH}\n먼저 data_pipeline/build_outputs.py를 실행하세요.")

    # 1) 저장 전에 전부 검사
    items, errors = load_and_validate(CSV_PATH)
    print(f"1) 검사: {len(items)}건 통과, {len(errors)}건 오류")
    if errors:
        print("\n".join(errors[:10]))
        sys.exit("[중단] 오류가 있어 아무것도 저장하지 않았습니다.")

    # 2) 비어 있을 때만
    db = get_db()
    collection = db.collection(COLLECTION)
    if collection.limit(1).get():
        sys.exit(f"[중단] '{COLLECTION}' 컬렉션에 이미 문서가 있습니다. 중복을 막기 위해 적재하지 않습니다.")

    # 3) 500건씩 묶음 쓰기
    for start in range(0, len(items), BATCH_SIZE):
        batch = db.batch()
        for item in items[start:start + BATCH_SIZE]:
            batch.set(collection.document(), to_document(item))   # 문서 ID는 자동 생성(API와 동일)
        batch.commit()
        print(f"2) 저장: {min(start + BATCH_SIZE, len(items))}/{len(items)}")

    # 4) 개수 세기로 확인 (문서를 하나씩 읽지 않아 비용이 적다)
    total = collection.count().get()[0][0].value
    print(f"3) 확인: 전체 {total}건")
    for group in get_args(GroupName):
        count = collection.where(filter=FieldFilter("memo", "==", group)).count().get()[0][0].value
        print(f"   - {group}: {count}건")


if __name__ == "__main__":
    main()
