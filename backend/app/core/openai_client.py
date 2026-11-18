"""
OpenAI(GPT) 연결을 한곳에서 관리한다.

- 키는 설정(OPENAI_API_KEY)에서만 읽는다. 코드에도, 화면 출력에도 키를 쓰지 않는다.
- 연결은 처음 GPT가 필요할 때 한 번만 만든다(지연 연결, firebase.py와 같은 이유).
  키가 비어 있어도 서버는 켜지고 /api/health·데이터·대화 API는 그대로 동작한다.
- 응답을 기다리는 시간과 자동 재시도 횟수에 상한을 둔다 → GPT가 느리거나 장애일 때 화면이 끝없이 기다리지 않게.
"""
from openai import OpenAI

from app.core.config import OPENAI_API_KEY

TIMEOUT_SECONDS = 30   # 한 번 요청에 최대 30초 기다린다
MAX_RETRIES = 1        # 일시적 오류(연결 끊김·서버 과부하)면 1번만 다시 시도한다(기본값 2 → 대기·비용 상한을 낮춤)

_client = None   # 한 번 만든 연결을 기억해 두는 자리


def get_client() -> OpenAI:
    """GPT 연결을 돌려준다. 처음 부를 때만 만들고, 이후에는 같은 연결을 재사용한다."""
    global _client
    if _client is not None:
        return _client
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY가 비어 있습니다 (backend/.env 또는 Render 환경변수).")
    _client = OpenAI(api_key=OPENAI_API_KEY, timeout=TIMEOUT_SECONDS, max_retries=MAX_RETRIES)
    return _client
