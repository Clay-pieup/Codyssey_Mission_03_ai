"""
U7-1. OpenAI 연결 시험: 아주 짧은 질문 1개를 보내 답이 오는지 본다.

실행(backend 폴더에서): python -m scripts.check_openai
비용: 답을 최대 30토큰으로 묶어 1회 약 $0.0001 이하(gpt-4.1-mini 기준).
키는 출력하지 않는다. 실패하면 흔한 원인을 알려 준다.
"""
from openai import APIConnectionError, AuthenticationError, NotFoundError, RateLimitError

from app.core.config import OPENAI_MODEL
from app.core.openai_client import get_client

MAX_TOKENS = 30   # 답 길이 상한(토큰). 연결 확인만 하므로 아주 짧게


def main():
    client = get_client()
    print(f"모델: {OPENAI_MODEL}")
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": "한 문장으로 짧게 인사해 줘."}],
            max_tokens=MAX_TOKENS,
        )
    except AuthenticationError:
        raise SystemExit("[실패] 키가 틀렸거나 폐기됐습니다. backend/.env의 OPENAI_API_KEY를 확인하세요.")
    except NotFoundError:
        raise SystemExit(f"[실패] 모델 '{OPENAI_MODEL}'을 찾을 수 없습니다. OPENAI_MODEL 이름을 확인하세요.")
    except RateLimitError:
        raise SystemExit("[실패] 사용 한도 초과 또는 크레딧 부족입니다. OpenAI 대시보드의 Billing·Limits를 확인하세요.")
    except APIConnectionError:
        raise SystemExit("[실패] OpenAI 서버에 연결하지 못했습니다. 인터넷 연결을 확인하세요.")

    print("답:", response.choices[0].message.content)
    usage = response.usage   # 이번 요청에 쓴 토큰 수 = 요금 계산 기준
    print(f"토큰: 입력 {usage.prompt_tokens} + 출력 {usage.completion_tokens} = {usage.total_tokens}")
    print("\n연결 정상")


if __name__ == "__main__":
    main()
