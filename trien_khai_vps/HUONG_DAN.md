# Game trên VPS — ghi chép triển khai

Triển khai ngày 14/11/2026, lúc 21:44–21:54. Đọc tệp này trước khi sửa, cập nhật hay gỡ game trên VPS.

## Địa chỉ

| | Địa chỉ |
|---|---|
| Trang người chơi | https://game.vtkt.online |
| Cổng quản trị | https://admin.vtkt.online (tự chuyển sang `/admin/`) |
| Kiểm tra máy chủ | https://game.vtkt.online/health |

- Tài khoản quản trị: `ADMIN_EMAIL` và `ADMIN_PASSWORD` trong tệp `trien_khai_vps/app.env` trên máy này.
- Mật khẩu do script sinh ngẫu nhiên, không ghi ở đâu khác.
- Vào `game.vtkt.online/admin/` thì tự chuyển sang `admin.vtkt.online/admin/`.

## Cách dựng (vì sao không đụng đồ án)

VPS này cũng đang chạy đồ án chuyên ngành (`/opt/royal`, Caddy giữ cổng 80/443, tường lửa chỉ nhận Cloudflare). Game được tách hẳn ra:

- **Thư mục riêng `/opt/sukydieutra`** trên VPS:
  - `src/` mã nguồn;
  - `docker-compose.yml`;
  - `.env`, `app.env` (quyền 600).
- **3 container riêng**, Docker project tên `sukydieutra`, mạng riêng `sukydieutra_noi_bo`:
  - `sukydieutra_db`: PostgreSQL 16, volume `sukydieutra_pgdata`, giới hạn 512 MB. **Không mở cổng.**
  - `sukydieutra_app`: FastAPI + game WebAssembly + trang quản trị. Volume `sukydieutra_media` cho ảnh tải lên, giới hạn 1 GB.
  - `sukydieutra_tunnel`: cloudflared, giới hạn 256 MB. Nó kết nối **ra** Cloudflare, nên VPS không mở thêm cổng nào.
- **Ra Internet bằng Cloudflare Tunnel** tên `sukydieutra`:
  - Xem ở dash.cloudflare.com → Networking → Tunnels → sukydieutra.
  - Có 2 route "Published application": `game.vtkt.online` và `admin.vtkt.online`, cùng trỏ vào `http://sukydieutra_app:8000`.
  - Cloudflare tự tạo 2 bản ghi DNS CNAME `game` và `admin` (Proxied).
- **Không sửa gì** ở Caddyfile, docker-compose, tường lửa hay CSDL của đồ án.
- Tunnel chạy giao thức **http2** (TCP 443). VPS này không ra được QUIC/UDP: chạy mặc định thì báo `failed to dial to edge with quic: timeout`.
- Lúc triển khai, 3 container dùng khoảng 175 MB RAM; VPS còn trống khoảng 4,4 GB.

## Các tệp trong thư mục này

| Tệp | Là gì | Lên git? |
|---|---|---|
| `HUONG_DAN.md` | tệp này | được |
| `docker-compose.yml` | 3 container trên VPS | được |
| `day_len_vps.py` | script đóng gói, gửi lên, build, chạy, xem trạng thái, gỡ | được |
| `vps.json` | địa chỉ VPS, người dùng SSH, đường dẫn khóa SSH, tên miền | **KHÔNG** |
| `.env` | mật khẩu PostgreSQL, token tunnel | **KHÔNG** |
| `app.env` | khóa JWT, tài khoản quản trị, tên miền | **KHÔNG** |
| `dan_token_vao_day.txt` | lệnh Cloudflare có token tunnel | **KHÔNG** |
| `_ban_goc_truoc_khi_sua/` | bản gốc các tệp code trước khi sửa cho VPS | không cần |

`.gitignore` ở gốc dự án đã loại các tệp "KHÔNG". Token tunnel cho phép chạy tunnel dưới tài khoản Cloudflare, đừng gửi cho ai.

## Những chỗ đã sửa trong code game (14/11)

Bản gốc nằm trong `_ban_goc_truoc_khi_sua/`.

1. **`backend/app/storage.py`**:
   - Trước đây môi trường production bắt buộc có Supabase, không có thì `get_storage()` báo lỗi.
   - Bảng xếp hạng gọi hàm này, nên trên VPS (và cả Render) sẽ **lỗi 500**.
   - Giờ không có Supabase thì lưu ảnh vào thư mục local (`MEDIA_LOCAL_DIR=/srv/media`, có volume).
2. **`backend/app/main.py`**:
   - Phục vụ `/media-files` từ thư mục local mỗi khi không có Supabase (trước chỉ khi dev).
   - Gắn `AdminHostMiddleware` khi có `ADMIN_HOST`.
3. **`backend/app/config.py`**: thêm biến `admin_host` (`ADMIN_HOST`).
4. **`backend/app/middleware.py`**: thêm `AdminHostMiddleware`.
   - `admin.<tên miền>/` → `/admin/`.
   - `/admin/...` trên tên miền khác → chuyển sang tên miền quản trị.
   - Chỉ đổi hướng; quyền quản trị vẫn do API kiểm tra.
5. **`backend/tests/test_admin_host.py`**: 3 bài kiểm cho middleware trên. Cả bộ kiểm thử: 49/49 đạt.
6. **`.gitignore`**: thêm các tệp bí mật của thư mục này.

## Việc thường làm

Chạy ở thư mục gốc dự án, cần mạng và khóa SSH ghi trong `vps.json`.

Cập nhật game sau khi sửa code (đóng gói lại, build lại; dữ liệu người chơi giữ nguyên):

```bash
python trien_khai_vps/day_len_vps.py
```

Xem container có chạy không, tunnel có nối không:

```bash
python trien_khai_vps/day_len_vps.py --trang-thai
```

Xem nhật ký (`app`, `tunnel` hoặc `db`):

```bash
python trien_khai_vps/day_len_vps.py --nhat-ky app
```

Tắt game, giữ dữ liệu (chạy lại thì dùng lệnh cập nhật ở trên):

```bash
python trien_khai_vps/day_len_vps.py --dung
```

Sao lưu CSDL người chơi về máy (chạy trong Git Bash, tệp ra ở thư mục hiện tại):

```bash
ssh -i ~/.ssh/royal_vps root@<ip VPS> "docker exec sukydieutra_db pg_dump -U sukydieutra sukydieutra" > sao_luu_game.sql
```

## Gỡ hẳn khi không cần nữa

1. Xóa toàn bộ game trên VPS: container, CSDL người chơi, ảnh và thư mục `/opt/sukydieutra`. Đồ án không bị ảnh hưởng.

   ```bash
   python trien_khai_vps/day_len_vps.py --go-sach --that
   ```

2. Trên Cloudflare: Networking → Tunnels → sukydieutra → **Delete**.
3. Trên Cloudflare: Domains → vtkt.online → DNS → xóa 2 bản ghi CNAME `game` và `admin`, nếu xóa tunnel mà chúng vẫn còn.

## Nhật ký cập nhật

- **15/11/2026 04:0x, cập nhật thách đấu PvP thật** (người dùng sửa từ khoảng 22:09 ngày 14/11 tới 03:xx ngày 15/11).
  - Các tệp đổi:
    - phía máy chủ: `backend/app/world/hub.py` (trận `Duel`, tin `pvp`, `pvp_hit`, `pvp_dead`, `pvp_quit`, phân xử hết giờ theo máu);
    - phía game: `game/core/net.py`, `scene.py`, `scenes/fight.py`, `multiplayer.py`, `social.py`, `trailer.py`, `world.py`, cùng 2 tệp mới `scenes/pvp.py`, `scenes/playercard.py`;
    - khác: `tools/make_spec.py`, `web/index.html`, cùng kiểm thử `backend/tests/test_world.py`, `game/tests/test_multiplayer.py`.
  - Kiểm trước khi đưa lên:
    - kiểm thử máy chủ 52/52, kiểm thử game 334/334;
    - ruff sạch (thêm `"trien_khai_vps/**" = ["E501"]` vào `ruff.toml` cho script triển khai);
    - biên dịch thử toàn bộ mã: OK.
    - Không có migration CSDL mới, dữ liệu người chơi giữ nguyên.
  - Sau khi đưa lên:
    - `/health` OK, 4 địa chỉ trả 200;
    - container có mã PvP mới, gói game có `scenes/pvp.py`;
    - Cloudflare phát đúng gói mới (md5 khớp với VPS).
  - Điểm còn để ngỏ (CHƯA sửa, để người dùng quyết):
    - trận **hòa** bị ghi `win=False` cho cả hai người (bảng `duel_record` không có cột hòa), nên lịch sử thách đấu hiện thành "thua";
    - `pvp_hit` không giới hạn tần suất. Máy bị sửa có thể gửi dồn dập đòn 400 sát thương. Máu vốn do máy người chơi tự báo, nên với bản demo chấp nhận được.
- **15/11/2026, sửa hai điểm để ngỏ ở trên** (CHƯA đưa lên VPS; chạy lệnh cập nhật để đưa lên).
  - Trận hòa: migration mới `0011_duel_draw` thêm cột `draw` vào `duel_records`; hòa thì ghi `draw=True`, `win=False` cho cả hai; API `/world/duels` trả thêm `draw`. `start.sh` tự chạy `alembic upgrade head` khi container khởi động, dữ liệu cũ giữ nguyên (cột mới mặc định `false`).
  - `pvp_hit`: máy chủ giới hạn sát thương theo ngân sách của người ra đòn, tính theo hệ số sức đánh lúc vào trận: mỗi đòn tối đa 50 × hệ số, hồi 60 × hệ số mỗi giây, dồn tối đa 150 × hệ số; mỗi tin tốn ít nhất 5 nên gửi dồn tin không sát thương cũng bị chặn. Máu vẫn do máy người chơi tự báo (chấp nhận cho bản demo).
  - Trailer `web/video/trailer.mp4` xuất lại theo phím mới (chuột trái chém, Shift né, bấm vào người chơi để mời).
  - Kiểm: kiểm thử máy chủ 52/52 (có thử ghi hòa vào PostgreSQL thật), kiểm thử game 334/334, ruff sạch.

## Lưu ý

- **Sau mỗi lần cập nhật, trình duyệt có thể giữ gói game cũ tới 4 giờ.** Cloudflare gắn `Cache-Control: max-age=14400` cho tệp tĩnh; cài đặt này chung cho cả tên miền, nên KHÔNG sửa (đồ án dùng chung).
  - Ai thấy game cũ thì bấm Ctrl+F5, hoặc mở bằng cửa sổ ẩn danh.
  - Phía Cloudflare tự lấy bản mới (đã kiểm: md5 khớp).

- **Email không gửi thật** (`EMAIL_BACKEND=console`, `SKIP_EMAIL_VERIFICATION=true`):
  - đăng ký xong dùng được ngay;
  - "quên mật khẩu" không gửi được thư;
  - người từ 16 tuổi trở xuống phải nhờ quản trị viên bấm Kích hoạt.
  - Muốn gửi thật thì xem phần email trong `DEPLOY.md`, sửa `app.env` rồi chạy lại lệnh cập nhật.
- **Đổi `ADMIN_PASSWORD` trong `app.env` KHÔNG đổi mật khẩu** của tài khoản đã tạo (`seed/create_admin.py` chỉ tạo hoặc nâng quyền). Muốn đổi thì đổi trong ứng dụng.
- **Token tunnel lộ:** vào Cloudflare → tunnel sukydieutra → Rotate token. Dán lệnh mới vào `dan_token_vao_day.txt` rồi chạy lại lệnh cập nhật.
- **Tunnel mất kết nối** (`--trang-thai` không thấy "Registered tunnel connection"): xem `--nhat-ky tunnel`. Nếu lại là lỗi QUIC thì kiểm tra lệnh trong `docker-compose.yml` vẫn có `--protocol http2`.
- **Phần chấm câu hỏi chạy ở trình duyệt,** người biết kỹ thuật có thể sửa bản lưu để lấy điểm (đã ghi trong `DEPLOY.md`).
- **Game tải bộ chạy Python cho trình duyệt (pygbag) từ CDN `pygame-web.github.io`,** nên máy người chơi cần Internet. Lần đầu tải khoảng 6 MB.
