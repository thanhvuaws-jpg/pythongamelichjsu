# Cốt truyện "Sử Ký Điều Tra"

Tài liệu này tách rõ hai lớp: **khung truyện** là phần hư cấu của trò chơi, còn **các sự kiện** là sử, lấy đúng mốc
và tên gọi đã có nguồn trong `game/content/*.json` (trích dẫn ở `game/content/sources.json`). Nhóm cần đối chiếu
lại từng mốc với sách gốc trước khi nộp.

## 1. Khung truyện (hư cấu)

Cụ Đồ Sử là già làng, cả đời giữ cuốn Sử Ký của làng. Một đêm mưa dột, gió lùa, sách bung chỉ, tờ rách, chữ nhoè.
Những trang sử ấy không mất hẳn: chúng nằm trong lời kể của ông lái đò, cụ từ giữ đền, bà cụ bán nước, người lính già.

Người chơi là một **tân binh** của làng, nhận lời Cụ Đồ đi khắp các di tích để chép lại cuốn sử:

1. Nhận việc ở già làng: di tích nào đang chờ, câu hỏi lớn ở đó là gì.
2. Tới di tích, nghe người giữ ký ức kể chuyện. Mỗi câu chuyện là một lần **chìm vào hồi ức**: trận đánh, hội nghị,
   bài hịch được diễn lại.
3. Trả lời câu hỏi của người giữ ký ức, nhặt các **mật thư** (mảnh ghép tư liệu), vào trận đánh dựng lại theo cách
   đánh của trận thật.
4. Quanh mỗi di tích có **bóng giặc**: hình bóng quân xâm lược của thời đó còn vương trong ký ức. Kẻ cầm đầu canh mật thư
   cuối cùng của di tích, mật thư cuối của cả chặng có **trùm** canh. Phải hạ được mới nhặt được.
5. Xong di tích thì được đóng dấu vào Hộ chiếu di sản rồi **về báo cáo già làng**: Cụ Đồ nhắc lại câu hỏi lớn, ghi công,
   trao thưởng và chỉ việc tiếp theo.
6. Đủ di tích thì cùng Cụ Đồ dựng lại dòng thời gian. Cổng dịch chuyển mở, người chơi bước sang thời kỳ sau.

Bóng giặc, cảnh giới, tiềm năng, tiền quan, lò rèn, người thách đấu đều là phần trò chơi, không phải chuyện sử. Lời dẫn
đầu game nói rõ điều này với người chơi.

## 2. Đường tu luyện (phần trò chơi)

| Thứ | Có từ đâu | Dùng vào |
|---|---|---|
| Kinh nghiệm, cấp | đánh bóng giặc, thắng thách đấu, trả lời đúng, báo cáo già làng | máu và sức đánh tăng theo cấp |
| Tiềm năng | đánh bóng giặc, thách đấu, báo cáo già làng | tăng Sức đánh, Thể lực, Nhanh nhẹn, Trí tuệ (phím K) |
| Tiền quan | như trên, thêm trả lời đúng | mua đồ, thuốc nam ở lò rèn đầu làng |
| Điểm kỹ năng | **chỉ** khi học sử: đúng ngay lần đầu, đóng dấu, khám phá, điều tra, ghép tư liệu | học và nâng 11 chiêu thức |
| Tinh hoa | **chỉ** khi học sử: chìm vào hồi ức, khám phá, ghép tư liệu, điều tra | đột phá cảnh giới |

Cảnh giới chặn cấp tối đa: Tân binh (cấp 10), Sử sinh (cấp 20, cần 8 tinh hoa), Sử quan (cấp 30, cần 20), Đại sử quan
(cấp 40, cần 36). Vì vậy cày quái mãi cũng không mạnh lên được nếu không học sử.

Đồ trang bị là đồ dùng chung của người xưa, không gán cho hiện vật có thật: gậy tre, đao, giáo, nỏ, kiếm, cung tên, mã tấu,
đại đao; áo vải, áo giáp da, áo bông, giáp vảy, giáp lá đồng; khăn chít, nón lá, mũ da, mũ sắt; dép rơm, giày vải, ủng da;
bao tay vải, găng da, găng bọc sắt; thuốc nam (phím Q trong trận). Câu mô tả nào nói tới sự thật (như kho mũi tên đồng ở
Cổ Loa) thì dựa vào nguồn khảo cổ Cổ Loa đã có trong `sources.json`.

Chiến mã: từ cấp 3 bấm H để gọi, đi nhanh hơn trên map. Người thách đấu là các võ sinh hư cấu ở võ đài, thỉnh thoảng đi tới
hỏi đấu: Y nhận lời, N từ chối, hoặc đi xa là coi như bỏ chạy.

## 2b. Vùng luyện (phần trò chơi, gắn với sự kiện có thật)

Học xong một số di tích thì mở đường sang vùng luyện của thời đó, có người kể chuyện (hư cấu) kể lại sự kiện kèm nguồn:

- Bến Đông Bộ Đầu năm 1258 (mở sau Đền Trần): quân Mông Cổ, có kỵ binh; nguồn Toàn thư, kỷ Trần Thái Tông.
- Thành Xương Giang năm 1427 (mở sau Tốt Động): quân Minh giữ thành, kỵ binh Minh; nguồn Toàn thư, kỷ Lê Thái Tổ và Lịch sử Việt Nam.
- Cánh đồng Mường Thanh năm 1954 (mở sau Ba Đình): chỉ có ụ súng, đồn bốt, lô cốt, xe tăng; nguồn Bảo tàng Chiến thắng lịch sử Điện Biên Phủ.
- Bến Chương Dương năm 1285 (mở sau Kiếp Bạc): quân Nguyên, thuyền chiến Nguyên neo ngoài sông; nguồn Toàn thư, kỷ Trần Nhân Tông.
- Vòng vây Đông Quan năm 1427 (mở sau Chi Lăng): lính khiên Minh, lính giữ thành; nguồn Toàn thư, kỷ Lê Thái Tổ và Quân trung từ mệnh tập.
- Sông Lô năm 1947 (mở sau Tân Trào): chỉ có tàu chiến, ca nô, đồn bốt, ụ súng; nguồn công trình của Viện Lịch sử quân sự.
- Sông Như Nguyệt năm 1077 (mở sau Như Nguyệt): quân Tống đóng trại bờ bắc, máy bắn đá; nguồn Toàn thư, kỷ Lý Nhân Tông.
- Diễn Châu năm 1425 (mở sau Trà Lân): quân Minh, thuyền lương neo ở bến, thành Diễn Châu; nguồn Toàn thư, kỷ Lê Thái Tổ.
- Đèo Bông Lau năm 1947 (mở sau Ba Đình): chỉ có xe vận tải, xe bọc thép, đồn bốt, ụ súng; nguồn công trình của Viện Lịch sử quân sự.
- Biển Vân Đồn năm 1288 (mở sau Vân Đồn): thuỷ binh Nguyên, thuyền chiến và thuyền lương Nguyên neo quanh đảo; nguồn Toàn thư, kỷ Trần Nhân Tông.
- Ải Lê Hoa năm 1427 (mở sau Chi Lăng): đạo viện binh Minh từ Vân Nam, có kỵ binh; nguồn Toàn thư, kỷ Lê Thái Tổ và Bình Ngô đại cáo.
- Cứ điểm Đông Khê năm 1950 (mở sau Biên giới): chỉ có đồn bốt, lô cốt, ụ súng, ụ pháo; nguồn công trình của Viện Lịch sử quân sự.

Chi tiết từng vật thể xem `docs/YEU_CAU_CHI_TIET.md`.

## 3. Ba chặng sử

### Chặng 1. Những khúc sông giữ nước (938 – 1288)

Từ cọc gỗ Ngô Quyền đến cọc Yên Giang: ba trăm năm dựng nước và giữ nước qua các đời Ngô, Lý, Trần.

| Di tích | Câu hỏi lớn | Mốc sử trong game |
|---|---|---|
| Đất hai vua Đường Lâm | Ngô Quyền là ai trước khi thắng trên sông Bạch Đằng? | không có mốc riêng: quê của Phùng Hưng và Ngô Quyền |
| Cửa sông Bạch Đằng năm 938 | Vì sao đội quân mới họp đánh tan thuỷ quân Nam Hán? | 931 Dương Đình Nghệ đuổi quân Nam Hán; 937 Kiều Công Tiễn giết Dương Đình Nghệ; 938 chiến thắng Bạch Đằng |
| Kinh đô mới ở Cổ Loa | Việc đóng đô ở Cổ Loa nói lên điều gì? | 939 Ngô Quyền xưng vương, đóng đô ở Cổ Loa |
| Phòng tuyến Như Nguyệt | Vì sao đã thắng thế mà Lý Thường Kiệt lại đề nghị giảng hoà? | 1075 đánh các châu Ung, Khâm, Liêm; 1076 – 1077 phòng tuyến Như Nguyệt và giảng hoà |
| Đền Trần và lời thề giữ nước | Nhà Trần đã làm gì để cả nước cùng đánh? | 1258 kháng chiến lần thứ nhất; 1282 Hội nghị Bình Than |
| Kiếp Bạc và bài hịch thức tỉnh | Hịch tướng sĩ có sức mạnh gì? | 1285 Chương Dương, Hàm Tử, Tây Kết |
| Đoàn thuyền lương Vân Đồn (phụ) | Vì sao phá thuyền lương lại quan trọng? | 1287 – 1288 Trần Khánh Dư phá thuyền lương |
| Bãi cọc Yên Giang năm 1288 | Trận 1288 kế thừa trận 938 thế nào? | 9/4/1288 chiến thắng Bạch Đằng của nhà Trần |

Bóng giặc theo đúng thời: quân Nam Hán quanh Đường Lâm, Bạch Đằng 938, Cổ Loa; quân Tống ở Như Nguyệt; quân Mông – Nguyên
ở Đền Trần, Kiếp Bạc, Vân Đồn, Yên Giang. Trùm chặng: "Tướng thuỷ quân Nguyên" (tên chung, không gán cho nhân vật có thật).

### Chặng 2. Mười năm nếm mật nằm gai (1418 – 1428)

Từ vùng núi Thanh Hoá đến kinh thành Đông Quan: mười năm khởi nghĩa Lam Sơn.

| Di tích | Câu hỏi lớn | Mốc sử trong game |
|---|---|---|
| Dựng cờ ở Lam Sơn | Vì sao khởi nghĩa ở vùng núi? | 1416 Hội thề Lũng Nhai; 1418 Lê Lợi dựng cờ |
| Người mặc áo bào chủ tướng | Sử sách và lời truyền ghi nhớ Lê Lai thế nào? | 1418 – 1419 Lê Lai liều mình cứu chủ tướng |
| Kế vào Nghệ An | Vì sao đây là bước ngoặt? | 1424 chuyển hướng vào Nghệ An |
| Cánh đồng Tốt Động | Tốt Động đổi cục diện thế nào? | 1426 trận Tốt Động – Chúc Động |
| Ải Chi Lăng năm 1427 | Vì sao Chi Lăng quyết định số phận quân Minh? | 10/1427 Chi Lăng – Xương Giang |
| Hồ Gươm và áng văn thiên cổ | Đâu là sử, đâu là truyền thuyết? | 1407 nhà Minh đặt ách đô hộ; 12/1427 Hội thề Đông Quan; 1428 Bình Ngô đại cáo |

Chuyện trả gươm ở Hồ Gươm là truyền thuyết và được ghi rõ là truyền thuyết. Bóng giặc là quân Minh; trùm chặng là
"Tướng trấn thủ quân Minh" (tên chung).

### Chặng 3. Từ Tân Trào đến Điện Biên (1945 – 1954)

Người kể là một cựu binh tuổi đã cao. Ở chặng này **không có quái là người**: chỉ có đồn bốt, lô cốt để phá, và không
vẽ chân dung các nhân vật lịch sử hiện đại.

| Di tích | Câu hỏi lớn | Mốc sử trong game |
|---|---|---|
| Cây đa Tân Trào | Vì sao tháng 8/1945 là "thời cơ ngàn năm có một"? | 16 – 17/8/1945 Quốc dân Đại hội Tân Trào; 10 – 12/1947 chiến dịch Việt Bắc |
| Ba Đình và Hà Nội 60 ngày đêm | Vì sao vừa độc lập đã phải kháng chiến? | 19/8/1945 khởi nghĩa ở Hà Nội; 2/9/1945 Tuyên ngôn Độc lập; 19/12/1946 Toàn quốc kháng chiến |
| Đông Khê mở màn Biên giới 1950 (phụ) | Vì sao đây là bước trưởng thành? | 9 – 10/1950 chiến dịch Biên giới |
| Lòng chảo Điện Biên Phủ | Vì sao "đánh chắc, tiến chắc" là mấu chốt? | 26/1/1954 đổi phương châm; 13/3/1954 mở màn ở Him Lam; 7/5/1954 toàn thắng; 21/7/1954 Hiệp định Genève |

Trùm chặng là "Cứ điểm kiên cố": một công trình, không phải con người.

## 4. Nguyên tắc giữ đúng sử

- Không bịa thêm chi tiết cho đẹp. Chỗ nào sử còn tranh luận hoặc chỉ là truyền thuyết thì ghi "Ghi chú sử học" hoặc
  "truyền thuyết".
- Nhân vật dẫn chuyện (Cụ Đồ, bà cụ bán nước, ông lái đò, cựu binh...) là hư cấu và được đánh dấu hư cấu trong lời thoại.
- Tên trùm, kẻ cầm đầu là tên chung theo chức, không gán cho tướng có thật.
- Không có máu; chặng 1945 – 1954 không có người ngã xuống trên màn hình.

## 5. Nguồn

Đại Việt sử ký toàn thư; Khâm định Việt sử thông giám cương mục; Lam Sơn thực lục; Nguyễn Trãi toàn tập; An Nam chí lược;
Lịch sử Việt Nam (NXB Khoa học Xã hội); Việt Nam sử lược; Lĩnh Nam chích quái (phần truyền thuyết); Hồ Chí Minh toàn tập;
Văn kiện Đảng toàn tập; công trình của Viện Lịch sử quân sự Việt Nam; hồi ký của Đại tướng Võ Nguyên Giáp; Bảo tàng Chiến
thắng lịch sử Điện Biên Phủ; các công bố khảo cổ về Cổ Loa và bãi cọc Bạch Đằng; sách giáo khoa Lịch sử, Ngữ văn theo
Chương trình GDPT 2018. Chi tiết từng trích dẫn ở `game/content/sources.json`.

## Câu cá, nướng cá

Mỗi màn có một người câu cá đứng ở mép sông, hồ gần chỗ xuất phát, cạnh một bếp lửa (`game/scenes/fishing.py`).

- Nói chuyện để nghe vài chuyện sử gắn với sông nước và cái ăn, có trích nguồn: tổ tiên nhà Trần làm nghề đánh cá ở Tức Mặc
  (Màn 1), Lê Thận kéo lưới được lưỡi gươm trong truyền thuyết Hồ Gươm và những ngày nghĩa quân Lam Sơn “lương hết mấy tuần”
  (Màn 2), nạn đói năm 1945 và việc cứu đói là việc cấp bách đầu tiên của Chính phủ lâm thời (Màn 3).
- Mua cần câu tre (20 quan) của người câu cá hoặc ở lò rèn, mục Đồ nghề.
- Đứng sát mép nước bấm C thả câu; phao chìm, hiện dấu chấm than thì bấm C kéo lên. Có cá chép, cá trắm, cá rô; đôi khi chỉ
  vớt được rong. Giỏ đựng tối đa 12 con.
- Mang cá đến bếp lửa để nướng (mang theo tối đa 10 xiên). Giữa trận bấm E ăn một xiên cá nướng, hồi 25% máu.

## Chat, bảng vàng, video hướng dẫn

- Chat (phím L): ô gõ nằm ở trang chơi nên gõ được tiếng Việt. Kênh cùng map miễn phí, lời chat hiện trên đầu người nói;
  kênh thế giới hiện ở góc trên phải, mỗi tin tốn 10 quan. Máy chủ tự che từ tục, chặn gửi dồn.
- Bảng vàng dựng ở map đầu, gần chỗ xuất phát: 20 người nhiều điểm học sử nhất và 20 người sức mạnh cao nhất.
- Góc trên phải chỉ còn nút ba gạch; bấm vào mới xổ danh sách các bảng, có ghi phím tắt.
- Video hướng dẫn (trailer trong game, cũng là phần đầu của `web/video/trailer.mp4`) dài gần ba phút, đi lần lượt: vòng
  chơi, màn hình, các nhân vật, học một di tích, kẻ canh mật thư, đánh nhau, lên cấp, tu luyện, cảnh giới, lò rèn, vùng
  luyện, sổ bóng giặc, câu cá, chơi cùng bạn bè và chat.
- `web/video/trailer.mp4` (video ở trang chủ) nối thêm hai đoạn sau phần hướng dẫn, tổng gần năm phút: người chơi máy
  đánh trận cuối Chiến dịch Điện Biên Phủ, rồi qua cổng cuối Màn 3 vào đoạn kết bảy cảnh. Đoạn kết cũng được cắt riêng
  (`--doan-ket`, 58 giây) để chiếu trên slide thuyết trình.

## Người chơi máy, cảnh đang đánh

- Người chơi máy do máy chủ điều khiển, chạy cả khi không ai online, để thế giới luôn có người: tự cày quái, làm nhiệm vụ,
  sắm đồ, câu cá, thỉnh thoảng nói một câu, hạ đủ quái thì lên cấp. Trong game họ trông như người chơi khác. Quản trị viên
  thêm, xoá ở trang quản trị (mục "Người chơi máy"). Họ không đụng quái đang ở gần người chơi thật, không có trên bảng xếp
  hạng, Bảng vàng.
- Ai hạ quái (người hay bot) thì người cùng map cũng thấy con quái ngã.
- Khi một người chơi đang đánh quái hay thách đấu, người cùng map thấy người đó vung vũ khí và dòng “đang đánh …”.

## Đoạn kết

Bước qua cổng cuối Màn 3 thì có đoạn kết bảy cảnh, tự chạy, phím cách sang cảnh sau, Esc bỏ qua:

1. Hơn một nghìn năm giữ nước: các mốc 938, 1077, 1288, 1428, 1945, 1954.
2. Chiều 7/5/1954: lá cờ “Quyết chiến Quyết thắng” kéo lên nóc hầm chỉ huy địch ở Điện Biên Phủ, bộ đội reo hò.
3. Tháng 7/1954: Hiệp định Giơnevơ, vĩ tuyến 17 là giới tuyến quân sự tạm thời, hẹn tổng tuyển cử tháng 7/1956.
4. 10/10/1954: Đại đoàn 308 vào tiếp quản Hà Nội, dân hai bên phố phất cờ đỏ sao vàng.
5. 15 giờ cùng ngày: lễ chào cờ ở sân Cột Cờ.
6. 30/4/1975: đất nước thống nhất (nói rõ là hơn hai mươi năm sau, game không đi tới giai đoạn này).
7. Hành trình của người chơi: số di tích, điểm, câu đúng, cấp, sức mạnh, sổ bóng giặc, vùng luyện.

Sau đó là lời dặn của Cụ Đồ Sử như cũ. Đi hết game thì màn hình tựa đề có thêm nút “Xem lại đoạn kết”.
