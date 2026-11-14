# Implementation Plan

- [ ] 1. Khởi tạo dự án và hạ tầng nền
- [x] 1.1 Tạo cấu trúc thư mục backend/, game/, web/, shared/ và cấu hình công cụ
  - pyproject.toml cho backend (FastAPI 0.162.x, SQLAlchemy 2.0, asyncpg, alembic, pydantic-settings, pwdlib[argon2], PyJWT, authlib, slowapi, jinja2) và game (pygame-ce 2.5.8, pygbag 0.9.3), ghim phiên bản
  - Cấu hình ruff, pytest, pytest-asyncio, hypothesis; docker-compose cho PostgreSQL local
  - _Requirements: 33.1, 33.2_

- [x] 1.2 Tạo ứng dụng FastAPI tối thiểu
  - `app/main.py` với CORS theo danh sách domain từ cấu hình, `config.py`, `db.py` (session async)
  - Middleware `request_id`, logger JSON lọc password/token/authorization
  - Định dạng lỗi thống nhất `{error: {code, message, details, request_id}}`
  - `GET /health` kiểm tra kết nối DB và Storage
  - _Requirements: 33.2, 33.5, 34.2_

- [ ]\* 1.3 Viết test cho health và định dạng lỗi
  - _Requirements: 33.5, 34.2_

- [ ] 2. Xác thực và phân quyền

- [x] 2.1 Tạo model và migration users, refresh_tokens, login_attempts, one_time_tokens, guardian_consents, audit_log
  - _Requirements: 23.1, 23.3, 27.3_

- [x] 2.2 Cài đặt băm mật khẩu, JWT và refresh token có thu hồi
  - `auth/password.py` (argon2), `auth/jwt.py` (access 15 phút, refresh 7 ngày lưu băm SHA-256)
  - _Requirements: 23.2, 23.3_

- [x] 2.3 Cài đặt endpoint register, verify-email, login, refresh, logout, password-reset
  - Kiểm tra mật khẩu ≥ 8 ký tự, bắt buộc đồng ý chính sách, năm sinh; dưới 16 tuổi chuyển `pending_guardian` và gửi email xác nhận người giám hộ
  - Khóa đăng nhập 15 phút sau 5 lần sai trong 15 phút (423)
  - Token đặt lại mật khẩu hiệu lực 30 phút, dùng một lần; lớp gửi email trừu tượng (console ở dev, SMTP/Resend ở prod)
  - _Requirements: 23.1, 23.4, 23.6, 27.1, 27.2_

- [ ] 2.4 Cài đặt đăng nhập Google OAuth 2.0
  - Liên kết với tài khoản có cùng email đã xác minh
  - _Requirements: 23.5_
- [x] 2.5 Cài đặt dependency `current_user` và `require_role` theo ma trận quyền
  - 401 khi thiếu/hết hạn token, 403 khi vượt quyền; cờ `is_teacher`
  - _Requirements: 24.1, 24.2, 24.3_

- [ ]\* 2.6 Viết test tích hợp luồng auth và ma trận phân quyền
  - Đăng ký → xác minh → đăng nhập → refresh; khóa sau 5 lần sai; 401/403 theo vai trò
  - _Requirements: 23.1–23.4, 24.1–24.3_

- [ ] 3. Danh mục nguồn và trích dẫn

- [x] 3.1 Tạo model và migration sources, citations, historian_notes, media
  - _Requirements: 1.1, 2.1, 3.1, 8.1_

- [x] 3.2 Cài đặt `content/validators.py`
  - `validate_citation` (nguồn phải thuộc danh mục đã duyệt, bắt buộc locator), `BLOCKED_DOMAINS` cấu hình được
  - `check_submit_rules`: ≥1 trích dẫn Cấp 1/2; trường date/numeric_facts cần ≥2 nguồn khác nhau với ≥1 Cấp 1; câu hỏi cần trích dẫn giải thích, sự kiện đã xuất bản, không dựa vào hư cấu; trích nguyên văn cần nguồn Cấp 1
  - _Requirements: 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5, 4.3, 4.4_

- [x] 3.3 Cài đặt endpoint nguồn: tạo đề xuất, sửa, duyệt với Cấp_Nguồn
  - _Requirements: 1.2, 1.3, 1.5_

- [x] 3.4 Cài đặt upload media có kiểm tra giấy phép lên Supabase Storage
  - Từ chối giấy phép ngoài danh sách cho phép; endpoint công khai `GET /public/credits`
  - _Requirements: 8.1, 8.2, 8.4_

- [x] 3.5 Tạo script seed Danh_Mục_Nguồn từ Phụ lục A
  - Nạp nguồn ở trạng thái `pending` để Người*Thẩm*Định xác nhận thông tin xuất bản và cấp
  - _Requirements: 1.1_

- [ ]\* 3.6 Viết unit test cho validators
  - Thiếu locator, chỉ Cấp 3, ngày chỉ 1 nguồn, 2 trích dẫn cùng nguồn, domain bị chặn, câu hỏi dựa vào hư cấu
  - _Requirements: 1.4, 1.5, 2.1–2.5, 4.4_
-

- [x] 4. Thực thể nội dung, phiên bản và thẩm định

- [x] 4.1 Tạo model và migration events, persons, places, causal_links, map_layers, fragments, dialogues, questions, levels, quests, objectives, badges kèm cột chung
  - Cột `status`, `is_fiction`, `author_id`, `last_editor_id`, `published_version_id`, `hidden_by_report`
  - Trường ngày `date_start/date_end/date_precision/lunar_date_text/era_name`
  - _Requirements: 1.1, 3.4, 4.1, 9.1, 21.1_

- [x] 4.2 Cài đặt CRUD chung `/content/{type}` với Pydantic schema cho từng loại
  - Mỗi lần lưu tạo bản ghi `content_versions`; sửa nội dung đã xuất bản không thay đổi `published_version_id`
  - _Requirements: 5.5, 6.1, 28.1_

- [x] 4.3 Cài đặt `review/workflow.py` và endpoint submit/approve/reject
  - Kiểm tra `check_submit_rules` khi submit và lại khi approve; chặn tự duyệt; bắt buộc xác nhận Ghi_Chú_Sử_Học cho câu hỏi liên quan; lưu `review_actions`, thông báo tác giả khi bị từ chối
  - _Requirements: 2.2, 3.3, 5.2, 5.3, 5.4_

- [x] 4.4 Cài đặt endpoint versions, diff theo trường và restore
  - _Requirements: 6.2, 6.3_

- [x] 4.5 Cài đặt nhập hàng loạt CSV/JSON
  - Kiểm tra từng dòng, nhập dòng hợp lệ ở Bản_Nháp, trả báo cáo lỗi
  - _Requirements: 28.5_

- [ ]\* 4.6 Viết test cho workflow và phiên bản
  - Chuyển trạng thái hợp lệ/không hợp lệ, tự duyệt bị từ chối, bản xuất bản cũ vẫn giữ khi sửa
  - _Requirements: 5.2–5.5, 6.1–6.3_
-

- [x] 5. Logic dùng chung trong `shared/` (thuần Python)

- [x] 5.1 Cài đặt `shared/histdate.py` và `shared/timeline_rules.py`
  - `HistDate` dạng khoảng theo Độ_Chính_Xác; `is_valid_placement` chấp nhận hoán đổi mốc chồng lấn; `hint_for` dựa trên Quan_Hệ_Nhân_Quả
  - _Requirements: 15.2, 15.3, 15.4_

- [x] 5.2 Cài đặt `shared/unlock.py` và `shared/quest_engine.py`
  - Đánh giá `unlock_rule`; xử lý on_arrive/on_collect/on_dialogue_done/on_question_correct/on_timeline_done trả về Effect; đủ mảnh ghép mở thẻ sự kiện; `is_level_complete` bỏ qua nhiệm vụ phụ
  - _Requirements: 9.3, 9.5, 12.3, 12.5, 13.3_

- [x] 5.3 Cài đặt `shared/grading.py`, `shared/scoring.py`, `shared/review_schedule.py`, `shared/progress_merge.py`
  - `grade()` cho 5 Loại_Câu_Hỏi (Haversine cho map_pick); `points_for` 10/20/30, 50% lần 2, 0 từ lần 3; chuỗi ôn 1-3-7-14-30; `merge` lấy hợp tập và `updated_at` mới hơn
  - _Requirements: 16.1, 18.1, 18.2, 18.3, 19.4, 20.2, 20.3, 20.4_

- [ ]\* 5.4 Viết unit test và property test (hypothesis) cho shared/
  - merge giao hoán và lũy đẳng; danh sách đúng thứ tự luôn hợp lệ; điểm không tăng theo lần thử
  - _Requirements: 15.4, 18.1–18.3, 19.4, 20.3, 20.4_

- [x] 6. Xuất bản Content_Bundle

- [x] 6.1 Cài đặt `publish/bundler.py` và endpoint `POST /levels/{id}/publish`
  - Kiểm tra mọi tham chiếu đã xuất bản (409 kèm danh sách thiếu); loại `correct_answer`, `explanation`, câu hỏi bị ẩn; tính sha256; tăng `version_no`; tải lên Storage
  - _Requirements: 5.1, 16.3, 29.1, 29.2, 29.3_

- [x] 6.2 Cài đặt `GET /bundles/manifest`
  - _Requirements: 29.4_

- [x] 6.3 Tạo `seed/check_bundle.py` kiểm tra tham chiếu, trích dẫn, giấy phép, phân bổ Độ_Khó
  - _Requirements: 2.2, 8.1, 16.4_

- [ ]\* 6.4 Viết test tích hợp luồng nguồn → sự kiện → duyệt → xuất bản
  - Bundle không chứa đáp án
  - _Requirements: 16.3, 29.1–29.3_

- [x] 7. API chơi game

- [x] 7.1 Tạo model và migration progress, question_attempts, score_ledger, review_items, review_points, user_badges, notifications
  - _Requirements: 18.5, 19.2, 20.6, 21.2_

- [x] 7.2 Cài đặt `GET/PUT /progress` dùng `progress_merge` và tính lại mở khóa ở server
  - _Requirements: 19.1, 19.2, 19.4_

- [x] 7.3 Cài đặt `POST /answers` và `POST /timeline/complete`
  - Khóa hàng question_attempts, chấm bằng `grade`, ghi score_ledger một lần, trả giải thích + trích dẫn; rate limit 30/phút; đưa câu đúng từ lần 3 vào review_items; thưởng 50 điểm timeline khi ≤ 2 lần sai
  - _Requirements: 16.2, 18.1–18.5, 22.5_

- [x] 7.4 Cài đặt `GET /review/{level_id}` và `POST /review/answers`
  - Chọn ≤ 10 câu theo ưu tiên; cập nhật stage; điểm vào review_points
  - _Requirements: 20.1, 20.2, 20.3, 20.4, 20.6_

- [ ] 7.5 Cài đặt đánh giá huy hiệu và `GET /me/badges`, `GET /me/notifications`
  - _Requirements: 21.2, 21.3, 7.4_

- [ ]\* 7.6 Viết test tích hợp chấm điểm và tiến trình
  - Cộng điểm một lần, 429 khi vượt ngưỡng, hợp nhất tiến trình
  - _Requirements: 18.5, 19.4, 22.5_

- [ ] 8. Bảng xếp hạng, lớp học, báo lỗi, quyền riêng tư

- [ ] 8.1 Cài đặt `GET /leaderboard` theo tuần/tháng/toàn bộ/lớp
  - Mốc tuần theo Asia/Ho_Chi_Minh; cache top 100 làm mới 60 giây; loại tài khoản bị vô hiệu; chỉ trả tên hiển thị và avatar
  - _Requirements: 22.1, 22.2, 22.3, 22.4, 25.3_

- [ ] 8.2 Cài đặt lớp học: tạo (mã 6 ký tự), tham gia, tiến độ, xuất CSV UTF-8
  - 403 khi giáo viên xem lớp khác

  - _Requirements: 26.1, 26.2, 26.3, 26.4, 26.5_

- [ ] 8.3 Cài đặt báo cáo sai sót
  - `POST /reports` (≤ 1000 ký tự); xử lý báo cáo; "Xác nhận sai" đặt `hidden_by_report` và dựng lại bundle; gửi thông báo cho người báo
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [ ] 8.4 Cài đặt quản lý người dùng
  - Tìm kiếm phân trang 50, lọc vai trò/trạng thái; đổi vai trò ghi audit_log; vô hiệu hóa thu hồi refresh token; chặn gỡ admin cuối
  - _Requirements: 25.1, 25.2, 25.3, 25.4_
- [ ] 8.5 Cài đặt `POST /me/export` và `DELETE /me`
  - Xuất JSON dữ liệu cá nhân; xóa dữ liệu cá nhân trong job định kỳ sau khi yêu cầu, giữ analytics ẩn danh
  - _Requirements: 25.5, 27.4_

- [ ]\* 8.6 Viết test cho leaderboard theo tuần, lớp học và chặn admin cuối
  - _Requirements: 22.2, 25.4, 26.5_

- [ ] 9. Phân tích và giám sát lỗi

- [ ] 9.1 Cài đặt `POST /analytics/events` (lô ≤ 50) với `anon_id = HMAC-SHA256`
  - _Requirements: 30.1, 30.5_

- [ ] 9.2 Cài đặt `GET /analytics/dashboard` và `/funnel/{level_id}`
  - DAU, tỷ lệ hoàn thành, thời gian trung bình theo màn, tỷ lệ đúng theo câu, cờ câu < 30% hoặc > 95% sau ≥ 50 lượt, phễu theo nhiệm vụ
  - _Requirements: 30.2, 30.3, 30.4_
- [ ] 9.3 Cài đặt `POST /client-errors`
  - _Requirements: 34.3_

- [ ] 10. Admin_Portal (Jinja2 + HTMX)

- [ ] 10.1 Tạo khung Admin_Portal: layout, đăng nhập cookie HttpOnly + CSRF, chuyển hướng Khách về trang đăng nhập
  - _Requirements: 24.4_
- [ ] 10.2 Tạo trang quản lý Danh_Mục_Nguồn và widget chọn trích dẫn
  - Widget chọn nguồn từ danh mục + nhập locator, field_path, đoạn trích, cờ trích nguyên văn
  - _Requirements: 1.2, 1.3, 2.1, 28.1_
- [ ] 10.3 Tạo biểu mẫu CRUD cho mọi loại nội dung
  - Đánh dấu trường trống mà giữ dữ liệu; chọn tọa độ bằng Leaflet; trình soạn Ghi_Chú_Sử_Học; trình soạn nodes Hội_Thoại có cờ hư cấu; upload media kèm giấy phép
  - _Requirements: 3.1, 4.1, 8.1, 28.1, 28.2, 28.3_
- [ ] 10.4 Tạo trang hàng đợi thẩm định, diff phiên bản, xuất bản màn và xem trước
  - _Requirements: 5.2, 5.4, 6.2, 6.3, 28.4, 29.1_
- [ ] 10.5 Tạo trang báo cáo sai sót, quản lý người dùng, lớp học và dashboard phân tích (Chart.js)
  - _Requirements: 7.2, 25.1, 26.3, 26.4, 30.2, 30.3, 30.4_

- [ ] 11. Web_Shell

- [ ] 11.1 Tạo trang index, register, login, privacy, credits, method
  - Register: đồng ý chính sách, năm sinh, email người giám hộ khi < 16 tuổi; nút Google; credits lấy từ `/public/credits`; method mô tả Cấp_Nguồn và quy trình thẩm định
  - _Requirements: 8.4, 23.1, 23.5, 27.1, 27.2, 32.1, 32.2_
- [ ] 11.2 Tạo trang play.html nhúng build pygbag và chuyển token qua localStorage
  - _Requirements: 33.1_

- [ ] 12. Nền tảng Game_Client
- [ ] 12.1 Tạo `game/main.py` vòng lặp async, App, SceneManager (push/pop/replace)
  - Bọc vòng lặp bằng try/except gửi client error và hiển thị màn hình lỗi
  - _Requirements: 34.3_
- [ ] 12.2 Tạo `core/display.py`, `core/fonts.py`, `core/theme.py`, `core/audio.py`
  - Canvas logic 1280×720 co giãn, bố cục dọc cho mobile; phông Be Vietnam Pro 3 cỡ, chuẩn hóa NFC, text_wrap; bảng màu tương phản ≥ 4.5:1; âm lượng nhạc/hiệu ứng riêng
  - _Requirements: 31.1, 31.2, 31.3_
- [ ] 12.3 Tạo `core/input.py` và bộ widget `ui/` có hỗ trợ focus bàn phím
  - Button, panel, scroll, card, toast; hợp nhất chuột/chạm/phím thành action
  - _Requirements: 10.4, 31.5_
- [-] 12.4 Tạo `net/api_client.py` (JS fetch trên web, httpx trên desktop) và `net/offline_queue.py`
  - Tự refresh khi 401; hàng đợi IndexedDB/localStorage gửi lại khi online
  - _Requirements: 19.3_

- [ ] 12.5 Tạo `GameState` và LoadingScene
  - Đọc token, so phiên bản bundle, tải bundle (kiểm tra sha256), tải progress; thanh tiến độ
  - _Requirements: 19.2, 29.4, 31.6_
- [ ]\* 12.6 Viết smoke test scene headless (SDL_VIDEODRIVER=dummy) với bundle mẫu
  - _Requirements: 31.6_

- [ ] 13. Các scene lối chơi
- [ ] 13.1 Tạo LevelSelectScene và TutorialScene
  - Trạng thái khóa kèm điều kiện; hướng dẫn 4 bước có nút bỏ qua
  - _Requirements: 9.2, 9.4, 31.4_
- [ ] 13.2 Tạo MapScene: nền bản đồ tile, camera pan/zoom 1x–4x, ghim Địa*Điểm, Lớp_Bản*Đồ
  - Phép chiếu equirectangular khung bao có Hoàng Sa, Trường Sa; panel thông tin Địa_Điểm theo tên lịch sử của giai đoạn
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_
- [ ] 13.3 Thêm di chuyển nhân vật theo tuyến và khung theo dõi nhiệm vụ vào MapScene
  - Gọi QuestEngine khi đến nơi; chặn đích bị khóa; hiển thị Mục_Tiêu, toast hoàn thành, bản tổng kết nhiệm vụ
  - _Requirements: 11.1, 11.2, 11.3, 12.1, 12.2, 12.3, 12.4, 12.5_
- [ ] 13.4 Tạo DialogueScene và FragmentView
  - Chân dung có nhãn "Tranh minh họa", tối đa 4 lựa chọn, nhãn "Lời dẫn hư cấu", ghi manh mối; tư liệu có bản dịch Hán Nôm, trích dẫn, dòng ghi công
  - _Requirements: 4.2, 8.3, 13.1, 13.2, 13.4, 14.1, 14.2, 14.3, 14.4_
- [ ] 13.5 Tạo QuestionScene với renderer cho 5 Loại_Câu_Hỏi
  - Xáo trộn phương án; gửi `/answers`; hiển thị kết quả, giải thích, trích dẫn; nút "Báo sai sót"; thông báo khi offline
  - _Requirements: 7.1, 16.1, 16.2, 16.5_
- [ ] 13.6 Tạo TimelineScene
  - Trục cuộn, khu vực chờ, kéo thả bằng chuột/chạm/phím, kiểm tra bằng `timeline_rules`, trả thẻ và gợi ý khi sai, mũi tên nhân quả khi hoàn tất, chi tiết thẻ có Ghi_Chú_Sử_Học; gọi `/timeline/complete`
  - _Requirements: 3.2, 15.1, 15.2, 15.3, 15.5, 15.6, 18.4_
- [ ] 13.7 Tạo NotebookScene
  - 5 tab, tìm kiếm bỏ dấu không phân biệt hoa thường, ô "?" cho mục khóa, chi tiết kèm trích dẫn
  - _Requirements: 17.1, 17.2, 17.3, 17.4_
- [ ] 13.8 Tạo ReviewScene, LeaderboardScene, ProfileScene
  - Đề xuất ôn tập khi xong màn, kết quả và liên kết Sổ tay; bảng xếp hạng 4 tab; huy hiệu, cài đặt, nhập mã lớp, thông báo
  - _Requirements: 20.1, 20.5, 21.3, 22.1, 26.2, 31.3_
- [ ] 13.9 Nối lưu tiến trình và gửi analytics vào các scene
  - PUT /progress sau mỗi Mục_Tiêu; gom lô analytics cho bắt đầu nhiệm vụ, hoàn thành mục tiêu, trả lời, đặt thẻ, hoàn thành màn
  - _Requirements: 19.1, 30.1_
- [ ]\* 13.10 Viết unit test cho tìm kiếm bỏ dấu và phép chiếu tọa độ
  - _Requirements: 10.2, 17.2_

- [ ] 14. Nội dung mẫu và triển khai

- [ ] 14.1 Tạo bộ dữ liệu mẫu tối thiểu cho Màn 1 dạng JSON nhập được qua `/content/import`
  - Khung sự kiện từ Phụ lục B với trường trích dẫn để trống ở dạng TODO cho Biên_Tập_Viên điền từ sách gốc; không tự điền số trang
  - _Requirements: 2.1, 28.5_
- [ ] 14.2 Tạo Dockerfile backend và cấu hình triển khai (Render/Fly.io), cấu hình static hosting cho web/ + build pygbag
  - _Requirements: 33.1, 33.2_
- [ ] 14.3 Tạo workflow GitHub Actions
  - ruff → pytest unit → pytest integration với Postgres service → pygbag build + docker build → alembic upgrade → deploy → kiểm tra /health; dừng khi có bước lỗi
  - _Requirements: 33.3, 33.4_
- [ ] 14.4 Cấu hình sao lưu DB hằng ngày giữ 7 ngày và job dọn dữ liệu (xóa tài khoản sau 30 ngày, giữ phiên bản ≥ 3 năm)
  - _Requirements: 6.4, 25.5, 34.1_
