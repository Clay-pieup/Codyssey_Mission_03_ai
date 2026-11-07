"""
U3-1. Firestore 연결 시험: 시험 문서 1개를 쓰고 → 읽고 → 지운다.

실행(backend 폴더에서): python -m scripts.check_firestore

보안 규칙이 'allow read, write: if false'(프로덕션 모드)인데도 성공하면,
관리자 키(Admin SDK)로 들어온 서버는 보안 규칙을 거치지 않는다는 것이 확인된다.
"""
from datetime import datetime, timezone

from app.core.firebase import get_db

TEST_COLLECTION = "_connection_test"   # 실제 데이터(data, conversations)와 섞이지 않게 따로 둔다


def main():
    db = get_db()
    doc_ref = db.collection(TEST_COLLECTION).document()   # 문서 ID는 Firestore가 자동으로 만든다
    written = {"message": "연결 시험", "at": datetime.now(timezone.utc)}

    doc_ref.set(written)
    print(f"1) 쓰기 성공: {TEST_COLLECTION}/{doc_ref.id}")

    read_back = doc_ref.get().to_dict()
    print(f"2) 읽기 성공: {read_back}")
    if read_back["message"] != written["message"]:
        raise SystemExit("[실패] 쓴 값과 읽은 값이 다릅니다.")

    doc_ref.delete()
    print(f"3) 삭제 성공: 다시 읽었을 때 존재 여부 = {doc_ref.get().exists}")
    print("\n연결 정상 — 보안 규칙이 'if false'여도 관리자 키로는 읽기·쓰기·삭제가 된다.")


if __name__ == "__main__":
    main()
