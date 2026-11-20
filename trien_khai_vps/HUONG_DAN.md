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
    - Cloudflare phát đúng gói mới (md5 khớp với VPS) — kiểm trên tệp `.apk`, không phải tệp `.tar.gz` game thật sự tải; xem mục 12:4x.
  - Điểm còn để ngỏ (CHƯA sửa, để người dùng quyết):
    - trận **hòa** bị ghi `win=False` cho cả hai người (bảng `duel_record` không có cột hòa), nên lịch sử thách đấu hiện thành "thua";
    - `pvp_hit` không giới hạn tần suất. Máy bị sửa có thể gửi dồn dập đòn 400 sát thương. Máu vốn do máy người chơi tự báo, nên với bản demo chấp nhận được.
- **15/11/2026, sửa hai điểm để ngỏ ở trên.** Đã đưa lên VPS lúc 07:31–07:33 (giờ VN; trước đây ghi nhầm 14:31), xem kết quả ở cuối mục này.
  - Trận hòa: migration mới `0011_duel_draw` thêm cột `draw` vào `duel_records`; hòa thì ghi `draw=True`, `win=False` cho cả hai; API `/world/duels` trả thêm `draw`. `start.sh` tự chạy `alembic upgrade head` khi container khởi động, dữ liệu cũ giữ nguyên (cột mới mặc định `false`).
  - `pvp_hit`: máy chủ giới hạn sát thương theo ngân sách của người ra đòn, tính theo hệ số sức đánh lúc vào trận: mỗi đòn tối đa 50 × hệ số, hồi 60 × hệ số mỗi giây, dồn tối đa 150 × hệ số; mỗi tin tốn ít nhất 5 nên gửi dồn tin không sát thương cũng bị chặn. Máu vẫn do máy người chơi tự báo (chấp nhận cho bản demo).
  - Trailer `web/video/trailer.mp4` xuất lại theo phím mới (chuột trái chém, Shift né, bấm vào người chơi để mời).
  - Kiểm: kiểm thử máy chủ 52/52 (có thử ghi hòa vào PostgreSQL thật), kiểm thử game 334/334, ruff sạch.
  - Claude kiểm lại trước khi đưa lên:
    - lịch sử git (5 commit, repo `thanhvuaws-jpg/pythongamelichjsu`) không chứa token tunnel, mật khẩu CSDL, khóa JWT, mật khẩu quản trị hay IP VPS;
    - chỉ 3 tệp công khai của `trien_khai_vps/` được git theo dõi;
    - `start.sh` vẫn xuống dòng kiểu Linux;
    - alembic chỉ có một head (`0011_duel_draw`);
    - trần mỗi đòn hợp lệ: đòn mạnh nhất (Phi mã cấp 3 + Hào khí) khoảng 42 × hệ số, dưới trần 50.
  - **Sao lưu CSDL trước migration:** `/opt/sukydieutra/sao_luu/truoc_0011_20261115_0731.sql.gz` trên VPS (giờ trong tên tệp là giờ VN, VPS đặt múi +07; lúc đó có 3 tài khoản, 7 bản ghi thách đấu).
    - Lệnh `--go-sach` xóa cả thư mục này, nên muốn giữ thì tải về máy trước.
  - Sau khi đưa lên:
    - log có `Running upgrade 0010_bot_players -> 0011_duel_draw`;
    - `alembic_version = 0011_duel_draw`, cột `draw boolean default false`;
    - dữ liệu cũ còn đủ: 3 tài khoản, 7 bản ghi thách đấu, 0 trận hòa;
    - container có mã ngân sách đòn mới (`PVP_BURST`);
    - `/health`, trang game, cổng quản trị, `/game/` trả 200; trailer mới (11.231.081 byte) khớp kích thước bản trên máy.
- **15/11/2026, chơi trên điện thoại.** Đã đưa lên VPS lúc 12:1x (giờ VN), xem kết quả ở cuối mục này. Không có migration mới.
  - Game: nút chạm ở góc dưới phải thay cho phím (nói chuyện / đánh với ai đứng cạnh, thả câu, kéo cần, gọi và xuống ngựa, lên bờ khi đang chèo thuyền, nhận lời / từ chối võ sinh thách đấu); trong trận chạm sân là đi, đánh bằng nút. Nhận biết điện thoại bằng `(pointer: coarse)` hoặc cú chạm đầu tiên (`SceneManager.touch`).
  - Trang web: `web/js/mobile.js` (dùng cho `play.html` và trang Chơi thử `/game/` qua `tools/build_web.py`): cầm dọc thì nhắc xoay ngang, cầm ngang thì ẩn thanh trên, nút Toàn màn hình (Android), khung game dùng `100dvh` nên không bị thanh địa chỉ cắt.
  - Kiểm: kiểm thử game 341/341 (thêm `game/tests/test_touch.py`), thử trên trình duyệt giả lập điện thoại có cảm ứng ở máy (127.0.0.1:8203): Chơi thử và trang chơi khi đăng nhập.
  - Claude kiểm lại trước khi đưa lên:
    - so với bản trên VPS: 8 tệp đổi (`platform_io.py`, `scene.py`, `fight.py`, `fishing.py`, `mobs.py`, `world.py`, `tools/build_web.py`, `web/play.html`) và 1 tệp mới (`web/js/mobile.js`); phía máy chủ không đổi;
    - git 7 commit, không chứa bí mật nào;
    - `mobile.js` chỉ gán chữ cố định vào `innerHTML`, không có dữ liệu người dùng;
    - kiểm thử máy chủ 52/52, game 341/341, ruff sạch.
    - Không có migration nên không sao lưu lại; bản sao lưu 07:31 vẫn còn.
  - Sau khi đưa lên:
    - `/health` OK;
    - `play.html` và `/game/` đều đã gắn `mobile.js`, `/js/mobile.js` trả 200;
    - gói game Cloudflare phát ra khớp md5 với bản trên VPS — **KIỂM SAI TỆP**: đó là `.apk`, mà game (ngoài itch.io) tải `sukydieutra.tar.gz`. Lần sau mới phát hiện tệp `.tar.gz` bị Cloudflare giữ đệm, xem mục kế tiếp;
    - dữ liệu còn đủ: 3 tài khoản, 7 bản ghi thách đấu;
    - không có lỗi trong log 3 phút đầu.

- **15/11/2026, cần điều khiển trên điện thoại và đi không còn giật.** Đã đưa lên VPS lúc 12:4x (giờ VN), xem kết quả ở cuối mục này. Không có migration mới, phía máy chủ không đổi.
  - Cần điều khiển ảo ở góc dưới trái (`game/core/touch.py`) trên map, trong trận và trong nhà tư liệu; nghe sự kiện ngón nên giữ cần bằng ngón này vẫn bấm CHÉM, nút chạm bằng ngón kia. Chuột giả của cú chạm trên cần bị nuốt nên nhấc tay không bị hiểu thành chạm để đi.
  - Đi giật: khi chạm lên bản đồ để đi, nhân vật đứng khựng một khung hình mỗi khi tới giữa một ô (`_follow_path`) và đi gấp khúc theo lưới. Nay đi tiếp ô sau bằng quãng còn lại trong cùng khung hình, đoạn thẳng không vướng thì cắt chéo.
  - Trang báo `data-sk-input="fingers"` trên thẻ `<html>` của khung game khi máy gửi sự kiện ngón (để soát trên máy thật).
  - Kiểm: kiểm thử game 347/347, thử chạm thật (CDP) trên trình duyệt giả lập điện thoại ở máy (127.0.0.1:8203).
  - Claude kiểm lại trước khi đưa lên:
    - 6 tệp đổi (`platform_io.py`, `scene.py`, `case.py`, `fight.py`, `multiplayer.py`, `world.py`) và 1 tệp mới (`game/core/touch.py`);
    - git 8 commit, không chứa bí mật nào;
    - kiểm thử máy chủ 52/52, game 347/347, ruff sạch.
  - **Phát hiện khi đưa lên: người chơi vẫn nhận gói game CŨ.**
    - Ngoài itch.io, trang `/game/` tải `sukydieutra.tar.gz` (không phải `.apk`).
    - Tệp này lần nào cũng cùng tên, nên Cloudflare giữ đệm (HIT, tồn 25 phút): VPS có gói mới, Cloudflare vẫn phát gói của lần trước. Trình duyệt còn giữ thêm tới 4 giờ (`max-age=14400`).
  - **Sửa tận gốc** trong `tools/build_web.py`, hàm `version_bundle`:
    - mỗi lần build, chép gói thành `sukydieutra-<12 ký tự băm sha256>.tar.gz` và sửa `index.html` trỏ vào tên đó;
    - xóa bản băm cũ; tệp `sukydieutra.tar.gz` và `.apk` vẫn để lại cho `--serve` và itch.io;
    - `index.html` (và `/game/` mà `play.html` nhúng qua iframe) không bị Cloudflare giữ đệm (DYNAMIC), nên lần nào người chơi cũng nhận gói mới, khỏi phải xóa đệm bằng tay.
    - Mỗi lần build, tar mới có thời điểm khác nên băm luôn đổi kể cả khi code giữ nguyên. Không sao, chỉ là tải lại 6 MB.
  - Sau khi đưa lên (12:4x):
    - `/game/` trỏ tới `sukydieutra-05a59bd107d0.tar.gz`; Cloudflare phát tệp này với MISS lần đầu, md5 khớp bản trên VPS;
    - mở thật trên Chrome: game vào màn hình chính, console ghi `cross_file.fetch sukydieutra-05a59bd107d0.tar.gz`, không lỗi;
    - dữ liệu còn đủ: 3 tài khoản, 11 bản ghi thách đấu.
- **20/11/2026, video trang chủ thêm trận cuối và đoạn kết.** Đã đưa lên VPS lúc 19:41 (giờ VN), cùng lần với mục kế tiếp. Không đổi code máy chủ, chỉ đổi tệp tĩnh.
  - `tools/make_trailer_video.py` quay ba đoạn rồi nối: phần hướng dẫn (2 phút 46), người chơi máy chơi hết ba màn (không quay) rồi đánh Chiến dịch Điện Biên Phủ (61 giây), đi qua cổng cuối vào đoạn kết (67 giây). Tổng 4 phút 53, 20,7 MB, 2560×1440.
  - `--doan-ket <tệp>` xuất riêng đoạn kết 58 giây (1280×720, 3 MB) kèm ảnh bìa, dùng cho slide 4 của bài thuyết trình.
  - `web/index.html` gọi `video/trailer.mp4?v=2` và `img/trailer.png?v=2` để Cloudflare không phát bản cũ (xem mục Lưu ý).
  - Video trong game (TrailerScene) giữ nguyên, vẫn gần ba phút.

- **20/11/2026, vào game lần đầu nhanh hơn, màn tải mới.** Đã đưa lên VPS lúc 19:41 (giờ VN). Không có migration, phía máy chủ không đổi.
  - Lý do: bạn bè người dùng báo lần đầu vào game tải lâu, trang tải xấu (chữ "Downloading..." / "Loading, please wait" mặc định của pygbag).
  - Đo trước khi sửa (bộ đệm trống): phải tải 16,5 MB, nối đuôi nhau: bộ chạy Python ~9 MB → gói game 6,1 MB (chỉ bắt đầu sau khi Python khởi động) → pygame 1,5 MB. Ở mạng 10 Mbps mất khoảng 19–20 giây.
  - Sửa (`tools/web_extras.py`, `tools/loader/`, `game/core/audio.py`, `game/main.py`):
    - phông cắt còn chữ Việt; NotoSerif 1,8 MB còn 155 KB (chốt kiểu mặc định của phông biến thiên). Gói game 6,1 MB còn 1,8 MB;
    - nhạc nền ngoài màn tựa đề (road, temple, fight, sad: 3,4 MB) nằm ở `/game/music/`, game tải ngầm sau khi đã vào;
    - gói game và pygame tải ngay khi bộ chạy Python tải xong, trong lúc Python khởi động, cùng cờ fetch với pygbag nên pygbag lấy lại từ bộ đệm (đã kiểm: không tải hai lần);
    - màn tải mới: mặt trống đồng, thanh tiến trình đếm byte thật, nhân vật đi theo thanh, mẩu "Biết không?" lấy từ các mốc sử có nguồn của game, nút "Bấm/Chạm để vào game" khi trình duyệt chặn tự phát tiếng. Game đánh dấu `data-sk-ready` ở khung hình đầu thì màn tải mờ đi.
  - Đo sau khi đưa lên (trang thật, Edge không giao diện, bộ đệm trống, giả lập 10 Mbps trễ 60 ms): game vẽ khung hình đầu sau 13,0–13,8 giây; lần vào thứ hai 3,6 giây. Thử thêm trên máy: điện thoại xoay ngang 780×360, trường hợp chặn tự phát tiếng (bấm nút là vào ngay).
  - Kiểm: ruff sạch, kiểm thử game 352/352 (thêm `test_web_loading.py`), máy chủ 47 đạt + 5 bỏ qua vì máy chưa bật PostgreSQL (phần máy chủ không đổi).
  - Sau khi đưa lên: `/health` OK; `/game/` có màn tải mới và trỏ `sukydieutra-bb1a8fc96fc6.tar.gz` (1,8 MB); 4 tệp `/game/music/*.ogg` trả 200; `/video/trailer.mp4?v=2` đủ 21,7 MB; trang chủ gọi video `?v=2`.
  - **Lỗi sau khi đưa lên (người dùng báo, chế độ khách):** hộp thoại "Error occurred: Cannot set properties of null (setting 'textContent')" hiện lại mỗi 8 giây. Hẹn giờ đổi mẩu "Biết không?" vẫn chạy sau khi màn tải đã gỡ, ghi vào phần tử không còn; pygbag bật `alert` cho mọi lỗi JS trên trang. Lúc thử không thấy vì Playwright tự đóng hộp thoại. Sửa trong `tools/loader/loader.js`: dừng hẹn giờ khi gỡ màn tải, mọi việc theo hẹn giờ bọc `safe()`, màn tải lỗi thì tự gỡ. Đã kiểm bằng script bắt hộp thoại và lỗi JS (30 giây sau khi vào game: không có). Người dùng tự đưa bản sửa lên VPS; kiểm lại trên trang thật: 25 giây sau khi vào game không có hộp thoại, không có lỗi JS.
  - Đổi pygbag thì phải đo lại `WHEEL_URL`, `WHEEL_BYTES`, `RUNTIME_BYTES` trong `tools/web_extras.py` (sai thì chỉ mất phần tải sớm và số MB hiện trên màn tải lệch, game vẫn chạy).
- **20/11/2026 tối, bạn người dùng vào trang chơi (đăng nhập) kẹt ở "Loading, please wait".** Đã đưa lên VPS lúc 23:43 (giờ VN).
  - Nguyên nhân: máy chủ gửi trang HTML chỉ kèm ETag/Last-Modified, không có Cache-Control, nên trình duyệt tự đoán `/game/index.html` còn mới và giữ bản trước 19:41 hàng giờ; F5 ở `play.html` không tải lại khung game. Bản cũ gọi gói `sukydieutra-05a59bd107d0.tar.gz` đã bị thay (404) nên kẹt. Chế độ khách mở `/game/` (địa chỉ khác) nên không gặp.
  - Sửa: `FreshPagesMiddleware` gắn `Cache-Control: no-cache` cho mọi trang HTML (không đổi thì 304); `GameBundleFallbackMiddleware` chuyển yêu cầu gói cũ sang gói hiện tại (307); `play.js` gọi khung game `/game/index.html?v=2` và `play.html` gọi `play.js?v=10` để thoát bản đang bị giữ. Kiểm thử `backend/tests/test_fresh_pages.py`, và thử trên `app.main` với bản đóng gói thật.
  - Ai đang kẹt: sau khi đưa lên, chỉ cần bấm F5 ở trang chơi một lần.
  - Sau khi đưa lên: `/health` OK; `play.html`, `/game/index.html` có `Cache-Control: no-cache`; xin `sukydieutra-05a59bd107d0.tar.gz` thì 307 sang gói hiện tại; trang chơi gọi `play.js?v=10`, khung game `index.html?v=2`; mở game 15 giây không có hộp thoại hay lỗi JS.

## Lưu ý

- **Bộ nhớ đệm Cloudflare:** Cloudflare giữ đệm tệp tĩnh và gắn `Cache-Control: max-age=14400` (4 giờ). Cài đặt này chung cho cả tên miền nên KHÔNG sửa (đồ án dùng chung).
  - Gói game: từ 15/11 12:4x mang tên theo nội dung (`tools/build_web.py`, `version_bundle`), nên luôn mới sau mỗi lần cập nhật.
  - JS / CSS / ảnh của trang web cùng tên thì vẫn có thể cũ tới vài giờ: sửa tệp nào thì tăng `?v=` ở chỗ gọi tệp đó (như `js/play.js?v=9`).
  - Kiểm sau khi cập nhật: so md5 tệp `sukydieutra-*.tar.gz` mà `/game/` trỏ tới với bản trong container (không phải tệp `.apk`).

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
