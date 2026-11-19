/**
 * 채팅 화면: 질문 보내기 → 로딩 표시 → 답(또는 오류) 표시 → 이어 대화.
 * 대화 ID만 기억했다가 다음 질문에 함께 보낸다. 이전 메시지는 서버가 DB에서 읽는다(U7 결정 A).
 */
const chatState = {
  conversationId: null,   // null이면 다음 질문이 새 대화가 된다
  sending: false,         // 답을 기다리는 중이면 true → 중복 전송 방지
};

const messagesBox = document.getElementById("messages");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const sendButton = document.getElementById("send");
const chatTitle = document.getElementById("chat-title");
const HINT = '예: "최근 4주 검색량 추세 알려줘" → 이어서 "그중 펜션/풀빌라는 어때?"';

// 말풍선 하나를 추가한다.
// textContent = 글자를 '그대로' 넣는다(HTML로 해석하지 않음) → AI 답이나 저장된 글에 코드가 섞여도 실행되지 않는다.
function addBubble(kind, text, note) {
  const bubble = document.createElement("div");
  bubble.className = `bubble ${kind}`;
  bubble.textContent = text;
  if (note) {
    const small = document.createElement("small");
    small.textContent = note;
    bubble.appendChild(small);
  }
  messagesBox.appendChild(bubble);
  messagesBox.scrollTop = messagesBox.scrollHeight;   // 새 말풍선이 보이게 맨 아래로
  return bubble;
}

function showHint() {
  messagesBox.replaceChildren();   // 말풍선을 모두 지운다
  addBubble("hint", HINT);
}

// 보내기 버튼: 서버가 깨어 있고, 답을 기다리는 중이 아닐 때만 누를 수 있다.
function updateSendButton() {
  sendButton.disabled = !window.serverReady || chatState.sending;
}

async function sendMessage(event) {
  event.preventDefault();   // form의 기본 동작(페이지 새로고침)을 막는다
  const message = chatInput.value.trim();
  if (!message || chatState.sending || !window.serverReady) return;

  messagesBox.querySelector(".hint")?.remove();
  addBubble("user", message);
  chatInput.value = "";
  chatState.sending = true;
  updateSendButton();
  const loading = addBubble("assistant loading", "AI가 답을 쓰는 중…");

  const body = { message };
  if (chatState.conversationId) body.conversation_id = chatState.conversationId;   // 있을 때만(없으면 새 대화)

  try {
    const result = await api("/api/chat", { method: "POST", body });
    chatState.conversationId = result.conversation_id;   // 다음 질문은 이 대화에 이어서
    chatTitle.textContent = result.title;
    loading.remove();
    addBubble("assistant", result.reply, `토큰 ${result.usage.total_tokens.toLocaleString()}`);
  } catch (error) {
    loading.remove();
    addBubble("error", error.message);   // 예: 429 "오늘 AI 대화 사용량(200회)을 다 썼습니다..."
  } finally {
    chatState.sending = false;
    updateSendButton();
    chatInput.focus();
  }
}

// 새 대화: 기억한 ID와 화면만 비운다(저장된 대화는 지우지 않음).
function startNewChat() {
  chatState.conversationId = null;
  chatTitle.textContent = "새 대화";
  showHint();
  chatInput.focus();
}

chatForm.addEventListener("submit", sendMessage);
document.getElementById("new-chat").addEventListener("click", startNewChat);
document.addEventListener("server-ready", updateSendButton);

// Enter = 보내기, Shift+Enter = 줄바꿈.
// isComposing: 한글을 조합하는 중(받침 입력 등)의 Enter는 무시한다 → 마지막 글자가 잘리거나 두 번 보내지는 것 방지.
chatInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    chatForm.requestSubmit();
  }
});

showHint();
updateSendButton();
