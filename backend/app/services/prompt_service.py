"""
시스템 프롬프트(대화 전에 GPT에게 주는 '역할 + 참고 자료 + 답하는 규칙' 글)를 만든다.

- 재료는 데이터 요약(summary_service.get_summary) 하나뿐이다(U7 결정: 자세한 통계는 U8 도구로).
- 요약은 전체 + 6그룹 모두 넣는다(U7-2 결정 가) → 그룹 질문에도 바로 답할 수 있다.
- 요약(사전) → 사람이 읽는 목록 글로 바꾼다(U7-2 결정 ㄱ). JSON보다 토큰이 적고 GPT·사람 모두 읽기 쉽다.
- build_system_prompt는 DB를 모르는 순수 함수라 숫자만으로 시험할 수 있다(U4-1과 같은 원칙).
"""
from app.services import summary_service

INTRO = (
    "당신은 통영 숙박·여행 관련 네이버 검색 데이터를 분석하는 비서입니다.\n"
    "아래 데이터는 6개 키워드 그룹의 주간 '추정 검색량'입니다"
    "(네이버 데이터랩 지수를 검색광고 API의 최근 30일 실제 검색수로 보정한 값)."
)

RULES = """[답변 규칙]
1. 위 데이터에 근거해 답하고, 데이터에 없는 내용은 "데이터에 없습니다"라고 말하세요. 숫자를 지어내지 마세요.
2. 숫자는 실제 검색 횟수가 아니라 추정 검색량임을 밝히세요.
3. 한국어로, 핵심부터 3~5문장으로 답하세요. 표나 목록은 꼭 필요할 때만 쓰세요.
4. 날짜는 그 주의 시작일(월요일)입니다. 예: "2021-07-26 주" = 2021-07-26(월)~2021-08-01(일).
5. 계절성·점유율 같은 자세한 통계는 아직 볼 수 없습니다. 그런 질문에는 위 요약 범위에서만 답하고 그 한계를 알려 주세요."""


def _comma(number: int) -> str:
    return f"{number:,}"   # 23341801 → '23,341,801' (사람과 GPT 모두 자릿수를 덜 헷갈림)


def _series_lines(series: dict) -> str:
    """요약 한 덩어리(전체 또는 그룹 하나) → 목록 글 몇 줄."""
    metrics = series["metrics"]
    if metrics is None:   # 데이터가 하나도 없는 경우(U4-1의 '데이터 없음')
        return f"■ {series['name']}\n- 데이터 없음"
    return "\n".join([
        f"■ {series['name']}",
        f"- 데이터 기간: {series['period']} ({series['weeks']}주, 레코드 {_comma(series['count'])}개)",
        f"- 합계: {_comma(metrics['total'])}회 / 주 평균: {_comma(metrics['average'])}회",
        f"- 최대: {metrics['max']['date']} 주 {_comma(metrics['max']['value'])}회"
        f" / 최소: {metrics['min']['date']} 주 {_comma(metrics['min']['value'])}회",
        f"- 최근 추세: {series['trend']}",
    ])


def build_system_prompt(summary: dict) -> str:
    """요약 사전 → 시스템 프롬프트 글. 순서: 역할 → 데이터 요약(전체 → 6그룹) → 답변 규칙."""
    computed_at = summary["computed_at"].strftime("%Y-%m-%d %H:%M")
    blocks = [series for series in [summary, *summary["groups"]]]   # 전체가 맨 앞, 그다음 정해 둔 6그룹 순서
    return "\n\n".join([
        INTRO,
        f"[사용자 데이터 요약] (계산 시각: {computed_at} 한국 시간)",
        *(_series_lines(series) for series in blocks),
        RULES,
    ])


def get_system_prompt() -> str:
    """지금의 요약으로 만든 시스템 프롬프트. 요약은 서버 기억(U4-1)에서 오므로 Firestore를 매번 읽지 않는다."""
    return build_system_prompt(summary_service.get_summary())
