# Yêu cầu chi tiết: “Sử Ký Điều Tra”, game nhập vai học lịch sử Việt Nam

Bản này mở rộng yêu cầu gốc của nhóm thành mô tả đến từng vật thể trong game. Bảng số liệu được sinh tự động từ code
(`tools/make_spec.py`), nên đúng với bản đang chạy. Phần nào là hư cấu của trò chơi đều ghi rõ.

## 1. Mục tiêu và nguyên tắc

- Mục tiêu: người chơi thấy vui khi học sử. Mọi thứ làm nhân vật mạnh lên đều phải đi qua việc học sử: cày quái chỉ lên
  được tới giới hạn cảnh giới, muốn đột phá phải có tinh hoa, mà tinh hoa chỉ có khi chìm vào hồi ức, khám phá, ghép tư liệu,
  điều tra; điểm kỹ năng chỉ có khi trả lời đúng, đóng dấu di tích.
- Đúng sử: mỗi câu kể, câu hỏi, dòng “Sử ghi” phải gắn mã trích dẫn trong `game/content/sources.json`. Chỗ còn tranh luận ghi
  “Ghi chú sử học”; truyền thuyết ghi rõ là truyền thuyết. Không bịa chi tiết cho đẹp.
- Hư cấu có đánh dấu: người kể chuyện, già làng, thợ rèn, võ sinh, bóng giặc, cảnh giới, tiềm năng, tiền quan là phần trò chơi.
- Không máu me; thời 1945 – 1954 không có quái là người (chỉ đồn bốt, lô cốt, ụ súng, xe tăng), không vẽ chân dung lãnh tụ hiện đại.
- Tên trùm, kẻ cầm đầu là tên theo chức (“Bách hộ quân Nguyên”, “Tướng tiên phong Mông Cổ”), không gán cho người có thật.
- Lối chơi lấy cảm hứng từ thể loại game nhập vai cày cấp; không chép tên, nhân vật, hình ảnh của game nào.

## 2. Vòng chơi

1. Già làng Cụ Đồ Sử giao việc: di tích tiếp theo và câu hỏi lớn ở đó.
2. Tới di tích, nghe người giữ ký ức kể, chìm vào hồi ức (trận đánh, hội nghị diễn lại), trả lời câu hỏi, nhặt mật thư, vào trận.
3. Quanh di tích có bóng giặc đúng thời: bấm F đánh ngay trên map để lấy kinh nghiệm, tiềm năng, quan, thuốc nam.
4. Mật thư cuối của di tích có kẻ cầm đầu canh; mật thư cuối của chặng có trùm. Thua thì bị đưa về chỗ già làng, trùm yếu dần
   mỗi lần thua (tối đa 45%) để không ai bị kẹt.
5. Xong di tích: đóng dấu, về báo cáo già làng nhận thưởng và việc tiếp theo.
6. Học xong di tích nhất định thì mở đường sang vùng luyện của thời đó.
7. Dùng tiềm năng tăng chỉ số (K), quan mua đồ ở lò rèn, điểm kỹ năng học chiêu, tinh hoa đột phá cảnh giới.
8. Đủ di tích thì dựng dòng thời gian, qua cổng sang chặng sau.
9. Qua cổng cuối Màn 3 là đoạn kết (`scenes/ending.py`), bảy cảnh tự chạy, có nguồn: các mốc giữ nước 938–1954; lá cờ
   “Quyết chiến Quyết thắng” trên nóc hầm chỉ huy địch ở Điện Biên Phủ chiều 7/5/1954; Hiệp định Giơnevơ tháng 7/1954 (vĩ
   tuyến 17 tạm thời, hẹn tổng tuyển cử 7/1956); Đại đoàn 308 vào tiếp quản Hà Nội giữa phố treo cờ đỏ sao vàng ngày
   10/10/1954; lễ chào cờ 15 giờ ở sân Cột Cờ; trang nói rõ đến 30/4/1975 đất nước mới thống nhất; tổng kết hành trình của
   người chơi. Sau đó là lời dặn của Cụ Đồ Sử. Phím cách sang cảnh sau, mũi tên trái lùi lại, Esc bỏ qua. Đi hết game thì màn
   hình tựa đề có nút "Xem lại đoạn kết".

## 3. Nhân vật

### Cảnh giới

| Cảnh giới | Cấp tối đa | Tinh hoa cần | Nhân chỉ số |
|---|---|---|---|
| Tân binh | 10 | 0 | x1.00 |
| Sử sinh | 20 | 8 | x1.12 |
| Sử quan | 30 | 20 | x1.25 |
| Đại sử quan | 40 | 36 | x1.40 |

Tinh hoa: mỗi hồi ức chìm vào lần đầu +1, mỗi khám phá +1, mỗi tư liệu ghép xong
+2, mỗi vụ điều tra +2. Lời dẫn đầu và lời kết không tính.

### Chỉ số (mua bằng tiềm năng, bậc n tốn 15 x n, tối đa 20 bậc)

Sức đánh +8% sát thương mỗi bậc; Thể lực +12 máu; Nhanh nhẹn +4% tốc độ; Trí tuệ −4% thời gian hồi chiêu. Mỗi cấp thêm
8 máu và 3% sát thương.

### Kỹ năng (học bằng điểm kỹ năng)

| Kỹ năng | Tác dụng | Điều kiện mở | Hồi chiêu |
|---|---|---|---|
| Phóng lao | Ném giáo thẳng vào đối thủ. | Cần trả lời đúng 3 câu | 2.5 giây |
| Đột kích | Lướt nhanh tới và chém, né được đòn trong lúc lướt. | Cần đóng dấu 1 di tích | 4.0 giây |
| Tên lửa | Bắn ba mũi lửa xoè ra, trúng thì cháy thêm vài giây. | Cần trả lời đúng 10 câu | 5.0 giây |
| Xoáy kiếm | Chém một vòng quanh mình, đánh trúng mọi đối thủ ở gần. | Cần đóng dấu 3 di tích | 6.0 giây |
| Thế thủ | Giơ khiên, giảm mạnh sát thương trong chốc lát. | Cần trả lời đúng 15 câu | 8.0 giây |
| Hồi khí | Lấy lại một phần máu. | Cần đóng dấu 5 di tích | 10.0 giây |
| Chông ngầm | Rải chông dưới chân, đối thủ đạp phải thì mất máu và đi chậm. Học từ kế đóng cọc. | Cần trả lời đúng 22 câu | 7.0 giây |
| Nỏ liên châu | Bắn liền năm mũi tên vào đối thủ gần nhất. | Cần trả lời đúng 28 câu | 6.0 giây |
| Hoả công | Đốt một vùng lửa trước mặt, đối thủ đứng trong lửa bị cháy dần. Học từ trận Vân Đồn đốt thuyền lương. | Cần đóng dấu 8 di tích | 9.0 giây |
| Hào khí | Hô vang khí thế: sức đánh và tốc độ tăng trong sáu giây, đẩy lùi đối thủ ở sát bên. | Cần đóng dấu 10 di tích | 14.0 giây |
| Phi mã xung trận | Gọi chiến mã phi thẳng tới, húc ngã mọi đối thủ trên đường phi. | Cần trả lời đúng 34 câu | 9.0 giây |

## 4. Trang bị: món nào cũng hiện lên người, vũ khí nào cũng có cách đánh và hiệu ứng riêng

Ngoại hình người chơi vẽ lại theo bộ đồ (`game/core/outfit.py`): áo đổi màu và hoa văn, mũ đổi phần đầu (không đội gì thì
là tóc búi), giày đổi bàn chân, găng đổi bàn tay. Vũ khí cầm trên tay khi đi; khi đánh thì vung, đâm, bổ hoặc bắn theo loại,
có vệt chém và hiệu ứng trúng đòn (`game/core/weapons.py`). Quái và võ sinh cũng cầm vũ khí đúng loại.

| Ô | Món | Cấp | Giá (quan) | Chỉ số | Hiện trên người / cách đánh | Ghi chú |
|---|---|---|---|---|---|---|
| Vũ khí | Gậy tre | 1 | 0 | +5% sát thương | chém vòng cung; quất mạnh, đẩy lùi xa, vụn gỗ văng, vệt vàng nhạt | Gậy tre đực đẽo nhẵn, thứ có sẵn ở mọi làng. |
| Vũ khí | Đao sắt | 3 | 60 | +12% sát thương | chém vòng cung; vệt chém cong trắng, tia lửa | Đao một lưỡi rèn bằng sắt. |
| Vũ khí | Giáo dài | 5 | 130 | +18% sát thương | đâm thẳng, với xa hơn; mũi giáo lao tới, vết cắt | Giáo cán dài mũi sắt, giữ đối thủ ở xa. |
| Vũ khí | Nỏ gỗ | 7 | 210 | +20% sát thương, -6% hồi chiêu | bắn đạn bay thật; tên nỏ ngắn mập, bay nhanh, nặng hơn tên cung | Nỏ là vũ khí bắn xa quen thuộc của người Việt; ở Cổ Loa từng đào được cả kho mũi tên đồng. |
| Vũ khí | Kiếm thép | 10 | 340 | +30% sát thương | chém vòng cung; vệt chém kép xanh nhạt, tia lửa | Kiếm hai lưỡi bằng thép tôi. |
| Vũ khí | Cung tên | 12 | 420 | +30% sát thương, +3% tốc độ, -8% hồi chiêu | bắn đạn bay thật; mũi tên bay, cắm vào thì toé tia nhỏ | Cung gỗ dây gai, tên tre; nhẹ, hồi chiêu nhanh. |
| Vũ khí | Mã tấu | 15 | 650 | +42% sát thương | chém vòng cung; vệt chém cong trắng, tia lửa | Lưỡi to bản, chém mạnh. |
| Vũ khí | Đại đao | 19 | 900 | +52% sát thương, +20 máu | bổ rộng, rung màn hình; vòng chém lớn, đất đá văng, rung màn hình | Đao lớn cán dài, phải khoẻ mới múa được. |
| Vũ khí | Bảo kiếm | 24 | 1300 | +62% sát thương, -5% hồi chiêu | chém vòng cung; vệt vàng, tia sáng vàng toé ra | Kiếm rèn kỹ, sắc và bền. Đồ trong game, không phải hiện vật có thật. |
| Áo giáp | Áo vải nâu | 1 | 0 | +10 máu | áo nâu vải thô | Áo vải nhuộm nâu của người làng. |
| Áo giáp | Áo giáp da | 4 | 80 | +35 máu | áo da nâu, vạt chéo viền sáng | Áo làm từ da thuộc dày. |
| Áo giáp | Áo bông dày | 8 | 200 | +60 máu | áo đỏ chần chỉ ngang, đai vàng | Áo nhồi bông nhiều lớp, đỡ được tên bắn. |
| Áo giáp | Giáp vảy sắt | 13 | 480 | +100 máu | giáp xám có vảy sáng xen kẽ, đai đỏ | Những miếng sắt nhỏ kết chồng lên nhau như vảy. |
| Áo giáp | Giáp lá đồng | 20 | 1000 | +160 máu | giáp màu đồng có vảy vàng, quần đỏ | Áo gắn những lá đồng che ngực và vai. |
| Mũ | Khăn chít | 1 | 0 | +2% tốc độ | khăn đen quấn đầu, đuôi khăn sau gáy | Khăn vải quấn đầu. |
| Mũ | Nón lá | 3 | 40 | +4% tốc độ | nón lá chóp có vòng nan, rộng hơn đầu | Nón lá che nắng che mưa. |
| Mũ | Mũ da | 7 | 130 | +20 máu, +5% tốc độ | mũ da nâu có viền | Mũ da cứng, che đầu khỏi đòn chém. |
| Mũ | Mũ sắt | 14 | 520 | +50 máu, +7% tốc độ | mũ sắt có vành vàng và chùm lông đỏ | Mũ sắt có chóp và tua đỏ. |
| Giày | Dép rơm | 1 | 10 | +3% tốc độ | bàn chân màu rơm | Dép kết bằng rơm, đi nhẹ chân. |
| Giày | Giày vải | 6 | 120 | +6% tốc độ | bàn chân màu vải sẫm | Giày vải đế mềm, chạy nhanh. |
| Giày | Ủng da | 12 | 400 | +30 máu, +8% tốc độ | ủng da nâu cao hai hàng điểm ảnh | Ủng da cổ cao, hợp đường dài. |
| Găng | Bao tay vải | 2 | 25 | +3% sát thương | bàn tay quấn vải trắng ngà | Quấn tay cho chắc cán vũ khí. |
| Găng | Găng da | 8 | 190 | +7% sát thương, -3% hồi chiêu | bàn tay màu da nâu | Găng da thuộc, cầm nỏ cầm đao đều chắc. |
| Găng | Găng bọc sắt | 16 | 700 | +12% sát thương, +25 máu | bàn tay màu thép | Mu bàn tay bọc sắt, đỡ được lưỡi đao. |
| Vật phẩm | Thuốc nam | 1 | 15 | hồi 40% máu (phím Q khi đang đánh) |  | Thuốc sắc sẵn, uống giữa trận để hồi máu. |
| Vật phẩm | Cá tươi | 1 | 0 |  |  | Cá câu được ở sông hồ. Mang đến bếp lửa của người câu cá để nướng. |
| Vật phẩm | Cá nướng | 1 | 0 | hồi 25% máu (phím E khi đang đánh) |  | Cá xiên que tre nướng trên than. Ăn giữa trận để lại sức. |
| Đồ nghề | Cần câu tre | 1 | 20 |  |  | Cần tre, dây câu, lưỡi câu sắt. Đứng sát mép nước bấm C để thả câu, cá cắn thì bấm C lần nữa. |

## 5. Quái

| Quái | Ngoại hình | Vũ khí | Cấp | Máu | Sức đánh | Tốc độ | Lối đánh | Chiêu | Thưởng (KN / tiềm năng / quan) | Dòng “Sử ghi” khi hạ lần đầu |
|---|---|---|---|---|---|---|---|---|---|---|
| Lính Nam Hán | mũ sắt sẫm có che gáy, giáp vảy xám, đai đỏ | Giáo dài | 2 | 42 | 0.5 | 150 | melee | — | 14 / 6 / 2–5 | Nam Hán là nước ở vùng Quảng Đông, Quảng Tây ngày nay. Năm 938, thuỷ quân Nam Hán do Lưu Hoằng Tháo chỉ huy bị Ngô Quyền đánh tan trên sông Bạch Đằng. (Kỷ Nhà Ngô (Tiền Ngô Vương)) |
| Thuỷ binh Nam Hán | mũ sắt sẫm có che gáy, giáp vảy xám, đai đỏ | Đao sắt | 3 | 50 | 0.58 | 160 | melee | Phóng lao | 18 / 7 / 2–6 | Quân Nam Hán theo đường biển vào cửa sông Bạch Đằng, nên Ngô Quyền cho đóng cọc ở lòng sông để chờ thuỷ triều. (Kỷ Nhà Ngô (Tiền Ngô Vương)) |
| Lính Tống | mũ sắt sẫm có che gáy, giáp vảy xám, đai đỏ | Giáo dài | 5 | 62 | 0.66 | 165 | melee | Phóng lao | 26 / 9 / 3–7 | Năm 1076 – 1077, quân Tống tiến sang và bị chặn lại ở phòng tuyến sông Như Nguyệt. (Lịch sử 7, Lịch sử 10: kháng chiến chống Tống, chống Mông – Nguyên, khởi nghĩa Lam Sơn) |
| Cung thủ Tống | mũ sắt sẫm có che gáy, giáp vảy xám, đai đỏ | Cung tên | 6 | 60 | 0.75 | 170 | ranged | Phi tiêu | 32 / 12 / 4–9 | Sau thất bại ở sông Như Nguyệt, nhà Tống phải chấp nhận giảng hoà và rút quân. (Lịch sử 7, Lịch sử 10: kháng chiến chống Tống, chống Mông – Nguyên, khởi nghĩa Lam Sơn) |
| Lính Nguyên | mũ sắt tròn viền lông, tai che bằng lông, áo choàng cài vạt chéo, đai da | Đao sắt | 8 | 85 | 0.85 | 185 | melee | Đột kích | 42 / 15 / 5–12 | Nhà Nguyên do người Mông Cổ lập ra năm 1271. Quân Nguyên sang đánh nước ta năm 1285 và năm 1287 – 1288. (Lịch sử 7, Lịch sử 10: kháng chiến chống Tống, chống Mông – Nguyên, khởi nghĩa Lam Sơn) |
| Cung thủ Nguyên | mũ sắt tròn viền lông, tai che bằng lông, áo choàng cài vạt chéo, đai da | Cung tên | 10 | 90 | 0.95 | 180 | ranged | Mưa tên, Phi tiêu | 54 / 19 / 6–14 | Cả ba lần kháng chiến chống Mông – Nguyên, quân dân nhà Trần đều thắng. (Lịch sử 7, Lịch sử 10: kháng chiến chống Tống, chống Mông – Nguyên, khởi nghĩa Lam Sơn) |
| Lính Minh | mũ sắt hình bát có chóp nhọn và tua đỏ, áo bông đỏ | Giáo dài | 12 | 120 | 1.0 | 185 | melee | Phóng lao, Liên hoàn đao | 70 / 24 / 8–16 | Nhà Minh đặt ách đô hộ nước ta từ năm 1407. Khởi nghĩa Lam Sơn kéo dài mười năm mới đuổi được quân Minh. (Lịch sử 7, Lịch sử 10: kháng chiến chống Tống, chống Mông – Nguyên, khởi nghĩa Lam Sơn) |
| Cung thủ Minh | mũ sắt hình bát có chóp nhọn và tua đỏ, áo bông đỏ | Nỏ gỗ | 15 | 125 | 1.1 | 180 | ranged | Mưa tên, Nỏ liên châu | 88 / 30 / 9–18 | Cuối năm 1427, viện binh Minh bị đánh tan ở Chi Lăng và Xương Giang. (Bản kỷ, Kỷ Nhà Lê, Thái Tổ hoàng đế, năm Đinh Mùi (1427)) |
| Lính trấn thủ Minh | mũ sắt hình bát có chóp nhọn và tua đỏ, áo bông đỏ | Đại đao | 18 | 170 | 1.2 | 185 | tank | Chấn địa, Thế thủ | 110 / 36 / 10–22 | Tháng 12 năm 1427, tướng Minh là Vương Thông phải dự Hội thề Đông Quan, hẹn rút quân về nước. (Lịch sử 7, Lịch sử 10: kháng chiến chống Tống, chống Mông – Nguyên, khởi nghĩa Lam Sơn) |
| Đồn bốt | khối bê tông có lỗ châu mai, bao cát quanh nóc (công trình, không có người) | — | 20 | 240 | 1.15 | 0 | ranged | Phi tiêu, Mưa tên | 130 / 42 / 14–28 | Trong kháng chiến chống Pháp, đối phương dựng đồn bốt dày đặc để giữ đường và giữ vùng. (Lịch sử 9, Lịch sử 12: kháng chiến chống thực dân Pháp, chiến dịch Điện Biên Phủ 1954) |
| Lô cốt | khối bê tông có lỗ châu mai, bao cát quanh nóc (công trình, không có người) | — | 25 | 340 | 1.3 | 0 | ranged | Phi tiêu, Mưa tên, Chấn địa | 170 / 55 / 18–34 | Tập đoàn cứ điểm Điện Biên Phủ có 49 cứ điểm, chia làm ba phân khu. (Tư liệu trưng bày về tập đoàn cứ điểm Điện Biên Phủ và chiến dịch năm 1954) |
| Lính Mông Cổ | mũ sắt tròn viền lông, tai che bằng lông, áo choàng cài vạt chéo, đai da | Đao sắt | 7 | 76 | 0.8 | 180 | melee | Đột kích | 38 / 14 / 5–11 | Năm 1258, khi chưa lập ra nhà Nguyên, quân Mông Cổ lần đầu đánh vào Đại Việt và bị đẩy lui ở Đông Bộ Đầu. (Bản kỷ, Kỷ Nhà Trần, Thái Tông hoàng đế, các năm Đinh Tỵ (1257) và Mậu Ngọ (1258)) |
| Cung thủ Mông Cổ | mũ sắt tròn viền lông, tai che bằng lông, áo choàng cài vạt chéo, đai da | Cung tên | 8 | 70 | 0.85 | 185 | ranged | Mưa tên | 44 / 16 / 5–12 | Quân Mông Cổ nổi tiếng giỏi cưỡi ngựa bắn cung, từng đánh chiếm nhiều vùng rộng lớn ở châu Á và châu Âu. (Lịch sử 7, Lịch sử 10: kháng chiến chống Tống, chống Mông – Nguyên, khởi nghĩa Lam Sơn) |
| Kỵ binh Mông Cổ | lính Mông Cổ cưỡi ngựa đen | Đao sắt | 10 | 104 | 0.95 | 240 | assassin | Xung phong, Đột kích | 58 / 20 / 7–15 | Kỵ binh là sức mạnh chính của quân Mông Cổ. Năm 1258, nhà Trần dùng thuyền chiến đánh ở bến Đông Bộ Đầu bên sông Hồng. (Bản kỷ, Kỷ Nhà Trần, Thái Tông hoàng đế, các năm Đinh Tỵ (1257) và Mậu Ngọ (1258)) |
| Lính giữ thành Minh | mũ sắt hình bát có chóp nhọn và tua đỏ, áo bông đỏ | Giáo dài | 14 | 150 | 1.05 | 175 | tank | Thế thủ, Phóng lao | 78 / 27 / 8–17 | Thành Xương Giang nằm trên đường từ Lạng Sơn về Đông Quan; nghĩa quân hạ thành trước khi viện binh Minh tới. (Phần khởi nghĩa Lam Sơn: vây hạ thành Xương Giang, trận Chi Lăng – Xương Giang (1427)) |
| Kỵ binh Minh | lính Minh cưỡi ngựa nâu | Giáo dài | 16 | 160 | 1.15 | 245 | assassin | Xung phong, Liên hoàn đao | 96 / 32 / 9–19 | Đạo viện binh của Liễu Thăng tiến sang qua ải Chi Lăng vào năm 1427. (Bản kỷ, Kỷ Nhà Lê, Thái Tổ hoàng đế, năm Đinh Mùi (1427)) |
| Ụ súng | vòng bao cát, nòng súng nhô lên (công sự, không có người) | súng | 21 | 210 | 1.1 | 0 | ranged | Mưa tên | 120 / 40 / 12–26 | Muốn tiến sát cứ điểm, bộ đội đào hệ thống giao thông hào chằng chịt quanh lòng chảo. (Lịch sử 9, Lịch sử 12: kháng chiến chống thực dân Pháp, chiến dịch Điện Biên Phủ 1954) |
| Xe tăng | xe tăng hạng nhẹ màu ô liu, tháp pháo, nòng dài, xích hai bên (cỗ máy, không vẽ người) | pháo | 25 | 330 | 1.3 | 110 | ranged | Chấn địa | 160 / 52 / 16–32 | Xe tăng ở Điện Biên Phủ được chở lên bằng máy bay theo từng bộ phận rồi lắp lại trong lòng chảo. (Tư liệu trưng bày về tập đoàn cứ điểm Điện Biên Phủ và chiến dịch năm 1954) |
| Thuyền chiến Nguyên | ThuyenNguyen | — | 11 | 240 | 1.0 | 0 | ranged | Mưa tên | 64 / 22 / 8–16 | Năm 1285, cánh quân Toa Đô theo đường thuỷ kéo về; nhà Trần chặn đánh ở bến Hàm Tử, rồi thắng lớn ở Chương Dương. (Bản kỷ, Kỷ Nhà Trần, Nhân Tông hoàng đế, năm Ất Dậu (1285)) |
| Lính khiên Minh | mũ sắt hình bát có chóp nhọn và tua đỏ, áo bông đỏ | Kiếm thép | 17 | 190 | 1.1 | 170 | tank | Thế thủ, Phóng lao | 100 / 34 / 10–20 | Cuối năm 1426, nghĩa quân Lam Sơn vây thành Đông Quan; quân Minh do Vương Thông cầm đầu đóng chặt cửa thành cố thủ. (Bản kỷ, Kỷ Nhà Lê, Thái Tổ hoàng đế, năm Bính Ngọ (1426)) |
| Tàu chiến | TauChien | pháo | 23 | 300 | 1.25 | 0 | ranged | Chấn địa | 145 / 48 / 15–30 | Thu đông 1947, một cánh quân Pháp theo đường thuỷ ngược sông Hồng vào sông Lô, tiến lên Tuyên Quang. (Chiến dịch Việt Bắc thu – đông 1947: binh đoàn thuỷ bộ của Pháp theo sông Hồng, sông Lô; trận phục kích Chí Đám (24/10/1947)) |
| Ca nô | CaNo | súng | 21 | 170 | 1.0 | 0 | ranged | Phi tiêu | 110 / 38 / 12–24 | Ngày 24 tháng 10 năm 1947, ở Chí Đám vùng Đoan Hùng, bộ đội phục kích đoàn tàu chiến địch trên sông Lô. (Chiến dịch Việt Bắc thu – đông 1947: binh đoàn thuỷ bộ của Pháp theo sông Hồng, sông Lô; trận phục kích Chí Đám (24/10/1947)) |
| Máy bắn đá Tống | MayBanDa | — | 8 | 170 | 0.85 | 0 | ranged | Chấn địa | 46 / 16 / 5–12 | Năm 1077, quân Tống đóng ở bờ bắc sông Như Nguyệt, dựng máy bắn đá và bắc cầu phao để vượt sông, nhưng đều bị đánh lui. (Bản kỷ, Kỷ Nhà Lý, Nhân Tông hoàng đế, năm Đinh Tỵ (1077)) |
| Thuyền lương Minh | ThuyenLuongMinh | — | 13 | 250 | 0.9 | 0 | ranged | Mưa tên | 74 / 25 / 14–26 | Năm 1425, Đô ty nhà Minh là Trương Hùng chở lương bằng hơn 300 chiếc thuyền đến Diễn Châu, bị Đinh Lễ phục binh đánh, cướp được thuyền lương. (Bản kỷ, Kỷ Nhà Lê, Thái Tổ hoàng đế, năm Ất Tỵ (1425)) |
| Xe vận tải | XeVanTai | súng | 21 | 220 | 1.0 | 0 | ranged | Phi tiêu | 118 / 40 / 14–28 | Thu đông 1947, đường số 4 dọc biên giới Cao Bằng – Lạng Sơn là đường tiến quân và tiếp tế của Pháp; các đoàn xe thường bị bộ đội phục kích. (Chiến dịch Việt Bắc thu – đông 1947: hướng đường số 4, trận phục kích đèo Bông Lau (30/10/1947)) |
| Xe bọc thép | XeBocThep | súng | 23 | 280 | 1.2 | 120 | ranged | Phi tiêu, Chấn địa | 140 / 46 / 15–30 | Ngày 30 tháng 10 năm 1947, ở đèo Bông Lau trên đường số 4, bộ đội tiêu diệt gọn một đoàn xe cơ giới của Pháp, trong đó có xe bọc thép. (Chiến dịch Việt Bắc thu – đông 1947: hướng đường số 4, trận phục kích đèo Bông Lau (30/10/1947)) |
| Thuỷ binh Nguyên | mũ sắt tròn viền lông, tai che bằng lông, áo choàng cài vạt chéo, đai da | Đao sắt | 12 | 104 | 0.92 | 178 | melee | Phóng lao, Đột kích | 64 / 22 / 7–15 | Cuối năm 1287, thuỷ quân Nguyên theo đường biển tiến vào nước ta, thuyền chiến đi trước, đoàn thuyền lương đi sau. (Bản kỷ, Kỷ Nhà Trần, Nhân Tông hoàng đế, năm Đinh Hợi (1287), tháng 12: Trần Khánh Dư ở Vân Đồn) |
| Thuyền lương Nguyên | thuyền thân sẫm buồm nâu đỏ như thuyền chiến Nguyên, trên boong chất bao lương (chỉ vẽ con thuyền) | — | 13 | 260 | 0.9 | 0 | ranged | Mưa tên | 72 / 24 / 14–26 | Ở Vân Đồn, Trần Khánh Dư đánh đoàn thuyền lương Nguyên; sử chép ông bắt được lương thực khí giới của giặc không xiết kể. (Bản kỷ, Kỷ Nhà Trần, Nhân Tông hoàng đế, năm Đinh Hợi (1287), tháng 12: Trần Khánh Dư ở Vân Đồn) |
| Ụ pháo | khẩu pháo dã chiến màu ô liu: càng pháo, bánh xe, tấm chắn, nòng dài, hai lớp bao cát phía trước (không có người) | pháo | 24 | 290 | 1.25 | 0 | ranged | Chấn địa, Mưa tên | 150 / 50 / 16–32 | Cụm cứ điểm Đông Khê có pháo 105 ly, pháo cối, lô cốt và hầm ngầm. Ngày 16 – 18/9/1950, bộ đội vẫn hạ được, mở màn chiến dịch Biên giới. (Chiến dịch Biên giới thu – đông 1950: trận Đông Khê (16 – 18/9/1950), cụm cứ điểm và lực lượng giữ đồn) |

### Bóng giặc quanh từng di tích

| Chặng | Di tích | Bóng giặc quanh di tích | Kẻ canh mật thư cuối |
|---|---|---|---|
| Những khúc sông giữ nước | Đất hai vua Đường Lâm | Lính Nam Hán | Đầu mục quân Nam Hán |
| Những khúc sông giữ nước | Cửa sông Bạch Đằng năm 938 | Lính Nam Hán, Thuỷ binh Nam Hán | Đầu mục quân Nam Hán |
| Những khúc sông giữ nước | Kinh đô mới ở Cổ Loa | Thuỷ binh Nam Hán, Lính Nam Hán | Đầu mục thuỷ binh Nam Hán |
| Những khúc sông giữ nước | Phòng tuyến Như Nguyệt | Lính Tống, Cung thủ Tống | Chỉ huy toán lính Tống |
| Những khúc sông giữ nước | Đền Trần và lời thề giữ nước | Lính Nguyên | Bách hộ quân Nguyên |
| Những khúc sông giữ nước | Kiếp Bạc và bài hịch thức tỉnh | Lính Nguyên, Cung thủ Nguyên | Bách hộ quân Nguyên |
| Những khúc sông giữ nước | Đoàn thuyền lương Vân Đồn | Lính Nguyên | Bách hộ quân Nguyên |
| Những khúc sông giữ nước | Bãi cọc Yên Giang năm 1288 | Cung thủ Nguyên, Lính Nguyên | Tướng thuỷ quân Nguyên (trùm cả chặng) |
| Mười năm nếm mật nằm gai | Dựng cờ ở Lam Sơn | Lính Minh | Bách hộ quân Minh |
| Mười năm nếm mật nằm gai | Người mặc áo bào chủ tướng | Lính Minh, Cung thủ Minh | Bách hộ quân Minh |
| Mười năm nếm mật nằm gai | Kế vào Nghệ An | Lính Minh | Bách hộ quân Minh |
| Mười năm nếm mật nằm gai | Cánh đồng Tốt Động | Cung thủ Minh, Lính Minh | Bách hộ cung thủ Minh |
| Mười năm nếm mật nằm gai | Ải Chi Lăng năm 1427 | Lính trấn thủ Minh, Cung thủ Minh | Thiên hộ trấn thủ Minh |
| Mười năm nếm mật nằm gai | Hồ Gươm và áng văn thiên cổ | Lính trấn thủ Minh | Tướng trấn thủ quân Minh (trùm cả chặng) |
| Từ Tân Trào đến Điện Biên | Cây đa Tân Trào | Đồn bốt | Đồn bốt kiên cố |
| Từ Tân Trào đến Điện Biên | Ba Đình và Hà Nội 60 ngày đêm | Đồn bốt | Đồn bốt kiên cố |
| Từ Tân Trào đến Điện Biên | Đông Khê mở màn Biên giới 1950 | Lô cốt | Lô cốt chỉ huy |
| Từ Tân Trào đến Điện Biên | Lòng chảo Điện Biên Phủ | Lô cốt | Cứ điểm kiên cố (trùm cả chặng) |

### Trùm và kẻ mạnh nhất vùng

| Ở đâu | Tên | Ngoại hình | Cấp | Máu | Chiêu | Thưởng |
|---|---|---|---|---|---|---|
| Mật thư cuối man1 | Tướng thuỷ quân Nguyên | mũ viền lông có chùm lông đỏ, áo choàng đỏ viền vàng | 12 | 420 | Liên hoàn đao, Chấn địa, Mưa tên, Xung phong | 320 KN, 120 tiềm năng, 150 quan |
| Mật thư cuối man2 | Tướng trấn thủ quân Minh | mũ bát viền vàng có tua đỏ, áo đỏ sẫm viền vàng | 20 | 620 | Liên hoàn đao, Khói mù, Mưa tên, Chấn địa, Hồi khí | 600 KN, 220 tiềm năng, 300 quan |
| Mật thư cuối man3 | Cứ điểm kiên cố | khối bê tông có lỗ châu mai, bao cát quanh nóc (công trình, không có người) | 28 | 950 | Phi tiêu, Mưa tên, Chấn địa, Nỏ liên châu | 900 KN, 320 tiềm năng, 450 quan |
| Vùng luyện f_dong_bo_dau | Tướng tiên phong Mông Cổ | tướng Mông Cổ cưỡi ngựa đen | 13 | 420 | Xung phong, Liên hoàn đao, Mưa tên | 300 KN, 110 tiềm năng, 140 quan, 1 thuốc nam; hồi sinh sau 150 giây |
| Vùng luyện f_xuong_giang | Chỉ huy giữ thành Xương Giang | mũ bát viền vàng có tua đỏ, áo đỏ sẫm viền vàng | 19 | 600 | Thế thủ, Liên hoàn đao, Chấn địa, Hồi khí | 520 KN, 190 tiềm năng, 260 quan, 1 thuốc nam; hồi sinh sau 150 giây |
| Vùng luyện f_chuong_duong | Vạn hộ thuỷ quân Nguyên | mũ viền lông có chùm lông đỏ, áo choàng đỏ viền vàng | 13 | 440 | Liên hoàn đao, Mưa tên, Xung phong | 320 KN, 115 tiềm năng, 150 quan, 1 thuốc nam; hồi sinh sau 150 giây |
| Vùng luyện f_dong_quan | Thiên hộ giữ thành Đông Quan | mũ bát viền vàng có tua đỏ, áo đỏ sẫm viền vàng | 21 | 640 | Thế thủ, Liên hoàn đao, Mưa tên, Hồi khí | 560 KN, 200 tiềm năng, 280 quan, 1 thuốc nam; hồi sinh sau 150 giây |
| Vùng luyện f_song_lo | Tàu chỉ huy | TauChien | 25 | 820 | Chấn địa, Mưa tên, Phi tiêu | 700 KN, 250 tiềm năng, 360 quan, 1 thuốc nam; hồi sinh sau 150 giây |
| Vùng luyện f_muong_thanh | Lô cốt chỉ huy phân khu | khối bê tông có lỗ châu mai, bao cát quanh nóc (công trình, không có người) | 27 | 900 | Phi tiêu, Mưa tên, Chấn địa | 800 KN, 280 tiềm năng, 400 quan, 1 thuốc nam; hồi sinh sau 150 giây |
| Vùng luyện f_nhu_nguyet | Chỉ huy doanh trại Tống | mũ sắt có tua đỏ, viền vàng, giáp vảy, quần đỏ | 9 | 320 | Thế thủ, Phóng lao, Liên hoàn đao | 230 KN, 85 tiềm năng, 110 quan, 1 thuốc nam; hồi sinh sau 150 giây |
| Vùng luyện f_dien_chau | Chỉ huy giữ thành Diễn Châu | mũ bát viền vàng có tua đỏ, áo đỏ sẫm viền vàng | 17 | 540 | Thế thủ, Liên hoàn đao, Mưa tên | 440 KN, 160 tiềm năng, 220 quan, 1 thuốc nam; hồi sinh sau 150 giây |
| Vùng luyện f_bong_lau | Xe bọc thép dẫn đầu | XeBocThep | 24 | 780 | Phi tiêu, Chấn địa, Mưa tên | 660 KN, 240 tiềm năng, 340 quan, 1 thuốc nam; hồi sinh sau 150 giây |
| Vùng luyện f_bien_van_don | Thuyền chỉ huy đoàn thuyền lương | thuyền thân sẫm buồm nâu đỏ như thuyền chiến Nguyên, trên boong chất bao lương (chỉ vẽ con thuyền) | 14 | 470 | Mưa tên, Chấn địa, Phi tiêu | 340 KN, 120 tiềm năng, 165 quan, 1 thuốc nam; hồi sinh sau 150 giây |
| Vùng luyện f_le_hoa | Tướng kỵ đạo Vân Nam | tướng Minh cưỡi ngựa nâu | 21 | 620 | Xung phong, Liên hoàn đao, Mưa tên | 540 KN, 195 tiềm năng, 270 quan, 1 thuốc nam; hồi sinh sau 150 giây |
| Vùng luyện f_dong_khe | Trận địa pháo trong đồn | khẩu pháo dã chiến màu ô liu: càng pháo, bánh xe, tấm chắn, nòng dài, hai lớp bao cát phía trước (không có người) | 26 | 860 | Chấn địa, Mưa tên, Phi tiêu | 760 KN, 270 tiềm năng, 380 quan, 1 thuốc nam; hồi sinh sau 150 giây |

## 6. Vùng luyện

Map phụ, mỗi vùng gắn với một sự kiện có thật. Quái hồi sinh sau 30 giây, kẻ mạnh nhất vùng sau
150 giây. Cổng ở mép tây đưa về map chính, đứng đúng chỗ biển chỉ đường.

### Bến Đông Bộ Đầu năm 1258

- Thuộc chặng `man1`, mở khi xong di tích `r_den_tran`; vào bằng biển chỉ đường “Đường ra bến Đông Bộ Đầu”.
- Vùng luyện · bến sông Hồng phía đông kinh thành Thăng Long. Thời tiết `leaf`, nhạc `road`.
- Trại `c1` (kiểu `trai`, ô [26, 11]): Lính Mông Cổ, Cung thủ Mông Cổ, Lính Mông Cổ.
- Trại `c2` (kiểu `trai`, ô [27, 35]): Kỵ binh Mông Cổ, Lính Mông Cổ, Cung thủ Mông Cổ.
- Trại `c3` (kiểu `ben`, ô [46, 23]): Kỵ binh Mông Cổ, Cung thủ Mông Cổ, Kỵ binh Mông Cổ + kẻ mạnh nhất vùng: Tướng tiên phong Mông Cổ.
- Người kể chuyện (hư cấu): Ông lái đò bến Đông. Lời kể:
  - “Cháu đến bến Đông à? Năm 1258, quân Mông Cổ tràn xuống, vua Trần Thái Tông lui quân để giữ sức, giặc vào được kinh thành Thăng Long.” — nguồn: Bản kỷ, Kỷ Nhà Trần, Thái Tông hoàng đế, các năm Đinh Tỵ (1257) và Mậu Ngọ (1258)
  - “Lúc nguy nhất, vua hỏi ý Thái sư Trần Thủ Độ. Ông đáp: “Đầu thần chưa rơi xuống đất, xin bệ hạ đừng lo”.” — nguồn: Bản kỷ, Kỷ Nhà Trần, Thái Tông hoàng đế, các năm Đinh Tỵ (1257) và Mậu Ngọ (1258)
  - “Chẳng bao lâu sau, vua cùng Thái tử ngự lâu thuyền ngược sông, đánh vào bến Đông Bộ Đầu. Quân Mông Cổ thua, rút khỏi Thăng Long.” — nguồn: Bản kỷ, Kỷ Nhà Trần, Thái Tông hoàng đế, các năm Đinh Tỵ (1257) và Mậu Ngọ (1258); Phần cuộc kháng chiến chống quân xâm lược Mông Cổ lần thứ nhất (1258)
  - “Bến ấy ở phía đông kinh thành, bên sông Hồng. Ghi chú sử học: vị trí chính xác còn được nghiên cứu, nhiều người cho là quanh khu Hòe Nhai – Hàng Than, gần cầu Long Biên của Hà Nội bây giờ.” — nguồn: Phần cuộc kháng chiến chống quân xâm lược Mông Cổ lần thứ nhất (1258)
  - “Bóng giặc trong ký ức còn quanh quẩn ở bờ sông đấy. Đánh được chúng thì cháu cứng tay lên. Nhưng nhớ cho: đó là phần trò chơi, chuyện thật là chuyện ông vừa kể.” — lời dặn của nhân vật hư cấu
- Câu hỏi: Năm 1258, trận đánh nào đã đẩy quân Mông Cổ ra khỏi Thăng Long? Đáp án: Trận Đông Bộ Đầu. Trả lời đúng lần đầu thưởng (120, 30, 50).
- Lính NPC (LinhDaiViet): Thuyền đã sẵn, chỉ chờ lệnh là ngược sông về bến Đông. / Giữ chặt mái chèo, nước sông Hồng chảy xiết lắm.
- Lính NPC (LinhDaiViet2): Kỵ binh của giặc phi nhanh lắm, đứng lệch khỏi đường lao của chúng mà đánh. / Cung thủ giặc bắn từ xa, phải áp sát mới hạ được.

### Thành Xương Giang năm 1427

- Thuộc chặng `man2`, mở khi xong di tích `r_tot_dong`; vào bằng biển chỉ đường “Đường lên thành Xương Giang”.
- Vùng luyện · thành đất của quân Minh bên sông Thương. Thời tiết `leaf`, nhạc `temple`.
- Trại `c1` (kiểu `trai`, ô [25, 11]): Lính giữ thành Minh, Cung thủ Minh, Lính Minh.
- Trại `c2` (kiểu `trai`, ô [26, 33]): Kỵ binh Minh, Lính Minh, Cung thủ Minh.
- Trại `c3` (kiểu `thanh`, ô [48, 22]): Lính giữ thành Minh, Kỵ binh Minh, Cung thủ Minh + kẻ mạnh nhất vùng: Chỉ huy giữ thành Xương Giang.
- Người kể chuyện (hư cấu): Người lính già Lam Sơn. Lời kể:
  - “Thành Xương Giang do quân Minh đắp, nằm trên đường từ Lạng Sơn về thành Đông Quan. Đất ấy trước tháng 7/2025 thuộc thành phố Bắc Giang, nay thuộc tỉnh Bắc Ninh.” — nguồn: Phần khởi nghĩa Lam Sơn: vây hạ thành Xương Giang, trận Chi Lăng – Xương Giang (1427)
  - “Năm 1427, nghĩa quân Lam Sơn vây thành nhiều tháng. Ngày 28 tháng 9 năm 1427 thành bị hạ, trước khi đạo viện binh của Liễu Thăng kịp tới.” — nguồn: Phần khởi nghĩa Lam Sơn: vây hạ thành Xương Giang, trận Chi Lăng – Xương Giang (1427); Bản kỷ, Kỷ Nhà Lê, Thái Tổ hoàng đế, năm Đinh Mùi (1427)
  - “Mất Xương Giang, viện binh mất chỗ dựa giữa đường. Sau trận Chi Lăng, đạo quân ấy bị vây và đánh tan ở cánh đồng Xương Giang.” — nguồn: Bản kỷ, Kỷ Nhà Lê, Thái Tổ hoàng đế, năm Đinh Mùi (1427)
  - “Bóng giặc vẫn còn quanh thành trong ký ức của ta. Cháu cứ luyện tay ở đây, nhưng đừng quên đó chỉ là trò chơi.” — lời dặn của nhân vật hư cấu
- Câu hỏi: Vì sao việc hạ thành Xương Giang trước khi viện binh Minh tới lại quan trọng? Đáp án: Viện binh mất chỗ dựa giữa đường tiến về Đông Quan. Trả lời đúng lần đầu thưởng (120, 30, 50).
- Lính NPC (NghiaQuan): Vây thành mấy tháng rồi, anh em vẫn giữ vững vòng vây. / Lính giữ thành giơ khiên đỡ đòn, phải chờ hắn hạ khiên mới đánh.
- Lính NPC (NghiaQuan): Kỵ binh Minh lao rất mạnh, thấy vạch đỏ thì tránh sang bên. / Nỏ của giặc bắn chậm mà nặng, né được phát đầu là áp sát được.

### Cánh đồng Mường Thanh năm 1954

- Thuộc chặng `man3`, mở khi xong di tích `r_ba_dinh`; vào bằng biển chỉ đường “Đường lên lòng chảo Điện Biên”.
- Vùng luyện · lòng chảo Điện Biên Phủ, sông Nậm Rốm chảy qua. Thời tiết `fog`, nhạc `sad`.
- Trại `c1` (kiểu `doi`, ô [24, 11]): Ụ súng, Đồn bốt, Ụ súng.
- Trại `c2` (kiểu `doi`, ô [25, 33]): Xe tăng, Ụ súng, Đồn bốt.
- Trại `c3` (kiểu `dien_bien`, ô [52, 22]): Xe tăng, Lô cốt, Ụ súng + kẻ mạnh nhất vùng: Lô cốt chỉ huy phân khu.
- Người kể chuyện (hư cấu): Cựu chiến binh Điện Biên. Lời kể:
  - “Điện Biên Phủ là một thung lũng lòng chảo, sông Nậm Rốm chảy qua cánh đồng Mường Thanh.” — nguồn: Tư liệu trưng bày về tập đoàn cứ điểm Điện Biên Phủ và chiến dịch năm 1954
  - “Quân Pháp xây ở đây một tập đoàn cứ điểm gồm 49 cứ điểm, chia thành ba phân khu: Bắc, Trung tâm và Nam, có cả sân bay Mường Thanh.” — nguồn: Tư liệu trưng bày về tập đoàn cứ điểm Điện Biên Phủ và chiến dịch năm 1954
  - “Họ còn chở xe tăng tháo rời bằng máy bay lên rồi lắp lại trong lòng chảo.” — nguồn: Tư liệu trưng bày về tập đoàn cứ điểm Điện Biên Phủ và chiến dịch năm 1954
  - “Chiến dịch kéo dài 56 ngày đêm, từ 13 tháng 3 đến 7 tháng 5 năm 1954.” — nguồn: Tư liệu trưng bày về tập đoàn cứ điểm Điện Biên Phủ và chiến dịch năm 1954
  - “Ở vùng này trò chơi chỉ cho cháu phá ụ súng, đồn bốt, xe tăng. Ông không muốn vẽ người ngã xuống ở trận đánh mà đồng đội ông đã nằm lại.” — lời dặn của nhân vật hư cấu
- Câu hỏi: Tập đoàn cứ điểm Điện Biên Phủ được chia thành mấy phân khu? Đáp án: Ba phân khu. Trả lời đúng lần đầu thưởng (120, 30, 50).
- Lính NPC (BoDoi): Đường hào cứ đào sát dần vào cứ điểm, đêm nào cũng đào. / Khẩu hiệu bây giờ là đánh chắc, tiến chắc.
- Lính NPC (BoDoi): Xe tăng chạy chậm mà bắn đau, đứng lệch khỏi nòng pháo của nó. / Ụ súng bắn liên tục, phải né rồi áp sát mà phá.

### Chương Dương – Hàm Tử năm 1285

- Thuộc chặng `man1`, mở khi xong di tích `r_kiep_bac`; vào bằng biển chỉ đường “Đường ra bến Chương Dương”.
- Vùng luyện · bến sông Hồng, nơi quân Trần đánh thuyền giặc năm 1285. Thời tiết `leaf`, nhạc `road`.
- Trại `c1` (kiểu `trai`, ô [24, 11]): Lính Nguyên, Cung thủ Nguyên, Lính Nguyên.
- Trại `c2` (kiểu `ben`, ô [40, 34]): Thuyền chiến Nguyên, Lính Nguyên, Thuyền chiến Nguyên.
- Trại `c3` (kiểu `ben`, ô [44, 15]): Thuyền chiến Nguyên, Cung thủ Nguyên, Thuyền chiến Nguyên + kẻ mạnh nhất vùng: Vạn hộ thuỷ quân Nguyên.
- Người kể chuyện (hư cấu): Ông lão làng Chương Dương. Lời kể:
  - “Năm 1285 quân Nguyên kéo sang lần thứ hai. Đầu năm ấy giặc chiếm được Thăng Long, nhà Trần lui ra để giữ sức.” — nguồn: Bản kỷ, Kỷ Nhà Trần, Nhân Tông hoàng đế, năm Ất Dậu (1285); Lịch sử 7, Lịch sử 10: kháng chiến chống Tống, chống Mông – Nguyên, khởi nghĩa Lam Sơn
  - “Giữa năm 1285 quân Trần phản công. Trần Nhật Duật đánh tan binh thuyền của Toa Đô ở bến Hàm Tử.” — nguồn: Bản kỷ, Kỷ Nhà Trần, Nhân Tông hoàng đế, năm Ất Dậu (1285); Lịch sử 7, Lịch sử 10: kháng chiến chống Tống, chống Mông – Nguyên, khởi nghĩa Lam Sơn
  - “Tiếp đó, Trần Quang Khải đánh tan giặc ở bến Chương Dương rồi kéo về giải phóng kinh thành Thăng Long.” — nguồn: Bản kỷ, Kỷ Nhà Trần, Nhân Tông hoàng đế, năm Ất Dậu (1285); Lịch sử 7, Lịch sử 10: kháng chiến chống Tống, chống Mông – Nguyên, khởi nghĩa Lam Sơn
  - “Phò giá về kinh, Trần Quang Khải làm bài thơ có câu: “Chương Dương cướp giáo giặc, Hàm Tử bắt quân thù.”” — nguồn: Ngữ văn 7: Phò giá về kinh (Tụng giá hoàn kinh sư) của Trần Quang Khải, bản dịch thơ của Trần Trọng Kim
  - “Bến Chương Dương nay ở vùng Thường Tín, Hà Nội; bến Hàm Tử ở vùng Khoái Châu, Hưng Yên.” — nguồn: Lịch sử 7, Lịch sử 10: kháng chiến chống Tống, chống Mông – Nguyên, khởi nghĩa Lam Sơn
  - “Bóng giặc trong ký ức còn quanh quẩn nơi này. Cháu cứ luyện tay, nhưng nhớ cho: đó là phần trò chơi, chuyện thật là chuyện ta vừa kể.” — lời dặn của nhân vật hư cấu
- Câu hỏi: Năm 1285, ai chỉ huy trận đánh thắng quân Nguyên ở bến Chương Dương? Đáp án: Trần Quang Khải. Trả lời đúng lần đầu thưởng (120, 30, 50).
- Lính NPC (LinhDaiViet): Thuyền giặc bắn tên từ xa, cứ đứng sát bờ mà đánh. / Nước lên rồi, thuyền ta sẵn sàng xuất bến.
- Lính NPC (LinhDaiViet2): Giặc đông nhưng xa nhà, thiếu lương. Giữ vững là thắng. / Đánh xong bến này là về kinh thành được rồi.

### Vây thành Đông Quan năm 1427

- Thuộc chặng `man2`, mở khi xong di tích `r_chi_lang`; vào bằng biển chỉ đường “Đường xuống bến Bồ Đề”.
- Vùng luyện · bến Bồ Đề bờ bắc sông Nhị, nhìn sang thành Đông Quan. Thời tiết `leaf`, nhạc `temple`.
- Trại `c1` (kiểu `trai`, ô [21, 34]): Lính khiên Minh, Cung thủ Minh, Lính Minh.
- Trại `c2` (kiểu `trai`, ô [58, 34]): Lính khiên Minh, Lính giữ thành Minh, Cung thủ Minh.
- Trại `c3` (kiểu `thanh`, ô [40, 31]): Lính khiên Minh, Cung thủ Minh, Lính trấn thủ Minh + kẻ mạnh nhất vùng: Thiên hộ giữ thành Đông Quan.
- Người kể chuyện (hư cấu): Bà cụ bán nước bến Bồ Đề. Lời kể:
  - “Cuối năm 1426, Lê Lợi và Nguyễn Trãi dời đại bản doanh từ Đông Phù Liệt về bến Bồ Đề, bờ bắc sông Nhị, nhìn sang thành Đông Quan.” — nguồn: Bản kỷ, Kỷ Nhà Lê, Thái Tổ hoàng đế, năm Bính Ngọ (1426); Phần khởi nghĩa Lam Sơn: vây hạ thành Xương Giang, trận Chi Lăng – Xương Giang (1427)
  - “Quân Minh do Vương Thông cầm đầu đóng chặt cửa thành. Nghĩa quân vừa vây đánh, vừa gửi thư dụ hàng.” — nguồn: Bản kỷ, Kỷ Nhà Lê, Thái Tổ hoàng đế, năm Bính Ngọ (1426)
  - “Nhiều bức thư ấy do Nguyễn Trãi viết thay Lê Lợi, nay còn trong Quân trung từ mệnh tập.” — nguồn: Quân trung từ mệnh tập: các thư gửi Vương Thông khi vây thành Đông Quan
  - “Viện binh bị đánh tan ở Chi Lăng, Xương Giang, Vương Thông hết đường cứu. Ngày 10 tháng 12 năm 1427, Hội thề Đông Quan diễn ra; cuối tháng ấy quân Minh bắt đầu rút về nước.” — nguồn: Bản kỷ, Kỷ Nhà Lê, Thái Tổ hoàng đế, năm Đinh Mùi (1427); Lịch sử 7, Lịch sử 10: kháng chiến chống Tống, chống Mông – Nguyên, khởi nghĩa Lam Sơn
  - “Bến Bồ Đề nay ở vùng Long Biên, Hà Nội.” — nguồn: Phần khởi nghĩa Lam Sơn: vây hạ thành Xương Giang, trận Chi Lăng – Xương Giang (1427)
  - “Bóng giặc trong ký ức còn quanh quẩn nơi này. Cháu cứ luyện tay, nhưng nhớ cho: đó là phần trò chơi, chuyện thật là chuyện ta vừa kể.” — lời dặn của nhân vật hư cấu
- Câu hỏi: Khi vây thành Đông Quan, Lê Lợi và Nguyễn Trãi đặt đại bản doanh ở đâu? Đáp án: Bến Bồ Đề. Trả lời đúng lần đầu thưởng (120, 30, 50).
- Lính NPC (NghiaQuan): Vây chặt bốn mặt, giặc trong thành chỉ còn trông vào viện binh. / Lính khiên giơ khiên lên thì khoan đánh, chờ hắn hạ khiên.
- Lính NPC (NghiaQuan): Thư dụ hàng gửi vào thành rồi, giờ chờ xem Vương Thông trả lời ra sao. / Qua cầu là tới chân thành, cẩn thận cung nỏ trên mặt luỹ.

### Sông Lô năm 1947

- Thuộc chặng `man3`, mở khi xong di tích `r_tan_trao`; vào bằng biển chỉ đường “Đường ra bờ sông Lô”.
- Vùng luyện · khúc sông Lô vùng Đoan Hùng, thu đông năm 1947. Thời tiết `fog`, nhạc `sad`.
- Trại `c1` (kiểu `ben`, ô [32, 12]): Tàu chiến, Ca nô, Đồn bốt.
- Trại `c2` (kiểu `doi`, ô [22, 34]): Đồn bốt, Ụ súng, Đồn bốt.
- Trại `c3` (kiểu `ben`, ô [37, 30]): Ca nô, Tàu chiến, Ca nô + kẻ mạnh nhất vùng: Tàu chỉ huy.
- Người kể chuyện (hư cấu): Cựu chiến binh pháo binh. Lời kể:
  - “Thu đông năm 1947, quân Pháp tiến công lên Việt Bắc, mong đánh nhanh thắng nhanh, phá cơ quan đầu não kháng chiến.” — nguồn: Lịch sử 9, Lịch sử 12: chiến dịch Việt Bắc thu – đông 1947
  - “Một cánh quân thuỷ bộ theo đường sông, ngược sông Hồng vào sông Lô, tiến lên Tuyên Quang.” — nguồn: Chiến dịch Việt Bắc thu – đông 1947: binh đoàn thuỷ bộ của Pháp theo sông Hồng, sông Lô; trận phục kích Chí Đám (24/10/1947); Lịch sử 9, Lịch sử 12: chiến dịch Việt Bắc thu – đông 1947
  - “Ngày 24 tháng 10 năm 1947, ở Chí Đám vùng Đoan Hùng, quân dân ta phục kích, đánh tan đoàn tàu chiến của địch.” — nguồn: Chiến dịch Việt Bắc thu – đông 1947: binh đoàn thuỷ bộ của Pháp theo sông Hồng, sông Lô; trận phục kích Chí Đám (24/10/1947)
  - “Nhạc sĩ Văn Cao viết Trường ca Sông Lô sau chiến thắng ấy; bài hát công bố năm 1948.” — nguồn: Trường ca Sông Lô
  - “Đoan Hùng nay thuộc tỉnh Phú Thọ.” — nguồn: Chiến dịch Việt Bắc thu – đông 1947: binh đoàn thuỷ bộ của Pháp theo sông Hồng, sông Lô; trận phục kích Chí Đám (24/10/1947)
  - “Ở vùng này trò chơi chỉ có tàu, ca nô, đồn bốt để phá, không vẽ người. Chuyện thật là chuyện bác vừa kể.” — lời dặn của nhân vật hư cấu
- Câu hỏi: Trong chiến dịch Việt Bắc thu – đông 1947, bộ đội ta phục kích đoàn tàu chiến Pháp trên con sông nào? Đáp án: Sông Lô. Trả lời đúng lần đầu thưởng (120, 30, 50).
- Lính NPC (BoDoi): Pháo đặt sẵn trên bờ rồi, chờ tàu địch lọt vào khúc sông này. / Ca nô chạy nhanh, bắn liên tục; né rồi hãy áp sát.
- Lính NPC (BoDoi): Tàu chiến bắn đạn pháo chậm mà đau, đứng lệch khỏi nòng. / Giữ kín, chưa có lệnh thì chưa bắn.

### Sông Như Nguyệt năm 1077

- Thuộc chặng `man1`, mở khi xong di tích `r_nhu_nguyet`; vào bằng biển chỉ đường “Đường ra phòng tuyến Như Nguyệt”.
- Vùng luyện · bờ bắc sông Như Nguyệt, nơi quân Tống đóng trại. Thời tiết `leaf`, nhạc `road`.
- Trại `c1` (kiểu `trai`, ô [17, 12]): Lính Tống, Cung thủ Tống, Lính Tống.
- Trại `c2` (kiểu `trai`, ô [40, 15]): Máy bắn đá Tống, Lính Tống, Máy bắn đá Tống.
- Trại `c3` (kiểu `trai`, ô [61, 11]): Máy bắn đá Tống, Cung thủ Tống, Lính Tống + kẻ mạnh nhất vùng: Chỉ huy doanh trại Tống.
- Người kể chuyện (hư cấu): Cụ từ giữ đền bên sông Cầu. Lời kể:
  - “Năm 1077, quân Tống kéo sang theo hai đường: Quách Quỳ chỉ huy cánh quân bộ, Hoà Mâu chỉ huy cánh quân thuỷ.” — nguồn: Bản kỷ, Kỷ Nhà Lý, Nhân Tông hoàng đế, năm Đinh Tỵ (1077); Lịch sử 7, Lịch sử 10: kháng chiến chống Tống, chống Mông – Nguyên, khởi nghĩa Lam Sơn
  - “Lý Thường Kiệt chọn sông Như Nguyệt vì khúc sông này chặn ngang các ngả đường bộ từ phía bắc về Thăng Long. Bờ nam đắp luỹ đất, ngoài luỹ cắm cọc tre dày.” — nguồn: Bản kỷ, Kỷ Nhà Lý, Nhân Tông hoàng đế, năm Đinh Tỵ (1077); Giai đoạn Lý – Trần
  - “Quân Tống đóng ở bờ bắc, dựng máy bắn đá, bắc cầu phao, nhiều lần vượt sông đều bị đánh lui.” — nguồn: Bản kỷ, Kỷ Nhà Lý, Nhân Tông hoàng đế, năm Đinh Tỵ (1077)
  - “Cánh quân thuỷ của giặc bị thuỷ quân nhà Lý chặn đánh ở vùng ven biển Đông Bắc, không vào hợp được với quân bộ.” — nguồn: Lịch sử 7, Lịch sử 10: kháng chiến chống Tống, chống Mông – Nguyên, khởi nghĩa Lam Sơn
  - “Có lần quân ta lặng lẽ vượt sông, đánh úp doanh trại giặc. Quân Tống lại khổ vì khí hậu, bệnh tật, hao mất rất nhiều người.” — nguồn: Bản kỷ, Kỷ Nhà Lý, Nhân Tông hoàng đế, năm Đinh Tỵ (1077); Giai đoạn Lý – Trần
  - “Rồi Lý Thường Kiệt chủ động đề nghị giảng hoà, quân Tống rút về nước.” — nguồn: Lịch sử 7, Lịch sử 10: kháng chiến chống Tống, chống Mông – Nguyên, khởi nghĩa Lam Sơn
  - “Sông Như Nguyệt là khúc sông Cầu chảy qua vùng Yên Phong, Bắc Ninh ngày nay.” — nguồn: Giai đoạn Lý – Trần
  - “Bóng giặc trong ký ức còn quanh quẩn nơi này. Cháu cứ luyện tay, nhưng nhớ cho: đó là phần trò chơi, chuyện thật là chuyện ta vừa kể.” — lời dặn của nhân vật hư cấu
- Câu hỏi: Năm 1077, quân Tống dựng máy bắn đá, bắc cầu phao để vượt con sông nào nhưng đều bị đánh lui? Đáp án: Sông Như Nguyệt. Trả lời đúng lần đầu thưởng (120, 30, 50).
- Lính NPC (LinhDaiViet): Luỹ đất bờ nam cao lắm, ngoài luỹ còn cọc tre dày. / Giặc bắc cầu phao sang là ta đánh bật lại.
- Lính NPC (LinhDaiViet2): Máy bắn đá của giặc ném đá qua sông, thấy đá bay tới thì tránh sang bên. / Sang bờ bắc phải đánh nhanh, đừng để giặc kịp dàn trận.

### Diễn Châu năm 1425

- Thuộc chặng `man2`, mở khi xong di tích `r_tra_lan`; vào bằng biển chỉ đường “Đường ra Diễn Châu”.
- Vùng luyện · bến sông và thành Diễn Châu của quân Minh. Thời tiết `leaf`, nhạc `temple`.
- Trại `c1` (kiểu `trai`, ô [18, 33]): Lính Minh, Cung thủ Minh, Lính Minh.
- Trại `c2` (kiểu `ben`, ô [46, 31]): Thuyền lương Minh, Lính Minh, Thuyền lương Minh.
- Trại `c3` (kiểu `thanh`, ô [34, 12]): Lính giữ thành Minh, Cung thủ Minh, Lính giữ thành Minh + kẻ mạnh nhất vùng: Chỉ huy giữ thành Diễn Châu.
- Người kể chuyện (hư cấu): Bà cụ làng chài Diễn Châu. Lời kể:
  - “Cuối năm 1424, nghĩa quân Lam Sơn vào Nghệ An, vây thành Trà Lân hơn một tháng; tướng giữ thành là Cầm Bành phải ra hàng.” — nguồn: Bản kỷ, Kỷ Nhà Lê, Thái Tổ hoàng đế, năm Giáp Thìn (1424)
  - “Ở cửa Khả Lưu, nghĩa quân nhử quân Minh vào chỗ phục kích; ở Bồ Ải lại đặt phục binh nơi hiểm, đánh tan giặc, bắt sống Đô ty Chu Kiệt.” — nguồn: Bản kỷ, Kỷ Nhà Lê, Thái Tổ hoàng đế, năm Giáp Thìn (1424)
  - “Tháng 5 năm Ất Tỵ (1425), Tư không Lê Lễ (vốn họ Đinh, tức Đinh Lễ) đi tuần ở Diễn Châu, đặt sẵn phục binh. Đô ty nhà Minh là Trương Hùng đem hơn 300 thuyền chở lương từ Đông Quan đến.” — nguồn: Bản kỷ, Kỷ Nhà Lê, Thái Tổ hoàng đế, năm Ất Tỵ (1425)
  - “Quân phục bất ngờ đánh ra, Trương Hùng tháo chạy. Lê Lễ cướp được thuyền lương, đuổi đánh đến tận thành Tây Đô. Đến giữa năm 1425, nghĩa quân đã làm chủ Thanh Hoá, Diễn Châu và Nghệ An.” — nguồn: Bản kỷ, Kỷ Nhà Lê, Thái Tổ hoàng đế, năm Ất Tỵ (1425)
  - “Tháng 8 năm ấy, Trần Nguyên Hãn đem hơn nghìn quân cùng voi chiến theo đường bộ, Lê Ngân đem thuyền chiến theo đường biển, tiến vào giải phóng Tân Bình, Thuận Hoá.” — nguồn: Bản kỷ, Kỷ Nhà Lê, Thái Tổ hoàng đế, năm Ất Tỵ (1425); Lịch sử 7, Lịch sử 10: kháng chiến chống Tống, chống Mông – Nguyên, khởi nghĩa Lam Sơn
  - “Diễn Châu nay là vùng Diễn Châu, tỉnh Nghệ An.” — nguồn: Bản kỷ, Kỷ Nhà Lê, Thái Tổ hoàng đế, năm Ất Tỵ (1425)
  - “Bóng giặc trong ký ức còn quanh quẩn nơi này. Cháu cứ luyện tay, nhưng nhớ cho: đó là phần trò chơi, chuyện thật là chuyện bà vừa kể.” — lời dặn của nhân vật hư cấu
- Câu hỏi: Năm 1425, tướng nào của nghĩa quân Lam Sơn phục binh ở Diễn Châu, cướp được đoàn thuyền lương của Đô ty Trương Hùng? Đáp án: Đinh Lễ. Trả lời đúng lần đầu thưởng (120, 30, 50).
- Lính NPC (NghiaQuan): Thuyền lương giặc neo ngoài bến, đứng ở mép bờ mà đánh. / Thu được thuyền lương là nghĩa quân có thêm cái ăn.
- Lính NPC (NghiaQuan): Giặc trong thành Diễn Châu còn đóng chặt cửa, ta vây dần. / Nghệ An đã về tay nghĩa quân, giờ đến lượt Diễn Châu.

### Đường số 4 năm 1947

- Thuộc chặng `man3`, mở khi xong di tích `r_ba_dinh`; vào bằng biển chỉ đường “Đường lên đèo Bông Lau”.
- Vùng luyện · đèo Bông Lau trên đường số 4, thu đông năm 1947. Thời tiết `fog`, nhạc `sad`.
- Trại `c1` (kiểu `deo`, ô [23, 25]): Đồn bốt, Ụ súng, Xe vận tải.
- Trại `c2` (kiểu `deo`, ô [42, 21]): Xe vận tải, Xe bọc thép, Xe vận tải.
- Trại `c3` (kiểu `deo`, ô [61, 22]): Xe bọc thép, Xe vận tải, Ụ súng + kẻ mạnh nhất vùng: Xe bọc thép dẫn đầu.
- Người kể chuyện (hư cấu): Cựu chiến binh đường số 4. Lời kể:
  - “Thu đông 1947, Pháp đánh lên Việt Bắc. Một binh đoàn bộ của chúng theo đường số 4 từ Lạng Sơn đánh lên Cao Bằng, chiếm các cứ điểm dọc đường.” — nguồn: Lịch sử 9, Lịch sử 12: chiến dịch Việt Bắc thu – đông 1947; Chiến dịch Việt Bắc thu – đông 1947: hướng đường số 4, trận phục kích đèo Bông Lau (30/10/1947)
  - “Ngày 30 tháng 10 năm 1947, bộ đội phục kích ở đèo Bông Lau trên đường số 4, tiêu diệt gọn một đoàn xe cơ giới của địch, có cả xe bọc thép, thu nhiều vũ khí. Đó là trận phục kích đầu tiên trên đường số 4 trong chiến dịch.” — nguồn: Chiến dịch Việt Bắc thu – đông 1947: hướng đường số 4, trận phục kích đèo Bông Lau (30/10/1947)
  - “Đường đèo quanh co, một bên núi dựng, một bên khe sâu. Từ đó đường số 4 thành nỗi khiếp sợ của các đoàn xe Pháp. Đèo nay thuộc vùng Tràng Định, Lạng Sơn, giáp Cao Bằng.” — nguồn: Chiến dịch Việt Bắc thu – đông 1947: hướng đường số 4, trận phục kích đèo Bông Lau (30/10/1947)
  - “Đến cuối năm 1947, cuộc tiến công lên Việt Bắc của Pháp thất bại.” — nguồn: Lịch sử 9, Lịch sử 12: chiến dịch Việt Bắc thu – đông 1947
  - “Ba năm sau, chiến dịch Biên giới 1950 mở màn ở Đông Khê, cũng trên con đường này.” — nguồn: Chiến dịch Biên giới 1950
  - “Ở vùng này trò chơi chỉ có xe, đồn bốt, ụ súng để phá, không vẽ người. Chuyện thật là chuyện bác vừa kể.” — lời dặn của nhân vật hư cấu
- Câu hỏi: Ngày 30/10/1947, bộ đội ta phục kích tiêu diệt cả một đoàn xe Pháp ở đâu? Đáp án: Đèo Bông Lau trên đường số 4. Trả lời đúng lần đầu thưởng (120, 30, 50).
- Lính NPC (BoDoi): Đoàn xe địch phải chạy chậm qua khúc đèo này, đường quanh co lắm. / Xe bọc thép bắn liên tục, né rồi hãy áp sát.
- Lính NPC (BoDoi): Chặn được xe đầu là cả đoàn phải dừng lại. / Giữ kín, chưa có lệnh thì chưa bắn.

### Vân Đồn năm 1288

- Thuộc chặng `man1`, mở khi xong di tích `r_van_don`; vào bằng biển chỉ đường “Đường ra biển Vân Đồn”.
- Vùng luyện · vùng biển đảo Vân Đồn, nơi đoàn thuyền lương Nguyên bị chặn đánh. Thời tiết `fog`, nhạc `road`.
- Trại `c1` (kiểu `trai`, ô [24, 11]): Lính Nguyên, Cung thủ Nguyên, Thuỷ binh Nguyên.
- Trại `c2` (kiểu `dao`, ô [30, 34]): Thuỷ binh Nguyên, Thuyền lương Nguyên, Thuyền chiến Nguyên.
- Trại `c3` (kiểu `ben`, ô [46, 18]): Thuyền lương Nguyên, Thuyền chiến Nguyên, Thuyền lương Nguyên + kẻ mạnh nhất vùng: Thuyền chỉ huy đoàn thuyền lương.
- Người kể chuyện (hư cấu): Ông lão làng chài Vân Đồn. Lời kể:
  - “Cuối năm 1287, quân Nguyên sang đánh nước ta lần thứ ba. Thuỷ quân của chúng theo đường biển kéo vào, đoàn thuyền chở lương đi sau.” — nguồn: Bản kỷ, Kỷ Nhà Trần, Nhân Tông hoàng đế, năm Đinh Hợi (1287), tháng 12: Trần Khánh Dư ở Vân Đồn
  - “Hưng Đạo Vương giao việc giữ vùng biên này cho phó tướng Vân Đồn là Nhân Huệ Vương Trần Khánh Dư.” — nguồn: Bản kỷ, Kỷ Nhà Trần, Nhân Tông hoàng đế, năm Đinh Hợi (1287), tháng 12: Trần Khánh Dư ở Vân Đồn
  - “Trận đầu, Khánh Dư đánh không lại, thuyền chiến giặc vượt qua. Thượng hoàng sai sứ triệu ông về kinh xét tội. Ông xin chịu tội theo quân luật, nhưng xin hoãn cho vài ba ngày.” — nguồn: Bản kỷ, Kỷ Nhà Trần, Nhân Tông hoàng đế, năm Đinh Hợi (1287), tháng 12: Trần Khánh Dư ở Vân Đồn
  - “Rồi đoàn thuyền lương của giặc kéo đến. Khánh Dư đánh, giặc thua. Sử chép ông bắt được “lương thực khí giới của giặc không xiết kể, bắt sống quân giặc rất nhiều”. Thượng hoàng tha tội cho ông.” — nguồn: Bản kỷ, Kỷ Nhà Trần, Nhân Tông hoàng đế, năm Đinh Hợi (1287), tháng 12: Trần Khánh Dư ở Vân Đồn
  - “Người cầm đầu đoàn thuyền lương phía Nguyên là Trương Văn Hổ. Sách vở ghi số thuyền, số lương khác nhau nên ông không kể con số.” — nguồn: Giai đoạn Lý – Trần
  - “Mất lương, quân Nguyên lâm vào cảnh thiếu ăn, phải tính đường rút. Tháng 4 năm 1288, chúng rút theo sông Bạch Đằng thì bị đánh tan.” — nguồn: Bản kỷ, Kỷ Nhà Trần, Nhân Tông hoàng đế, năm Đinh Hợi (1287), tháng 12: Trần Khánh Dư ở Vân Đồn; Lịch sử 7, Lịch sử 10: kháng chiến chống Tống, chống Mông – Nguyên, khởi nghĩa Lam Sơn
  - “Ở đây chỉ còn bóng thuyền giặc trong ký ức. Đứng ở mép bờ là đánh được thuyền neo ngoài biển.” — lời dặn của nhân vật hư cấu
- Câu hỏi: Đầu năm 1288, vị tướng nào phá đoàn thuyền lương của quân Nguyên ở Vân Đồn? Đáp án: Trần Khánh Dư. Trả lời đúng lần đầu thưởng (120, 30, 50).
- Lính NPC (LinhDaiViet): Thuyền lương chở nặng, chạy chậm lắm. Đứng ở mép bờ mà đánh. / Đừng lội ra xa, sóng biển ở đây mạnh hơn sóng sông.
- Lính NPC (LinhDaiViet2): Sương biển dày quá, nhìn kỹ kẻo lạc đường. / Đánh được thuyền lương là giặc phải nhịn đói.

### Ải Lê Hoa năm 1427

- Thuộc chặng `man2`, mở khi xong di tích `r_chi_lang`; vào bằng biển chỉ đường “Đường lên ải Lê Hoa”.
- Vùng luyện · cửa ải chặn đạo viện binh Minh từ Vân Nam sang. Thời tiết `leaf`, nhạc `temple`.
- Trại `c1` (kiểu `trai`, ô [26, 11]): Lính Minh, Cung thủ Minh, Lính Minh.
- Trại `c2` (kiểu `deo`, ô [30, 35]): Lính khiên Minh, Cung thủ Minh, Kỵ binh Minh.
- Trại `c3` (kiểu `ai`, ô [55, 22]): Kỵ binh Minh, Lính khiên Minh, Lính trấn thủ Minh + kẻ mạnh nhất vùng: Tướng kỵ đạo Vân Nam.
- Người kể chuyện (hư cấu): Người lính già giữ ải Lê Hoa. Lời kể:
  - “Năm 1427, nhà Minh sai hai đạo viện binh sang cứu Vương Thông. Đạo chính do Liễu Thăng cầm đầu qua Lạng Sơn, đạo thứ hai do Tổng binh Vân Nam là Mộc Thạnh tiến sang.” — nguồn: Bản kỷ, Kỷ Nhà Lê, Thái Tổ hoàng đế, năm Đinh Mùi (1427)
  - “Từ tháng 4 năm ấy, Lê Lợi đã sai phòng ngự sứ Trần Ban đôn đốc tu sửa ải Lê Hoa.” — nguồn: Bản kỷ, Kỷ Nhà Lê, Thái Tổ hoàng đế, năm Đinh Mùi (1427)
  - “Tháng 10, quân Mộc Thạnh kéo đến cửa ải. Phạm Văn Xảo, Lê Khả đem quân chặn giữ, hai bên cầm cự nhau ở Lê Hoa.” — nguồn: Bản kỷ, Kỷ Nhà Lê, Thái Tổ hoàng đế, năm Đinh Mùi (1427)
  - “Lê Lợi liệu rằng Mộc Thạnh tuổi đã già, từng trải nhiều, thế nào cũng chờ xem đạo Liễu Thăng thắng hay thua rồi mới tiến. Vua mật dặn các tướng chỉ đặt phục binh, chớ giao chiến.” — nguồn: Bản kỷ, Kỷ Nhà Lê, Thái Tổ hoàng đế, năm Đinh Mùi (1427)
  - “Liễu Thăng thua rồi, Lê Lợi sai đưa người bị bắt cùng ấn tín của Liễu Thăng đến cho quân Mộc Thạnh xem. Quân Minh hoảng sợ, tan vỡ. Phạm Văn Xảo, Lê Khả đuổi đánh ở Lãnh Câu, Đan Xá; Mộc Thạnh chỉ còn một mình một ngựa chạy thoát.” — nguồn: Bản kỷ, Kỷ Nhà Lê, Thái Tổ hoàng đế, năm Đinh Mùi (1427)
  - “Bình Ngô đại cáo cũng nhắc chuyện quân Vân Nam bị chặn ở Lê Hoa, nghe tin Liễu Thăng thua thì giẫm lên nhau mà chạy.” — nguồn: Bình Ngô đại cáo; Bản kỷ, Kỷ Nhà Lê, Thái Tổ hoàng đế, năm Đinh Mùi (1427)
  - “Bóng giặc ở đây chỉ là ký ức. Giữ chắc cửa ải, chờ đúng lúc mới đánh.” — lời dặn của nhân vật hư cấu
- Câu hỏi: Năm 1427, đạo viện binh Minh từ Vân Nam do Mộc Thạnh chỉ huy bị nghĩa quân Lam Sơn chặn ở đâu? Đáp án: Ải Lê Hoa. Trả lời đúng lần đầu thưởng (120, 30, 50).
- Lính NPC (NghiaQuan): Giữ chặt cửa ải. Chưa có lệnh thì chưa ra đánh. / Kỵ binh giặc lao nhanh lắm, né sang bên rồi hãy đánh.
- Lính NPC (NghiaQuan): Lệnh trên dặn cứ đặt phục binh mà chờ, đừng vội giao chiến. / Nghe nói đạo giặc bên Lạng Sơn đã thua to ở Chi Lăng.

### Đông Khê năm 1950

- Thuộc chặng `man3`, mở khi xong di tích `r_bien_gioi`; vào bằng biển chỉ đường “Đường lên cứ điểm Đông Khê”.
- Vùng luyện · cụm cứ điểm Đông Khê trên đường số 4, mở màn chiến dịch Biên giới. Thời tiết `fog`, nhạc `sad`.
- Trại `c1` (kiểu `doi`, ô [30, 13]): Đồn bốt, Ụ súng, Ụ pháo.
- Trại `c2` (kiểu `doi`, ô [34, 39]): Ụ pháo, Ụ súng, Lô cốt.
- Trại `c3` (kiểu `don`, ô [58, 27]): Lô cốt, Ụ pháo, Ụ súng + kẻ mạnh nhất vùng: Trận địa pháo trong đồn.
- Người kể chuyện (hư cấu): Cựu chiến binh Biên giới. Lời kể:
  - “Thu đông 1950, quân ta mở chiến dịch Biên giới. Sáng sớm ngày 16 tháng 9 năm 1950, bộ đội nổ súng đánh cụm cứ điểm Đông Khê, mở màn chiến dịch.” — nguồn: Chiến dịch Biên giới thu – đông 1950: trận Đông Khê (16 – 18/9/1950), cụm cứ điểm và lực lượng giữ đồn; Chiến dịch Biên giới 1950
  - “Đông Khê nằm trên một ngọn đồi cao ở vùng Thạch An, Cao Bằng, ngay trên đường số 4. Giữ đồn có hai đại đội lính lê dương và một trung đội ngụy quân, có pháo 105 ly, pháo cối, lô cốt, hầm ngầm và hàng rào.” — nguồn: Chiến dịch Biên giới thu – đông 1950: trận Đông Khê (16 – 18/9/1950), cụm cứ điểm và lực lượng giữ đồn
  - “Tổng Tham mưu trưởng Hoàng Văn Thái trực tiếp chỉ huy trận này. Địch chống cự quyết liệt, bộ đội xung phong nhiều đợt. Sáng ngày 18 tháng 9, ta làm chủ toàn bộ cụm cứ điểm.” — nguồn: Chiến dịch Biên giới thu – đông 1950: trận Đông Khê (16 – 18/9/1950), cụm cứ điểm và lực lượng giữ đồn
  - “Mất Đông Khê, Thất Khê bị uy hiếp, thị xã Cao Bằng bị cô lập. Pháp phải rút quân khỏi Cao Bằng theo đường số 4, lại cho binh đoàn Lơ Pa-giơ từ Thất Khê lên đón.” — nguồn: Chiến dịch Biên giới 1950
  - “Binh đoàn Lơ Pa-giơ định chiếm lại Đông Khê để đón binh đoàn Sác-tông từ Cao Bằng rút về, nhưng bị chặn đánh, phải dồn vào vùng núi đá Cốc Xá rồi bị bắt gọn.” — nguồn: Chiến dịch Biên giới 1950
  - “Đó là lần đầu tiên sau bốn năm kháng chiến, quân ta mở một chiến dịch tiến công lớn.” — nguồn: Chiến dịch Biên giới 1950
  - “Di tích Đông Khê, với lô cốt và hầm ngầm còn lại, nay là di tích lịch sử cách mạng cấp quốc gia.” — nguồn: Chiến dịch Biên giới thu – đông 1950: trận Đông Khê (16 – 18/9/1950), cụm cứ điểm và lực lượng giữ đồn
  - “Ở vùng này trò chơi chỉ có lô cốt, ụ pháo, ụ súng để phá, không vẽ người. Chuyện thật là chuyện bác vừa kể.” — lời dặn của nhân vật hư cấu
- Câu hỏi: Chiến dịch Biên giới thu – đông 1950 mở màn bằng trận đánh cụm cứ điểm nào? Đáp án: Đông Khê. Trả lời đúng lần đầu thưởng (120, 30, 50).
- Lính NPC (BoDoi): Đồn nằm trên đồi cao, hàng rào mấy lớp, phải phá từng lớp một. / Pháo trong đồn bắn mạnh, nấp rồi hãy tiến.
- Lính NPC (BoDoi): Đánh xong Đông Khê, ta còn chờ đánh quân địch kéo lên ứng cứu. / Đường số 4 này, ba năm trước đã có trận Bông Lau.

## 7. Nhân vật phụ

- Cụ Đồ Sử (già làng, hư cấu): giao việc, nghe báo cáo, trao thưởng, dựng dòng thời gian.
- Thợ rèn (hư cấu): đứng gần chỗ xuất phát mỗi chặng, bán đồ.
- Người giữ ký ức ở từng di tích (hư cấu): kể chuyện có nguồn, hỏi câu hỏi.
- Võ sinh thách đấu (hư cấu): thỉnh thoảng đi tới hỏi đấu; Y nhận lời, N từ chối, đi xa là coi như bỏ chạy. Mạnh lên theo cấp người chơi.

## 8. Sổ bóng giặc

Mỗi loại quái một trang (phím G). Hạ được lần đầu thì mở dòng “Sử ghi” về đội quân đó kèm nguồn (bảng ở mục 5); chưa hạ thì
chỉ thấy bóng đen và gợi ý nơi gặp. Biến việc đánh quái thành việc sưu tầm kiến thức.

## 9. Chơi nhiều người

- Thế giới chung: người chơi đã đăng nhập thấy nhau trên cùng map, mặc đúng bộ đồ, cầm đúng vũ khí, có tên và cấp.
- Tổ đội tối đa 4 người (lưu trong bảng `parties`, `party_members`): đồng đội đứng gần nhau khi một người hạ quái thì
  người kia được chia một nửa kinh nghiệm và tiềm năng.
- Đồng minh (bảng `alliances`): luôn thấy bạn mình đang chơi hay vắng, đang ở chặng nào.
- Bấm vào một người chơi khác trên map: hiện bảng trạng thái của họ (hình nhân vật mặc đúng đồ, cấp, cảnh giới, lực chiến,
  đồ đang dùng) cùng các nút Mời vào tổ đội, Kết đồng minh, Thách đấu. Lời mời tới hiện thành thẻ ở góc trên phải màn chơi
  của người được mời, có nút Đồng ý, Từ chối và đếm lùi 60 giây.
- Thách đấu thật: hai người cùng map, người được mời bấm Đồng ý thì cả hai cùng được đưa tới võ đài, mỗi người tự điều
  khiển nhân vật của mình (không có bot). Mỗi máy gửi trạng thái khoảng 15 lần mỗi giây qua WebSocket; đòn trúng do máy người
  ra đòn báo sang, máy bị đánh tự trừ máu nên né và thế thủ vẫn có tác dụng. Máy chủ phân xử khi có người gục, rút lui, rời
  game hoặc hết 90 giây (ai còn nhiều máu hơn thì thắng), lưu kết quả của cả hai vào bảng `duel_records`. Thách đấu không
  dùng thuốc nam hay cá nướng.
- Lời nói nhanh: 12 câu có sẵn (“Cùng ôn bài nhé!”...) ở bảng Bạn chơi.
- Chat gõ tự do (phím L, ô gõ nằm ở trang chơi nên dùng được bộ gõ tiếng Việt): kênh cùng map miễn phí, lời chat hiện trên
  đầu người nói và trong khung ở góc dưới trái; kênh thế giới tới mọi người đang online, hiện ở góc trên phải, mỗi tin tốn
  10 quan (game trừ trong bản lưu trước khi gửi). Máy chủ làm sạch câu chữ, tối đa 120 ký tự, tự che từ
  tục, chặn gửi dồn (cùng map 1 giây một tin, thế giới 5 giây một tin), gửi 20 tin thế giới gần nhất
  cho người mới vào.
- Đang đánh quái trên map: màn trận che map nhưng vẫn gửi vị trí kèm "đang đánh ai, ở đâu", người cùng map thấy mình vung
  vũ khí vào con quái đó và dòng "đang đánh …". Thách đấu cũng vậy.
- Người chơi máy (`backend/app/world/bots.py`): máy chủ tự cho chạy suốt, kể cả khi không ai online; không gắn với tài
  khoản nào. Quản trị viên thêm, xoá ở trang quản trị, mục "Người chơi máy" (chọn map, việc hay làm: cày quái, làm nhiệm vụ
  hay cả hai, số bot, cấp đầu, tên); tối đa 60 bot, lưu ở bảng `bot_players` nên khởi động lại không mất. Bot hiện trong
  danh sách người cùng map như người chơi khác (tên, cấp, đồ, "đang đánh …"), nói câu có sẵn, hạ 3 quái thì lên một cấp, mời
  tổ đội hay thách đấu thì báo "đang bận". Máy chủ đọc bản đồ đi được ở `backend/app/world/botmaps.json`, xuất bằng
  `tools/export_botmaps.py` (đổi map thì chạy lại; có test báo khi file cũ). Bot không đụng quái gần người chơi thật,
  không đụng kẻ canh, kẻ mạnh nhất vùng, trùm, thuyền.
- Ai hạ quái (người hay bot) thì người cùng map cũng thấy con đó ngã (tin `mob_kill`, `mob_down`), rồi mọc lại sau 30 giây.
- Bảng vàng ở map đầu, gần chỗ xuất phát: 20 người nhiều điểm học sử nhất và 20 người sức mạnh cao nhất toàn máy chủ
  (`GET /api/v1/game/honor`, chỉ có tên hiển thị). Trang chơi lấy mỗi phút rồi để vào localStorage cho game đọc.
- Kỹ thuật: trang chơi giữ WebSocket `/api/v1/world/ws`, game trong khung đọc ghi qua `window.parent.SKNet`; máy chủ chỉ giữ
  vị trí trong bộ nhớ, chặn giá trị lạ, giới hạn tần suất gửi. Không có máy chủ thì game vẫn chơi một mình.

## 10. Điều khiển

WASD hoặc bấm chuột: đi · E: nói chuyện · F: đánh quái · H: gọi chiến mã (từ cấp 3) · R: cưỡi ngựa có sẵn ·
B: túi đồ · G: sổ bóng giặc · P: bạn chơi · L: chat · K: tu luyện · T: tư liệu · J: lộ trình · M: bản đồ · N: sổ tay. Các bảng
cũng mở được từ nút ba gạch ở góc trên phải (bấm vào mới xổ danh sách, có ghi phím tắt). Trong trận: chuột trái chém (giữ
chuột để chém liên tục, phím cách cũng chém được), Shift né, giữ chuột phải để đi theo con trỏ, 1–4 kỹ năng, Q uống thuốc,
E ăn cá nướng.

## 11. Asset

- Gói Ninja Adventure của Pixel-Boy và AAA, giấy phép CC0 (https://pixel-boy.itch.io/ninja-adventure-asset-pack), bản đầy đủ tải
  ngày 12/11/2026: nhân vật, thú, hiệu ứng, âm thanh, nhạc; thêm vũ khí cầm tay (gậy, đao, giáo, kiếm, đại đao, cung), ngựa đen,
  hiệu ứng chém kép, đạn pháo.
- Tự vẽ bằng code: lính Tống, Nguyên, Minh, Đại Việt, nghĩa quân, bộ đội (`tools/make_soldiers.py`); ngoại hình người chơi theo đồ
  (`core/outfit.py`); nỏ, kỵ binh, xe tăng, ụ súng (`core/mobart.py`, `core/weapons.py`); icon đồ và kỹ năng (`tools/make_icons.py`);
  nhà cửa, cung điện, thành luỹ (`core/buildings.py`); chiến mã (`core/chienma.py`).

## 12. Tiêu chí hoàn thành

- Mọi bảng trên khớp code (sinh lại bằng `tools/make_spec.py`).
- Bộ kiểm thử tự động chơi hết game, kiểm tra: quái đứng ở ô đi được, mỗi chặng đúng một trùm, thời 1945 – 1954 không có quái
  là người, mỗi loại quái có dòng sử có nguồn, vũ khí có ảnh và cách đánh, đồ đổi ngoại hình, vùng luyện mở đúng lúc và quay về đúng chỗ.
- Nhóm đối chiếu từng câu kể, câu hỏi, dòng “Sử ghi” với sách gốc trước khi nộp; nhật ký rà soát ở `docs/RA_SOAT_SU_LIEU.md`.

## 13. Mở rộng tiếp

- Thêm vùng luyện: Chương Dương – Hàm Tử (1285), Chi Lăng (1427), Đường số 4 (1950), mỗi vùng cần tìm nguồn trước khi viết.
- Thêm loại quái: thuyền chiến Nguyên trên sông (đánh khi chèo thuyền), voi chiến (nếu tìm được nguồn đúng thời và đúng phe).
