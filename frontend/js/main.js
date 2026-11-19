/**
 * 모든 화면에 공통인 두 가지: ① 탭 바꾸기 ② 잠든 서버 깨우기 안내(미션 제약: 콜드 스타트 대응).
 */

// ① 탭: 누른 탭의 영역만 보이고 나머지는 숨긴다.
//    지우지 않고 숨기기만 하므로 다른 탭에 다녀와도 채팅 내용이 그대로 남는다.
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((other) => other.classList.toggle("active", other === tab));
    document.querySelectorAll(".panel").forEach((panel) => {
      panel.hidden = panel.id !== `tab-${tab.dataset.tab}`;
    });
    // 어떤 탭이 열렸는지 알린다 → 데이터·기록 화면은 처음 열릴 때만 서버에서 불러온다(안 보는 화면은 요청 안 함)
    document.dispatchEvent(new CustomEvent("tab-shown", { detail: tab.dataset.tab }));
  });
});

// ② 서버 깨우기: 화면을 열자마자 /api/health를 부른다.
//    1.5초 안에 답이 없으면(= 서버가 자고 있음) 안내 띠를 보여 주고 경과 초를 센다. (실측 깨우기 약 33초, U5)
const WAKE_NOTICE_DELAY_MS = 1500;
window.serverReady = false;   // 채팅의 보내기 버튼이 이 값을 보고 잠금/해제한다

async function wakeServer() {
  const banner = document.getElementById("wake-banner");
  const secondsText = document.getElementById("wake-seconds");
  const startedAt = Date.now();
  const timer = setInterval(() => {   // 0.5초마다 경과 시간 갱신
    const elapsed = Date.now() - startedAt;
    if (elapsed >= WAKE_NOTICE_DELAY_MS) banner.hidden = false;
    secondsText.textContent = Math.floor(elapsed / 1000);
  }, 500);

  try {
    await api("/api/health");
    window.serverReady = true;
    banner.hidden = true;
    document.dispatchEvent(new Event("server-ready"));   // 다른 파일(chat.js 등)에 "깨어났다"고 알림
  } catch {
    banner.textContent = "서버에 연결하지 못했습니다. 잠시 후 새로고침해 주세요.";
    banner.classList.add("error");
    banner.hidden = false;
  } finally {
    clearInterval(timer);
  }
}

wakeServer();
