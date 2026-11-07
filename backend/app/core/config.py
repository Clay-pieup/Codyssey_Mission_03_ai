"""
서버 설정값을 한곳에서 읽는다.

값은 로컬에서는 backend/.env, 배포(Render)에서는 Render 환경변수에서 온다.
코드에는 실제 값을 쓰지 않는다 — 주소나 키가 바뀌어도 코드를 고치지 않기 위해서다.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[2]   # 이 파일(app/core/config.py)에서 두 단계 위 = backend 폴더
load_dotenv(BACKEND_DIR / ".env")   # .env 가 없으면(배포 환경) 조용히 넘어가고 실제 환경변수를 쓴다


def _split_by_comma(value):
    """'a, b,c' → ['a', 'b', 'c']. 빈 칸과 빈 항목은 버린다."""
    return [item.strip() for item in value.split(",") if item.strip()]


# CORS 허용 주소 목록. 비어 있으면 어떤 외부 화면도 허용하지 않는다(안전한 기본값).
ALLOWED_ORIGINS = _split_by_comma(os.getenv("ALLOWED_ORIGINS", ""))

# Firebase 서비스 계정 키 파일의 경로. 키 '내용'이 아니라 '위치'만 설정에 적는다(키 파일은 레포 밖).
FIREBASE_SERVICE_ACCOUNT_PATH = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "").strip()
