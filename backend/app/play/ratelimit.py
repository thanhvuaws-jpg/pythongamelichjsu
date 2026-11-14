"""Giới hạn 30 lần gửi đáp án mỗi phút cho mỗi Người_Chơi (Req 22.5).

Dùng thư viện `limits` (lõi của slowapi) với khóa là user_id thay vì IP, để học sinh
chung mạng trường không chặn lẫn nhau. Bộ nhớ trong tiến trình: đủ cho một instance;
khi chạy nhiều instance cần đổi sang storage Redis.
"""

import math
import time
from typing import Annotated

from fastapi import Depends
from limits import RateLimitItemPerMinute
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter

from app.auth.deps import CurrentUser
from app.errors import AppError
from app.models import User

ANSWER_LIMIT = RateLimitItemPerMinute(30)
_limiter = MovingWindowRateLimiter(MemoryStorage())


def check_answer_rate(user_id: str) -> None:
    if _limiter.hit(ANSWER_LIMIT, "answers", user_id):
        return
    reset_at, _ = _limiter.get_window_stats(ANSWER_LIMIT, "answers", user_id)
    retry = max(1, math.ceil(reset_at - time.time()))
    raise AppError(
        429,
        "RATE_LIMITED",
        "Bạn gửi đáp án quá nhanh, vui lòng thử lại sau",
        {"retry_after": retry},
        headers={"Retry-After": str(retry)},
    )


async def _answer_rate_limited(user: CurrentUser) -> User:
    check_answer_rate(str(user.id))
    return user


AnswerUser = Annotated[User, Depends(_answer_rate_limited)]
