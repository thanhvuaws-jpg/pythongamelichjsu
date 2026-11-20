/* Màn tải của trang game. tools/build_web.py chèn tệp này lên ĐẦU index.html của pygbag (trước cả pythons.js) và thay
 * __SK_CONFIG__ bằng { bundle, bundleBytes, wheel, wheelBytes, runtimeBytes, facts }.
 *
 * 1. Tải sớm: pygbag chỉ tải gói game sau khi Python khởi động xong, và chỉ tải pygame sau khi đã giải nén gói game
 *    (có khi còn đợi người chơi bấm). Ở đây hai tệp đó được tải ngay khi bộ chạy Python tải xong, trong lúc Python
 *    khởi động, với ĐÚNG cờ fetch pygbag dùng (credentials: omit) nên lần pygbag hỏi tới thì lấy luôn từ bộ đệm.
 * 2. Thanh tiến trình đếm byte thật của hai tệp đó, cộng với tiến độ tải main.data mà pygbag báo qua #progress.
 * 3. Chữ trạng thái đọc từ #status và #infobox của pygbag (đã bị CSS giấu đi), gỡ màn tải khi game đánh dấu
 *    data-sk-ready trên thẻ <html> (main.py, khung hình đầu tiên).
 */
(() => {
  const C = __SK_CONFIG__;
  const MB = (b) => (b / 1048576).toLocaleString("vi-VN", { maximumFractionDigits: 1, minimumFractionDigits: 1 });
  const got = { bundle: 0, wheel: 0 };
  const done = { bundle: false, wheel: false };

  function warm(key, url, expected) {
    // Cùng cờ với aio.filelike.fopen của pygbag (mặc định mode "cors"): cùng khoá bộ đệm, không tải hai lần
    fetch(url, { credentials: "omit", redirect: "follow" })
      .then(async (resp) => {
        if (!resp.ok || !resp.body) throw new Error(resp.status);
        const reader = resp.body.getReader();
        for (;;) {
          const { done: end, value } = await reader.read();
          if (end) break;
          got[key] = Math.min(expected, got[key] + value.byteLength);
        }
      })
      .catch(() => {}) // pygbag vẫn tự tải như cũ, chỉ mất phần song song
      .finally(() => { got[key] = expected; done[key] = true; });
  }
  let warmed = false;
  function warmAll() {
    if (warmed) return;
    warmed = true;
    if (C.bundle && !location.host.includes(".itch.zone")) warm("bundle", C.bundle, C.bundleBytes);
    if (C.wheel) warm("wheel", C.wheel, C.wheelBytes);
  }
  // Bộ chạy Python (main.wasm, main.data) phải có trước; gói game và pygame chỉ cần sau khi Python khởi động xong (thêm
  // 2-3 giây nữa). Nên đợi bộ chạy tải xong rồi mới tải hai tệp này, trong lúc Python khởi động: mạng yếu thì chúng
  // không giành băng thông của bộ chạy (đo 20/11 ở 10 Mbps: tải cùng lúc thì bộ chạy xong muộn hơn gần 2 giây).
  const runtimeSeen = new Set();
  try {
    new PerformanceObserver((list) => {
      for (const e of list.getEntries()) {
        const m = /cpython\d+\/main\.(wasm|data)$/.exec(e.name);
        if (m) runtimeSeen.add(m[1]);
      }
      if (runtimeSeen.size >= 2) warmAll();
    }).observe({ type: "resource", buffered: true });
  } catch (e) {
    warmAll();
  }
  setTimeout(warmAll, 20000);

  const TOTAL = C.runtimeBytes + C.bundleBytes + C.wheelBytes;
  const started = Date.now();
  let shown = 0, runtimeDone = false, needClick = false, clicked = false, gone = false;

  function setup() {
    const $ = (id) => document.getElementById(id);
    const root = $("sk-load"), fill = $("sk-fill"), walker = $("sk-walker"), step = $("sk-step"), pct = $("sk-pct");
    const note = $("sk-note"), go = $("sk-go");
    const isTouch = matchMedia("(pointer: coarse)").matches;
    go.textContent = isTouch ? "Chạm để vào game" : "Bấm để vào game";

    // ---- mẩu sử "Biết không?" lấy từ dữ liệu có nguồn của game, đổi mỗi 8 giây ----
    // pygbag bật hộp thoại alert cho MỌI lỗi JS trên trang, nên màn tải không bao giờ được ném lỗi: mọi việc chạy theo
    // hẹn giờ đều đi qua safe() và dừng hẳn khi màn tải đã gỡ (lỗi 20/11: hẹn giờ đổi mẩu sử còn chạy sau khi gỡ màn
    // tải, ghi vào phần tử không còn, hộp thoại "Cannot set properties of null" hiện lại mỗi 8 giây).
    const safe = (fn) => () => { if (!gone) try { fn(); } catch (e) { /* màn tải hỏng thì thôi, game vẫn chạy */ } };
    const fact = $("sk-fact");
    let fi = Math.floor(Math.random() * C.facts.length);
    const put = (id, text) => { const el = $(id); if (el) el.textContent = text; };
    function showFact() {
      const f = C.facts[fi++ % C.facts.length];
      put("sk-year", f.y);
      put("sk-title", f.t);
      put("sk-text", f.s);
      put("sk-src", f.src ? "Nguồn: " + f.src : "");
    }
    let factTimer = 0;
    if (C.facts.length) {
      safe(showFact)();
      factTimer = setInterval(safe(() => {
        fact.classList.add("fade");
        setTimeout(safe(() => { showFact(); fact.classList.remove("fade"); }), 460);
      }), 8000);
    } else fact.hidden = true;

    function unlockAudio() {
      if (clicked) return;
      clicked = true;
      try {
        const a = new Audio((window.config && config.cdn ? config.cdn : "") + "empty.ogg");
        const p = a.play();
        if (p) p.then(() => { if (window.MM) MM.UME = true; }).catch(() => {});
      } catch (e) { /* pygbag tự thử lại mỗi 2 giây */ }
    }
    go.addEventListener("click", unlockAudio);
    // Bấm/chạm ở đâu trên màn tải cũng tính là cho phép phát tiếng, kể cả khi đang tải (đỡ phải đợi bấm ở cuối)
    root.addEventListener("pointerdown", () => { if (needClick) unlockAudio(); }, { passive: true });

    function finish() {
      if (gone) return;
      gone = true;
      clearInterval(factTimer);
      try {
        root.classList.add("out");
        const canvas = $("canvas");
        if (canvas) canvas.focus();
      } catch (e) { /* như trên */ }
      setTimeout(() => { try { root.remove(); } catch (e) { /* đã gỡ */ } }, 900);
    }

    function tick() {
      if (gone) return;
      try {
        step_();
      } catch (e) {
        finish(); // màn tải lỗi thì gỡ luôn cho thấy game, không để lỗi lặp lại mỗi khung hình
        return;
      }
      requestAnimationFrame(tick);
    }

    function step_() {
      const status = ($("status") || {}).textContent || "";
      const info = $("infobox");
      const infoText = info && getComputedStyle(info).display !== "none" ? info.textContent : "";
      const prog = $("progress");
      const canvas = $("canvas");
      const pythonUp = canvas && canvas.style.visibility === "visible";
      if (pythonUp || /Running/i.test(status)) runtimeDone = true;
      if (runtimeDone) warmAll();

      // byte bộ chạy: main.data báo tiến độ qua #progress; main.wasm tải song song nên coi như cùng nhịp
      let rt = runtimeDone ? 1 : 0;
      if (!runtimeDone && prog && !prog.hidden && prog.value > 0) rt = Math.min(1, prog.value / 100);
      const bytes = rt * C.runtimeBytes + got.bundle + got.wheel;
      const allIn = runtimeDone && done.bundle && done.wheel;
      const ready = document.documentElement.dataset.skReady === "1";
      needClick = /click|touch/i.test(infoText);

      let target = Math.min(0.9, (bytes / TOTAL) * 0.9); // 90% cho tải, 10% cho khởi động
      let text;
      if (ready) { target = 1; text = "Xong!"; }
      else if (needClick && !clicked) { target = 1; text = "Đã tải xong"; }
      else if (clicked || (pythonUp && !infoText)) { target = Math.max(target, 0.97); text = "Đang dựng thế giới…"; }
      else if (allIn) { target = Math.max(target, 0.93); text = "Đang mở gói game…"; }
      else if (runtimeDone) text = "Đang tải dữ liệu game…";
      else text = "Đang tải bộ chạy Python cho trình duyệt…";

      // nhích từ từ tới đích, và tự bò chậm khi đang đợi để không trông như bị treo
      shown += (target - shown) * 0.12;
      if (!ready && shown < target + 0.02 && shown < 0.985) shown += 0.0004;
      const p = Math.max(0, Math.min(1, shown));
      fill.style.width = (p * 100).toFixed(1) + "%";
      walker.style.left = (p * 100).toFixed(1) + "%";
      step.textContent = text;
      pct.textContent = Math.round(p * 100) + "%" + (allIn ? "" : ` · ${MB(Math.min(bytes, TOTAL))} / ${MB(TOTAL)} MB`);
      go.hidden = !(needClick && !clicked);

      const secs = (Date.now() - started) / 1000;
      if (!allIn && secs > 25) note.textContent = "Mạng hơi chậm, game vẫn đang tải. Lần sau trình duyệt nhớ sẵn nên vào nhanh hơn.";

      // khung hình đầu của game đã vẽ: gỡ màn tải. Bản game cũ chưa biết đánh dấu thì gỡ sau khi pygbag xong 6 giây.
      if (ready) setTimeout(finish, 250);
      else if (pythonUp && !infoText && !tick.hiddenAt) tick.hiddenAt = Date.now();
      if (tick.hiddenAt && Date.now() - tick.hiddenAt > 6000) finish();
    }
    requestAnimationFrame(tick);
  }

  // Chạy ngay khi khối #sk-load vừa được dựng (build_web.py đặt lời gọi ngay sau khối đó), không đợi cả trang:
  // trang còn đợi browserfs.min.js từ CDN nên DOMContentLoaded đến muộn, màn tải sẽ đứng trống một lúc.
  let ran = false;
  window.__skSetup = () => {
    if (!ran && document.getElementById("sk-load")) { ran = true; setup(); }
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", window.__skSetup);
  else window.__skSetup();
})();
