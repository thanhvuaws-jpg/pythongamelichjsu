// Trang chơi: nạp bản lưu từ máy chủ trước khi mở game, rồi đẩy bản lưu lên định kỳ.
// Game chỉ đọc ghi localStorage nên không cần biết có máy chủ; bản lưu đi qua lại ở đây.
(async () => {
  const SAVE_KEY = "sukydieutra.save.v1"; // trùng với core/platform_io.py
  const OWNER_KEY = "sukydieutra.owner";
  const ROLE_KEY = "sukydieutra.role"; // game đọc để mở quyền đi lại của quản trị viên
  const BONUS_KEY = "sukydieutra.bonus"; // game đọc để cộng điểm được tặng
  const HONOR_KEY = "sukydieutra.honor"; // game đọc để vẽ Bảng vàng ở map đầu
  const HONOR_MS = 60000;
  const BONUS_MS = 15000;
  const SYNC_MS = 20000;
  const KEEPALIVE_LIMIT = 60000; // trình duyệt giới hạn 64 KB cho yêu cầu gửi lúc đóng trang

  const user = await SK.me().catch(() => null);
  if (!user) return SK.toLogin();

  const status = SK.h("span", { class: "savestate", role: "status" }, "");
  let lastSent = null;

  function parse(raw) {
    try {
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  function applyBonus(out) {
    localStorage.setItem(BONUS_KEY, JSON.stringify({ points: out.bonus_points, skill_points: out.bonus_skill_points }));
  }

  // Chuỗi đưa sang game chỉ gồm ký tự ASCII (chữ có dấu đổi thành mã thoát của JSON): tránh lỗi mã chữ giữa JavaScript
  // và Python trong pygbag
  function asciiJson(raw) {
    return raw.replace(/[^\x00-\x7e]/g, (c) => "\\" + "u" + c.charCodeAt(0).toString(16).padStart(4, "0"));
  }

  function isNewer(a, b) {
    return String(a?.updated_at || "") > String(b?.updated_at || "");
  }

  // Bản nào mới hơn thì dùng. Máy dùng chung: bản của người khác để lại thì bỏ, để không lẫn tiến trình.
  async function restore() {
    let local = parse(localStorage.getItem(SAVE_KEY));
    const owner = localStorage.getItem(OWNER_KEY);
    if (owner && owner !== user.id) {
      localStorage.removeItem(SAVE_KEY);
      local = null;
    }
    const server = await SK.call("/game/save");
    applyBonus(server);
    if (server.data && (!local || isNewer(server.data, local))) {
      const raw = JSON.stringify(server.data);
      localStorage.setItem(SAVE_KEY, raw);
      lastSent = raw;
    }
    localStorage.setItem(OWNER_KEY, user.id);
  }

  async function sync(closing = false) {
    const raw = localStorage.getItem(SAVE_KEY);
    if (!raw || raw === lastSent) return;
    const data = parse(raw);
    if (!data) return;
    try {
      const out = await SK.call("/game/save", {
        method: "PUT",
        body: { data },
        keepalive: closing && raw.length < KEEPALIVE_LIMIT,
      });
      lastSent = raw;
      applyBonus(out);
      const time = new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
      status.textContent = `Đã lưu lúc ${time}, ${out.points + out.bonus_points} điểm xếp hạng`;
    } catch {
      status.textContent = "Chưa lưu lên máy chủ được, sẽ tự thử lại. Tiến trình vẫn còn trên máy này.";
    }
  }

  await SK.renderBar(user);
  const bar = document.getElementById("bar");
  bar.insertBefore(status, bar.querySelector(".spacer").nextSibling);
  // Đăng xuất trên máy dùng chung: lưu lần cuối rồi xoá để người sau không thấy tiến trình của bạn
  const logoutButton = [...bar.querySelectorAll("button.link")].pop();
  logoutButton.replaceWith(
    SK.h("button", {
      class: "link",
      type: "button",
      onclick: async () => {
        await sync();
        localStorage.removeItem(SAVE_KEY);
        localStorage.removeItem(OWNER_KEY);
        localStorage.removeItem(ROLE_KEY);
        localStorage.removeItem(BONUS_KEY);
        localStorage.removeItem(HONOR_KEY);
        await SK.logout();
        location.href = "index.html";
      },
    }, "Đăng xuất"),
  );

  localStorage.setItem(ROLE_KEY, user.role);
  try {
    await restore();
  } catch {
    status.textContent = "Chưa nạp được bản lưu từ máy chủ, đang dùng bản trên máy này.";
  }

  // Thế giới chung: trang chơi giữ WebSocket, game (cùng nguồn, trong khung) đọc ghi qua window.SKNet bằng chuỗi JSON.
  // Mất kết nối thì tự nối lại; game vẫn chơi một mình được khi máy chủ không có.
  const NET = { ws: null, queue: [], status: "off", retry: 0 };
  async function connectWorld() {
    NET.status = "connecting";
    await SK.me().catch(() => null); // làm mới mã truy cập nếu đã hết hạn
    const proto = location.protocol === "https:" ? "wss" : "ws";
    let ws;
    try {
      ws = new WebSocket(`${proto}://${location.host}/api/v1/world/ws`);
    } catch {
      NET.status = "off";
      return;
    }
    NET.ws = ws;
    ws.onopen = () => {
      ws.send(JSON.stringify({ t: "auth", token: SK.token() }));
      NET.status = "on";
      NET.retry = 0;
    };
    ws.onmessage = (event) => {
      NET.queue.push(event.data);
      if (NET.queue.length > 400) NET.queue.splice(0, NET.queue.length - 300); // game đang tạm dừng thì bỏ bớt tin cũ
    };
    ws.onclose = () => {
      NET.status = "off";
      NET.ws = null;
      NET.retry = Math.min(NET.retry + 1, 6);
      setTimeout(connectWorld, 1500 * NET.retry + Math.random() * 1000);
    };
  }
  window.SKNet = {
    send(raw) {
      if (NET.ws && NET.ws.readyState === WebSocket.OPEN && typeof raw === "string" && raw.length < 8000) NET.ws.send(raw);
    },
    take() {
      const out = asciiJson("[" + NET.queue.join(",") + "]");
      NET.queue = [];
      return out;
    },
    status() {
      return NET.status;
    },
  };
  connectWorld();

  const frame = document.getElementById("game");
  frame.addEventListener("load", () => frame.focus());
  frame.src = "/game/index.html";

  // Chat: game gọi SKChat.open khi bấm L; tin gõ xong nằm chờ trong hộp thư đi, game lấy ra bằng SKChat.take để tự trừ
  // tiền quan (kênh thế giới) trong bản lưu rồi mới gửi lên máy chủ.
  const chatForm = document.getElementById("chatbar");
  const chatInput = document.getElementById("chatinput");
  const chatOut = [];
  let chatCh = "map";
  function setChannel(ch) {
    chatCh = ch === "world" ? "world" : "map";
    for (const b of chatForm.querySelectorAll("[data-ch]")) b.setAttribute("aria-selected", String(b.dataset.ch === chatCh));
  }
  function closeChat() {
    chatForm.hidden = true;
    chatInput.value = "";
    frame.focus();
    try {
      frame.contentWindow.focus();
    } catch {
      /* khung game chưa nạp xong */
    }
  }
  for (const b of chatForm.querySelectorAll("[data-ch]")) {
    b.addEventListener("click", () => {
      setChannel(b.dataset.ch);
      chatInput.focus();
    });
  }
  chatForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const text = chatInput.value.trim().slice(0, 120);
    if (text) chatOut.push({ ch: chatCh, text });
    closeChat();
  });
  chatInput.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      event.preventDefault();
      closeChat();
    } else if (event.key === "Tab") {
      event.preventDefault();
      setChannel(chatCh === "map" ? "world" : "map");
    }
  });
  window.SKChat = {
    open(ch) {
      setChannel(String(ch || chatCh));
      chatForm.hidden = false;
      chatInput.focus();
      return "ok";
    },
    take() {
      const out = asciiJson(JSON.stringify(chatOut));
      chatOut.length = 0;
      return out;
    },
  };

  setInterval(sync, SYNC_MS);
  setInterval(() => SK.call("/game/bonus").then(applyBonus).catch(() => null), BONUS_MS);
  const loadHonor = () =>
    SK.call("/game/honor")
      .then((out) => localStorage.setItem(HONOR_KEY, JSON.stringify({ ...out, at: Date.now() })))
      .catch(() => null);
  loadHonor();
  setInterval(loadHonor, HONOR_MS);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") sync(true);
  });
  window.addEventListener("pagehide", () => sync(true));
})();
