// Sử quán: cổng quản trị. Các trang (tổng quan, người dùng, người chơi máy, sổ thao tác) đổi theo #địa chỉ để tải lại vẫn
// ở đúng chỗ.
// Máy chủ kiểm tra quyền ở từng thao tác; ở đây chỉ ẩn những gì thẩm định viên không dùng được.
(async () => {
  const { h } = SK;
  const ROLES = { player: "Người chơi", editor: "Biên tập", reviewer: "Thẩm định", admin: "Quản trị" };
  const STATUS = {
    active: ["Đang hoạt động", ""],
    disabled: ["Đã khoá", "off"],
    pending_guardian: ["Chờ người lớn xác nhận", "wait"],
    deleting: ["Đang xoá", "off"],
  };
  const SKILLS = {
    phong_lao: "Phóng lao", dot_kich: "Đột kích", ten_lua: "Tên lửa", xoay_kiem: "Xoáy kiếm",
    the_thu: "Thế thủ", hoi_khi: "Hồi khí", chong_ngam: "Chông ngầm",
  };
  const BOTS = {
    b_trai_lang: "Trai làng tập võ", b_linh_tran: "Lính trấn thủ", b_vo_sinh: "Võ sinh áo đỏ",
    b_tho_san: "Thợ săn mạn ngược", b_thich_khach: "Thích khách áo xám", b_vo_su: "Võ sư già",
    b_xa_thu: "Xạ thủ nỏ", b_do_vat: "Đô vật làng", b_cao_thu: "Cao thủ ẩn danh",
  };
  // Chữ trên con dấu (ngắn để vừa ô vuông) và tên đầy đủ cho bộ lọc
  const ACTIONS = {
    user_grant: ["Điểm", "Cộng hoặc trừ điểm"],
    user_disable: ["Khoá", "Khoá tài khoản"],
    user_enable: ["Mở khoá", "Mở khoá, kích hoạt"],
    user_delete: ["Xoá", "Xoá tài khoản"],
    user_role_change: ["Đổi quyền", "Đổi vai trò"],
    password_reset: ["Mật khẩu", "Đặt lại mật khẩu"],
    guardian_consent: ["Xác nhận", "Người lớn xác nhận"],
    account_delete_request: ["Xin xoá", "Người chơi xin xoá tài khoản"],
    account_purged: ["Đã xoá", "Xoá hẳn dữ liệu"],
    link_google: ["Google", "Liên kết Google"],
    content_import: ["Nhập", "Nhập nội dung"],
    content_restore: ["Khôi phục", "Khôi phục nội dung"],
    level_publish: ["Xuất bản", "Xuất bản màn chơi"],
    media_upload: ["Tệp", "Tải tệp lên"],
    bot_add: ["Bot", "Thêm người chơi máy"],
    bot_remove: ["Bớt bot", "Xoá người chơi máy"],
  };

  const user = await SK.me().catch(() => null);
  if (!SK.canAdmin(user)) {
    location.replace("login.html");
    return;
  }
  const isAdmin = user.role === "admin";
  const side = document.getElementById("side");
  const work = document.getElementById("work");
  const drawer = document.getElementById("drawer");
  const ask = document.getElementById("ask");
  const toasts = document.getElementById("toasts");
  const fmt = new Intl.NumberFormat("vi-VN");
  const num = (n) => fmt.format(n || 0);

  // ----- tiện ích -----
  function when(iso) {
    const t = new Date(iso);
    const mins = Math.round((Date.now() - t) / 60000);
    if (mins < 1) return "vừa xong";
    if (mins < 60) return `${mins} phút trước`;
    if (mins < 24 * 60) return `${Math.round(mins / 60)} giờ trước`;
    return t.toLocaleString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
  }

  function toast(text, bad = false) {
    const node = h("div", { class: "toast" + (bad ? " bad" : "") }, text);
    toasts.append(node);
    setTimeout(() => node.remove(), bad ? 7000 : 4000);
  }

  function initial(name) {
    return (name || "?").trim().charAt(0).toUpperCase() || "?";
  }

  function head(title, sub, ...tools) {
    return h("header", { class: "head" },
      h("div", {}, h("h1", {}, title), sub ? h("p", {}, sub) : null),
      tools.length ? h("div", { class: "tools" }, tools) : null,
    );
  }

  function sheet(title, note, ...children) {
    return h("section", { class: "sheet2" }, title ? h("h2", {}, title) : null, note ? h("p", { class: "note" }, note) : null, children);
  }

  function state(u) {
    const [label, tone] = STATUS[u.status] || [u.status, ""];
    return h("span", { class: "state " + tone }, label);
  }

  function seal(text, cls = "") {
    return h("span", { class: "seal " + cls, "aria-hidden": "true" }, text);
  }

  // Mở hộp thoại và trả kết quả ngay khi bấm nút. Không chờ sự kiện "close" vì trình duyệt chỉ phát nó khi trang
  // đang được vẽ; Esc thì bắt qua sự kiện "cancel".
  function modal(build) {
    return new Promise((resolve) => {
      const finish = (value) => {
        ask.oncancel = null;
        if (ask.open) ask.close();
        resolve(value);
      };
      const first = build(finish);
      ask.oncancel = (event) => {
        event.preventDefault();
        finish(false);
      };
      ask.showModal();
      if (first) first.focus();
    });
  }

  // ----- hộp thoại xác nhận: việc không làm lại được thì bắt gõ tên để tránh bấm nhầm -----
  function confirmBox({ title, body, ok, danger = false, typeName = null }) {
    return modal((finish) => {
      const typed = typeName ? h("input", { type: "text", autocomplete: "off", "aria-label": "Gõ tên để xác nhận" }) : null;
      const okBtn = h("button", { class: "btn " + (danger ? "danger" : "gold"), type: "submit", disabled: Boolean(typeName) }, ok);
      if (typed) typed.addEventListener("input", () => { okBtn.disabled = typed.value.trim() !== typeName; });
      const form = h("form", {
        method: "dialog",
        onsubmit: (event) => {
          event.preventDefault();
          finish(true);
        },
      },
        h("h2", {}, title),
        h("div", { class: "body" }, body),
        typed ? h("label", { class: "field" }, `Gõ đúng tên “${typeName}” để xác nhận`, typed) : null,
        h("div", { class: "choices" },
          h("button", { class: "btn ghost", type: "button", onclick: () => finish(false) }, "Huỷ"),
          okBtn,
        ),
      );
      ask.replaceChildren(form);
      return typed || okBtn;
    });
  }

  function grantBox(u) {
    return modal((finish) => {
      const points = h("input", { name: "points", type: "number", value: 0, step: 1 });
      const skill = h("input", { name: "skill", type: "number", value: 0, step: 1 });
      const reason = h("input", { name: "reason", maxLength: 500, placeholder: "Ví dụ: thưởng thắng cuộc thi lớp" });
      const err = h("p", { class: "err", role: "alert", hidden: true });
      const quick = (input, amounts) => h("div", { class: "quick" }, amounts.map((n) => h("button", {
        class: "btn small ghost", type: "button",
        onclick: () => { input.value = Number(input.value || 0) + n; },
      }, (n > 0 ? "+" : "") + num(n))));
      const form = h("form", {
        method: "dialog",
        onsubmit: async (event) => {
          event.preventDefault();
          const body = { points: Number(points.value || 0), skill_points: Number(skill.value || 0), reason: reason.value.trim() || null };
          if (!body.points && !body.skill_points) {
            err.textContent = "Nhập số điểm cần cộng hoặc trừ.";
            err.hidden = false;
            return;
          }
          try {
            await SK.call(`/users/${u.id}/grant`, { method: "POST", body });
            finish(true);
            const parts = [];
            if (body.points) parts.push(`${body.points > 0 ? "+" : ""}${num(body.points)} điểm xếp hạng`);
            if (body.skill_points) parts.push(`${body.skill_points > 0 ? "+" : ""}${num(body.skill_points)} điểm kỹ năng`);
            toast(`Đã đổi điểm của ${u.display_name}: ${parts.join(", ")}.`);
          } catch (e) {
            err.textContent = e.status === 422 ? "Số điểm vượt giới hạn: tối đa 1.000.000 điểm xếp hạng và 10.000 điểm kỹ năng mỗi lần." : e.message;
            err.hidden = false;
          }
        },
      },
        h("h2", {}, "Cộng hoặc trừ điểm"),
        h("p", { class: "body" }, "Cho ", h("strong", {}, u.display_name + (u.id === user.id ? " (bạn)" : "")), ". Nhập số âm để trừ. Lần nào cũng được ghi vào sổ thao tác."),
        err,
        h("label", { class: "field" }, "Điểm xếp hạng", points),
        quick(points, [100, 1000, 10000, -100]),
        h("label", { class: "field" }, "Điểm kỹ năng", skill),
        quick(skill, [5, 20, 100, -5]),
        h("label", { class: "field" }, "Lý do", reason),
        h("div", { class: "choices" },
          h("button", { class: "btn ghost", type: "button", onclick: () => finish(false) }, "Huỷ"),
          h("button", { class: "btn gold", type: "submit" }, "Lưu điểm"),
        ),
      );
      ask.replaceChildren(form);
      setTimeout(() => points.select(), 0);
      return points;
    });
  }

  // ----- các thao tác dùng chung cho bảng và ngăn hồ sơ; trả về true khi đã đổi dữ liệu -----
  async function run(fn, okText) {
    try {
      await fn();
      toast(okText);
      return true;
    } catch (err) {
      toast(err.message, true);
      return false;
    }
  }

  function lock(u) {
    return confirmBox({
      title: `Khoá tài khoản ${u.display_name}?`,
      body: "Người này bị đăng xuất ngay và không đăng nhập được cho tới khi mở khoá. Tiến trình và điểm vẫn giữ nguyên.",
      ok: "Khoá tài khoản",
      danger: true,
    }).then((yes) => yes && run(() => SK.call(`/users/${u.id}/disable`, { method: "POST" }), `Đã khoá ${u.display_name}.`));
  }

  function unlock(u) {
    const label = u.status === "disabled" ? "Mở khoá" : "Kích hoạt";
    return run(() => SK.call(`/users/${u.id}/enable`, { method: "POST" }), `${label} xong cho ${u.display_name}.`);
  }

  function remove(u) {
    return confirmBox({
      title: "Xoá vĩnh viễn tài khoản?",
      body: [h("strong", {}, u.display_name), ` (${u.email}) sẽ mất toàn bộ tiến trình và điểm. Việc này không khôi phục được.`],
      ok: "Xoá vĩnh viễn",
      danger: true,
      typeName: u.display_name,
    }).then((yes) => yes && run(() => SK.call(`/users/${u.id}`, { method: "DELETE" }), `Đã xoá tài khoản ${u.display_name}.`));
  }

  function changeRole(u, role, isTeacher) {
    return run(
      () => SK.call(`/users/${u.id}/role`, { method: "PATCH", body: { role, is_teacher: isTeacher } }),
      `Đã lưu vai trò của ${u.display_name}.`,
    );
  }

  function actionsFor(u, after) {
    const isMe = u.id === user.id;
    const out = [h("button", { class: "btn small gold", type: "button", onclick: () => grantBox(u).then((ok) => ok && after()) }, "Điểm")];
    if (u.status === "active" && !isMe) {
      out.push(h("button", { class: "btn small ghost", type: "button", onclick: () => lock(u).then((ok) => ok && after()) }, "Khoá"));
    } else if (u.status === "disabled" || u.status === "pending_guardian") {
      out.push(h("button", { class: "btn small", type: "button", onclick: () => unlock(u).then((ok) => ok && after()) }, u.status === "disabled" ? "Mở khoá" : "Kích hoạt"));
    }
    if (!isMe) {
      out.push(h("button", { class: "btn small danger", type: "button", onclick: () => remove(u).then((ok) => { if (ok) { closeDrawer(); after(); } }) }, "Xoá"));
    }
    return out;
  }

  // ----- sổ thao tác: mỗi dòng một câu đọc được, kèm con dấu -----
  function grantText(after) {
    const parts = [];
    for (const [key, label] of [["points", "điểm xếp hạng"], ["skill_points", "điểm kỹ năng"]]) {
      const n = after?.[key] || 0;
      if (n) parts.push(`${n > 0 ? "+" : "−"}${num(Math.abs(n))} ${label}`);
    }
    return parts.join(", ");
  }

  function entryLine(e) {
    const actor = h("b", {}, e.actor_name || (e.actor_id ? "Một quản trị viên (tài khoản đã xoá)" : "Hệ thống"));
    const target = e.target_name ? h("b", {}, e.target_name) : "một tài khoản đã xoá";
    const after = e.after || {};
    const before = e.before || {};
    switch (e.action) {
      case "user_grant":
        return [[actor, " đổi điểm của ", target, ": ", grantText(after), "."], after.reason];
      case "user_disable":
        return [[actor, " khoá tài khoản ", target, "."], after.reason];
      case "user_enable":
        return [[actor, before.status === "pending_guardian" ? " kích hoạt tài khoản " : " mở khoá tài khoản ", target, "."], null];
      case "user_delete":
        return [[actor, " xoá vĩnh viễn một tài khoản", before.role ? ` (vai trò ${ROLES[before.role] || before.role})` : "", "."], null];
      case "user_role_change": {
        const bits = [];
        if (before.role !== after.role) bits.push(`từ ${ROLES[before.role] || before.role} sang ${ROLES[after.role] || after.role}`);
        if (before.is_teacher !== after.is_teacher) bits.push(after.is_teacher ? "đánh dấu là giáo viên" : "bỏ dấu giáo viên");
        return [[actor, " đổi vai trò của ", target, bits.length ? ": " + bits.join(", ") : "", "."], null];
      }
      case "bot_add": {
        const names = (after.bots || []).map((b) => b.name).join(", ");
        return [[actor, ` thêm ${(after.bots || []).length} người chơi máy ở ${after.map || "?"}: `, h("b", {}, names), "."], null];
      }
      case "bot_remove":
        return [[actor, e.target_id === "all" ? ` xoá hết người chơi máy (${before.count || 0} bot).` : [" xoá người chơi máy ", h("b", {}, before.name || "đã xoá"), "."]], null];
      default:
        return [[actor, ": ", (ACTIONS[e.action] || [e.action, e.action])[1].toLowerCase(), e.target_name ? [" cho ", target] : "", "."], null];
    }
  }

  function sealFor(e, i) {
    const [text] = ACTIONS[e.action] || ["Ghi"];
    if (e.action === "user_grant") {
      const neg = (e.after?.points || 0) < 0 || (e.after?.skill_points || 0) < 0;
      return seal(neg ? "Trừ" : "Cộng", (neg ? "minus " : "") + (i % 2 ? "even" : ""));
    }
    return seal(text, i % 2 ? "even" : "");
  }

  function ledger(entries, small = false) {
    return h("ol", { class: "ledger" }, entries.map((e, i) => {
      const [line, why] = entryLine(e);
      const s = sealFor(e, i);
      if (small) s.classList.add("small");
      return h("li", {},
        s,
        h("p", { class: "line" }, line, why ? h("span", { class: "why" }, "Lý do: " + why) : null),
        h("time", { datetime: e.created_at, title: new Date(e.created_at).toLocaleString("vi-VN") }, when(e.created_at)),
      );
    }));
  }

  // ----- biểu đồ -----
  function columns(days) {
    const top = Math.max(1, ...days.map((d) => d.count));
    const best = days.reduce((a, b) => (b.count > a.count ? b : a), days[0]);
    const label = (iso) => iso.slice(8, 10) + "/" + iso.slice(5, 7);
    return [
      h("div", { class: "cols", "aria-hidden": "true" }, days.map((d) => {
        const show = d.count > 0 && (d === best || d === days[days.length - 1]);
        const pct = (d.count / top) * 100;
        return h("div", { class: "c" + (d.count ? "" : " zero"), tabindex: "0" },
          h("i", { style: `height:${pct}%` }),
          show ? h("em", { style: `bottom:calc(${pct}% + 4px)` }, String(d.count)) : null,
          h("span", { class: "tip" }, `${label(d.date)}: ${d.count} tài khoản mới`),
        );
      })),
      h("div", { class: "days", "aria-hidden": "true" }, days.map((d) => h("span", {}, label(d.date)))),
      h("table", { class: "sr" }, h("caption", {}, "Tài khoản mới theo ngày"),
        h("tbody", {}, days.map((d) => h("tr", {}, h("th", {}, label(d.date)), h("td", {}, String(d.count)))))),
    ];
  }

  function hbars(rows) {
    return h("div", { class: "hbars" }, rows.map(({ label, ratio, text }) => h("div", { class: "hbar", title: `${label}: ${text}` },
      h("span", {}, label),
      h("div", { class: "track" }, h("div", { class: "fill", style: `width:${Math.round(Math.min(1, ratio) * 100)}%` })),
      h("span", { class: "val" }, text),
    )));
  }

  function countBars(counts, names, unit) {
    const rows = Object.entries(counts).sort((a, b) => b[1] - a[1]);
    const top = rows.length ? rows[0][1] : 1;
    return hbars(rows.map(([key, n]) => ({ label: names[key] || key, ratio: n / top, text: `${n} ${unit}` })));
  }

  // ===================== Tổng quan =====================
  async function overview() {
    work.replaceChildren(head("Tổng quan", "Đang tính số liệu..."));
    let s;
    try {
      s = await SK.call("/game/analytics");
    } catch (err) {
      work.replaceChildren(head("Tổng quan"), sheet(null, null, h("p", { class: "empty2" }, err.message)));
      return;
    }
    const tools = [h("a", { class: "btn small ghost", href: "/play.html", target: "_blank", rel: "noopener" }, "Vào game")];
    if (isAdmin) tools.unshift(h("button", { class: "btn small gold", type: "button", onclick: () => grantBox(user).then((ok) => ok && overview()) }, "Cộng điểm cho tôi"));
    const parts = [
      head("Tổng quan", `Cập nhật lúc ${new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" })}. Số liệu chơi tính từ bản lưu của người chơi.`, ...tools),
      h("section", { class: "sheet2 figures" },
        [[s.accounts, "tài khoản"], [s.accounts_new_7d, "tài khoản mới trong 7 ngày"], [s.players_with_save, "người đã chơi"],
          [s.active_7d, "người chơi trong 7 ngày"], [s.avg_points, "điểm trung bình"], [`${s.avg_stamps}/${s.total_relics}`, "di tích đóng dấu trung bình"]]
          .map(([v, l]) => h("div", { class: "figure" }, h("b", {}, typeof v === "number" ? num(v) : v), h("span", {}, l)))),
    ];
    const signups = s.signups_daily || [];
    const total14 = signups.reduce((a, d) => a + d.count, 0);
    const levelSheet = s.players_with_save
      ? sheet("Hoàn thành từng màn", `Trên ${s.players_with_save} người đã chơi.`,
        hbars(s.levels.map((lv) => ({ label: lv.title, ratio: lv.completed / s.players_with_save, text: `${lv.completed} người` }))))
      : sheet("Hoàn thành từng màn", null, h("p", { class: "empty2" }, "Chưa ai lưu tiến trình. Khi có người đăng nhập và chơi, số liệu sẽ hiện ở đây."));
    parts.push(h("div", { class: "grid2" },
      sheet("Tài khoản mới trong 14 ngày", `${total14} tài khoản. Rê chuột lên cột để xem từng ngày.`, columns(signups)),
      levelSheet,
    ));

    const hardest = s.hardest_questions.length
      ? h("div", { class: "tablewrap" }, h("table", { class: "tbl" },
        h("thead", {}, h("tr", {}, h("th", {}, "Câu hỏi"), h("th", { class: "num" }, "Thử trung bình"), h("th", { class: "num" }, "Bỏ cuộc"))),
        h("tbody", {}, s.hardest_questions.slice(0, 6).map((q) => h("tr", {},
          h("td", {}, q.prompt),
          h("td", { class: "num", "data-label": "Thử trung bình" }, `${q.avg_attempts} lần`),
          h("td", { class: "num", "data-label": "Bỏ cuộc" }, `${q.gave_up}/${q.players}`),
        )))))
      : h("p", { class: "empty2" }, "Chưa ai trả lời câu nào.");
    const row = [sheet("Câu hỏi khó nhất", "Câu nào người chơi phải thử nhiều lần nhất, nên xem lại cách hỏi hoặc lời giải thích.", hardest)];
    if (isAdmin) {
      const recent = sheet("Thao tác gần đây", null, h("p", { class: "empty2" }, "Đang tải sổ..."));
      row.push(recent);
      SK.call("/users/audit").then((out) => {
        const body = out.items.length
          ? [ledger(out.items.slice(0, 5), true), h("a", { class: "btn small ghost", href: "#so-thao-tac" }, "Mở sổ thao tác")]
          : [h("p", { class: "empty2" }, "Chưa có thao tác quản trị nào.")];
        recent.replaceChildren(h("h2", {}, "Thao tác gần đây"), ...body);
      }).catch((err) => recent.replaceChildren(h("h2", {}, "Thao tác gần đây"), h("p", { class: "empty2" }, err.message)));
    }
    parts.push(h("div", { class: "grid2" }, row));

    if (s.players_with_save) {
      const extra = [h("section", { class: "sheet2 figures" },
        [[s.activity.discovered, "lượt khám phá"], [s.activity.case_done, "vụ điều tra đã xong"], [s.activity.side_done, "nhiệm vụ phụ đã xong"], [s.activity.skirmish_done, "trận giao tranh đã thắng"], [s.activity.doc_done || 0, "tư liệu đã phục dựng"]]
          .map(([v, l]) => h("div", { class: "figure" }, h("b", {}, num(v)), h("span", {}, l))))];
      const pair = [];
      if (Object.keys(s.skills).length) pair.push(sheet("Kỹ năng được học", null, countBars(s.skills, SKILLS, "người")));
      if (Object.keys(s.arena_wins).length) pair.push(sheet("Thắng ở võ đài", null, countBars(s.arena_wins, BOTS, "người")));
      parts.push(...extra);
      if (pair.length) parts.push(h("div", { class: "grid2" }, pair));
    }
    work.replaceChildren(...parts);
  }

  // ===================== Người dùng =====================
  const query = { q: "", role: "", status: "", page: 1 };

  async function users() {
    const search = h("input", { type: "search", placeholder: "Tìm theo email hoặc tên", value: query.q, "aria-label": "Tìm người dùng" });
    const role = h("select", { "aria-label": "Lọc theo vai trò" }, h("option", { value: "" }, "Mọi vai trò"),
      Object.entries(ROLES).map(([value, label]) => h("option", { value, selected: value === query.role }, label)));
    const status = h("select", { "aria-label": "Lọc theo trạng thái" }, h("option", { value: "" }, "Mọi trạng thái"),
      Object.entries(STATUS).map(([value, [label]]) => h("option", { value, selected: value === query.status }, label)));
    const results = h("div", {}, h("p", { class: "empty2" }, "Đang tải danh sách..."));
    const apply = () => {
      Object.assign(query, { q: search.value.trim(), role: role.value, status: status.value, page: 1 });
      loadUsers(results);
    };
    role.addEventListener("change", apply);
    status.addEventListener("change", apply);
    work.replaceChildren(
      head("Người dùng", "Bấm vào tên để xem hồ sơ, tiến trình chơi và lịch sử thao tác.",
        h("button", { class: "btn small gold", type: "button", onclick: () => grantBox(user).then((ok) => ok && loadUsers(results)) }, "Cộng điểm cho tôi")),
      h("section", { class: "sheet2" },
        h("form", { class: "filters", onsubmit: (event) => { event.preventDefault(); apply(); } },
          search, role, status, h("button", { class: "btn small", type: "submit" }, "Tìm")),
        results,
      ),
    );
    loadUsers(results);
  }

  async function loadUsers(results) {
    const params = new URLSearchParams({ page: query.page });
    for (const key of ["q", "role", "status"]) if (query[key]) params.set(key, query[key]);
    let out;
    try {
      out = await SK.call("/users?" + params);
    } catch (err) {
      results.replaceChildren(h("p", { class: "empty2" }, err.message));
      return;
    }
    if (!out.items.length) {
      if (query.page > 1) {
        query.page -= 1;
        return loadUsers(results);
      }
      const filtered = query.q || query.role || query.status;
      results.replaceChildren(h("div", { class: "empty2" },
        h("p", {}, filtered ? "Không có tài khoản nào khớp bộ lọc." : "Chưa có tài khoản nào."),
        filtered ? h("button", { class: "btn small ghost", type: "button", onclick: () => { Object.assign(query, { q: "", role: "", status: "", page: 1 }); users(); } }, "Bỏ bộ lọc") : null,
      ));
      return;
    }
    const again = () => loadUsers(results);
    const pages = Math.max(1, Math.ceil(out.total / out.page_size));
    results.replaceChildren(
      h("div", { class: "tablewrap" }, h("table", { class: "tbl" },
        h("thead", {}, h("tr", {},
          h("th", {}, "Tài khoản"), h("th", {}, "Vai trò"), h("th", {}, "Trạng thái"),
          h("th", { class: "num" }, "Điểm xếp hạng"), h("th", { class: "num" }, "Kỹ năng tặng"), h("th", {}, h("span", { class: "sr" }, "Thao tác")),
        )),
        h("tbody", {}, out.items.map((u) => userRow(u, again))),
      )),
      h("div", { class: "pager2" },
        h("span", {}, `${num(out.total)} tài khoản, trang ${out.page}/${pages}`),
        h("span", { class: "rowactions" },
          h("button", { class: "btn small ghost", type: "button", disabled: query.page <= 1, onclick: () => { query.page -= 1; again(); } }, "Trang trước"),
          h("button", { class: "btn small ghost", type: "button", disabled: query.page >= pages, onclick: () => { query.page += 1; again(); } }, "Trang sau"),
        ),
      ),
    );
  }

  function userRow(u, again) {
    const isMe = u.id === user.id;
    return h("tr", {},
      h("td", {}, h("div", { class: "person" },
        h("span", { class: "avatar", "aria-hidden": "true" }, initial(u.display_name)),
        h("button", { type: "button", onclick: () => openUser(u.id, again) },
          h("b", {}, u.display_name + (isMe ? " (bạn)" : "")), h("small", {}, u.email)),
      )),
      h("td", { "data-label": "Vai trò" }, roleSelect(u, again)),
      h("td", {}, state(u)),
      h("td", { class: "num", "data-label": "Điểm xếp hạng" }, num(u.points)),
      h("td", { class: "num", "data-label": "Kỹ năng tặng" }, num(u.bonus_skill_points)),
      h("td", {}, h("div", { class: "rowactions" }, actionsFor(u, again))),
    );
  }

  function roleSelect(u, after) {
    return h("select", {
      "aria-label": "Vai trò của " + u.display_name,
      onchange: (event) => changeRole(u, event.target.value, u.is_teacher).then(after),
    }, Object.entries(ROLES).map(([value, label]) => h("option", { value, selected: value === u.role }, label)));
  }

  // ----- ngăn hồ sơ -----
  let lastFocus = null;

  function closeDrawer() {
    if (drawer.hidden) return;
    drawer.hidden = true;
    drawer.replaceChildren();
    if (lastFocus) lastFocus.focus();
  }

  drawer.addEventListener("click", (event) => { if (event.target === drawer) closeDrawer(); });
  document.addEventListener("keydown", (event) => { if (event.key === "Escape" && !drawer.hidden && !ask.open) closeDrawer(); });

  async function openUser(id, after) {
    lastFocus = document.activeElement;
    const pane = h("div", { class: "pane", role: "dialog", "aria-modal": "true", "aria-label": "Hồ sơ người dùng" }, h("p", { class: "empty2" }, "Đang mở hồ sơ..."));
    drawer.replaceChildren(pane);
    drawer.hidden = false;
    let d;
    try {
      d = await SK.call(`/users/${id}`);
    } catch (err) {
      pane.replaceChildren(h("button", { class: "btn small ghost close", type: "button", onclick: closeDrawer }, "Đóng"), h("p", { class: "empty2" }, err.message));
      return;
    }
    const refresh = () => { after(); openUser(id, after); };
    const sv = d.save;
    const close = h("button", { class: "btn small ghost close", type: "button", onclick: closeDrawer }, "Đóng");
    pane.replaceChildren(
      h("div", { class: "top" },
        h("span", { class: "avatar", "aria-hidden": "true" }, initial(d.display_name)),
        h("div", {}, h("h2", {}, d.display_name + (d.id === user.id ? " (bạn)" : "")), h("p", {}, d.email)),
        close,
      ),
      h("p", { class: "muted" }, state(d), `, tạo ngày ${new Date(d.created_at).toLocaleDateString("vi-VN")}${d.email_verified ? ", đã xác minh email" : ""}.`),
      h("div", { class: "acts" }, actionsFor(d, refresh)),
      h("div", { class: "roleline" },
        h("label", {}, "Vai trò ", roleSelect(d, refresh)),
        h("label", {}, h("input", {
          type: "checkbox", checked: d.is_teacher,
          onchange: (event) => changeRole(d, d.role, event.target.checked).then(refresh),
        }), " Là giáo viên (được tạo lớp, xem tiến độ học sinh)"),
      ),
      h("h3", {}, "Điểm"),
      h("div", { class: "facts" },
        h("div", {}, h("b", {}, num(d.points)), h("span", {}, "điểm xếp hạng")),
        h("div", {}, h("b", {}, num(d.bonus_skill_points)), h("span", {}, "điểm kỹ năng được tặng")),
      ),
      h("h3", {}, "Tiến trình chơi"),
      sv.has_save
        ? h("div", {},
          h("div", { class: "levels" }, sv.levels.map((lv, i) => h("div", {},
            seal(lv.completed ? "Xong" : "Chưa", lv.completed ? (i % 2 ? "even" : "") : "blank"),
            lv.title,
          ))),
          h("div", { class: "facts" },
            h("div", {}, h("b", {}, `Cấp ${num(sv.level)}`), h("span", {}, `cảnh giới ${sv.realm}`)),
            h("div", {}, h("b", {}, `${sv.stamps}/${sv.total_relics}`), h("span", {}, "di tích đã đóng dấu")),
            h("div", {}, h("b", {}, num(sv.solved)), h("span", {}, "câu hỏi đã giải")),
            h("div", {}, h("b", {}, num(sv.badges)), h("span", {}, "danh hiệu")),
            h("div", {}, h("b", {}, num(sv.skills)), h("span", {}, "kỹ năng đã học")),
            h("div", {}, h("b", {}, num(sv.discovered)), h("span", {}, "lượt khám phá")),
            h("div", {}, h("b", {}, num(sv.cases + sv.sides)), h("span", {}, "vụ điều tra và nhiệm vụ phụ")),
            h("div", {}, h("b", {}, num(sv.mobs_killed)), h("span", {}, "bóng giặc đã hạ")),
            h("div", {}, h("b", {}, num(sv.guards_beaten)), h("span", {}, "kẻ canh mật thư đã hạ")),
          ),
          h("p", { class: "muted" }, `Lưu lần cuối ${when(sv.updated_at)}.`),
        )
        : h("p", { class: "muted" }, "Chưa chơi lần nào, hoặc chưa đăng nhập khi chơi nên tiến trình chưa được lưu lên máy chủ."),
      h("h3", {}, "Thao tác quản trị lên tài khoản này"),
      d.history.length ? ledger(d.history, true) : h("p", { class: "muted" }, "Chưa có thao tác nào."),
    );
    close.focus();
  }

  // ===================== Sổ thao tác =====================
  const auditQuery = { action: "", page: 1 };

  async function audit() {
    const pick = h("select", { "aria-label": "Lọc theo loại thao tác", onchange: (event) => { auditQuery.action = event.target.value; auditQuery.page = 1; loadAudit(results); } },
      h("option", { value: "" }, "Mọi thao tác"),
      Object.entries(ACTIONS).map(([value, [, label]]) => h("option", { value, selected: value === auditQuery.action }, label)));
    const results = h("div", {}, h("p", { class: "empty2" }, "Đang mở sổ..."));
    work.replaceChildren(
      head("Sổ thao tác", "Mọi lần cộng điểm, khoá, mở khoá, đổi vai trò và xoá tài khoản đều được ghi lại, kể cả của chính bạn. Không ai sửa được sổ này."),
      h("section", { class: "sheet2" }, h("div", { class: "filters" }, pick), results),
    );
    loadAudit(results);
  }

  async function loadAudit(results) {
    let out;
    try {
      out = await SK.call("/users/audit?" + new URLSearchParams({ page: auditQuery.page, ...(auditQuery.action ? { action: auditQuery.action } : {}) }));
    } catch (err) {
      results.replaceChildren(h("p", { class: "empty2" }, err.message));
      return;
    }
    if (!out.items.length) {
      results.replaceChildren(h("p", { class: "empty2" }, auditQuery.action ? "Chưa có thao tác loại này." : "Sổ còn trống. Thao tác đầu tiên của quản trị viên sẽ hiện ở đây."));
      return;
    }
    const pages = Math.max(1, Math.ceil(out.total / out.page_size));
    results.replaceChildren(
      ledger(out.items),
      h("div", { class: "pager2" },
        h("span", {}, `${num(out.total)} dòng, trang ${out.page}/${pages}`),
        h("span", { class: "rowactions" },
          h("button", { class: "btn small ghost", type: "button", disabled: auditQuery.page <= 1, onclick: () => { auditQuery.page -= 1; loadAudit(results); } }, "Trang trước"),
          h("button", { class: "btn small ghost", type: "button", disabled: auditQuery.page >= pages, onclick: () => { auditQuery.page += 1; loadAudit(results); } }, "Trang sau"),
        ),
      ),
    );
  }

  // ===================== Người chơi máy =====================
  // Nhân vật máy chủ tự điều khiển cho thế giới có người: tự cày quái, làm nhiệm vụ. Không gắn với tài khoản nào.
  let botTimer = null;

  async function botsView() {
    work.replaceChildren(head("Người chơi máy", "Đang tải..."));
    let out;
    try {
      out = await SK.call("/world/bots");
    } catch (err) {
      work.replaceChildren(head("Người chơi máy"), sheet(null, null, h("p", { class: "empty2" }, err.message)));
      return;
    }
    const mapPick = h("select", { "aria-label": "Map", required: true },
      out.maps.map((m) => h("option", { value: m.id }, m.name)));
    const actPick = h("select", { "aria-label": "Việc bot làm" },
      Object.entries(out.activities).map(([value, label]) => h("option", { value }, label)));
    const count = h("input", { type: "number", min: 1, max: 20, value: 3, "aria-label": "Số bot", style: "width:5.5em" });
    const level = h("input", { type: "number", min: 1, max: 40, value: 5, "aria-label": "Cấp lúc đầu", style: "width:5.5em" });
    const name = h("input", { type: "text", maxlength: 40, placeholder: "Tên (để trống: tự đặt tên)", "aria-label": "Tên bot" });
    const form = h("form", {
      class: "filters",
      onsubmit: async (event) => {
        event.preventDefault();
        const body = { map_id: mapPick.value, activity: actPick.value, count: Number(count.value), level: Number(level.value), name: name.value.trim() || null };
        if (await run(() => SK.call("/world/bots", { method: "POST", body }), `Đã thêm ${body.count} người chơi máy`)) botsView();
      },
    },
      h("label", { class: "field" }, "Map", mapPick),
      h("label", { class: "field" }, "Việc", actPick),
      h("label", { class: "field" }, "Số bot", count),
      h("label", { class: "field" }, "Cấp đầu", level),
      h("label", { class: "field" }, "Tên", name),
      h("button", { class: "btn small gold", type: "submit" }, "Thêm bot"),
    );
    const list = h("div", {});
    const removeAll = h("button", {
      class: "btn small danger", type: "button", disabled: !out.bots.length,
      onclick: async () => {
        const ok = await confirmBox({ title: "Xoá hết người chơi máy?", body: `Xoá ${out.bots.length} bot khỏi mọi map. Người chơi thật không bị ảnh hưởng.`, ok: "Xoá hết", danger: true });
        if (ok && await run(() => SK.call("/world/bots", { method: "DELETE" }), "Đã xoá hết người chơi máy")) botsView();
      },
    }, "Xoá hết");
    work.replaceChildren(
      head("Người chơi máy", `Nhân vật do máy chủ điều khiển, hiện trong game như người chơi khác: tự cày quái, làm nhiệm vụ, sắm đồ, câu cá. Không gắn với tài khoản nào, không có trên bảng xếp hạng. Đang có ${num(out.bots.length)}/${num(out.max)} bot và ${num(out.online_people)} người chơi thật online.`, removeAll),
      sheet("Thêm người chơi máy", "Chọn map và việc bot hay làm. Bot tự lên cấp khi hạ đủ quái; khởi động lại máy chủ không mất bot.", form),
      sheet("Đang chạy", "Tự làm mới vài giây một lần.", list),
    );
    const draw = (bots) => {
      if (!bots.length) {
        list.replaceChildren(h("p", { class: "empty2" }, "Chưa có người chơi máy nào. Thêm vài bot ở trên để map đỡ vắng."));
        return;
      }
      list.replaceChildren(h("div", { class: "tablewrap" }, h("table", { class: "tbl" },
        h("thead", {}, h("tr", {}, h("th", {}, "Tên"), h("th", {}, "Map"), h("th", {}, "Việc"), h("th", { class: "num" }, "Cấp"),
          h("th", {}, "Đang làm gì"), h("th", {}, h("span", { class: "sr" }, "Thao tác")))),
        h("tbody", {}, bots.map((b) => h("tr", {},
          h("td", {}, h("b", {}, b.name)), h("td", {}, b.map_name), h("td", {}, out.activities[b.activity] || b.activity),
          h("td", { class: "num" }, b.level), h("td", {}, b.doing),
          h("td", {}, h("button", { class: "btn small ghost", type: "button", onclick: async () => {
            if (await run(() => SK.call(`/world/bots/${b.id}`, { method: "DELETE" }), `Đã xoá ${b.name}`)) botsView();
          } }, "Xoá")),
        ))),
      )));
    };
    draw(out.bots);
    clearInterval(botTimer);
    botTimer = setInterval(async () => {
      if (location.hash !== "#nguoi-choi-may") {
        clearInterval(botTimer);
        return;
      }
      try {
        const fresh = await SK.call("/world/bots");
        out.bots = fresh.bots;
        draw(fresh.bots);
      } catch {
        /* mất mạng một lúc: lần sau làm mới tiếp */
      }
    }, 4000);
  }

  // ===================== Khung trang =====================
  const VIEWS = [
    { id: "tong-quan", label: "Tổng quan", run: overview },
    { id: "nguoi-dung", label: "Người dùng", run: users, admin: true },
    { id: "nguoi-choi-may", label: "Người chơi máy", run: botsView, admin: true },
    { id: "so-thao-tac", label: "Sổ thao tác", run: audit, admin: true },
  ].filter((v) => isAdmin || !v.admin);

  function renderSide(current) {
    side.replaceChildren(
      h("a", { class: "brand", href: "#tong-quan" }, h("img", { src: "../img/icon.png", alt: "" }),
        h("span", {}, "Sử quán", h("small", {}, "Quản trị Sử Ký Điều Tra"))),
      h("nav", { "aria-label": "Mục quản trị" }, VIEWS.map((v) => h("a", { href: "#" + v.id, "aria-current": v.id === current ? "page" : "false" }, v.label))),
      h("div", { class: "sidefoot" },
        h("p", { class: "who" }, h("b", {}, user.display_name), `${ROLES[user.role]}, ${user.email}`),
        h("a", { class: "link", href: "/play.html", target: "_blank", rel: "noopener" }, "Vào game"),
        h("button", { type: "button", onclick: async () => { await SK.logout(); location.replace("login.html"); } }, "Đăng xuất"),
      ),
    );
  }

  function route() {
    closeDrawer();
    const id = location.hash.slice(1);
    const view = VIEWS.find((v) => v.id === id) || VIEWS[0];
    renderSide(view.id);
    document.title = `${view.label}: Sử quán`;
    view.run();
    work.focus({ preventScroll: true });
  }

  window.addEventListener("hashchange", route);
  route();
})();
