<div align="center">

<img src="web/img/icon.png" alt="Biểu tượng Sử Ký Điều Tra" width="96">

# Sử Ký Điều Tra

**Game web nhập vai pixel học lịch sử Việt Nam: đi qua các di tích, nghe hồi ức, trả lời câu hỏi có nguồn,<br>
đánh trận theo đúng cách đánh của trận thật, chơi cùng bạn bè và thách đấu nhau ngay trên trình duyệt.**

[![Kiểm thử](https://github.com/thanhvuaws-jpg/pythongamelichjsu/actions/workflows/ci.yml/badge.svg)](https://github.com/thanhvuaws-jpg/pythongamelichjsu/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![pygame-ce](https://img.shields.io/badge/pygame--ce-2.5-5C9E2E)
![WebAssembly](https://img.shields.io/badge/pygbag-WebAssembly-654FF0?logo=webassembly&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.162-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)

### [▶ Chơi ngay: game.vtkt.online](https://game.vtkt.online)

<img src="docs/readme/gioi_thieu.gif" alt="Ảnh động: trận Bạch Đằng, cách đánh trong trận và chơi cùng bạn bè" width="100%">

</div>

> Đề số 5, học phần **Lập trình Python**, Nhóm 1. Mọi câu chuyện sử trong game đều có nguồn; bóng giặc, cảnh giới, tiềm năng,
> tiền quan là phần trò chơi, không phải chuyện sử.

## Mục lục

- [Video giới thiệu](#video-giới-thiệu)
- [Game có gì](#game-có-gì)
- [Ảnh trong game](#ảnh-trong-game)
- [Chơi cùng bạn bè và thách đấu thật](#chơi-cùng-bạn-bè-và-thách-đấu-thật)
- [Điều khiển](#điều-khiển)
- [Kiến trúc](#kiến-trúc)
- [Chạy trên máy](#chạy-trên-máy)
- [Kiểm thử](#kiểm-thử)
- [Triển khai](#triển-khai)
- [Cấu trúc thư mục](#cấu-trúc-thư-mục)
- [Nguồn sử liệu và tài nguyên](#nguồn-sử-liệu-và-tài-nguyên)

## Video giới thiệu

Video quay thẳng từ game (`tools/make_trailer_video.py`), nên luôn khớp với thứ người chơi thấy. Bản đủ dài 4 phút 53 giây:

1. phần hướng dẫn 2 phút 45 giây (cũng là video hướng dẫn trong game);
2. người chơi máy đánh nhiệm vụ cuối, Chiến dịch Điện Biên Phủ: chọn phương châm, kéo pháo, đánh ba đợt;
3. qua cổng cuối của Màn 3 vào đoạn kết: lá cờ trên nóc hầm Đờ Cát-xtơ-ri, Hiệp định Giơnevơ, tiếp quản Thủ đô, lễ chào
   cờ ở Cột Cờ năm 1954 và ngày thống nhất 30/4/1975.

Đoạn phát ngay dưới đây là phần hướng dẫn.

https://github.com/user-attachments/assets/8f33c440-58b6-497c-a96e-062cc5967504

<sub>Bản đủ (1440p) nằm ở <code>web/video/trailer.mp4</code> (tải về để xem), và cũng phát ngay ở trang chủ <a href="https://game.vtkt.online">game.vtkt.online</a>.</sub>

## Game có gì

| Phần | Có gì |
|---|---|
| **3 màn sử, 18 di tích** | *Những khúc sông giữ nước* (938 – 1288), *Mười năm nếm mật nằm gai* (1418 – 1428), *Từ Tân Trào đến Điện Biên* (1945 – 1954). Từ Đường Lâm, Bạch Đằng, Như Nguyệt, Kiếp Bạc, Lam Sơn, Chi Lăng, Hồ Gươm tới Tân Trào, Ba Đình, Đông Khê, Điện Biên Phủ. |
| **Học sử bằng việc làm** | Nghe người giữ ký ức kể chuyện (hồi ức tự diễn), trả lời 44 câu hỏi có ghi nguồn (12 dạng: chọn đáp án, sắp xếp sự kiện, chỉ trên bản đồ, đối chiếu nguồn, sử hay truyền thuyết...), nhặt và ghép 28 mảnh tư liệu, phá vụ điều tra, xếp dòng thời gian rồi mới qua cổng sang giai đoạn sau. |
| **Trận đánh theo trận thật** | 4 trận cờ đỏ: Bạch Đằng 938 và 1288 (cắm cọc, chờ con nước), Chi Lăng 1427, Điện Biên Phủ 1954. |
| **Nhập vai, cày cấp** | Đánh 29 loại bóng giặc, 12 kẻ mạnh, 3 trùm cuối màn; lên cấp, tiềm năng, cảnh giới và đột phá; 11 kỹ năng (lắp 4 ô); lò rèn 28 món đồ, mặc gì nhân vật trông như thế; chiến mã, câu cá nướng cá, 12 vùng luyện, sổ bóng giặc. |
| **Chơi nhiều người** | Thấy nhau trên map, tổ đội chia kinh nghiệm, kết đồng minh, chat cùng map và kênh thế giới, Bảng vàng 20 người giỏi nhất, **thách đấu thật giữa hai người chơi**. |
| **Trang web và quản trị** | Đăng ký, đăng nhập, phân quyền, bảng xếp hạng, lưu tiến trình lên máy chủ; cổng quản trị "Sử quán" riêng: tổng quan, quản lý người dùng (cộng điểm, khoá, xoá), sổ thao tác. |
| **Đoạn kết** | Điện Biên Phủ 7/5/1954, Giơnevơ, tiếp quản Hà Nội 10/10/1954, và một trang nói rõ phải tới 30/4/1975 đất nước mới thống nhất. |

## Ảnh trong game

<table>
  <tr>
    <td width="50%"><img src="docs/readme/man_tua_de.png" alt="Màn tựa đề"><br><sub><b>Màn tựa đề</b>: nhân vật của bạn, di tích đã đóng dấu, mẩu "Biết không?".</sub></td>
    <td width="50%"><img src="docs/readme/ban_do.png" alt="Đi lại trên map"><br><sub><b>Map đầu</b>: Bảng vàng, lò rèn, người chơi khác cùng map, việc cần làm ở góc trên trái.</sub></td>
  </tr>
  <tr>
    <td><img src="docs/readme/hoi_uc.png" alt="Hồi ức tự diễn"><br><sub><b>Hồi ức</b>: người giữ ký ức kể, cảnh tự diễn lại sự kiện.</sub></td>
    <td><img src="docs/readme/cau_hoi.png" alt="Câu hỏi có nguồn"><br><sub><b>Câu hỏi</b>: trả lời đúng mới đi tiếp, lời giải thích ghi rõ nguồn.</sub></td>
  </tr>
  <tr>
    <td><img src="docs/readme/tran_danh.png" alt="Trận Bạch Đằng"><br><sub><b>Trận Bạch Đằng 938</b>: cọc nhọn dưới lòng sông, triều lên nhử địch vào, triều xuống đánh quật lại.</sub></td>
    <td><img src="docs/readme/danh_quai.png" alt="Đánh quái trên map"><br><sub><b>Đánh bóng giặc</b>: chuột trái chém, Shift né, 1 đến 4 tung kỹ năng.</sub></td>
  </tr>
  <tr>
    <td><img src="docs/readme/dieu_tra.png" alt="Vụ điều tra"><br><sub><b>Vụ điều tra</b>: tìm manh mối trong căn nhà tư liệu.</sub></td>
    <td><img src="docs/readme/dong_thoi_gian.png" alt="Dòng thời gian"><br><sub><b>Dựng dòng thời gian</b>: xếp sự kiện đúng thứ tự rồi mới qua cổng.</sub></td>
  </tr>
  <tr>
    <td><img src="docs/readme/lo_ren.png" alt="Lò rèn"><br><sub><b>Lò rèn và túi đồ</b>: vũ khí, áo, mũ, giày, găng, cần câu.</sub></td>
    <td><img src="docs/readme/tu_luyen.png" alt="Tu luyện"><br><sub><b>Tu luyện</b>: cộng tiềm năng, học kỹ năng bằng điểm có được khi học sử.</sub></td>
  </tr>
  <tr>
    <td><img src="docs/readme/vung_luyen.png" alt="Vùng luyện"><br><sub><b>Vùng luyện</b>: 12 vùng như phòng tuyến Như Nguyệt, bến Chương Dương, cứ điểm Đông Khê.</sub></td>
    <td><img src="docs/readme/cau_ca.png" alt="Câu cá"><br><sub><b>Câu cá</b>: câu, nướng ở bếp lửa, vào trận ăn cho lại sức.</sub></td>
  </tr>
  <tr>
    <td><img src="docs/readme/ban_do_dai_viet.png" alt="Bản đồ"><br><sub><b>Bản đồ</b> (phím M): các di tích đã mở theo từng màn.</sub></td>
    <td><img src="docs/readme/bang_vang.png" alt="Bảng vàng"><br><sub><b>Bảng vàng</b>: 20 người giỏi nhất về điểm học sử và sức mạnh.</sub></td>
  </tr>
  <tr>
    <td><img src="docs/readme/doan_ket.png" alt="Đoạn kết Điện Biên Phủ"><br><sub><b>Đoạn kết</b>: lá cờ "Quyết chiến Quyết thắng" trên nóc hầm chỉ huy địch, chiều 7/5/1954.</sub></td>
    <td><img src="docs/readme/trang_chu.png" alt="Trang chủ"><br><sub><b>Trang chủ</b>: giới thiệu, đăng ký, đăng nhập, bảng xếp hạng.</sub></td>
  </tr>
  <tr>
    <td><img src="docs/readme/quan_tri.png" alt="Cổng quản trị Sử quán"><br><sub><b>Cổng quản trị "Sử quán"</b>: tổng quan, người dùng, sổ thao tác.</sub></td>
    <td><img src="docs/readme/ket_qua.png" alt="Thắng trận thách đấu"><br><sub><b>Thắng thách đấu</b>: máy chủ phân xử, ghi kết quả cho cả hai người.</sub></td>
  </tr>
</table>

## Chơi cùng bạn bè và thách đấu thật

<div align="center">
<img src="docs/readme/thach_dau.gif" alt="Ảnh động: bấm vào người chơi, mời thách đấu, hai người vào võ đài đánh nhau" width="85%">
</div>

- **Bấm vào một người chơi trên map** để mở bảng trạng thái của họ: hình nhân vật mặc đúng bộ đồ, cấp, cảnh giới, lực chiến,
  đồ đang dùng, cùng các nút *Mời vào tổ đội*, *Kết đồng minh*, *Thách đấu*.
- **Lời mời hiện ở góc trên phải** màn chơi của người được mời, có nút Đồng ý, Từ chối và đếm ngược 60 giây.
- **Thách đấu thật:** người được mời bấm Đồng ý là cả hai cùng được đưa tới võ đài, mỗi người tự điều khiển nhân vật của mình.
  Máy người ra đòn báo đòn trúng, máy bị đánh tự trừ máu nên né và thế thủ vẫn có tác dụng. Máy chủ phân xử khi có người gục,
  rút lui, rời game hoặc hết 90 giây (ai còn nhiều máu hơn thì thắng, ngang nhau là hoà) và ghi kết quả cho cả hai.
- Người vào map, đổi map hay thoát game được báo ngay cho mọi người ở map đó, kể cả khi họ đang mở túi đồ hay bảng khác.
- Tổ đội tối đa 4 người, đứng gần nhau khi đồng đội hạ quái thì được chia một nửa kinh nghiệm và tiềm năng.
- Chat (phím L): cùng map miễn phí, kênh thế giới tốn 10 quan một tin; máy chủ lọc từ tục và chặn gửi dồn.

<table>
  <tr>
    <td width="33%"><img src="docs/readme/bang_trang_thai.png" alt="Bảng trạng thái người chơi"><br><sub>Bảng trạng thái khi bấm vào người chơi</sub></td>
    <td width="33%"><img src="docs/readme/loi_moi.png" alt="Lời mời ở góc trên phải"><br><sub>Lời mời ở góc trên phải</sub></td>
    <td width="33%"><img src="docs/readme/vo_dai.png" alt="Võ đài thách đấu"><br><sub>Hai người thật trên võ đài</sub></td>
  </tr>
</table>

## Điều khiển

| Trên map | | Trong trận | |
|---|---|---|---|
| `W A S D` hoặc bấm chuột | đi lại | **Chuột trái** | chém (giữ chuột để chém liên tục) |
| `E` | nói chuyện, xem | **Shift** | né |
| `F` | đánh bóng giặc gần nhất | giữ **chuột phải** | đi theo con trỏ |
| bấm vào **người chơi khác** | bảng trạng thái, mời, thách đấu | `1` – `4` | tung kỹ năng |
| `B` · `G` · `K` | túi đồ · sổ bóng giặc · tu luyện | `Q` | uống thuốc nam |
| `T` · `J` · `M` · `N` | tư liệu · lộ trình · bản đồ · sổ tay | `E` | ăn cá nướng |
| `H` · `R` · `C` | gọi chiến mã · cưỡi ngựa · câu cá | `Esc` | rút lui |
| `P` · `L` | bạn chơi · chat | | |

Mọi bảng đều mở được từ nút ba gạch ở góc trên phải.

**Trên điện thoại** (mở bằng trình duyệt, cầm ngang): giữ **cần điều khiển ở góc dưới trái** rồi kéo về hướng muốn đi
(kéo càng xa càng nhanh), hoặc chạm lên bản đồ để đi tới đó. Góc dưới phải có nút chạm thay cho phím: nói chuyện hay đánh
với ai đứng cạnh, thả câu và kéo cần, gọi và xuống ngựa, lên bờ khi đang chèo thuyền, nhận lời hay từ chối võ sinh thách
đấu. Trong trận cũng có cần điều khiển, cùng các nút CHÉM (giữ để chém liên tục), NÉ, kỹ năng; nhiều ngón cùng lúc nên vừa
giữ cần đi vừa chém được. Trang chơi tự ẩn thanh trên khi cầm ngang, có nút Toàn màn hình (Android) và nhắc xoay ngang
khi đang cầm dọc.

## Kiến trúc

```mermaid
flowchart LR
    subgraph Browser["Trình duyệt"]
        Web["Trang web<br/>HTML, CSS, JS"]
        Game["Game pygame-ce<br/>WebAssembly (pygbag)"]
        Web -- "window.SKNet, SKChat" --> Game
    end
    subgraph Server["Máy chủ FastAPI"]
        API["REST API<br/>đăng nhập, lưu game,<br/>xếp hạng, quản trị"]
        Hub["Thế giới chung<br/>WebSocket /api/v1/world/ws<br/>tổ đội, chat, thách đấu"]
        Bots["Người chơi máy"]
    end
    DB[("PostgreSQL 16")]
    Web -- "HTTPS / JWT" --> API
    Web -- "WebSocket" --> Hub
    Bots --> Hub
    API --> DB
    Hub --> DB
```

- **Game** viết bằng pygame-ce, các cảnh xếp chồng theo ngăn xếp (`game/core/scene.py`), đóng gói sang WebAssembly bằng
  pygbag nên chạy thẳng trên trình duyệt; vẫn chạy được trên máy tính để phát triển và kiểm thử.
- **Bản web nhẹ hơn bản máy tính** (`tools/web_extras.py`): phông cắt còn chữ Việt, nhạc nền ngoài màn tựa đề tải ngầm sau
  khi vào game, gói game tải sẵn trong lúc Python khởi động, và có màn tải riêng (`tools/loader/`) với mẩu sử có nguồn.
  Gói game 6,1 MB còn 1,8 MB; ở mạng 10 Mbps, lần đầu vào game từ khoảng 20 giây còn khoảng 13 giây.
- **Trang chơi** giữ kết nối WebSocket và chuyển tin cho game qua `window.SKNet` (JSON thuần ASCII, vì chuỗi có dấu đi từ
  Python sang JavaScript trong pygbag bị đọc sai mã).
- **Máy chủ** FastAPI, SQLAlchemy 2 bất đồng bộ (asyncpg), Alembic, JWT (access 15 phút, refresh 7 ngày), mật khẩu băm argon2,
  giới hạn tần suất bằng slowapi. Bộ điều phối thế giới chung ở `backend/app/world/hub.py`.
- **Triển khai** bằng Docker: một container ứng dụng (API, game WebAssembly, trang quản trị), một PostgreSQL, ra Internet
  qua Cloudflare Tunnel.

## Chạy trên máy

Cần **Python 3.12+** và **Docker Desktop** (để chạy PostgreSQL).

```bash
git clone https://github.com/thanhvuaws-jpg/pythongamelichjsu.git
```

```bash
cd pythongamelichjsu
```

```bash
python -m venv .venv
```

```bash
.venv/Scripts/pip install ./backend[dev] -r game/requirements-dev.txt
```

**Cách nhanh trên Windows:** mở Docker Desktop rồi bấm đúp `CHAY_THU.bat`. Script tự bật cơ sở dữ liệu, tạo `backend/.env`
từ `.env.example`, đóng gói game nếu chưa có, chạy migration, tạo tài khoản quản trị rồi mở `http://127.0.0.1:8200`.

**Chạy từng bước:** sao chép `.env.example` thành `backend/.env`, điền `ADMIN_EMAIL`, `ADMIN_PASSWORD`, rồi:

```bash
docker compose up -d db
```

```bash
.venv/Scripts/python tools/build_web.py
```

```bash
cd backend && PYTHONPATH=.. ../.venv/Scripts/python -m alembic upgrade head
```

```bash
cd backend && PYTHONPATH=.. ../.venv/Scripts/python -m seed.create_admin
```

```bash
cd backend && PYTHONPATH=.. ../.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Mở `http://127.0.0.1:8000`. Phải dùng `127.0.0.1`: với `localhost`, pygbag tìm thư viện trên máy thay vì trên CDN nên đứng
ở màn hình tải. Muốn chơi thử ngay trên máy tính không cần máy chủ: `.venv/Scripts/python game/main.py`.

## Kiểm thử

| Phần | Lệnh | Kết quả |
|---|---|---|
| Game (có bot chơi hết game, hai máy thách đấu nhau qua bộ điều phối thật) | `cd game && ../.venv/Scripts/python -m pytest tests -q` | 347 bài đạt |
| Máy chủ (API, WebSocket, PostgreSQL thật) | `cd backend && ../.venv/Scripts/python -m pytest tests -q` | 52 bài đạt |
| Phong cách code | `.venv/Scripts/ruff check game backend shared tools` | sạch |
| Nội dung lịch sử (18 di tích, 44 câu hỏi, 28 tư liệu, 4 trận đánh) | `.venv/Scripts/python tools/check_content.py` | không có lỗi |

GitHub Actions (`.github/workflows/ci.yml`) chạy cả bốn bước với PostgreSQL 16 mỗi lần đẩy code.

## Triển khai

- Bản đang chạy: **https://game.vtkt.online**, trên VPS bằng Docker Compose, ra Internet qua Cloudflare Tunnel nên VPS không mở thêm cổng nào. Ghi chép và lệnh cập nhật ở
  [`trien_khai_vps/HUONG_DAN.md`](trien_khai_vps/HUONG_DAN.md); các tệp bí mật (`.env`, token tunnel) không đưa lên git.
- Cách triển khai khác (Render, Docker) ở [`DEPLOY.md`](DEPLOY.md).
- Container ứng dụng tự chạy `alembic upgrade head` khi khởi động (`backend/start.sh`).

## Cấu trúc thư mục

```text
├── game/                  Game pygame-ce
│   ├── main.py            điểm vào (vòng lặp async cho pygbag)
│   ├── core/              cảnh, mạng, nhân vật, vũ khí, bản đồ, lưu game, âm thanh
│   ├── scenes/            map, trận đánh, thách đấu, hồi ức, câu hỏi, lò rèn, quản trị trong game...
│   ├── content/           nội dung sử: màn, di tích, câu hỏi, tư liệu, vùng luyện, nguồn
│   ├── assets/            hình, nhạc, phông chữ
│   └── tests/             kiểm thử, có bot chơi hết game
├── backend/               Máy chủ FastAPI
│   ├── app/               auth, admin, game, social, world (WebSocket), models
│   ├── alembic/           migration cơ sở dữ liệu
│   └── tests/
├── web/                   Trang chủ, đăng nhập, xếp hạng, trang chơi, cổng quản trị
├── shared/                mã dùng chung cho game và máy chủ
├── tools/                 đóng gói web, xuất video, sinh đặc tả, kiểm nội dung
├── docs/                  cốt truyện, rà soát sử liệu, yêu cầu chi tiết, ảnh README
└── trien_khai_vps/        script và ghi chép triển khai lên VPS
```

## Nguồn sử liệu và tài nguyên

- Mỗi câu hỏi, tư liệu và đoạn hồi ức có ghi nguồn, lấy từ 22 nguồn như *Đại Việt sử ký toàn thư*, *Khâm định Việt sử thông
  giám cương mục*, *Lam Sơn thực lục*, *Nguyễn Trãi toàn tập*, *Lịch sử Việt Nam* (NXB Khoa học Xã hội), sách giáo khoa theo
  Chương trình GDPT 2018, tư liệu của Bảo tàng Chiến thắng lịch sử Điện Biên Phủ; danh mục ở `game/content/sources.json`. Các đợt rà soát và chỗ đã sửa ghi ở [`docs/RA_SOAT_SU_LIEU.md`](docs/RA_SOAT_SU_LIEU.md);
  chi tiết nào không tìm được nguồn thì bỏ. Cốt truyện ở [`docs/COT_TRUYEN.md`](docs/COT_TRUYEN.md), đặc tả từng vật thể
  ở [`docs/YEU_CAU_CHI_TIET.md`](docs/YEU_CAU_CHI_TIET.md).
- Đồ hoạ, nhạc: [Ninja Adventure Asset Pack](https://pixel-boy.itch.io/ninja-adventure-asset-pack) của Pixel-Boy và AAA,
  giấy phép CC0 1.0. Quân Tống, Nguyên, Minh được vẽ đè mũ giáp lên nhân vật gốc bằng `tools/make_soldiers.py`.
- Phông chữ: Be Vietnam Pro và Noto Serif, giấy phép SIL Open Font License.

<div align="center"><sub>Bài tập học phần Lập trình Python · Nhóm 1 · dùng cho mục đích học tập.</sub></div>
