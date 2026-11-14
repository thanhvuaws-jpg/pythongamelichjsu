"""Nạp Danh_Mục_Nguồn khởi tạo từ Phụ lục A của requirements (Req 1.1).

Chạy từ thư mục backend/:  python -m seed.seed_sources

Mọi nguồn nạp ở trạng thái `pending`. `tier` chỉ là Cấp_Nguồn đề xuất; Người_Thẩm_Định
chỉ định cấp chính thức khi duyệt. Chỉ điền nhà xuất bản/năm khi Phụ lục A nêu rõ;
các trường còn lại để trống để đối chiếu với bản sách thực tế nhóm sử dụng
(một tác phẩm có nhiều bản dịch, lần tái bản với số trang khác nhau).
Endpoint duyệt từ chối nguồn còn thiếu nhà xuất bản hoặc năm.

Chạy lại an toàn: bỏ qua nguồn đã có cùng tiêu đề.
"""

import asyncio
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal, engine
from app.models import Source, SourceStatus

VERIFY_NOTE = "Seed từ Phụ lục A: cần đối chiếu thông tin xuất bản với bản sách thực tế."


@dataclass(frozen=True)
class SeedSource:
    title: str
    tier: int
    notes: str
    authors: str | None = None
    translators: str | None = None
    publisher: str | None = None
    year: int | None = None
    volume: str | None = None


APPENDIX_A: tuple[SeedSource, ...] = (
    # Cấp 1
    SeedSource(
        "Đại Việt sử ký toàn thư",
        1,
        "Nguồn chính cho Màn 1 và Màn 2. Phụ lục A ghi năm 1993 và các lần tái bản.",
        translators="Viện Khoa học xã hội Việt Nam (Viện Nghiên cứu Hán Nôm)",
        publisher="NXB Khoa học Xã hội",
        year=1993,
    ),
    SeedSource(
        "Khâm định Việt sử thông giám cương mục",
        1,
        "Đối chiếu niên đại, địa danh Màn 1 và Màn 2.",
        translators="Viện Sử học",
        publisher="NXB Giáo dục",
    ),
    SeedSource(
        "Lam Sơn thực lục",
        1,
        "Nguồn chính cho khởi nghĩa Lam Sơn. Cần chọn bản dịch đã xuất bản cụ thể.",
    ),
    SeedSource(
        "Nguyễn Trãi toàn tập",
        1,
        "Văn bản Bình Ngô đại cáo, Quân trung từ mệnh tập.",
        publisher="NXB Khoa học Xã hội",
    ),
    SeedSource(
        "An Nam chí lược",
        1,
        "Đối chiếu góc nhìn đương thời về kháng chiến chống Nguyên. Cần chọn bản dịch cụ thể.",
        authors="Lê Tắc",
    ),
    SeedSource(
        "Lịch sử Việt Nam",
        1,
        "Khung tổng quan, quan hệ nhân quả, ý nghĩa sự kiện cho cả 3 màn. "
        "Bộ 15 tập xuất bản 2013–2017; mỗi tập nên nhập thành một nguồn riêng có năm cụ thể.",
        authors="Viện Sử học",
        publisher="NXB Khoa học Xã hội",
        volume="15 tập",
    ),
    SeedSource(
        "Đất nước Việt Nam qua các đời",
        1,
        "Địa lý lịch sử, tên địa danh cổ cho Lớp Bản Đồ.",
        authors="Đào Duy Anh",
    ),
    SeedSource(
        "Hồ Chí Minh toàn tập",
        1,
        "Văn bản Tuyên ngôn Độc lập, Lời kêu gọi toàn quốc kháng chiến.",
        publisher="NXB Chính trị quốc gia Sự thật",
        year=2011,
    ),
    SeedSource(
        "Văn kiện Đảng toàn tập",
        1,
        "Văn kiện giai đoạn 1945–1954.",
        publisher="NXB Chính trị quốc gia",
    ),
    SeedSource(
        "Công trình của Viện Lịch sử quân sự Việt Nam về kháng chiến chống Pháp",
        1,
        "Diễn biến chiến dịch, số liệu Màn 3. Cần tách thành từng công trình cụ thể "
        "(NXB Chính trị quốc gia hoặc NXB Quân đội nhân dân).",
        authors="Viện Lịch sử quân sự Việt Nam",
    ),
    SeedSource(
        "Tài liệu tại Trung tâm Lưu trữ quốc gia I và III",
        1,
        "Văn bản gốc, ảnh tư liệu; cần xin phép sử dụng. Ghi mã lưu trữ cho từng hồ sơ.",
        authors="Trung tâm Lưu trữ quốc gia I, Trung tâm Lưu trữ quốc gia III",
    ),
    # Cấp 2
    SeedSource(
        "Sách giáo khoa Lịch sử và Địa lí (lớp 6–9), Lịch sử (lớp 10–12) "
        "theo Chương trình GDPT 2018",
        2,
        "Chuẩn mức độ kiến thức, căn cứ phân Độ Khó. Nhập từng cuốn theo bộ sách được Bộ GD&ĐT "
        "phê duyệt.",
        publisher="NXB Giáo dục Việt Nam",
    ),
    SeedSource(
        "Chương trình giáo dục phổ thông môn Lịch sử (Thông tư 32/2018/TT-BGDĐT)",
        2,
        "Căn cứ yêu cầu cần đạt cho Câu Hỏi.",
        authors="Bộ Giáo dục và Đào tạo",
        year=2018,
    ),
    SeedSource(
        "Bảo tàng Lịch sử Quốc gia — hiện vật, tư liệu trưng bày, ấn phẩm",
        2,
        "Mảnh Ghép hiện vật; cần kiểm tra giấy phép hình ảnh.",
        authors="Bảo tàng Lịch sử Quốc gia",
    ),
    SeedSource(
        "Bảo tàng Chiến thắng lịch sử Điện Biên Phủ; Bảo tàng Lịch sử Quân sự Việt Nam",
        2,
        "Mảnh Ghép cho Màn 3.",
        authors="Bảo tàng Chiến thắng lịch sử Điện Biên Phủ, Bảo tàng Lịch sử Quân sự Việt Nam",
    ),
    SeedSource(
        "Tạp chí Nghiên cứu Lịch sử",
        2,
        "Nghiên cứu chuyên sâu, tranh luận về niên đại. Nhập từng bài kèm số tạp chí.",
        authors="Viện Sử học",
    ),
    SeedSource(
        "Atlat Địa lí Việt Nam",
        2,
        "Nền Bản Đồ, ranh giới hành chính hiện nay, Hoàng Sa và Trường Sa. Kết hợp dữ liệu "
        "bản đồ của Cục Đo đạc, Bản đồ và Thông tin địa lý Việt Nam.",
        publisher="NXB Giáo dục Việt Nam",
    ),
    # Cấp 3
    SeedSource(
        "Việt Nam sử lược",
        3,
        "Văn phong dễ đọc, cần đối chiếu với nguồn Cấp 1 hoặc Cấp 2.",
        authors="Trần Trọng Kim",
    ),
)


async def seed_sources(session: AsyncSession) -> tuple[int, int]:
    """Trả về (số nguồn thêm mới, số nguồn bỏ qua vì đã có)."""
    existing = set(await session.scalars(select(Source.title)))
    added = 0
    for item in APPENDIX_A:
        if item.title in existing:
            continue
        session.add(
            Source(
                id=uuid.uuid4(),
                title=item.title,
                authors=item.authors,
                translators=item.translators,
                publisher=item.publisher,
                year=item.year,
                volume=item.volume,
                tier=item.tier,
                notes=f"{item.notes} {VERIFY_NOTE}",
                status=SourceStatus.pending,
            )
        )
        added += 1
    await session.commit()
    return added, len(APPENDIX_A) - added


async def main() -> None:
    async with SessionLocal() as session:
        added, skipped = await seed_sources(session)
    await engine.dispose()
    print(f"Đã thêm {added} nguồn ở trạng thái pending, bỏ qua {skipped} nguồn đã có.")


if __name__ == "__main__":
    asyncio.run(main())
