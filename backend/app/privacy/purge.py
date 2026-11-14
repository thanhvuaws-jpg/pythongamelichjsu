"""Job định kỳ xóa hẳn tài khoản đã yêu cầu xóa (Req 25.5).

Chạy: `python -m app.privacy.purge` (cron hằng ngày, cấu hình ở bước triển khai).
"""

import asyncio
import logging

from app.db import SessionLocal, engine
from app.logging_config import setup_logging
from app.privacy.service import purge_deleted_accounts

logger = logging.getLogger("app.privacy.purge")


async def run() -> int:
    async with SessionLocal() as session:
        n = await purge_deleted_accounts(session)
        await session.commit()
    await engine.dispose()
    logger.info("accounts_purged", extra={"count": n})
    return n


if __name__ == "__main__":
    setup_logging("INFO")
    asyncio.run(run())
