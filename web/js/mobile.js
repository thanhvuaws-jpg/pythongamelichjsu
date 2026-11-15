// Chơi trên điện thoại: dùng chung cho trang chơi (play.html) và chế độ Chơi thử (/game/, trang của pygbag).
// - Cầm dọc: che game bằng lời nhắc xoay ngang (vẫn cho chơi dọc nếu muốn), vì khung game 16:9 cầm dọc chữ quá nhỏ.
// - Cầm ngang: ẩn thanh trên cùng của trang chơi để khung game được cao nhất.
// - Nút "Toàn màn hình" ẩn thanh địa chỉ của trình duyệt, xoay ngang luôn nếu máy cho phép (Android). iPhone không cho
//   trang web vào toàn màn hình nên không hiện nút.
// Tự gắn CSS và phần tử của mình nên chỉ cần một thẻ <script>.
(() => {
  const coarse = matchMedia("(pointer: coarse)").matches;
  const style = document.createElement("style");
  style.textContent = `
    .playpage { height: 100vh; height: 100dvh; }
    @media (pointer: coarse) and (orientation: landscape) and (max-height: 560px) {
      .playpage .bar { display: none; }
    }
    .sk-rotate { display: none; }
    @media (pointer: coarse) and (orientation: portrait) {
      body:not(.sk-doc) .sk-rotate {
        display: flex; position: fixed; inset: 0; z-index: 2147483000; align-items: center; justify-content: center;
        padding: 24px; background: rgba(20, 12, 10, 0.95); color: #f0e4c8; text-align: center;
        font: 16px/1.5 "Be Vietnam Pro", system-ui, sans-serif;
      }
    }
    .sk-rotate b { display: block; margin: 18px 0 6px; color: #f3d48c; font-size: 20px; }
    .sk-rotate p { margin: 0 0 18px; max-width: 320px; }
    .sk-phone {
      width: 38px; height: 64px; margin: 0 auto; border: 4px solid #f3d48c; border-radius: 8px;
      animation: sk-xoay 1.8s ease-in-out infinite;
    }
    @keyframes sk-xoay { 0%, 25% { transform: rotate(0); } 60%, 100% { transform: rotate(-90deg); } }
    .sk-rotate button, .sk-fs {
      font: 600 14px/1 "Be Vietnam Pro", system-ui, sans-serif; color: #f0e4c8; background: #2e1b15;
      border: 2px solid #b05e28; border-radius: 6px; padding: 10px 16px;
    }
    .sk-fs {
      position: fixed; top: 6px; left: 50%; transform: translateX(-50%); z-index: 2147482000; padding: 7px 12px;
      font-size: 13px; color: #f3d48c; background: rgba(28, 18, 15, 0.82); opacity: 0.9;
    }
  `;
  document.head.appendChild(style);

  const hint = document.createElement("div");
  hint.className = "sk-rotate";
  hint.setAttribute("role", "dialog");
  hint.setAttribute("aria-label", "Xoay ngang điện thoại");
  hint.innerHTML =
    '<div><div class="sk-phone" aria-hidden="true"></div><b>Xoay ngang điện thoại để chơi</b>' +
    "<p>Khung game rộng như màn hình máy tính, cầm ngang mới đủ chỗ đọc chữ và bấm nút.</p>" +
    '<button type="button">Vẫn chơi dọc</button></div>';
  hint.querySelector("button").addEventListener("click", () => document.body.classList.add("sk-doc"));
  document.body.appendChild(hint);

  const root = document.documentElement;
  const enter = root.requestFullscreen || root.webkitRequestFullscreen;
  if (!coarse || !enter) return;
  const fs = document.createElement("button");
  fs.type = "button";
  fs.className = "sk-fs";
  fs.textContent = "Toàn màn hình";
  const isFull = () => !!(document.fullscreenElement || document.webkitFullscreenElement);
  const sync = () => {
    fs.hidden = isFull();
  };
  fs.addEventListener("click", async () => {
    try {
      await enter.call(root, { navigationUI: "hide" });
      await screen.orientation?.lock?.("landscape");
    } catch {
      // trình duyệt từ chối khoá xoay hay toàn màn hình: vẫn chơi bình thường
    }
    sync();
    document.getElementById("game")?.focus();
  });
  document.addEventListener("fullscreenchange", sync);
  document.addEventListener("webkitfullscreenchange", sync);
  document.body.appendChild(fs);
  sync();
})();
