# Requirements Document

## Introduction

"Sử Ký Điều Tra" (tên tạm) là game điều tra lịch sử Việt Nam 2D chạy trên trình duyệt. Game_Client viết bằng Python (Pygame hoặc Arcade) và đóng gói sang WebAssembly bằng pygbag. Backend_API viết bằng FastAPI, lưu dữ liệu trên PostgreSQL (khuyến nghị Supabase để có sẵn Auth và Storage). Sản phẩm được triển khai trực tuyến qua HTTPS với URL công khai.

Bài toán: học lịch sử dễ bị xem là học thuộc lòng khi thiếu bối cảnh không gian, thời gian và quan hệ nhân quả. Game giải quyết bằng ba trục gắn với nhau:

- Bản đồ: Người*Chơi di chuyển qua các Địa*Điểm có thật, thấy được sự kiện xảy ra ở đâu.
- Dòng thời gian: Người_Chơi tự sắp xếp Sự_Kiện, thấy được trình tự và quan hệ nguyên nhân – kết quả.
- Nhiệm vụ điều tra: Người_Chơi thu thập Mảnh_Ghép tư liệu, đối thoại với Nhân_Vật, trả lời Câu_Hỏi để mở khóa Sự_Kiện tiếp theo.

Nguyên tắc nội dung: mọi dữ liệu lịch sử hiển thị trong game phải truy xuất được về Nguồn_Tin_Cậy cụ thể (tên tài liệu, nhà xuất bản, năm, tập, trang) và phải qua quy trình thẩm định trước khi xuất bản. Nội dung hư cấu phục vụ lối chơi (lời thoại dẫn dắt, nhân vật dẫn đường) phải được gắn nhãn hư cấu và tách biệt khỏi dữ kiện lịch sử.

Phạm vi MVP gồm 3 Màn_Chơi (danh mục sự kiện ứng viên ở Phụ lục B):

1. Màn 1 — Ba lần thắng trên sông Bạch Đằng và kháng chiến chống Tống, chống Nguyên Mông (938–1288).
2. Màn 2 — Khởi nghĩa Lam Sơn (1418–1428).
3. Màn 3 — Cách mạng tháng Tám và kháng chiến chống Pháp đến Hiệp định Genève (1945–1954).

Ngoài phạm vi MVP: chế độ nhiều người chơi thời gian thực, ứng dụng di động gốc, nội dung giai đoạn 1954–1975 và sau 1975 (để giai đoạn sau, do cần quy trình thẩm định chuyên sâu hơn).

## Glossary

### Thành phần hệ thống

- **Game_Client**: Ứng dụng game Python 2D chạy trong trình duyệt qua WebAssembly (pygbag).
- **Backend_API**: Dịch vụ FastAPI cung cấp API xác thực, nội dung, tiến trình, chấm điểm, bảng xếp hạng và phân tích.
- **Admin_Portal**: Ứng dụng web dành cho Biên*Tập_Viên, Người_Thẩm*Định và Quản_Trị_Viên.
- **Content_Store**: Cơ sở dữ liệu PostgreSQL lưu nội dung lịch sử, nguồn, nhiệm vụ và câu hỏi.
- **Media_Store**: Kho lưu trữ đối tượng (Supabase Storage hoặc tương đương) chứa hình ảnh, âm thanh, bản đồ.
- **Content_Bundle**: Gói dữ liệu JSON đã xuất bản của một Màn_Chơi, được Game_Client tải về để chơi.
- **CI_Pipeline**: Quy trình tích hợp và triển khai tự động (ví dụ GitHub Actions).

### Vai trò

- **Khách**: Người truy cập chưa đăng nhập.
- **Người_Chơi**: Người dùng đã đăng nhập có quyền chơi game.
- **Biên_Tập_Viên**: Người dùng có quyền soạn và chỉnh sửa nội dung lịch sử.
- **Người*Thẩm*Định**: Người dùng có quyền phê duyệt hoặc từ chối nội dung; khuyến nghị là giáo viên lịch sử hoặc người có chuyên môn sử học.
- **Quản_Trị_Viên**: Người dùng có toàn quyền quản lý người dùng, vai trò và cấu hình hệ thống.

### Nguồn và trích dẫn

- **Nguồn_Tin_Cậy**: Tài liệu thuộc Danh*Mục_Nguồn, đã được Người_Thẩm*Định chấp nhận.
- **Danh_Mục_Nguồn**: Danh sách Nguồn_Tin_Cậy được quản lý trong Content_Store (danh mục khởi tạo ở Phụ lục A).
- **Cấp_Nguồn**: Mức độ tin cậy của một Nguồn_Tin_Cậy:
  - Cấp 1 — Chính sử, văn kiện gốc và công trình học thuật chính thống.
  - Cấp 2 — Tài liệu giáo dục chính thức, tư liệu bảo tàng nhà nước, tạp chí chuyên ngành sử học.
  - Cấp 3 — Sách khảo cứu đã xuất bản có tác giả rõ ràng, chỉ dùng bổ trợ.
- **Trích_Dẫn**: Liên kết giữa một nội dung và một Nguồn_Tin_Cậy, gồm tập, trang hoặc mục, và đoạn trích ngắn tùy chọn.
- **Ghi_Chú_Sử_Học**: Ghi chú hiển thị khi các Nguồn_Tin_Cậy ghi nhận khác nhau về niên đại, địa điểm, số liệu hoặc diễn biến.
- **Nhãn_Hư_Cấu**: Nhãn đánh dấu nội dung do nhóm phát triển sáng tác để phục vụ lối chơi, không phải dữ kiện lịch sử.
- **Giấy_Phép_Media**: Thông tin bản quyền của một tệp media: chủ sở hữu, loại giấy phép (ví dụ CC BY-SA 4.0, phạm vi công cộng, tự sản xuất) và đường dẫn nguồn.

### Nội dung

- **Sự_Kiện**: Biến cố lịch sử có tên, mốc thời gian, Địa_Điểm, Nhân_Vật liên quan, mô tả, ý nghĩa và Trích_Dẫn.
- **Mốc_Thời_Gian**: Thời điểm của Sự_Kiện, lưu theo dương lịch, kèm âm lịch hoặc niên hiệu tùy chọn và Độ_Chính_Xác.
- **Độ_Chính_Xác**: Mức chi tiết của Mốc_Thời_Gian: ngày, tháng, năm, khoảng năm hoặc khoảng thế kỷ.
- **Quan_Hệ_Nhân_Quả**: Liên kết có hướng giữa hai Sự_Kiện với loại "nguyên nhân của", "dẫn đến" hoặc "bối cảnh của", có Trích_Dẫn.
- **Nhân_Vật**: Cá nhân lịch sử có tên, tên khác (tên húy, miếu hiệu, tước hiệu), năm sinh – mất, tiểu sử và Trích_Dẫn.
- **Địa_Điểm**: Vị trí trên Bản_Đồ có tọa độ, tên lịch sử theo từng giai đoạn, tên hành chính hiện nay và Trích_Dẫn.
- **Mảnh_Ghép**: Mẩu tư liệu (trích đoạn văn bản, ảnh hiện vật, bản đồ cổ, ảnh tư liệu) gắn với một Sự_Kiện, có Trích_Dẫn và Giấy_Phép_Media nếu có media.
- **Câu_Hỏi**: Câu hỏi gắn với một Sự_Kiện, có loại câu hỏi, đáp án, giải thích, Độ_Khó và Trích_Dẫn.
- **Loại_Câu_Hỏi**: Một trong: trắc nghiệm một đáp án, trắc nghiệm nhiều đáp án, sắp xếp thứ tự, ghép cặp, chọn vị trí trên bản đồ.
- **Độ_Khó**: Mức 1 (nhận biết), 2 (thông hiểu), 3 (vận dụng) theo thang Bloom rút gọn dùng trong Chương trình GDPT 2018.
- **Hội_Thoại**: Chuỗi lời thoại giữa Người_Chơi và một Nhân_Vật hoặc nhân vật dẫn đường, có thể chứa lựa chọn.
- **Trạng_Thái_Nội_Dung**: Một trong: Bản*Nháp, Chờ_Thẩm*Định, Đã_Xuất_Bản, Lưu_Trữ.

### Lối chơi

- **Bản_Đồ**: Bản đồ Việt Nam tương tác 2D trong Game_Client.
- **Lớp*Bản*Đồ**: Lớp hiển thị chồng lên Bản_Đồ (ranh giới lịch sử, đường hành quân, địa danh cổ) gắn với một giai đoạn.
- **Dòng_Thời_Gian**: Thành phần hiển thị và cho phép sắp xếp các Sự_Kiện theo thứ tự thời gian.
- **Màn_Chơi**: Một chương nội dung gồm nhiều Nhiệm*Vụ, một Dòng_Thời_Gian và một tập Địa*Điểm.
- **Nhiệm_Vụ**: Chuỗi Mục_Tiêu điều tra gắn với một hoặc nhiều Sự_Kiện.
- **Mục_Tiêu**: Một bước trong Nhiệm*Vụ: đến Địa*Điểm, thu thập Mảnh_Ghép, hoàn thành Hội_Thoại, trả lời Câu_Hỏi hoặc sắp xếp Dòng_Thời_Gian.
- **Điều_Kiện_Mở_Khóa**: Tập điều kiện (Nhiệm*Vụ đã hoàn thành, Điểm_Kiến_Thức tối thiểu) để mở một Nhiệm_Vụ, Địa*Điểm hoặc Màn_Chơi.
- **Sổ*Tay*Điều_Tra**: Màn hình tổng hợp Mảnh_Ghép, Sự_Kiện, Nhân_Vật đã mở khóa và Trích_Dẫn tương ứng.
- **Điểm_Kiến_Thức**: Điểm Người_Chơi nhận khi hoàn thành mục tiêu học tập.
- **Huy_Hiệu**: Thành tích trao cho Người_Chơi khi đạt điều kiện cấu hình sẵn.
- **Bảng_Xếp_Hạng**: Danh sách Người_Chơi xếp theo Điểm_Kiến_Thức trong một khoảng thời gian.
- **Chế*Độ*Ôn_Tập**: Phiên ôn lại Câu_Hỏi của Màn_Chơi đã hoàn thành, ưu tiên Câu_Hỏi trả lời sai.
- **Lớp_Học**: Nhóm Người_Chơi do một Giáo_Viên tạo để theo dõi tiến độ chung.
- **Giáo_Viên**: Người_Chơi được cấp quyền tạo Lớp_Học và xem tiến độ của thành viên Lớp_Học.
- **Sự_Kiện_Phân_Tích**: Bản ghi hành vi Người_Chơi dùng cho thống kê.
- **Báo_Cáo_Sai_Sót**: Phản hồi do người dùng gửi khi nghi ngờ nội dung lịch sử sai.

## Requirements

### A. Nguồn tin cậy và quản trị nội dung lịch sử

### Requirement 1: Danh mục nguồn tin cậy

**User Story:** Là Người*Thẩm*Định, tôi muốn quản lý một Danh_Mục_Nguồn có phân cấp, để mọi trích dẫn trong game đều trỏ về tài liệu đã được kiểm chứng.

#### Acceptance Criteria

1. THE Content_Store SHALL lưu mỗi Nguồn_Tin_Cậy với các trường: tên tài liệu, tác giả hoặc cơ quan biên soạn, người dịch hoặc hiệu đính, nhà xuất bản, năm xuất bản, lần tái bản, số tập, Cấp_Nguồn, mã ISBN hoặc mã lưu trữ tùy chọn và đường dẫn bản số tùy chọn.
2. WHEN Biên*Tập_Viên đề xuất thêm một nguồn mới, THE Backend_API SHALL lưu nguồn ở trạng thái Chờ_Thẩm*Định.
3. WHEN Người*Thẩm*Định chấp nhận một nguồn đề xuất, THE Backend*API SHALL thêm nguồn vào Danh_Mục_Nguồn với Cấp_Nguồn do Người_Thẩm*Định chỉ định.
4. IF Biên_Tập_Viên chọn một nguồn ngoài Danh_Mục_Nguồn khi tạo Trích_Dẫn, THEN THE Backend_API SHALL từ chối lưu Trích_Dẫn.
5. WHEN Biên_Tập_Viên nhập một đường dẫn có tên miền thuộc danh sách chặn (ví dụ wikipedia.org, blog cá nhân, mạng xã hội) làm nguồn, THE Backend_API SHALL từ chối nguồn và hiển thị thông báo "Chỉ dùng làm đầu mối tra cứu, cần trích từ tài liệu gốc".

### Requirement 2: Trích dẫn bắt buộc cho dữ kiện lịch sử

**User Story:** Là Biên_Tập_Viên, tôi muốn hệ thống bắt buộc trích dẫn đầy đủ, để không có dữ kiện nào được xuất bản mà thiếu căn cứ.

#### Acceptance Criteria

1. IF một Trích_Dẫn thiếu Nguồn_Tin_Cậy hoặc thiếu số trang, số mục hoặc mã văn bản, THEN THE Backend_API SHALL từ chối lưu Trích_Dẫn và liệt kê các trường còn thiếu.
2. WHEN Biên*Tập_Viên gửi một Sự_Kiện, Nhân_Vật, Địa*Điểm hoặc Quan*Hệ_Nhân_Quả sang Chờ_Thẩm*Định, THE Backend_API SHALL kiểm tra nội dung có ít nhất một Trích_Dẫn thuộc Cấp_Nguồn 1 hoặc Cấp_Nguồn 2.
3. WHEN Biên*Tập_Viên gửi một Mốc_Thời_Gian hoặc số liệu (quân số, thương vong) sang Chờ_Thẩm*Định, THE Backend_API SHALL kiểm tra trường đó có ít nhất hai Trích_Dẫn từ hai Nguồn_Tin_Cậy khác nhau, trong đó ít nhất một nguồn thuộc Cấp_Nguồn 1.
4. IF một nội dung chỉ có Trích_Dẫn thuộc Cấp_Nguồn 3, THEN THE Backend_API SHALL từ chối chuyển trạng thái và trả về thông báo nêu rõ thiếu nguồn Cấp 1 hoặc Cấp 2.
5. WHEN một Câu*Hỏi được gửi sang Chờ_Thẩm*Định, THE Backend_API SHALL kiểm tra phần giải thích đáp án có ít nhất một Trích_Dẫn và Câu_Hỏi gắn với một Sự_Kiện có Trạng_Thái_Nội_Dung là Đã_Xuất_Bản.

### Requirement 3: Ghi nhận dị biệt giữa các nguồn

**User Story:** Là Người_Chơi, tôi muốn biết khi các sử liệu ghi khác nhau, để hiểu lịch sử là kết quả của nghiên cứu chứ không phải một đáp án duy nhất cần học thuộc.

#### Acceptance Criteria

1. WHERE các Nguồn_Tin_Cậy ghi nhận khác nhau về một trường dữ kiện, THE Content_Store SHALL lưu Ghi_Chú_Sử_Học gồm từng phương án, Trích_Dẫn của từng phương án và phương án được dùng làm mặc định trong lối chơi.
2. WHEN Người_Chơi xem một Sự_Kiện có Ghi_Chú_Sử_Học, THE Game_Client SHALL hiển thị biểu tượng "Có nhiều ghi chép" và cho phép mở nội dung Ghi_Chú_Sử_Học.
3. IF một Câu*Hỏi kiểm tra trường dữ kiện có Ghi_Chú_Sử_Học, THEN THE Backend_API SHALL yêu cầu Người_Thẩm*Định xác nhận đáp án theo phương án mặc định trước khi xuất bản Câu_Hỏi.
4. WHERE một Sự_Kiện có Mốc_Thời_Gian theo âm lịch trong nguồn gốc, THE Content_Store SHALL lưu cả ngày âm lịch gốc, ngày dương lịch quy đổi và Trích_Dẫn của phương pháp quy đổi.

### Requirement 4: Tách biệt nội dung hư cấu

**User Story:** Là Người*Thẩm*Định, tôi muốn nội dung hư cấu phục vụ lối chơi được đánh dấu rõ, để Người_Chơi không nhầm lời thoại sáng tác với sử liệu.

#### Acceptance Criteria

1. THE Content_Store SHALL lưu mỗi Hội_Thoại, Mảnh_Ghép và lời dẫn với cờ phân loại "dữ kiện lịch sử" hoặc "hư cấu".
2. WHEN Game_Client hiển thị nội dung có Nhãn_Hư_Cấu, THE Game_Client SHALL hiển thị nhãn "Lời dẫn hư cấu" cạnh nội dung đó.
3. WHEN một Hội_Thoại trích nguyên văn lời của Nhân_Vật lịch sử (ví dụ Hịch tướng sĩ, Bình Ngô đại cáo, Tuyên ngôn Độc lập), THE Backend_API SHALL yêu cầu đoạn trích có Trích_Dẫn tới văn bản gốc hoặc bản dịch thuộc Cấp_Nguồn 1.
4. IF một Câu*Hỏi lấy đáp án từ nội dung có Nhãn_Hư_Cấu, THEN THE Backend_API SHALL từ chối gửi Câu_Hỏi sang Chờ_Thẩm*Định.

### Requirement 5: Quy trình thẩm định và xuất bản

**User Story:** Là Người*Thẩm*Định, tôi muốn duyệt nội dung trước khi xuất bản, để Người_Chơi chỉ thấy dữ liệu đã được kiểm chứng.

#### Acceptance Criteria

1. THE Backend_API SHALL đưa vào Content_Bundle các nội dung có Trạng_Thái_Nội_Dung là Đã_Xuất_Bản.
2. WHEN Người*Thẩm*Định phê duyệt nội dung ở trạng thái Chờ*Thẩm*Định, THE Backend*API SHALL chuyển nội dung sang Đã_Xuất_Bản và ghi mã Người_Thẩm*Định, thời điểm phê duyệt và danh sách Trích_Dẫn đã kiểm tra.
3. IF Người*Thẩm*Định là tác giả hoặc người chỉnh sửa gần nhất của nội dung, THEN THE Backend_API SHALL từ chối thao tác phê duyệt.
4. WHEN Người*Thẩm*Định từ chối nội dung, THE Backend_API SHALL chuyển nội dung về Bản_Nháp, lưu lý do từ chối và thông báo cho tác giả trong Admin_Portal.
5. WHEN nội dung Đã_Xuất_Bản được chỉnh sửa, THE Backend_API SHALL giữ phiên bản Đã_Xuất_Bản hiện hành trong Content_Bundle cho đến khi phiên bản mới được phê duyệt.

### Requirement 6: Lịch sử phiên bản và kiểm toán nội dung

**User Story:** Là Người*Thẩm*Định, tôi muốn xem ai đã sửa gì và khi nào, để truy vết sai sót và khôi phục khi cần.

#### Acceptance Criteria

1. WHEN một nội dung được lưu, THE Backend_API SHALL tạo một bản ghi phiên bản gồm toàn bộ giá trị trường, mã người sửa và thời điểm.
2. WHEN Người*Thẩm*Định chọn hai phiên bản của một nội dung, THE Admin_Portal SHALL hiển thị khác biệt giữa hai phiên bản theo từng trường.
3. WHEN Người*Thẩm*Định khôi phục một phiên bản cũ, THE Backend*API SHALL tạo phiên bản mới với giá trị của phiên bản cũ ở trạng thái Chờ_Thẩm*Định.
4. THE Backend_API SHALL lưu bản ghi phiên bản tối thiểu 3 năm.

### Requirement 7: Báo cáo sai sót nội dung

**User Story:** Là Người_Chơi hoặc Giáo_Viên, tôi muốn báo cáo nội dung nghi sai, để đội ngũ biên tập kiểm tra và sửa.

#### Acceptance Criteria

1. WHEN Người_Chơi chọn "Báo sai sót" trên một Sự_Kiện, Mảnh_Ghép hoặc Câu_Hỏi, THE Game_Client SHALL cho phép nhập mô tả tối đa 1000 ký tự và nguồn đối chứng tùy chọn.
2. WHEN Backend_API nhận một Báo_Cáo_Sai_Sót, THE Backend_API SHALL lưu báo cáo ở trạng thái Mới và hiển thị báo cáo trong hàng đợi của Admin_Portal.
3. WHEN Người*Thẩm*Định đánh dấu Báo_Cáo_Sai_Sót là "Xác nhận sai", THE Backend_API SHALL tạm ẩn Câu_Hỏi liên quan khỏi Content_Bundle cho đến khi bản sửa được phê duyệt.
4. WHEN Báo_Cáo_Sai_Sót được xử lý xong, THE Backend_API SHALL gửi thông báo kết quả cho người báo cáo trong Game_Client.

### Requirement 8: Bản quyền media

**User Story:** Là Quản_Trị_Viên, tôi muốn mọi hình ảnh và âm thanh có giấy phép rõ ràng, để sản phẩm triển khai công khai mà không vi phạm bản quyền.

#### Acceptance Criteria

1. WHEN Biên_Tập_Viên tải một tệp media lên Media_Store, THE Backend_API SHALL yêu cầu Giấy_Phép_Media gồm chủ sở hữu, loại giấy phép và đường dẫn nguồn.
2. IF loại giấy phép của tệp media nằm ngoài danh sách được phép (phạm vi công cộng, CC0, CC BY, CC BY-SA, tự sản xuất, có văn bản cho phép), THEN THE Backend_API SHALL từ chối lưu tệp.
3. WHEN Game_Client hiển thị một tệp media có giấy phép yêu cầu ghi công, THE Game_Client SHALL hiển thị dòng ghi công gồm tên tác giả và loại giấy phép.
4. THE Game_Client SHALL cung cấp màn hình "Nguồn và ghi công" liệt kê toàn bộ Nguồn_Tin_Cậy và Giấy_Phép_Media được dùng trong game.

### B. Lối chơi

### Requirement 9: Cấu trúc màn chơi và progression

**User Story:** Là Người_Chơi, tôi muốn các màn chơi mở khóa theo trình tự, để tiếp cận lịch sử từ bối cảnh đến diễn biến và kết quả.

#### Acceptance Criteria

1. THE Content*Store SHALL lưu mỗi Màn_Chơi với tên, giai đoạn lịch sử, mô tả bối cảnh, danh sách Nhiệm_Vụ có thứ tự, danh sách Địa*Điểm và Điều_Kiện_Mở_Khóa.
2. WHEN Người_Chơi mở game lần đầu sau khi đăng ký, THE Game_Client SHALL mở khóa Màn 1 và Nhiệm_Vụ đầu tiên của Màn 1.
3. WHEN Người_Chơi hoàn thành mọi Nhiệm_Vụ bắt buộc và Dòng_Thời_Gian của một Màn_Chơi, THE Backend_API SHALL đánh dấu Màn_Chơi hoàn thành và mở khóa Màn_Chơi kế tiếp.
4. WHILE một Màn_Chơi chưa được mở khóa, THE Game_Client SHALL hiển thị Màn_Chơi ở trạng thái khóa kèm Điều_Kiện_Mở_Khóa còn thiếu.
5. WHERE một Nhiệm_Vụ được cấu hình là nhiệm vụ phụ, THE Game_Client SHALL cho phép Người_Chơi hoàn thành Màn_Chơi mà không cần hoàn thành Nhiệm_Vụ đó.

### Requirement 10: Bản đồ Việt Nam tương tác

**User Story:** Là Người_Chơi, tôi muốn di chuyển trên bản đồ Việt Nam để khám phá các địa điểm lịch sử, để hiểu bối cảnh không gian của sự kiện.

#### Acceptance Criteria

1. WHEN Người*Chơi mở một Màn_Chơi, THE Game_Client SHALL hiển thị Bản*Đồ với các Địa_Điểm của Màn_Chơi trong vòng 3 giây trên kết nối 10 Mbps.
2. THE Game*Client SHALL hiển thị Bản*Đồ Việt Nam bao gồm quần đảo Hoàng Sa và quần đảo Trường Sa thuộc chủ quyền Việt Nam.
3. WHEN Người*Chơi chọn một Địa*Điểm đã mở khóa, THE Game_Client SHALL hiển thị tên lịch sử theo giai đoạn của Màn_Chơi, tên hành chính hiện nay và danh sách Sự_Kiện liên quan.
4. THE Game*Client SHALL hỗ trợ phóng to trong khoảng 1x đến 4x, kéo Bản*Đồ và chọn Địa_Điểm bằng chuột, bàn phím và cảm ứng.
5. WHERE Màn*Chơi có Lớp_Bản*Đồ, THE Game*Client SHALL cho phép Người_Chơi bật hoặc tắt từng Lớp_Bản*Đồ và hiển thị Trích_Dẫn của nguồn bản đồ.

### Requirement 11: Di chuyển nhân vật trên bản đồ

**User Story:** Là Người_Chơi, tôi muốn điều khiển nhân vật đi đến các địa điểm, để có cảm giác đang thực hiện một chuyến điều tra.

#### Acceptance Criteria

1. WHEN Người*Chơi chọn một Địa*Điểm đã mở khóa làm đích, THE Game*Client SHALL di chuyển biểu tượng Người_Chơi theo tuyến đường cấu hình giữa các Địa*Điểm.
2. WHEN biểu tượng Người*Chơi đến một Địa*Điểm, THE Game*Client SHALL hiển thị các Mảnh_Ghép, Hội_Thoại và Mục_Tiêu khả dụng tại Địa*Điểm đó.
3. IF Người*Chơi chọn một Địa*Điểm bị khóa làm đích, THEN THE Game*Client SHALL hiển thị Điều_Kiện_Mở_Khóa của Địa*Điểm và giữ nguyên vị trí biểu tượng Người_Chơi.
4. THE Game*Client SHALL duy trì tốc độ khung hình tối thiểu 30 FPS khi di chuyển trên Bản*Đồ trên máy tính có trình duyệt Chrome phiên bản phát hành trong 2 năm gần nhất.

### Requirement 12: Nhiệm vụ điều tra

**User Story:** Là Người_Chơi, tôi muốn nhận nhiệm vụ điều tra với các mục tiêu rõ ràng, để học lịch sử qua quá trình khám phá tư liệu.

#### Acceptance Criteria

1. WHEN Người*Chơi nhận một Nhiệm_Vụ, THE Game_Client SHALL hiển thị câu hỏi điều tra trung tâm (ví dụ "Vì sao quân Nguyên thua ở Bạch Đằng năm 1288?"), danh sách Mục_Tiêu và Địa*Điểm liên quan.
2. WHILE một Nhiệm_Vụ đang hoạt động, THE Game_Client SHALL hiển thị tiến độ từng Mục_Tiêu trong khung theo dõi nhiệm vụ.
3. WHEN Người_Chơi hoàn thành một Mục_Tiêu, THE Game_Client SHALL cập nhật tiến độ và hiển thị Mục_Tiêu kế tiếp trong vòng 500 ms.
4. WHEN Người_Chơi hoàn thành mọi Mục_Tiêu của một Nhiệm_Vụ, THE Game_Client SHALL hiển thị bản tổng kết gồm Sự_Kiện đã mở khóa, câu trả lời cho câu hỏi điều tra trung tâm kèm Trích_Dẫn và Điểm_Kiến_Thức nhận được.
5. WHEN Người*Chơi hoàn thành một Nhiệm_Vụ, THE Game_Client SHALL mở khóa các Nhiệm_Vụ, Địa*Điểm và Sự_Kiện theo Điều_Kiện_Mở_Khóa của Màn_Chơi.

### Requirement 13: Thu thập mảnh ghép tư liệu

**User Story:** Là Người_Chơi, tôi muốn thu thập mảnh ghép tư liệu thật, để tiếp xúc trực tiếp với sử liệu.

#### Acceptance Criteria

1. WHEN Người*Chơi chọn một Mảnh_Ghép tại Địa*Điểm hiện tại, THE Game*Client SHALL thêm Mảnh_Ghép vào Sổ_Tay*Điều_Tra và hiển thị nội dung tư liệu kèm Trích_Dẫn.
2. WHERE Mảnh_Ghép là trích đoạn văn bản Hán Nôm, THE Game_Client SHALL hiển thị bản dịch tiếng Việt và tên bản dịch được trích dẫn.
3. WHEN Người_Chơi thu thập đủ Mảnh_Ghép của một Sự_Kiện, THE Game_Client SHALL ghép các Mảnh_Ghép thành thẻ Sự_Kiện hoàn chỉnh và mở khóa thẻ Sự_Kiện đó.
4. IF Người*Chơi đã thu thập một Mảnh_Ghép, THEN THE Game_Client SHALL hiển thị Mảnh_Ghép đó ở trạng thái "đã thu thập" tại Địa*Điểm.

### Requirement 14: Hội thoại với nhân vật

**User Story:** Là Người_Chơi, tôi muốn trò chuyện với nhân vật để nhận manh mối, để câu chuyện lịch sử trở nên sinh động.

#### Acceptance Criteria

1. WHEN Người*Chơi tương tác với một Nhân_Vật tại Địa*Điểm, THE Game_Client SHALL hiển thị Hội_Thoại theo từng câu với tên người nói và chân dung.
2. WHERE Hội_Thoại có lựa chọn, THE Game_Client SHALL hiển thị tối đa 4 lựa chọn và chuyển đến nhánh Hội_Thoại tương ứng.
3. WHEN Người*Chơi hoàn thành một Hội_Thoại có gắn manh mối, THE Game_Client SHALL ghi manh mối vào Sổ_Tay*Điều_Tra.
4. WHERE chân dung Nhân_Vật là tranh minh họa sáng tác, THE Game_Client SHALL hiển thị nhãn "Tranh minh họa" trên chân dung.

### Requirement 15: Dòng thời gian sự kiện

**User Story:** Là Người_Chơi, tôi muốn sắp xếp các sự kiện vào dòng thời gian, để nắm trình tự và quan hệ nhân quả.

#### Acceptance Criteria

1. WHEN Người_Chơi mở khóa một thẻ Sự_Kiện, THE Game_Client SHALL thêm thẻ vào khu vực chờ sắp xếp của Dòng_Thời_Gian.
2. WHEN Người_Chơi kéo thả một thẻ Sự_Kiện vào Dòng_Thời_Gian, THE Game_Client SHALL kiểm tra thứ tự của thẻ so với các thẻ đã đặt dựa trên Mốc_Thời_Gian.
3. IF Người_Chơi đặt thẻ sai thứ tự, THEN THE Game_Client SHALL trả thẻ về khu vực chờ và hiển thị một gợi ý dựa trên Quan_Hệ_Nhân_Quả của Sự_Kiện.
4. WHERE hai Sự_Kiện có Mốc_Thời_Gian trùng nhau ở Độ_Chính_Xác thấp hơn, THE Game_Client SHALL chấp nhận mọi thứ tự giữa hai Sự_Kiện đó.
5. WHEN Người_Chơi đặt đúng tất cả thẻ Sự_Kiện của Màn_Chơi, THE Game_Client SHALL hiển thị Dòng_Thời_Gian hoàn chỉnh với mũi tên Quan_Hệ_Nhân_Quả giữa các Sự_Kiện.
6. WHEN Người*Chơi chọn một thẻ Sự_Kiện trên Dòng_Thời_Gian, THE Game_Client SHALL hiển thị mô tả, ý nghĩa, Nhân_Vật liên quan, Địa*Điểm, Ghi_Chú_Sử_Học nếu có và danh sách Trích_Dẫn.

### Requirement 16: Câu hỏi kiến thức

**User Story:** Là Người_Chơi, tôi muốn trả lời nhiều dạng câu hỏi, để kiểm tra mức độ hiểu chứ không chỉ ghi nhớ.

#### Acceptance Criteria

1. THE Game_Client SHALL hỗ trợ mọi Loại_Câu_Hỏi định nghĩa trong Glossary.
2. WHEN Người_Chơi gửi đáp án, THE Backend_API SHALL chấm đáp án phía máy chủ và trả về kết quả, đáp án đúng, giải thích và Trích_Dẫn trong vòng 1 giây.
3. THE Content_Bundle SHALL chứa nội dung Câu_Hỏi và các phương án nhưng loại trừ đáp án đúng.
4. THE Content_Store SHALL phân bổ Câu_Hỏi của mỗi Màn_Chơi với tối thiểu 30% ở Độ_Khó 2 và tối thiểu 20% ở Độ_Khó 3.
5. WHEN Game_Client hiển thị một Câu_Hỏi trắc nghiệm, THE Game_Client SHALL xáo trộn thứ tự các phương án.

### Requirement 17: Sổ tay điều tra

**User Story:** Là Người_Chơi, tôi muốn xem lại mọi tư liệu đã thu thập ở một nơi, để tra cứu khi giải nhiệm vụ.

#### Acceptance Criteria

1. WHEN Người*Chơi mở Sổ_Tay*Điều*Tra, THE Game_Client SHALL hiển thị các tab Sự_Kiện, Nhân_Vật, Địa*Điểm, Mảnh_Ghép và Manh mối đã mở khóa.
2. WHEN Người*Chơi tìm kiếm trong Sổ_Tay*Điều_Tra, THE Game_Client SHALL lọc kết quả theo tên, không phân biệt dấu và chữ hoa thường.
3. WHEN Người*Chơi chọn một mục trong Sổ_Tay*Điều_Tra, THE Game_Client SHALL hiển thị chi tiết mục và danh sách Trích_Dẫn.
4. WHILE một mục chưa được mở khóa, THE Game_Client SHALL hiển thị mục dưới dạng ô ẩn với dấu "?".

### C. Điểm số, ôn tập, thành tích

### Requirement 18: Điểm kiến thức

**User Story:** Là Người_Chơi, tôi muốn nhận điểm công bằng theo mức độ hiểu bài, để thấy được tiến bộ của mình.

#### Acceptance Criteria

1. WHEN Người_Chơi trả lời đúng một Câu_Hỏi ở lần thử đầu tiên, THE Backend_API SHALL cộng 10 điểm cho Độ_Khó 1, 20 điểm cho Độ_Khó 2 và 30 điểm cho Độ_Khó 3.
2. WHEN Người_Chơi trả lời đúng một Câu_Hỏi ở lần thử thứ hai, THE Backend_API SHALL cộng 50% số điểm của Độ_Khó tương ứng, làm tròn xuống.
3. WHEN Người_Chơi trả lời đúng một Câu_Hỏi từ lần thử thứ ba trở đi, THE Backend_API SHALL cộng 0 điểm và ghi nhận Câu_Hỏi vào danh sách cần ôn tập.
4. WHEN Người_Chơi hoàn thành một Dòng_Thời_Gian với tối đa 2 lần đặt sai, THE Backend_API SHALL cộng 50 điểm thưởng.
5. IF Backend_API nhận đáp án cho một Câu_Hỏi đã được tính điểm cho Người_Chơi, THEN THE Backend_API SHALL trả kết quả chấm và giữ nguyên tổng Điểm_Kiến_Thức.

### Requirement 19: Lưu và đồng bộ tiến trình

**User Story:** Là Người_Chơi, tôi muốn tiến trình được lưu tự động, để chơi tiếp trên bất kỳ thiết bị nào.

#### Acceptance Criteria

1. WHEN Người_Chơi hoàn thành một Mục_Tiêu, THE Game_Client SHALL gửi tiến trình lên Backend_API trong vòng 2 giây.
2. WHEN Người*Chơi đăng nhập, THE Game_Client SHALL khôi phục tiến trình gần nhất gồm Màn_Chơi, Nhiệm_Vụ, Mục_Tiêu, Mảnh_Ghép, vị trí trên Bản*Đồ và trạng thái Dòng_Thời_Gian.
3. IF Game_Client mất kết nối khi gửi tiến trình, THEN THE Game_Client SHALL lưu tiến trình vào IndexedDB của trình duyệt và gửi lại khi kết nối được khôi phục.
4. IF tiến trình cục bộ và tiến trình trên Backend_API xung đột, THEN THE Backend_API SHALL hợp nhất theo hợp của các Mục_Tiêu đã hoàn thành.

### Requirement 20: Chế độ ôn tập sau màn

**User Story:** Là Người_Chơi, tôi muốn ôn tập sau mỗi màn, để ghi nhớ lâu hơn thay vì học thuộc lòng.

#### Acceptance Criteria

1. WHEN Người*Chơi hoàn thành một Màn_Chơi, THE Game_Client SHALL đề xuất phiên Chế*Độ_Ôn_Tập gồm tối đa 10 Câu_Hỏi của Màn_Chơi đó.
2. THE Backend*API SHALL chọn Câu_Hỏi cho Chế*Độ_Ôn_Tập theo thứ tự ưu tiên: trả lời sai, trả lời đúng sau nhiều lần thử, lâu chưa ôn nhất.
3. WHEN Người*Chơi trả lời đúng một Câu_Hỏi trong Chế*Độ_Ôn_Tập, THE Backend_API SHALL tăng khoảng cách lần ôn kế tiếp của Câu_Hỏi theo chuỗi 1, 3, 7, 14, 30 ngày.
4. WHEN Người*Chơi trả lời sai một Câu_Hỏi trong Chế*Độ_Ôn_Tập, THE Backend_API SHALL đặt lại khoảng cách lần ôn kế tiếp của Câu_Hỏi về 1 ngày.
5. WHEN Người*Chơi kết thúc phiên Chế*Độ*Ôn_Tập, THE Game_Client SHALL hiển thị tỷ lệ trả lời đúng và danh sách Sự_Kiện cần xem lại kèm liên kết mở Sổ_Tay*Điều_Tra.
6. THE Backend*API SHALL ghi điểm Chế*Độ_Ôn_Tập vào một bộ đếm riêng, tách khỏi Điểm_Kiến_Thức dùng cho Bảng_Xếp_Hạng.

### Requirement 21: Huy hiệu thành tích

**User Story:** Là Người_Chơi, tôi muốn nhận huy hiệu khi đạt cột mốc, để có thêm động lực khám phá.

#### Acceptance Criteria

1. THE Content_Store SHALL lưu mỗi Huy_Hiệu với tên, mô tả, hình ảnh và điều kiện đạt được.
2. WHEN Người_Chơi đạt điều kiện của một Huy_Hiệu, THE Backend_API SHALL trao Huy_Hiệu và Game_Client SHALL hiển thị thông báo trong vòng 2 giây.
3. WHEN Người_Chơi mở trang hồ sơ, THE Game_Client SHALL hiển thị Huy_Hiệu đã đạt và Huy_Hiệu chưa đạt kèm điều kiện.

### Requirement 22: Bảng xếp hạng

**User Story:** Là Người_Chơi, tôi muốn xem bảng xếp hạng, để có động lực học và so sánh với bạn bè.

#### Acceptance Criteria

1. WHEN Người_Chơi mở Bảng_Xếp_Hạng, THE Game_Client SHALL hiển thị 100 Người_Chơi có Điểm_Kiến_Thức cao nhất và thứ hạng của Người_Chơi hiện tại.
2. THE Backend_API SHALL cung cấp Bảng_Xếp_Hạng theo tuần (bắt đầu 00:00 thứ Hai giờ Việt Nam), theo tháng, toàn thời gian và theo Lớp_Học.
3. THE Backend_API SHALL trả về Bảng_Xếp_Hạng trong vòng 500 ms với 10.000 Người_Chơi.
4. WHEN Bảng_Xếp_Hạng hiển thị một Người_Chơi, THE Game_Client SHALL hiển thị tên hiển thị và ảnh đại diện, loại trừ email.
5. IF tần suất gửi đáp án của một Người_Chơi vượt 30 yêu cầu mỗi phút, THEN THE Backend_API SHALL từ chối yêu cầu với mã lỗi 429.

### D. Người dùng, bảo mật, lớp học

### Requirement 23: Đăng ký và đăng nhập

**User Story:** Là người dùng, tôi muốn đăng ký và đăng nhập an toàn, để bảo vệ tài khoản và tiến trình.

#### Acceptance Criteria

1. WHEN Khách đăng ký bằng email và mật khẩu, THE Backend_API SHALL kiểm tra mật khẩu dài tối thiểu 8 ký tự, tạo tài khoản vai trò Người_Chơi và gửi email xác minh.
2. THE Backend_API SHALL lưu mật khẩu dưới dạng băm bằng thuật toán bcrypt hoặc argon2.
3. WHEN người dùng đăng nhập với thông tin hợp lệ, THE Backend_API SHALL cấp access token hết hạn sau 15 phút và refresh token hết hạn sau 7 ngày.
4. IF người dùng nhập sai mật khẩu 5 lần trong 15 phút, THEN THE Backend_API SHALL tạm khóa đăng nhập tài khoản trong 15 phút.
5. WHERE người dùng chọn đăng nhập bằng Google, THE Backend_API SHALL xác thực qua OAuth 2.0 và liên kết với tài khoản có cùng email đã xác minh.
6. WHEN người dùng yêu cầu đặt lại mật khẩu, THE Backend_API SHALL gửi liên kết đặt lại có hiệu lực 30 phút và sử dụng một lần.

### Requirement 24: Phân quyền theo vai trò

**User Story:** Là Quản_Trị_Viên, tôi muốn mỗi vai trò chỉ truy cập đúng chức năng, để bảo vệ nội dung và dữ liệu người dùng.

#### Acceptance Criteria

1. THE Backend*API SHALL áp dụng ma trận quyền: Khách xem trang giới thiệu; Người_Chơi chơi game và gửi Báo_Cáo_Sai_Sót; Giáo_Viên thêm quyền quản lý Lớp_Học; Biên_Tập_Viên thêm quyền soạn nội dung; Người_Thẩm*Định thêm quyền phê duyệt nội dung và nguồn; Quản_Trị_Viên có toàn quyền.
2. IF một yêu cầu thiếu access token hợp lệ cho endpoint yêu cầu đăng nhập, THEN THE Backend_API SHALL trả về mã lỗi 401.
3. IF một yêu cầu vượt quyền của vai trò hiện tại, THEN THE Backend_API SHALL trả về mã lỗi 403.
4. WHEN Khách truy cập Admin_Portal, THE Admin_Portal SHALL chuyển hướng Khách đến trang đăng nhập.

### Requirement 25: Quản lý người dùng

**User Story:** Là Quản_Trị_Viên, tôi muốn quản lý tài khoản và vai trò, để vận hành hệ thống an toàn.

#### Acceptance Criteria

1. WHEN Quản_Trị_Viên tìm kiếm người dùng theo email hoặc tên hiển thị, THE Admin_Portal SHALL hiển thị kết quả phân trang tối đa 50 bản ghi mỗi trang, có lọc theo vai trò và trạng thái.
2. WHEN Quản_Trị_Viên thay đổi vai trò của người dùng, THE Backend_API SHALL ghi nhật ký kiểm toán gồm người thực hiện, vai trò cũ, vai trò mới và thời điểm.
3. WHEN Quản_Trị_Viên vô hiệu hóa một tài khoản, THE Backend_API SHALL thu hồi mọi refresh token của tài khoản và ẩn tài khoản khỏi Bảng_Xếp_Hạng.
4. IF Quản_Trị_Viên gỡ vai trò của Quản_Trị_Viên cuối cùng đang hoạt động, THEN THE Backend_API SHALL từ chối thao tác.
5. WHEN người dùng yêu cầu xóa tài khoản, THE Backend_API SHALL xóa dữ liệu cá nhân trong vòng 30 ngày và giữ Sự_Kiện_Phân_Tích ở dạng ẩn danh.

### Requirement 26: Lớp học cho giáo viên

**User Story:** Là Giáo_Viên, tôi muốn tạo lớp và theo dõi tiến độ học sinh, để dùng game trong giờ học lịch sử.

#### Acceptance Criteria

1. WHEN Giáo_Viên tạo một Lớp_Học, THE Backend_API SHALL sinh mã tham gia gồm 6 ký tự chữ và số.
2. WHEN Người_Chơi nhập mã tham gia hợp lệ, THE Backend_API SHALL thêm Người_Chơi vào Lớp_Học.
3. WHEN Giáo_Viên mở trang Lớp_Học, THE Admin_Portal SHALL hiển thị tiến độ Màn_Chơi, Điểm_Kiến_Thức và tỷ lệ trả lời đúng theo Sự_Kiện của từng thành viên.
4. WHEN Giáo_Viên xuất báo cáo Lớp_Học, THE Admin_Portal SHALL tạo tệp CSV mã hóa UTF-8 chứa dữ liệu tiến độ của các thành viên.
5. IF Giáo_Viên truy cập dữ liệu của Người_Chơi ngoài Lớp_Học của mình, THEN THE Backend_API SHALL trả về mã lỗi 403.

### Requirement 27: Bảo vệ dữ liệu cá nhân

**User Story:** Là Người_Chơi, tôi muốn dữ liệu cá nhân được bảo vệ, để yên tâm sử dụng, kể cả khi là học sinh.

#### Acceptance Criteria

1. WHEN Khách đăng ký, THE Game_Client SHALL hiển thị chính sách quyền riêng tư và yêu cầu Khách xác nhận đồng ý trước khi tạo tài khoản.
2. WHERE Khách khai báo dưới 16 tuổi, THE Backend_API SHALL yêu cầu email xác nhận của phụ huynh hoặc Giáo_Viên trước khi kích hoạt tài khoản.
3. THE Backend_API SHALL thu thập các trường cá nhân: email, tên hiển thị, năm sinh và ảnh đại diện tùy chọn.
4. WHEN người dùng yêu cầu xuất dữ liệu cá nhân, THE Backend_API SHALL tạo tệp JSON chứa dữ liệu của người dùng trong vòng 72 giờ.

### E. Công cụ biên tập, phân tích, giao diện

### Requirement 28: Công cụ soạn nội dung trong Admin Portal

**User Story:** Là Biên_Tập_Viên, tôi muốn soạn sự kiện, nhiệm vụ và câu hỏi qua giao diện web, để không phải sửa mã nguồn khi thêm nội dung.

#### Acceptance Criteria

1. THE Admin*Portal SHALL cung cấp biểu mẫu tạo và sửa Nguồn_Tin_Cậy, Sự_Kiện, Nhân_Vật, Địa*Điểm, Quan_Hệ_Nhân_Quả, Mảnh_Ghép, Hội_Thoại, Câu_Hỏi, Nhiệm_Vụ, Màn_Chơi và Huy_Hiệu.
2. WHEN Biên*Tập_Viên tạo một Địa*Điểm, THE Admin_Portal SHALL cho phép chọn tọa độ bằng cách nhấp trên bản đồ hoặc nhập vĩ độ và kinh độ.
3. WHEN Biên_Tập_Viên lưu một biểu mẫu có trường bắt buộc còn trống, THE Admin_Portal SHALL đánh dấu từng trường còn trống và giữ nguyên dữ liệu đã nhập.
4. WHEN Biên_Tập_Viên chọn "Xem trước", THE Admin_Portal SHALL hiển thị nội dung theo bố cục của Game_Client.
5. WHEN Biên_Tập_Viên nhập dữ liệu hàng loạt từ tệp CSV hoặc JSON theo mẫu, THE Backend_API SHALL kiểm tra từng dòng, nhập các dòng hợp lệ ở trạng thái Bản_Nháp và trả về báo cáo lỗi của các dòng không hợp lệ.

### Requirement 29: Xuất bản gói nội dung

**User Story:** Là Người*Thẩm*Định, tôi muốn xuất bản nội dung theo từng màn, để Người_Chơi nhận nội dung nhất quán.

#### Acceptance Criteria

1. WHEN Người*Thẩm*Định chọn "Xuất bản Màn_Chơi", THE Backend_API SHALL kiểm tra mọi Nhiệm_Vụ, Sự_Kiện, Câu_Hỏi và Mảnh_Ghép tham chiếu trong Màn_Chơi đều ở trạng thái Đã_Xuất_Bản.
2. IF Màn_Chơi tham chiếu nội dung chưa ở trạng thái Đã_Xuất_Bản, THEN THE Backend_API SHALL từ chối xuất bản và liệt kê nội dung còn thiếu.
3. WHEN Màn_Chơi được xuất bản, THE Backend_API SHALL tạo Content_Bundle mới có số phiên bản tăng dần.
4. WHEN Game_Client khởi động, THE Game_Client SHALL so sánh phiên bản Content_Bundle đã lưu cục bộ với phiên bản trên Backend_API và tải bản mới khi phiên bản khác nhau.

### Requirement 30: Phân tích học tập

**User Story:** Là Quản_Trị_Viên, tôi muốn xem thống kê hành vi chơi, để cải thiện nội dung và độ khó.

#### Acceptance Criteria

1. WHEN Người_Chơi bắt đầu Nhiệm_Vụ, hoàn thành Mục_Tiêu, trả lời Câu_Hỏi, đặt thẻ Dòng_Thời_Gian hoặc hoàn thành Màn_Chơi, THE Game_Client SHALL gửi Sự_Kiện_Phân_Tích tới Backend_API.
2. WHEN Quản_Trị_Viên mở trang thống kê, THE Admin_Portal SHALL hiển thị số Người_Chơi hoạt động theo ngày, tỷ lệ hoàn thành và thời gian trung bình của từng Màn_Chơi, và tỷ lệ trả lời đúng của từng Câu_Hỏi.
3. THE Admin_Portal SHALL đánh dấu Câu_Hỏi có tỷ lệ trả lời đúng dưới 30% hoặc trên 95% sau ít nhất 50 lượt trả lời.
4. THE Admin_Portal SHALL hiển thị phễu rời bỏ theo Nhiệm_Vụ của mỗi Màn_Chơi.
5. THE Backend_API SHALL lưu Sự_Kiện_Phân_Tích với mã Người_Chơi ẩn danh hóa, tách khỏi email và tên hiển thị.

### Requirement 31: Giao diện và trải nghiệm

**User Story:** Là Người_Chơi, tôi muốn giao diện tiếng Việt rõ ràng, dễ dùng trên máy tính và điện thoại, để tập trung vào việc học.

#### Acceptance Criteria

1. THE Game_Client SHALL hiển thị văn bản tiếng Việt có dấu bằng phông chữ hỗ trợ đầy đủ Unicode tiếng Việt dựng sẵn (NFC).
2. THE Game_Client SHALL hiển thị bố cục phù hợp ở độ rộng màn hình từ 360 px đến 1920 px theo cả chiều ngang và chiều dọc.
3. THE Game_Client SHALL cung cấp cài đặt cỡ chữ 3 mức, âm lượng nhạc và hiệu ứng riêng biệt, và tỷ lệ tương phản văn bản tối thiểu 4.5:1.
4. WHEN Người*Chơi mở game lần đầu, THE Game_Client SHALL chạy phần hướng dẫn tương tác về Bản*Đồ, Nhiệm*Vụ, Sổ_Tay*Điều_Tra và Dòng_Thời_Gian, có tùy chọn bỏ qua.
5. THE Game_Client SHALL cho phép thực hiện mọi thao tác chính bằng bàn phím, gồm di chuyển tiêu điểm, chọn và kéo thả thẻ Dòng_Thời_Gian.
6. WHEN Game_Client tải lần đầu, THE Game_Client SHALL hiển thị màn hình tải có thanh tiến độ và hoàn tất tải trong vòng 15 giây trên kết nối 10 Mbps.

### Requirement 32: Trang web giới thiệu

**User Story:** Là Khách, tôi muốn xem giới thiệu game trước khi đăng ký, để biết game dạy những gì và dựa trên nguồn nào.

#### Acceptance Criteria

1. WHEN Khách truy cập URL gốc, THE Game_Client SHALL hiển thị trang giới thiệu gồm mô tả game, danh sách Màn_Chơi, nút đăng ký, nút đăng nhập và liên kết "Nguồn và ghi công".
2. THE Game*Client SHALL hiển thị trang "Phương pháp biên soạn" mô tả Cấp_Nguồn, quy trình thẩm định và danh sách Người_Thẩm*Định đồng ý công khai tên.

### F. Triển khai và vận hành

### Requirement 33: Triển khai trực tuyến

**User Story:** Là chủ dự án, tôi muốn sản phẩm chạy online qua URL công khai, để đáp ứng yêu cầu đề tài.

#### Acceptance Criteria

1. THE Game_Client SHALL được phục vụ qua HTTPS tại một URL công khai.
2. THE Backend_API SHALL được phục vụ qua HTTPS và chấp nhận yêu cầu CORS từ tên miền của Game_Client và Admin_Portal.
3. WHEN mã nguồn được đẩy lên nhánh main, THE CI_Pipeline SHALL chạy kiểm thử tự động và triển khai Game_Client, Admin_Portal và Backend_API khi toàn bộ kiểm thử đạt.
4. IF kiểm thử tự động thất bại, THEN THE CI_Pipeline SHALL dừng triển khai và giữ phiên bản đang chạy.
5. THE Backend_API SHALL cung cấp endpoint kiểm tra sức khỏe trả về trạng thái kết nối Content_Store và Media_Store.

### Requirement 34: Sao lưu và giám sát

**User Story:** Là Quản_Trị_Viên, tôi muốn dữ liệu được sao lưu và lỗi được ghi nhận, để khôi phục khi có sự cố.

#### Acceptance Criteria

1. THE Content_Store SHALL được sao lưu tự động mỗi 24 giờ và giữ bản sao lưu tối thiểu 7 ngày.
2. WHEN Backend_API gặp lỗi máy chủ (mã 5xx), THE Backend_API SHALL ghi nhật ký lỗi có mã yêu cầu, endpoint và thời điểm, loại trừ mật khẩu và token.
3. WHEN Game_Client gặp ngoại lệ chưa xử lý, THE Game_Client SHALL gửi báo cáo lỗi gồm phiên bản Game_Client, trình duyệt và ngăn xếp lỗi tới Backend_API.
4. WHILE Backend_API phục vụ tối đa 500 Người_Chơi đồng thời, THE Backend_API SHALL trả lời 95% yêu cầu API trong vòng 500 ms.

---

## Phụ lục A: Danh mục nguồn khởi tạo (đề xuất)

Đây là danh mục đề xuất để khởi tạo Danh*Mục_Nguồn. Cấp_Nguồn là đề xuất ban đầu; Người_Thẩm*Định xác nhận lần cuối. Thông tin xuất bản (năm, lần tái bản, người dịch) phải đối chiếu với bản sách thực tế nhóm sử dụng khi nhập, vì một tác phẩm có nhiều bản dịch và nhiều lần tái bản với số trang khác nhau.

### Cấp 1 — Chính sử, văn kiện gốc, công trình học thuật

| Tài liệu                                                                                                                                       | Ghi chú dùng cho game                                             |
| ---------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| _Đại Việt sử ký toàn thư_ — bản dịch của Viện Khoa học xã hội Việt Nam (Viện Nghiên cứu Hán Nôm), NXB Khoa học Xã hội, 1993 và các lần tái bản | Nguồn chính cho Màn 1 và Màn 2                                    |
| _Khâm định Việt sử thông giám cương mục_ — Viện Sử học dịch, NXB Giáo dục                                                                      | Đối chiếu niên đại, địa danh Màn 1 và Màn 2                       |
| _Lam Sơn thực lục_ — bản dịch đã xuất bản                                                                                                      | Nguồn chính cho khởi nghĩa Lam Sơn                                |
| _Nguyễn Trãi toàn tập_ — NXB Khoa học Xã hội                                                                                                   | Văn bản _Bình Ngô đại cáo_, _Quân trung từ mệnh tập_              |
| _An Nam chí lược_ (Lê Tắc) — bản dịch đã xuất bản                                                                                              | Đối chiếu góc nhìn đương thời về kháng chiến chống Nguyên         |
| _Lịch sử Việt Nam_ (15 tập) — Viện Sử học, NXB Khoa học Xã hội, 2013–2017                                                                      | Khung tổng quan, quan hệ nhân quả, ý nghĩa sự kiện cho cả 3 màn   |
| _Đất nước Việt Nam qua các đời_ — Đào Duy Anh                                                                                                  | Địa lý lịch sử, tên địa danh cổ cho Lớp*Bản*Đồ                    |
| _Hồ Chí Minh toàn tập_ — NXB Chính trị quốc gia Sự thật, 2011                                                                                  | Văn bản _Tuyên ngôn Độc lập_, _Lời kêu gọi toàn quốc kháng chiến_ |
| _Văn kiện Đảng toàn tập_ — NXB Chính trị quốc gia                                                                                              | Văn kiện giai đoạn 1945–1954                                      |
| Các công trình của Viện Lịch sử quân sự Việt Nam về kháng chiến chống Pháp — NXB Chính trị quốc gia / NXB Quân đội nhân dân                    | Diễn biến chiến dịch, số liệu Màn 3                               |
| Tài liệu tại Trung tâm Lưu trữ quốc gia I và III                                                                                               | Văn bản gốc, ảnh tư liệu (cần xin phép sử dụng)                   |

### Cấp 2 — Giáo dục chính thức, bảo tàng, tạp chí chuyên ngành

| Tài liệu                                                                                                                                                         | Ghi chú dùng cho game                                                      |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Sách giáo khoa _Lịch sử và Địa lí_ (lớp 6–9) và _Lịch sử_ (lớp 10–12) theo Chương trình GDPT 2018 — NXB Giáo dục Việt Nam và các bộ sách được Bộ GD&ĐT phê duyệt | Chuẩn mức độ kiến thức, cách diễn đạt phù hợp học sinh; căn cứ phân Độ_Khó |
| Chương trình giáo dục phổ thông môn Lịch sử (Thông tư 32/2018/TT-BGDĐT)                                                                                          | Căn cứ yêu cầu cần đạt cho Câu_Hỏi                                         |
| Bảo tàng Lịch sử Quốc gia — hiện vật, tư liệu trưng bày, ấn phẩm                                                                                                 | Mảnh_Ghép hiện vật (cần kiểm tra giấy phép hình ảnh)                       |
| Bảo tàng Chiến thắng lịch sử Điện Biên Phủ; Bảo tàng Lịch sử Quân sự Việt Nam                                                                                    | Mảnh_Ghép cho Màn 3                                                        |
| Tạp chí _Nghiên cứu Lịch sử_ — Viện Sử học                                                                                                                       | Nghiên cứu chuyên sâu, các tranh luận về niên đại                          |
| _Atlat Địa lí Việt Nam_ — NXB Giáo dục Việt Nam; dữ liệu bản đồ của Cục Đo đạc, Bản đồ và Thông tin địa lý Việt Nam                                              | Nền Bản_Đồ, ranh giới hành chính hiện nay, Hoàng Sa và Trường Sa           |

### Cấp 3 — Bổ trợ (bắt buộc đi kèm nguồn Cấp 1 hoặc Cấp 2)

| Tài liệu                                                             | Ghi chú                         |
| -------------------------------------------------------------------- | ------------------------------- |
| _Việt Nam sử lược_ — Trần Trọng Kim                                  | Văn phong dễ đọc, cần đối chiếu |
| Sách khảo cứu, phổ biến kiến thức có tác giả và nhà xuất bản rõ ràng | Gợi ý cách kể chuyện            |

### Không được dùng làm Nguồn_Tin_Cậy

Wikipedia, blog cá nhân, báo mạng không trích nguồn, mạng xã hội, video trên YouTube/TikTok, nội dung do AI tạo sinh, phim và truyện lịch sử hư cấu. Các nguồn này chỉ dùng làm đầu mối để tìm đến tài liệu gốc.

## Phụ lục B: Danh mục sự kiện ứng viên cho MVP

Danh mục dưới đây là khung nội dung để Biên_Tập_Viên bắt đầu soạn. Mốc thời gian ghi ở đây chỉ để định hướng, chưa phải dữ liệu chính thức; mỗi mục phải được nhập lại với Trích_Dẫn và qua thẩm định theo Requirement 2 và 5. Các mục đánh dấu (†) đã biết có ghi chép khác nhau giữa các nguồn, cần Ghi_Chú_Sử_Học.

### Màn 1 — Bạch Đằng và kháng chiến chống Tống, Nguyên Mông (938–1288)

- Chiến thắng Bạch Đằng của Ngô Quyền (938)
- Lê Hoàn đánh Tống (981)
- Kháng chiến chống Tống thời Lý, phòng tuyến sông Như Nguyệt, Lý Thường Kiệt (1075–1077); bài thơ _Nam quốc sơn hà_ (†, tác giả và hoàn cảnh ra đời có nhiều ý kiến)
- Kháng chiến chống Mông Cổ lần thứ nhất (1258)
- Hội nghị Bình Than (1282) và Hội nghị Diên Hồng (1284/1285)
- _Hịch tướng sĩ_ của Trần Hưng Đạo (†, năm soạn có nhiều ý kiến)
- Kháng chiến chống Nguyên lần thứ hai: Hàm Tử, Chương Dương, Tây Kết (1285)
- Trận Vân Đồn, Trần Khánh Dư đánh đoàn thuyền lương (1287–1288)
- Chiến thắng Bạch Đằng (1288) (†, quy đổi ngày âm lịch sang dương lịch)

### Màn 2 — Khởi nghĩa Lam Sơn (1418–1428)

- Hội thề Lũng Nhai (†, năm có nhiều ghi chép)
- Lê Lợi dựng cờ khởi nghĩa ở Lam Sơn, Thanh Hóa (1418)
- Lê Lai cứu chúa (†)
- Chuyển địa bàn vào Nghệ An theo kế của Nguyễn Chích (1424)
- Trận Tốt Động – Chúc Động (1426)
- Trận Chi Lăng – Xương Giang (1427)
- Hội thề Đông Quan, quân Minh rút về nước (1427)
- Nguyễn Trãi soạn _Bình Ngô đại cáo_ (1428)

### Màn 3 — Cách mạng tháng Tám và kháng chiến chống Pháp (1945–1954)

- Tổng khởi nghĩa giành chính quyền tháng Tám, khởi nghĩa ở Hà Nội (19/8/1945)
- Chủ tịch Hồ Chí Minh đọc _Tuyên ngôn Độc lập_ tại Quảng trường Ba Đình (2/9/1945)
- _Lời kêu gọi toàn quốc kháng chiến_ (19/12/1946)
- Chiến dịch Việt Bắc thu – đông (1947)
- Chiến dịch Biên giới thu – đông (1950)
- Chiến dịch Điện Biên Phủ (13/3 – 7/5/1954) (†, số liệu quân số và thương vong khác nhau giữa các nguồn)
- Ký Hiệp định Genève về Đông Dương (21/7/1954)
