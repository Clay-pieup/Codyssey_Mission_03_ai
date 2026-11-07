"""
Firebase(Firestore) 연결을 한곳에서 관리한다.

- 서비스 계정 키 파일의 경로는 설정(FIREBASE_SERVICE_ACCOUNT_PATH)에서만 읽는다. 키 내용은 코드에 없다.
- 로그인은 처음 DB가 필요할 때 한 번만 한다(지연 연결).
  서버를 켤 때 바로 로그인하면, 키 설정이 잘못됐을 때 서버 전체가 켜지지 않아 /api/health조차 확인할 수 없다.
"""
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore

from app.core.config import FIREBASE_SERVICE_ACCOUNT_PATH

_db = None   # 한 번 만든 DB 연결을 기억해 두는 자리


def get_db():
    """Firestore 연결을 돌려준다. 처음 부를 때만 로그인하고, 이후에는 같은 연결을 재사용한다."""
    global _db
    if _db is not None:
        return _db

    if not FIREBASE_SERVICE_ACCOUNT_PATH:
        raise RuntimeError("FIREBASE_SERVICE_ACCOUNT_PATH가 비어 있습니다 (backend/.env 또는 Render 환경변수).")
    key_path = Path(FIREBASE_SERVICE_ACCOUNT_PATH)
    if not key_path.is_file():
        raise RuntimeError(f"서비스 계정 키 파일을 찾을 수 없습니다: {key_path}")

    try:
        app = firebase_admin.get_app()   # 이미 로그인해 둔 앱이 있으면 그대로 쓴다
    except ValueError:
        app = firebase_admin.initialize_app(credentials.Certificate(str(key_path)))
    _db = firestore.client(app)
    return _db
