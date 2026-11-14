# Sử Ký Điều Tra — Kế hoạch cập nhật

> Tài liệu này đối chiếu yêu cầu đề bài (đề số 5) với hiện trạng thư mục, chốt các quyết định
> dọn dẹp, bổ sung thiết kế lối chơi và lộ trình tới khi deploy. Spec gốc vẫn nằm ở
> `.kiro/specs/vietnam-history-quest-game/` và vẫn là căn cứ chi tiết.

## 1. Yêu cầu của đề — checklist

| Mục trong đề | Ý nghĩa cụ thể | Trạng thái |
|---|---|---|
| Lĩnh vực: Game — History Learning | Học lịch sử qua chơi, không phải ôn thuộc lòng | Thiết kế lối chơi ở mục 4 |
| Hướng tiếp cận: Map + Timeline + Quest | Bản đồ Việt Nam tương tác, dòng thời gian, hệ thống nhiệm vụ | Game client đợt 1 |
| Công nghệ: Pygame (pygame-ce) + **pygbag** chạy web (WebAssembly) | Toàn bộ game viết Python, build thành web | `game/` + `tools/build_web.py` |
| Firebase/Supabase/**PostgreSQL** lưu trữ | Dữ liệu người dùng, tiến trình, điểm | Backend đã có (PostgreSQL + Alembic) |
| **FastAPI** cho leaderboard/backend, analytics | API xác thực, chấm điểm, xếp hạng, phân tích | Backend đã có phần lớn; analytics chưa |
| Dữ liệu sự kiện **có nguồn** | Mỗi dữ kiện gắn trích dẫn từ Danh mục nguồn | Nội dung đợt 1 gắn nguồn mức chương/kỷ |
| Bản đồ tương tác, điểm kiến thức, **ôn tập sau màn**, progression | | Game client đợt 1 |
| **Deployed online, có URL** | Không chấp nhận chỉ chạy localhost | Đợt 3 (cần tài khoản của nhóm) |
| **Đăng nhập & phân quyền cơ bản** | Người chơi / Biên tập / Thẩm định / Quản trị | Backend có; cần trang web đăng nhập |
| **Giao diện UI/UX hoàn chỉnh** | | Game + Web_Shell |
| **Quản lý user** | Trang quản trị danh sách, đổi vai trò, khoá tài khoản | API có `users/`; cần trang quản trị |
| Không chấp nhận: notebook, script CLI, prototype localhost | | Phải deploy thật trước buổi chấm |

## 2. Hiện trạng thư mục (đánh giá ngày 05/11/2026)

**Tốt, giữ nguyên**

- `backend/`: FastAPI có auth (argon2, JWT, refresh token thu hồi được, khoá sau 5 lần sai), phân quyền theo vai trò, danh mục nguồn + trích dẫn, quy trình thẩm định, phiên bản nội dung, xuất bản bundle, chấm điểm phía server, ôn tập, bảng xếp hạng, lớp học, báo lỗi, quyền riêng tư. 6 migration Alembic. Test chạy được (8/8).
- `shared/`: luật chơi thuần Python (quest_engine, unlock, grading, scoring, review_schedule, timeline_rules, histdate) — game dùng lại trực tiếp, không viết lại.
- `.venv`: đủ pygame-ce 2.5.8, pygbag 0.9.3 và thư viện backend.

**Thiếu (đây là phần sẽ bị chấm khi demo)**

- `game/`: chỉ có vòng lặp rỗng → **viết mới toàn bộ game client** (đợt 1).
- `web/`: mới có trang giới thiệu tạm → trang đăng nhập/đăng ký/chơi/quản trị (đợt 2).
- Chưa có nội dung lịch sử nào (Content_Store trống, Admin_Portal chưa làm) → nội dung đợt 1 soạn dạng JSON trong `game/content/`, sau đó nạp vào DB bằng script (đợt 2).
- Chưa có Dockerfile, cấu hình deploy, CI (đợt 3).

**Quyết định dọn dẹp / dời lại** (để kịp deadline, không ảnh hưởng yêu cầu bắt buộc)

| Hạng mục | Quyết định | Lý do |
|---|---|---|
| Admin_Portal Jinja2 + HTMX đầy đủ (task 10) | Thay bằng **trang quản trị gọn** (HTML + JS gọi API): quản lý user, duyệt nguồn, nhập nội dung JSON | Đề chỉ bắt buộc quản lý user; CRUD form cho 12 loại nội dung tốn nhiều công |
| Google OAuth (task 2.4) | Dời sau | Không bắt buộc, cần cấu hình Google Cloud |
| Lớp học, xuất CSV, analytics dashboard | Giữ API, giao diện làm sau cùng | Điểm cộng, không bắt buộc |
| Thư mục cache (`.ruff_cache`, `.pytest_cache`, `*.egg-info`) | Không commit (đã có trong `.gitignore`) | File sinh tự động |
| Thư mục chưa có Git | **Nên `git init` và đẩy lên GitHub sớm** | Cần cho CI/CD và deploy |

## 3. Kiến trúc chơi trên web

```
Trình duyệt ──► Web_Shell (HTML/JS: giới thiệu, đăng nhập, đăng ký, quản trị)
            └─► /play: Game_Client (pygame-ce → WebAssembly bằng pygbag)
                   ├─ nội dung: game/content/*.json  (đợt 2: tải bundle từ API)
                   ├─ tiến trình: localStorage (web) / file JSON (desktop)
                   └─ khi có token: đồng bộ tiến trình, gửi điểm → FastAPI ─► PostgreSQL
```

- Font **Be Vietnam Pro** và **Noto Serif** (SIL OFL) nhúng trong `game/assets/fonts/` —
  trình duyệt không có font Windows, nếu không nhúng sẽ lỗi chữ ô vuông.
- Mọi chuỗi đều chuẩn hoá NFC trước khi vẽ.
- Vòng lặp `async` + `await asyncio.sleep(0)` mỗi khung hình (bắt buộc với pygbag).

## 4. Thiết kế lối chơi (bổ sung ý tưởng)

### 4.1 Khung truyện

Người chơi là **sử quan tập sự** được **Cụ Đồ Sử** (nhân vật hư cấu, có nhãn "Lời dẫn hư cấu")
giao nhiệm vụ: cuốn *Sử ký* của làng bị thất lạc thành nhiều mảnh, rơi rớt ở các **di tích**.
Mỗi di tích có một **người giữ ký ức** (cụ từ giữ đền, bà cụ bán nước, người lái đò, cựu binh…)
kể lại câu chuyện. Nghe chuyện, thu **mảnh ghép tư liệu**, vượt các **cửa kiểm tra**, rồi
dựng lại **dòng thời gian** đúng thì chương sử được phục hồi.

### 4.2 Vòng lặp một màn

```
Bản đồ Việt Nam ─► chọn di tích (mở khoá dần) ─► đi tới (hoạt cảnh di chuyển)
   └─► Di tích: người giữ ký ức chào ─► Hồi ức (cảnh sepia, chữ chạy, có lựa chọn)
         ├─► xen giữa câu chuyện: cửa kiểm tra (câu hỏi nhiều dạng)
         ├─► trận đánh tương tác (mini-game) ở các di tích chiến trận
         ├─► nhận mảnh ghép tư liệu + con dấu "Hộ chiếu di sản"
   ─► đủ di tích bắt buộc ─► Dòng thời gian (kéo thả) ─► Tổng kết màn ─► Ôn tập
```

### 4.3 Các dạng thử thách (đa dạng câu hỏi)

| Dạng | Ví dụ |
|---|---|
| Chọn 1 đáp án | Ai giết Dương Đình Nghệ năm 937? |
| Đúng / Sai | "Trận Bạch Đằng 938 chấm dứt hơn một nghìn năm Bắc thuộc." |
| Chọn nhiều | Những yếu tố làm nên chiến thắng Bạch Đằng (có đáp án gây nhiễu sai niên đại như "súng thần công") |
| Sắp xếp thứ tự | Xếp các sự kiện 931 → 937 → 938 → 939 |
| Nối cặp | Câu nói nổi tiếng ↔ nhân vật ("Ta thà làm ma nước Nam…" ↔ Trần Bình Trọng) |
| Chỉ trên bản đồ | Bấm vào nơi Ngô Quyền đóng đô năm 939 (sai số cho phép tính bằng Haversine) |
| Phân biệt sử – truyền thuyết | "Chuyện trả gươm cho Rùa Vàng" là sự kiện có ghi chép hay truyền thuyết? |
| Đối chiếu nguồn (Ghi chú sử học) | Các nguồn ghi năm Lê Lai cứu chúa khác nhau — chọn cách hiểu đúng |

### 4.4 Trận đánh tương tác (hiệu ứng chiến trận)

- **Kiểu "thuỷ triều"** (Bạch Đằng 938, 1288): người chơi cắm cọc, nhử địch khi triều lên, chọn
  đúng lúc triều rút để phản công; thuyền địch va cọc vỡ tung.
- **Kiểu "phục kích"** (Chi Lăng 1427): chờ đạo quân địch lọt hẳn vào ải rồi phát lệnh phục binh.
- **Kiểu "vây lấn"** (Điện Biên Phủ 1954): chọn phương châm "đánh chắc, tiến chắc", lần lượt
  đánh các cứ điểm theo đúng thứ tự.
- Hiệu ứng: tên bay, khói lửa, nước bắn, mảnh vỡ, rung màn hình, vệt đỏ khi trúng đòn.
  **Cài đặt "Hiệu ứng chiến trận: Đầy đủ / Giảm nhẹ"** — người chơi dưới 16 tuổi mặc định Giảm nhẹ
  (không có vệt máu), phù hợp nền tảng giáo dục.

### 4.5 Phần thưởng và giữ chân người chơi

- **Điểm kiến thức** theo độ khó (10/20/30), lần 2 được 50%, từ lần 3 không cộng (đã có trong `shared/scoring.py`).
- **Hộ chiếu di sản**: mỗi di tích đã đến được đóng một con dấu.
- **Bảo vật sưu tầm**: thẻ hiện vật/tư liệu (cọc gỗ Bạch Đằng, Hịch tướng sĩ, Bình Ngô đại cáo…).
- **Danh hiệu**: "Người giữ lửa Bạch Đằng", "Hào khí Đông A", "Nghĩa sĩ Lam Sơn"…
- **Sổ tay sử quan**: nhân vật, sự kiện, địa danh, tư liệu, nguồn; tìm kiếm không dấu.
- **Ôn tập sau màn**: câu sai/đúng muộn quay lại theo chu kỳ 1-3-7-14-30 ngày.
- Bảng xếp hạng tuần/tháng/toàn bộ/lớp (đã có API).

### 4.6 Tôn trọng sự thật lịch sử

- Nội dung hư cấu (người kể chuyện, lời thoại dựng lại) **luôn có nhãn**; câu hỏi chấm điểm chỉ dựa trên dữ kiện có nguồn.
- Chi tiết mang tính truyền tụng ghi rõ "truyền tụng/huyền thoại" (ví dụ trả gươm hồ Tả Vọng).
- Các điểm các nguồn ghi khác nhau (†) có **Ghi chú sử học**.
- Trích dẫn đợt 1 ghi ở mức tác phẩm + kỷ/chương (ví dụ *Đại Việt sử ký toàn thư*, Bản kỷ, Kỷ nhà Trần).
  **Số trang để trống có chủ đích** — Biên tập viên điền theo đúng bản sách nhóm sử dụng, không bịa số trang.

## 5. Nội dung đợt 1

| Màn | Di tích | Trận đánh tương tác |
|---|---|---|
| 1. Bạch Đằng & Hào khí Đông A (938–1288) | Đường Lâm, Cổ Loa, Bạch Đằng Giang, Sông Như Nguyệt, Đền Trần, Kiếp Bạc, Vân Đồn | Bạch Đằng 938, Bạch Đằng 1288 |
| 2. Khởi nghĩa Lam Sơn (1418–1428) | Lam Kinh, Đền thờ Lê Lai, Ải Chi Lăng, Hồ Gươm – Đông Quan | Chi Lăng 1427 |
| 3. Cách mạng tháng Tám & kháng chiến chống Pháp (1945–1954) | Quảng trường Ba Đình, Việt Bắc – Tân Trào, Điện Biên Phủ, Genève | Điện Biên Phủ 1954 |

## 6. Lộ trình

| Đợt | Nội dung | Kết quả |
|---|---|---|
| **1 (đang làm)** | Game client chơi được trên desktop và build web bằng pygbag: bản đồ, di tích, hồi ức, trận đánh, câu hỏi 8 dạng, dòng thời gian, sổ tay, ôn tập, phần thưởng, lưu tiến trình | `game/` |
| 2 | Web_Shell (đăng nhập, đăng ký, chơi, quản trị user); nối game với API (token, đồng bộ tiến trình, gửi điểm); script nạp `game/content/*.json` vào DB; analytics tối thiểu | `web/`, `backend/seed/` |
| 3 | Dockerfile backend, Render/Fly.io + Supabase Postgres, GitHub Pages/Cloudflare Pages cho web, GitHub Actions; tài khoản demo cho từng vai trò | URL online |
| 4 | Kiểm thử với bạn bè, sửa lỗi, quay video demo, viết báo cáo | Nộp bài |

## 7. Việc nhóm cần tự làm (không làm thay được)

- Tạo tài khoản **GitHub**, **Supabase** (hoặc Render Postgres), **Render/Fly.io**, và trang static (**GitHub Pages / Cloudflare Pages**); điền biến môi trường vào dịch vụ.
- Biên tập viên điền **số trang** cho trích dẫn theo bản sách nhóm sử dụng; người thẩm định duyệt nguồn.
- Kiểm tra lại nội dung với giáo viên hướng dẫn.

## 8. Cách chạy (đợt 1)

```bash
# chơi trên máy (desktop)
.venv/Scripts/python game/main.py

# build bản web (WebAssembly) và chạy thử ở http://localhost:8000
.venv/Scripts/python tools/build_web.py --serve
```

## Cập nhật: chuyển sang game nhập vai pixel art

Theo góp ý khi chơi thử, game được làm lại từ "màn hình hỏi đáp" thành game nhập vai góc nhìn từ trên xuống:

- **Lối chơi:** điều khiển nhân vật đi trong map (WASD, phím mũi tên, bấm chuột hoặc chạm). Mỗi di tích là một khu vực trên map: nghe chuyện ở người giữ ký ức, trả lời ở bia đá hoặc dân làng, nhặt mảnh ghép phát sáng, vào trận ở cờ trận.
- **Chuyển màn:** gặp Cụ Đồ Sử để dựng dòng thời gian, xong thì cổng dịch chuyển mở và đưa sang map mới. Có cổng quay về màn trước.
- **Bản đồ Việt Nam (phím M):** xem vị trí thật của di tích, đi nhanh tới nơi đã mở; vẫn hiển thị Hoàng Sa, Trường Sa.
- **Đồ hoạ, nhạc:** Ninja Adventure Asset Pack của Pixel-Boy và AAA, giấy phép CC0 (https://pixel-boy.itch.io/ninja-adventure-asset-pack). Bản rút gọn nằm ở `game/assets/pixel/`, do `tools/pack_assets.py` lọc ra.
- **Mã nguồn mới:** `core/sprites.py`, `core/tilemap.py`, `core/worldgen.py`, `core/diorama.py`, `scenes/world.py`, `scenes/atlas.py`, dữ liệu map ở `content/worlds.json`. Đã bỏ `scenes/relic.py`, `scenes/map_scene.py` và tranh vẽ bằng code trong `core/art.py`.
- **Chạy thử web:** `.venv/Scripts/python tools/build_web.py --serve`, mở đúng địa chỉ `http://127.0.0.1:8000` (dùng `localhost` sẽ kẹt ở màn tải).
- **Kiểm thử:** `.venv/Scripts/python -m pytest game/tests -q` cho bot chơi hết game, `.venv/Scripts/python tools/check_content.py` kiểm tra nội dung.
- **Âm thanh:** chỉ dùng OGG, pygbag từ chối đóng gói WAV khi build web. `tools/pack_assets.py` tự đổi WAV sang OGG (cần `pip install soundfile`).
- **Trận Bạch Đằng:** lính đứng trên thuyền, 3 kỹ năng có hồi chiêu (tên lửa, phóng lao, xung phong), triều rút làm lộ cọc rồi thuyền đâm cọc. Kỹ năng là phần cách điệu, có ghi rõ trên màn hình.
