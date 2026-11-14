// Trang chủ: vẽ mặt trống đồng trang trí, cho các phần hiện dần khi cuộn tới, đếm số liệu, lấy số người đang chơi.
(() => {
  const NS = "http://www.w3.org/2000/svg";
  const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ----- mặt trống: ngôi sao ở tâm, vành chấm tròn, vành chim bay (hình trang trí phỏng theo, không phải bản vẽ một chiếc trống cụ thể)
  const drum = document.querySelector(".drum");
  if (drum) {
    const star = drum.querySelector(".d-star");
    const pts = [];
    for (let i = 0; i < 28; i++) {
      const a = (Math.PI * 2 * i) / 28 - Math.PI / 2;
      const r = i % 2 ? 5 : 16;
      pts.push(`${(Math.cos(a) * r).toFixed(2)},${(Math.sin(a) * r).toFixed(2)}`);
    }
    star.setAttribute("points", pts.join(" "));
    const dots = drum.querySelector(".d-dots");
    for (let i = 0; i < 36; i++) {
      const a = (Math.PI * 2 * i) / 36;
      const c = document.createElementNS(NS, "circle");
      c.setAttribute("cx", (Math.cos(a) * 91).toFixed(2));
      c.setAttribute("cy", (Math.sin(a) * 91).toFixed(2));
      c.setAttribute("r", "2.2");
      dots.append(c);
    }
    const birds = drum.querySelector(".d-birds");
    for (let i = 0; i < 18; i++) {
      const g = document.createElementNS(NS, "path");
      // chim mỏ dài, đuôi xoè, bay theo vòng
      g.setAttribute("d", "M-9 0 L-2 -2 L4 0 L-2 2 Z M4 0 L10 -1 M-2 -1 L1 -6 L3 -1 M-2 1 L1 6 L3 1 M-9 0 L-13 -3 L-13 3 Z");
      g.setAttribute("transform", `rotate(${(360 * i) / 18}) translate(74 0) rotate(-90)`);
      birds.append(g);
    }
  }

  // ----- hiện dần khi cuộn tới
  const targets = document.querySelectorAll(".reveal, .eras li, .step");
  if (still || !("IntersectionObserver" in window)) {
    targets.forEach((el) => el.classList.add("in"));
  } else {
    const io = new IntersectionObserver((entries) => {
      for (const e of entries) {
        if (e.isIntersecting) {
          e.target.classList.add("in");
          io.unobserve(e.target);
        }
      }
    }, { threshold: 0.15 });
    targets.forEach((el, i) => {
      el.classList.add("reveal");
      el.style.transitionDelay = `${(i % 4) * 70}ms`;
      io.observe(el);
    });
  }

  // ----- đếm số liệu lên dần
  function countUp(el, to) {
    if (still) {
      el.textContent = to;
      return;
    }
    const start = performance.now();
    const step = (now) => {
      const k = Math.min(1, (now - start) / 900);
      el.textContent = Math.round(to * (1 - (1 - k) ** 3));
      if (k < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }
  const nums = document.querySelectorAll(".stats b[data-count]");
  const seen = new IntersectionObserver((entries) => {
    for (const e of entries) {
      if (e.isIntersecting) {
        countUp(e.target, Number(e.target.dataset.count));
        seen.unobserve(e.target);
      }
    }
  });
  nums.forEach((el) => seen.observe(el));

  // ----- số người đang ở thế giới chung (máy chủ chỉ trả số người mỗi map, không lộ ai ở đâu)
  const online = document.getElementById("online");
  async function refreshOnline() {
    try {
      const res = await fetch("/api/v1/world/online");
      if (!res.ok) throw new Error();
      const maps = await res.json();
      const total = Object.values(maps).reduce((a, b) => a + b, 0);
      online.textContent = total;
      online.closest(".stat").classList.toggle("on", total > 0);
    } catch {
      online.textContent = "–";
    }
  }
  if (online) {
    refreshOnline();
    setInterval(refreshOnline, 15000);
  }
})();
