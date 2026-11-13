"use strict";

const API_BASE = "/api/links";
const STATS_DAYS = 7;

const createForm = document.getElementById("create-form");
const urlInput = document.getElementById("url-input");
const titleInput = document.getElementById("title-input");
const formMessage = document.getElementById("form-message");
const listMessage = document.getElementById("list-message");
const linkList = document.getElementById("link-list");
const summary = document.getElementById("summary");

const statsDialog = document.getElementById("stats-dialog");
const statsSummary = document.getElementById("stats-summary");
const statsChart = document.getElementById("stats-chart");

const editDialog = document.getElementById("edit-dialog");
const editForm = document.getElementById("edit-form");
const editUrl = document.getElementById("edit-url");
const editTitle = document.getElementById("edit-title-input");
const editMessage = document.getElementById("edit-message");

/** 수정 중인 링크의 코드 */
let editingCode = null;

/**
 * 백엔드 API를 호출하고 JSON을 돌려준다. 실패하면 사용자에게 보여줄 메시지로 Error를 던진다.
 * @param {string} path
 * @param {RequestInit} [options]
 */
async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(path, {
      ...options,
      headers: { "Content-Type": "application/json", ...(options.headers ?? {}) },
    });
  } catch {
    throw new Error("서버에 연결할 수 없습니다. 잠시 후 다시 시도하세요.");
  }
  if (response.status === 204) return null;
  if (response.ok) return response.json();

  if (response.status === 422) {
    throw new Error("올바른 주소를 입력하세요. http:// 또는 https:// 로 시작해야 합니다.");
  }
  if (response.status === 429 || response.status === 503) {
    throw new Error("요청이 많습니다. 잠시 후 다시 시도하세요.");
  }
  const body = await response.json().catch(() => null);
  const detail = typeof body?.detail === "string" ? body.detail : null;
  throw new Error(detail ?? `요청에 실패했습니다. (${response.status})`);
}

/** 스킴 없이 입력한 주소에 https:// 를 붙인다. */
function normalizeUrl(value) {
  const trimmed = value.trim();
  if (trimmed === "") return "";
  return /^[a-z][a-z0-9+.-]*:/i.test(trimmed) ? trimmed : `https://${trimmed}`;
}

function shortUrl(code) {
  return `${window.location.origin}/${code}`;
}

/** "2026-11-13T09:30:00" 형태(KST)를 "2026-11-13 09:30" 으로 바꾼다. */
function formatDateTime(value) {
  return value ? value.replace("T", " ").slice(0, 16) : "";
}

function setMessage(element, text, isError = false) {
  element.textContent = text;
  element.classList.toggle("error", isError);
}

/**
 * HTTPS가 아닌 주소(예: ECS 퍼블릭 IP)에서는 Clipboard API가 없으므로 예전 방식으로 대신한다.
 * @param {string} text
 */
async function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const helper = document.createElement("textarea");
  helper.value = text;
  helper.setAttribute("readonly", "");
  helper.style.position = "fixed";
  helper.style.opacity = "0";
  document.body.append(helper);
  helper.select();
  const copied = document.execCommand("copy");
  helper.remove();
  if (!copied) throw new Error("복사하지 못했습니다.");
}

function makeButton(label, onClick, className = "") {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  if (className) button.className = className;
  button.addEventListener("click", onClick);
  return button;
}

/** 링크 한 건을 목록 항목으로 만든다. 사용자 입력은 textContent 로만 넣는다. */
function renderLink(link) {
  const item = document.createElement("li");
  item.className = "link-item";

  const info = document.createElement("div");
  info.className = "link-info";

  const short = document.createElement("a");
  short.className = "link-short";
  short.href = shortUrl(link.code);
  short.target = "_blank";
  short.rel = "noopener noreferrer";
  short.textContent = shortUrl(link.code).replace(/^https?:\/\//, "");
  info.append(short);

  if (link.title) {
    const title = document.createElement("span");
    title.className = "link-title";
    title.textContent = link.title;
    info.append(title);
  }

  const original = document.createElement("p");
  original.className = "link-original";
  original.textContent = link.original_url;
  original.title = link.original_url;
  info.append(original);

  const meta = document.createElement("p");
  meta.className = "link-meta";
  meta.textContent = `생성 ${formatDateTime(link.created_at)}` +
    (link.last_clicked_at ? ` · 마지막 클릭 ${formatDateTime(link.last_clicked_at)}` : "");
  info.append(meta);

  const clicks = document.createElement("div");
  clicks.className = "link-clicks";
  const count = document.createElement("strong");
  count.textContent = link.clicks.toLocaleString("ko-KR");
  const unit = document.createElement("span");
  unit.textContent = "클릭";
  clicks.append(count, unit);

  const actions = document.createElement("div");
  actions.className = "link-actions";
  const copyButton = makeButton("복사", async () => {
    try {
      await copyText(shortUrl(link.code));
      copyButton.textContent = "복사됨";
      setTimeout(() => { copyButton.textContent = "복사"; }, 1500);
    } catch (error) {
      setMessage(listMessage, error.message, true);
    }
  });
  actions.append(
    copyButton,
    makeButton("통계", () => openStats(link)),
    makeButton("수정", () => openEdit(link)),
    makeButton("삭제", () => removeLink(link), "danger"),
  );

  item.append(info, clicks, actions);
  return item;
}

async function loadLinks() {
  try {
    const links = await request(API_BASE);
    linkList.replaceChildren(...links.map(renderLink));
    const totalClicks = links.reduce((sum, link) => sum + link.clicks, 0);
    summary.textContent = links.length
      ? `링크 ${links.length}개 · 총 ${totalClicks.toLocaleString("ko-KR")}클릭`
      : "";
    setMessage(listMessage, links.length ? "" : "아직 만든 링크가 없습니다.");
  } catch (error) {
    setMessage(listMessage, error.message, true);
  }
}

async function openStats(link) {
  statsSummary.textContent = "불러오는 중…";
  statsChart.replaceChildren();
  statsDialog.showModal();
  try {
    const stats = await request(`${API_BASE}/${link.code}/stats?days=${STATS_DAYS}`);
    const recent = stats.daily.reduce((sum, day) => sum + day.clicks, 0);
    statsSummary.textContent =
      `/${stats.code} · 누적 ${stats.total_clicks.toLocaleString("ko-KR")}클릭 · 최근 ${STATS_DAYS}일 ${recent.toLocaleString("ko-KR")}클릭`;
    const peak = Math.max(1, ...stats.daily.map((day) => day.clicks));
    statsChart.replaceChildren(...stats.daily.map((day) => {
      const column = document.createElement("div");
      column.className = "chart-col";
      const value = document.createElement("span");
      value.className = "chart-value";
      value.textContent = String(day.clicks);
      const bar = document.createElement("div");
      bar.className = "chart-bar";
      bar.style.height = `${(day.clicks / peak) * 100}%`;
      const label = document.createElement("span");
      label.className = "chart-label";
      label.textContent = day.date.slice(5).replace("-", "/");
      column.append(value, bar, label);
      return column;
    }));
  } catch (error) {
    statsSummary.textContent = error.message;
  }
}

function openEdit(link) {
  editingCode = link.code;
  editUrl.value = link.original_url;
  editTitle.value = link.title ?? "";
  setMessage(editMessage, "");
  editDialog.showModal();
}

async function removeLink(link) {
  if (!window.confirm(`/${link.code} 링크를 삭제할까요? 클릭 기록도 함께 지워집니다.`)) return;
  try {
    await request(`${API_BASE}/${link.code}`, { method: "DELETE" });
    await loadLinks();
  } catch (error) {
    setMessage(listMessage, error.message, true);
  }
}

createForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const url = normalizeUrl(urlInput.value);
  if (url === "") {
    setMessage(formMessage, "단축할 주소를 입력하세요.", true);
    urlInput.focus();
    return;
  }
  const submitButton = createForm.querySelector("button[type=submit]");
  submitButton.disabled = true;
  try {
    const link = await request(API_BASE, {
      method: "POST",
      body: JSON.stringify({ url, title: titleInput.value || null }),
    });
    createForm.reset();
    setMessage(formMessage, `만들었습니다: ${shortUrl(link.code)}`);
    await loadLinks();
  } catch (error) {
    setMessage(formMessage, error.message, true);
  } finally {
    submitButton.disabled = false;
  }
});

editForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const url = normalizeUrl(editUrl.value);
  if (url === "") {
    setMessage(editMessage, "주소를 입력하세요.", true);
    return;
  }
  try {
    await request(`${API_BASE}/${editingCode}`, {
      method: "PUT",
      body: JSON.stringify({ url, title: editTitle.value || null }),
    });
    editDialog.close();
    await loadLinks();
  } catch (error) {
    setMessage(editMessage, error.message, true);
  }
});

for (const closeButton of document.querySelectorAll("[data-close]")) {
  closeButton.addEventListener("click", () => closeButton.closest("dialog").close());
}

// 다른 탭에서 단축 링크를 눌러 보고 돌아오면 클릭 수를 새로 고친다.
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") loadLinks();
});

loadLinks();
