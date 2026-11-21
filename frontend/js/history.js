/**
 * 대화 기록 탭: 최신 20개 목록 → 누르면 채팅 탭에 펼쳐 이어서 묻기 / 삭제.
 * 탭을 열 때마다 목록을 다시 불러온다 → 방금 채팅한 대화가 바로 보인다(U11 결정).
 * 서버 창구는 U6 그대로: 목록(메시지 제외, 가벼움) → 하나 불러오기(메시지 전체) → 삭제.
 */
const HISTORY_LIMIT = 20;
const historyList = document.getElementById("history-list");

// "2026-11-19T01:03:27.735488+09:00" → "2026-11-19 01:03"
// 서버가 이미 한국 시간(+09:00)으로 보내므로(U6-1) 앞 16글자만 잘라 쓰면 된다.
function formatTime(isoText) {
  return isoText.slice(0, 16).replace("T", " ");
}

// 안내 한 줄(불러오는 중·없음·오류)
function historyNotice(text, isError = false) {
  const item = document.createElement("li");
  item.className = isError ? "history-notice error" : "history-notice";
  item.textContent = text;
  return item;
}

// 대화 한 줄: [제목 + 메시지 수·바뀐 시각] 누르면 열기, 오른쪽 삭제 버튼
function makeHistoryItem(item) {
  const row = document.createElement("li");
  row.className = "history-item";

  const open = document.createElement("button");
  open.type = "button";
  open.className = "history-open";
  const title = document.createElement("strong");
  title.textContent = item.title;   // 글자 그대로(보안 원칙, U9)
  const meta = document.createElement("small");
  meta.textContent = `메시지 ${item.message_count}개 · ${formatTime(item.updated_at)}`;
  open.append(title, meta);
  open.addEventListener("click", () => openFromHistory(item.id));

  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "ghost small danger";
  remove.textContent = "삭제";
  remove.addEventListener("click", () => deleteFromHistory(item));

  row.append(open, remove);
  return row;
}

async function loadHistory() {
  historyList.replaceChildren(historyNotice("불러오는 중…"));
  try {
    const items = await api(`/api/conversations?limit=${HISTORY_LIMIT}`);
    historyList.replaceChildren();
    if (items.length === 0) {
      historyList.append(historyNotice("저장된 대화가 없습니다. 채팅 탭에서 질문해 보세요."));
      return;
    }
    items.forEach((item) => historyList.append(makeHistoryItem(item)));
  } catch (error) {
    historyList.replaceChildren(historyNotice(`목록을 불러오지 못했습니다: ${error.message}`, true));
  }
}

// 대화 하나를 불러와(메시지 전체) 채팅 탭에 펼친다
async function openFromHistory(conversationId) {
  if (chatState.sending) {   // 답을 기다리는 중에 다른 대화로 바꾸면 답이 엉뚱한 화면에 붙는다 → 막는다
    historyList.prepend(historyNotice("AI 답을 기다리는 중에는 다른 대화를 열 수 없습니다.", true));
    return;
  }
  try {
    const detail = await api(`/api/conversations/${conversationId}`);
    openConversation(detail);   // chat.js: 말풍선 다시 그리기 + ID 기억
    showTab("chat");            // main.js: 채팅 탭으로 이동
  } catch (error) {
    historyList.prepend(historyNotice(`대화를 열지 못했습니다: ${error.message}`, true));
  }
}

async function deleteFromHistory(item) {
  const ok = confirm(`"${item.title}" 대화(메시지 ${item.message_count}개)를 삭제할까요? 되돌릴 수 없습니다.`);
  if (!ok) return;
  try {
    await api(`/api/conversations/${item.id}`, { method: "DELETE" });
    if (chatState.conversationId === item.id) startNewChat();   // 채팅에 열려 있던 대화면 채팅도 비운다
    await loadHistory();
  } catch (error) {
    historyList.prepend(historyNotice(`삭제하지 못했습니다: ${error.message}`, true));
  }
}

// 기록 탭을 열 때마다 다시 불러온다(서버가 아직 자고 있으면 깨어난 뒤에)
document.addEventListener("tab-shown", (event) => {
  if (event.detail !== "history") return;
  if (window.serverReady) loadHistory();
  else document.addEventListener("server-ready", loadHistory, { once: true });
});
