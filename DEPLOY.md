# Đưa game lên mạng

> **Đang chạy thật trên VPS (từ 14/11/2026):** https://game.vtkt.online và https://admin.vtkt.online, qua Cloudflare Tunnel, thư mục riêng `/opt/sukydieutra`. Cách cập nhật, xem trạng thái, sao lưu, gỡ: xem `trien_khai_vps/HUONG_DAN.md`. Phần Render bên dưới là cách cũ, giữ để tham khảo.

Toàn bộ game, trang web và API chạy chung một địa chỉ, gói trong một Docker image. Cách dưới đây dùng Render vì có gói miễn phí và tự đọc được file `render.yaml`. Bạn cần tự tạo tài khoản GitHub và Render.

## Trước khi bắt đầu

Nên biết trước về gói miễn phí của Render:

- Máy chủ ngủ sau khoảng 15 phút không có ai vào, lần vào đầu tiên sau đó phải chờ khoảng 1 phút. Trước buổi chấm, hãy mở trang trước vài phút.
- Cơ sở dữ liệu miễn phí có hạn dùng, thường là 30 ngày. Hãy tạo gần ngày chấm và kiểm tra hạn trên trang Render.

## Bước 1: đẩy code lên GitHub

Chạy trong thư mục `webgamelichsuvietnam`. File `.gitignore` đã loại `.venv`, `build` và `.env`.

```bash
git init
```

```bash
git add .
```

```bash
git commit -m "Sử Ký Điều Tra"
```

Tạo một repository trống trên github.com rồi làm theo hướng dẫn "push an existing repository" hiện trên trang đó.

## Bước 2: tạo dịch vụ trên Render

1. Đăng nhập [render.com](https://render.com) bằng GitHub.
2. Chọn **New**, rồi **Blueprint**, rồi chọn repository vừa tạo. Render đọc `render.yaml` và đề xuất một dịch vụ web, một cơ sở dữ liệu.
3. Render hỏi các giá trị cần tự điền:
   - `ADMIN_EMAIL`: email của tài khoản quản trị đầu tiên.
   - `ADMIN_PASSWORD`: mật khẩu tối thiểu 8 ký tự. Đừng dùng lại mật khẩu của tài khoản khác.
   - `WEB_BASE_URL` và `CORS_ORIGINS`: để trống lần đầu, điền ở bước 3.
4. Bấm **Apply**. Lần build đầu mất khoảng 5 đến 10 phút vì phải đóng gói game sang WebAssembly.

## Bước 3: điền địa chỉ trang

Khi build xong, Render cấp một địa chỉ dạng `https://sukydieutra.onrender.com`. Vào **Environment** của dịch vụ, điền địa chỉ đó vào `WEB_BASE_URL` và `CORS_ORIGINS`, rồi lưu. Dịch vụ tự khởi động lại.

## Bước 4: kiểm tra

- Mở địa chỉ trang, bấm **Vào chơi**, tạo một tài khoản, chơi thử rồi trả lời một câu hỏi.
- Mở thêm `/health`, trường `database` phải là `ok`.
- Mở `/admin/` để vào cổng quản trị, đăng nhập bằng tài khoản quản trị. Trang người chơi không có liên kết tới đây, nên chỉ đưa địa chỉ này cho người quản trị.

## Gửi email thật (không bắt buộc)

Để `SKIP_EMAIL_VERIFICATION=true` thì đăng ký xong dùng được ngay, nhưng chức năng quên mật khẩu không gửi được email và người từ 16 tuổi trở xuống phải nhờ quản trị viên bấm **Kích hoạt**.

Muốn gửi email thật, đặt `EMAIL_BACKEND=resend`, `RESEND_API_KEY`, `EMAIL_FROM` rồi đổi `SKIP_EMAIL_VERIFICATION=false`. Đăng nhập Google là tuỳ chọn, xem các biến `GOOGLE_*` trong `.env.example`.

## Chạy trên máy để thử

Mở Docker Desktop rồi bấm đúp file `CHAY_THU.bat`. Trình duyệt tự mở trang game, trang quản trị ở `/admin/`. Giữ cửa sổ đen đó mở trong lúc chơi, đóng nó là tắt game.

Muốn tự chạy từng bước thì làm như sau:

```bash
docker compose up -d db
```

Sao chép `.env.example` thành `backend/.env`, điền `ADMIN_EMAIL`, `ADMIN_PASSWORD`, rồi trong thư mục `backend`:

```bash
PYTHONPATH=.. ../.venv/Scripts/python -m alembic upgrade head
```

```bash
PYTHONPATH=.. ../.venv/Scripts/python -m seed.create_admin
```

```bash
PYTHONPATH=.. ../.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Mở `http://127.0.0.1:8000`. Phải dùng `127.0.0.1`: với `localhost`, game sẽ tìm thư viện trên máy thay vì trên CDN và đứng ở màn hình tải. Nhớ chạy `tools/build_web.py` trước nếu vừa sửa game.

## Những việc nhóm cần tự rà lại trước khi nộp

- Nội dung lịch sử, đặc biệt các trích dẫn mới trong `game/content/extras.json`. Các nguồn có ghi chú "cần đối chiếu" trong `game/content/sources.json` chưa được kiểm tra với sách gốc.
- Tên địa danh sau đợt sáp nhập tỉnh năm 2025.
- Điểm xếp hạng được máy chủ tính lại từ bản lưu và không thể vượt mức tối đa của game, nhưng game vẫn chấm câu hỏi ở trình duyệt, nên người biết kỹ thuật vẫn có thể sửa bản lưu để lấy điểm.
