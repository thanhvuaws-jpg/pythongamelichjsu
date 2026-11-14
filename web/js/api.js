// Gọi API và giữ phiên đăng nhập. Mã truy cập ngắn hạn nằm trong sessionStorage; phiên dài hạn là cookie HttpOnly do máy chủ đặt.
window.SK = (() => {
  const API = "/api/v1";
  const TOKEN_KEY = "sk_access";
  const SAFE_NEXT = ["play.html", "leaderboard.html"];
  let access = sessionStorage.getItem(TOKEN_KEY);
  let pending = null;

  function setToken(value) {
    access = value;
    if (value) sessionStorage.setItem(TOKEN_KEY, value);
    else sessionStorage.removeItem(TOKEN_KEY);
  }

  async function doRefresh() {
    const res = await fetch(API + "/auth/refresh", { method: "POST", credentials: "same-origin" });
    if (!res.ok) {
      setToken(null);
      return false;
    }
    setToken((await res.json()).access_token);
    return true;
  }

  // Mỗi mã làm mới chỉ dùng được một lần, hai lần gọi đồng thời sẽ bị máy chủ coi là bị đánh cắp.
  // Vì vậy gộp các lần gọi trong một tab và khoá giữa các tab.
  function refresh() {
    if (!pending) {
      const run = navigator.locks ? navigator.locks.request("sk_refresh", doRefresh) : doRefresh();
      pending = run.finally(() => { pending = null; });
    }
    return pending;
  }

  async function send(path, { method = "GET", body, keepalive = false }) {
    const headers = {};
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (access) headers.Authorization = "Bearer " + access;
    return fetch(API + path, {
      method, headers, keepalive, credentials: "same-origin",
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  }

  async function call(path, options = {}) {
    let res = await send(path, options);
    if (res.status === 401 && !path.startsWith("/auth/login") && (await refresh())) {
      res = await send(path, options);
    }
    if (res.status === 204) return null;
    const data = await res.json().catch(() => null);
    if (!res.ok) {
      const err = new Error(data?.error?.message || "Không kết nối được máy chủ, hãy thử lại sau ít phút.");
      err.status = res.status;
      err.code = data?.error?.code;
      throw err;
    }
    return data;
  }

  async function me() {
    if (!access && !(await refresh())) return null;
    try {
      return await call("/auth/me");
    } catch (err) {
      if (err.status === 401) return null;
      throw err;
    }
  }

  async function login(email, password) {
    const out = await call("/auth/login", { method: "POST", body: { email, password } });
    setToken(out.access_token);
  }

  async function logout() {
    await call("/auth/logout", { method: "POST" }).catch(() => null);
    setToken(null);
  }

  function toLogin() {
    const here = location.pathname.split("/").pop();
    location.replace("login.html" + (SAFE_NEXT.includes(here) ? "?next=" + here : ""));
  }

  function nextPage() {
    const next = new URLSearchParams(location.search).get("next");
    return SAFE_NEXT.includes(next) ? next : "play.html";
  }

  // Tạo phần tử bằng textContent: tên người dùng không bao giờ được hiểu là HTML.
  function h(tag, props = {}, ...children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(props)) {
      if (key === "class") node.className = value;
      else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
      else if (key in node && key !== "style") node[key] = value;
      else node.setAttribute(key, value);
    }
    for (const child of children.flat(Infinity)) {
      if (child !== null && child !== undefined) node.append(child);
    }
    return node;
  }

  function canAdmin(user) {
    return user && (user.role === "admin" || user.role === "reviewer");
  }

  // Dựng thanh trên cùng theo trạng thái đăng nhập. `user` là undefined thì tự hỏi máy chủ.
  async function renderBar(user) {
    const bar = document.getElementById("bar");
    if (!bar) return null;
    if (user === undefined) user = await me().catch(() => null);
    const right = document.createDocumentFragment();
    right.append(h("a", { class: "link", href: "leaderboard.html" }, "Bảng xếp hạng"));
    // Người chơi thường không thấy liên kết này; cổng quản trị có địa chỉ và trang đăng nhập riêng
    if (canAdmin(user)) right.append(h("a", { class: "link", href: "/admin/" }, "Trang quản trị"));
    if (user) {
      right.append(h("span", { class: "who" }, user.display_name));
      right.append(h("button", { class: "link", type: "button", onclick: async () => { await logout(); location.href = "index.html"; } }, "Đăng xuất"));
    } else {
      right.append(h("a", { class: "link", href: "login.html" }, "Đăng nhập"));
    }
    bar.replaceChildren(
      h("a", { class: "brand", href: "index.html" }, h("img", { src: "img/icon.png", alt: "" }), "Sử Ký Điều Tra"),
      h("span", { class: "spacer" }),
      right,
    );
    return user;
  }

  function show(id, text, bad = false) {
    const box = document.getElementById(id);
    box.textContent = text;
    box.classList.toggle("bad", bad);
    box.hidden = !text;
  }

  // Mã truy cập hiện tại, cho WebSocket của thế giới chung (trình duyệt không cho WebSocket gửi header Authorization)
  function token() {
    return access;
  }

  return { call, me, login, logout, toLogin, nextPage, h, canAdmin, renderBar, show, token };
})();
