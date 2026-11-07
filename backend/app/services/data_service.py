"""
data 컬렉션을 실제로 다루는 '일하는 함수'들.

- HTTP(상태 코드, 요청/응답)를 모른다. 문제가 생기면 이 파일의 예외를 던지고,
  그것을 HTTP 상태 코드로 바꾸는 일은 라우터가 한다.
  → 같은 함수를 API 창구에서도, U8의 AI 도구(Function Calling)에서도 그대로 쓸 수 있다.
- 날짜는 'YYYY-MM-DD' 글자로 저장한다. 글자 순서 = 날짜 순서라 정렬·기간 검색이 그대로 되고,
  Firestore 시각 형식에서 겪은 UTC 변환 문제(U3-1)가 생기지 않는다.
"""
import datetime as dt

from google.cloud.firestore_v1 import FieldFilter, Query

from app.core.firebase import get_db
from app.schemas.data import DataIn, DataOut

COLLECTION = "data"


class DataNotFoundError(Exception):
    """해당 ID의 문서가 없다."""


class DuplicateDataError(Exception):
    """같은 date + memo 문서가 이미 있다."""


def to_document(item: DataIn) -> dict:
    """입력 모델 → Firestore에 저장할 사전(날짜는 글자로). 적재 스크립트(scripts/seed_data.py)도 같은 함수를 써서 저장 형식이 항상 같다."""
    return {"date": item.date.isoformat(), "value": item.value, "memo": item.memo}


def _find_same(db, date_text: str, memo: str, exclude_id: str | None = None) -> list:
    """같은 날짜·같은 그룹 문서를 찾는다. 수정할 때는 자기 자신(exclude_id)은 빼고 본다."""
    query = (
        db.collection(COLLECTION)
        .where(filter=FieldFilter("date", "==", date_text))
        .where(filter=FieldFilter("memo", "==", memo))
        .limit(2)   # 자기 자신을 빼고도 1개가 남는지 보려면 2개까지 확인
    )
    return [doc for doc in query.stream() if doc.id != exclude_id]


def create_data(item: DataIn) -> DataOut:
    db = get_db()
    document = to_document(item)
    if _find_same(db, document["date"], document["memo"]):
        raise DuplicateDataError(f"{document['date']} / {document['memo']} 데이터가 이미 있습니다. 바꾸려면 수정(PUT)을 사용하세요.")
    ref = db.collection(COLLECTION).document()   # 문서 ID는 Firestore가 자동 생성
    ref.set(document)
    return DataOut(id=ref.id, **document)


def list_data(memo: str | None, date_from: dt.date | None, date_to: dt.date | None, limit: int) -> list[DataOut]:
    """그룹·기간으로 거르고 최신 날짜순으로 최대 limit건. 읽기 비용 = 돌려준 건수."""
    query = get_db().collection(COLLECTION)
    if memo:
        query = query.where(filter=FieldFilter("memo", "==", memo))
    if date_from:
        query = query.where(filter=FieldFilter("date", ">=", date_from.isoformat()))
    if date_to:
        query = query.where(filter=FieldFilter("date", "<=", date_to.isoformat()))
    query = query.order_by("date", direction=Query.DESCENDING).limit(limit)
    return [DataOut(id=doc.id, **doc.to_dict()) for doc in query.stream()]


def update_data(data_id: str, item: DataIn) -> DataOut:
    """문서 전체를 새 값으로 바꾼다(PUT = 통째로 교체)."""
    db = get_db()
    ref = db.collection(COLLECTION).document(data_id)
    if not ref.get().exists:
        raise DataNotFoundError(f"ID {data_id} 데이터가 없습니다.")
    document = to_document(item)
    if _find_same(db, document["date"], document["memo"], exclude_id=data_id):
        raise DuplicateDataError(f"{document['date']} / {document['memo']} 데이터가 이미 다른 ID로 있습니다.")
    ref.set(document)
    return DataOut(id=data_id, **document)


def delete_data(data_id: str) -> None:
    ref = get_db().collection(COLLECTION).document(data_id)
    if not ref.get().exists:   # Firestore는 없는 문서를 지워도 오류가 없어서 직접 확인한다
        raise DataNotFoundError(f"ID {data_id} 데이터가 없습니다.")
    ref.delete()
