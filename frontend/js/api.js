/**
 * 서버 통신 공통 함수. 채팅·데이터·대화 기록 화면이 모두 이 함수 하나로 백엔드를 부른다.
 * - 주소 앞부분(API_BASE_URL)을 붙이고, 보낼 내용을 JSON 글자로 바꾸고, 받은 JSON을 다시 값으로 바꾼다.
 * - 실패(4xx·5xx)면 서버가 보낸 안내(detail)를 꺼내 오류로 던진다 → 화면은 그 문구만 보여 주면 된다.
 */
async function api(path, { method = "GET", body } = {}) {
  const options = { method, headers: {} };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);   // {message: "..."} → '{"message":"..."}' 글자로
  }

  let response;
  try {
    response = await fetch(window.API_BASE_URL + path, options);   // fetch: 브라우저 기본 '서버에 요청 보내기' 기능
  } catch {
    // 인터넷이 끊겼거나, CORS 허용 목록에 이 화면 주소가 없으면 여기로 온다
    throw new Error("서버에 연결하지 못했습니다. 잠시 후 다시 시도하세요.");
  }

  if (response.status === 204) return null;   // 삭제 성공: 돌려줄 내용 없음
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(readDetail(data) || `요청 실패 (${response.status})`);
  }
  return data;
}

// FastAPI 오류 안내는 두 모양이다: 글자 하나(404·429·502 등) 또는 목록(422 입력 규칙 위반).
function readDetail(data) {
  if (!data || data.detail === undefined) return "";
  if (typeof data.detail === "string") return data.detail;
  // Pydantic이 붙이는 "Value error, " 머리말은 떼고 사람이 읽을 안내만 남긴다
  return data.detail.map((item) => item.msg.replace(/^Value error, /, "")).join(" / ");
}
