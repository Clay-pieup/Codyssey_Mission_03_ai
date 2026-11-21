/**
 * 데이터 탭: ① 요약(전체 카드 + 6그룹 표) ② 추가·수정 겸용 입력 칸 ③ 목록(그룹 + 최신 N건)과 수정·삭제.
 * 추가·수정·삭제가 끝나면 목록과 요약을 다시 불러온다(서버는 데이터가 바뀌면 요약 기억을 버린다, U4-1).
 */
// 6개 그룹 이름: 백엔드 규칙(schemas/data.py의 GroupName)과 글자까지 같아야 한다
const GROUPS = ["브랜드 키워드", "핵심 키워드", "일반숙박", "펜션/풀빌라", "주변명소", "대형 키워드"];

const dataState = {
  loaded: false,     // 탭을 처음 열 때만 불러오기 위해
  editingId: null,   // null이면 '추가', 값이 있으면 그 ID를 '수정' 중
};

const $ = (id) => document.getElementById(id);   // 자주 쓰는 '아이디로 찾기'를 짧게
const comma = (n) => n.toLocaleString();          // 23341801 → "23,341,801"

// 표 한 줄 만들기: 칸마다 글자를 그대로(textContent) 넣는다(채팅과 같은 보안 원칙)
function makeRow(cells, tag = "td") {
  const row = document.createElement("tr");
  cells.forEach((cell) => {
    const box = document.createElement(tag);
    if (cell instanceof Node) box.appendChild(cell);   // 버튼 같은 요소는 그대로 붙인다
    else box.textContent = cell;
    row.appendChild(box);
  });
  return row;
}

// 변화율 → "감소 -32.5%". 색만으로 뜻을 전하지 않도록 글자(증가·감소·유지)를 함께 쓴다(서버와 같은 ±5% 기준)
function pctText(pct) {
  if (pct === null || pct === undefined) return "비교 불가";
  const label = Math.abs(pct) < 5 ? "유지" : pct > 0 ? "증가" : "감소";
  return `${label} ${pct > 0 ? "+" : ""}${pct.toFixed(1)}%`;
}

// ① 요약
async function loadSummary() {
  const box = $("summary-total");
  try {
    const s = await api("/api/data/summary");
    const m = s.metrics;
    box.replaceChildren();
    const lines = m
      ? [
          ["기간", `${s.period} (${s.weeks}주)`],
          ["레코드", `${comma(s.count)}개`],
          ["합계 / 주 평균", `${comma(m.total)}회 / ${comma(m.average)}회`],
          ["최대", `${m.max.date} 주 ${comma(m.max.value)}회`],
          ["최소", `${m.min.date} 주 ${comma(m.min.value)}회`],
          ["최근 추세", s.trend],
        ]
      : [["상태", "데이터 없음"]];
    lines.forEach(([label, value]) => {
      const item = document.createElement("div");
      const name = document.createElement("span");
      name.textContent = label;
      const text = document.createElement("strong");
      text.textContent = value;
      item.append(name, text);
      box.appendChild(item);
    });

    const table = $("summary-groups");
    table.replaceChildren(makeRow(["그룹", "합계", "주 평균", "최근 4주", "최근 12주"], "th"));
    s.groups.forEach((g) => {
      table.appendChild(makeRow([
        g.name,
        g.metrics ? comma(g.metrics.total) : "-",
        g.metrics ? comma(g.metrics.average) : "-",
        pctText(g.changes.recent_4w_vs_last_year_pct),
        pctText(g.changes.recent_12w_vs_last_year_pct),
      ]));
    });
  } catch (error) {
    box.textContent = `요약을 불러오지 못했습니다: ${error.message}`;
  }
}

// ③ 목록
async function loadList() {
  const memo = $("l-memo").value;
  const limit = $("l-limit").value;
  const query = new URLSearchParams({ limit });   // ?limit=20&memo=... 모양의 주소 뒷부분을 안전하게 만든다
  if (memo) query.set("memo", memo);
  const table = $("data-list");
  try {
    const rows = await api(`/api/data?${query}`);
    table.replaceChildren(makeRow(["주 시작일", "그룹", "추정 검색량", ""], "th"));
    rows.forEach((item) => {
      const edit = document.createElement("button");
      edit.type = "button"; edit.className = "ghost small"; edit.textContent = "수정";
      edit.addEventListener("click", () => startEdit(item));
      const del = document.createElement("button");
      del.type = "button"; del.className = "ghost small danger"; del.textContent = "삭제";
      del.addEventListener("click", () => removeItem(item));
      const actions = document.createElement("span");
      actions.className = "actions";
      actions.append(edit, del);
      table.appendChild(makeRow([item.date, item.memo, comma(item.value), actions]));
    });
    if (rows.length === 0) table.appendChild(makeRow(["데이터 없음", "", "", ""]));
  } catch (error) {
    table.replaceChildren(makeRow([`목록을 불러오지 못했습니다: ${error.message}`]));
  }
}

function showMessage(text, isError = false) {
  const box = $("data-message");
  box.textContent = text;
  box.classList.toggle("error", isError);
  box.hidden = false;
}

// ② 추가·수정 겸용
function startEdit(item) {
  dataState.editingId = item.id;
  $("f-date").value = item.date;
  $("f-memo").value = item.memo;
  $("f-value").value = item.value;
  $("form-title").textContent = `데이터 수정 중: ${item.date} / ${item.memo}`;
  $("f-submit").textContent = "수정 저장";
  $("f-cancel").hidden = false;
  $("data-form").scrollIntoView({ behavior: "smooth" });
}

function resetForm() {
  dataState.editingId = null;
  $("data-form").reset();
  $("form-title").textContent = "새 데이터 추가";
  $("f-submit").textContent = "추가";
  $("f-cancel").hidden = true;
}

async function submitForm(event) {
  event.preventDefault();
  const value = Number($("f-value").value);   // 서버는 '숫자'만 받는다(U3-2 strict) → 글자 "123"이 아니라 숫자 123으로 보냄
  if (!Number.isInteger(value) || value < 0) {
    showMessage("추정 검색량은 0 이상의 정수여야 합니다.", true);
    return;
  }
  const body = { date: $("f-date").value, memo: $("f-memo").value, value };
  const editing = dataState.editingId;
  try {
    if (editing) await api(`/api/data/${editing}`, { method: "PUT", body });
    else await api("/api/data", { method: "POST", body });
    showMessage(editing ? "수정했습니다." : "추가했습니다.");
    resetForm();
    await Promise.all([loadList(), loadSummary()]);   // 목록과 요약을 동시에 다시 불러온다
    document.dispatchEvent(new Event("data-changed"));   // 채팅 위 요약 한 줄도 다시 불러오게 알림
  } catch (error) {
    showMessage(error.message, true);   // 예: "date는 주 시작일(월요일)이어야 합니다." / 409 중복
  }
}

async function removeItem(item) {
  // 되돌릴 수 없는 삭제만 한 번 더 묻는다(U10 결정)
  const ok = confirm(`${item.date} / ${item.memo} / ${comma(item.value)}회\n이 데이터를 삭제할까요? 되돌릴 수 없습니다.`);
  if (!ok) return;
  try {
    await api(`/api/data/${item.id}`, { method: "DELETE" });
    if (dataState.editingId === item.id) resetForm();
    showMessage("삭제했습니다.");
    await Promise.all([loadList(), loadSummary()]);
    document.dispatchEvent(new Event("data-changed"));   // 채팅 위 요약 한 줄도 다시 불러오게 알림
  } catch (error) {
    showMessage(error.message, true);
  }
}

// 그룹 선택 칸 2곳(입력용·목록 거르기용)을 6그룹으로 채운다
GROUPS.forEach((name) => {
  $("f-memo").append(new Option(name, name));
  $("l-memo").append(new Option(name, name));
});

$("data-form").addEventListener("submit", submitForm);
$("f-cancel").addEventListener("click", resetForm);
$("l-memo").addEventListener("change", loadList);
$("l-limit").addEventListener("change", loadList);

// 데이터 탭을 처음 열 때 한 번만 불러온다(서버가 아직 자고 있으면 깨어난 뒤에)
document.addEventListener("tab-shown", (event) => {
  if (event.detail !== "data" || dataState.loaded) return;
  dataState.loaded = true;
  const load = () => Promise.all([loadSummary(), loadList()]);
  if (window.serverReady) load();
  else document.addEventListener("server-ready", load, { once: true });
});
