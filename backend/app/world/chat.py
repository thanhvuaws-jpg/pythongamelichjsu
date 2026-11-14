"""Chat trong game: làm sạch câu chữ, che từ tục, giới hạn tốc độ gửi.

Hai kênh: `map` (người cùng map, miễn phí) và `world` (mọi người đang online). Tiền quan cho
kênh thế giới do game trừ trong bản lưu trước khi gửi; máy chủ chỉ lo nội dung và tốc độ. Câu chữ
tự do nên mọi tin đều qua `clean` và `censor`.
"""

from __future__ import annotations

import re
import unicodedata

MAX_LEN = 120
CHANNELS = ("map", "world")
GAP = {"map": 1.0, "world": 5.0}  # giây tối thiểu giữa hai tin cùng kênh của một người
RECENT = 20  # tin thế giới gần nhất gửi cho người mới vào

# Từ tục, chửi thề hay gặp (có dấu và kiểu gõ tắt không dấu). So khớp theo cả từ, không phân
# biệt hoa thường. Không đưa vào những chữ không dấu trùng với từ thường dùng (như "cac" là "các",
# "deo" là "đeo") để khỏi che nhầm câu bình thường.
BAD_WORDS = (
    "địt",
    "đít mẹ",
    "đụ",
    "đụ má",
    "đéo",
    "đĩ",
    "lồn",
    "buồi",
    "cặc",
    "cứt",
    "đần độn",
    "óc chó",
    "con mẹ mày",
    "dit",
    "dit me",
    "du ma",
    "lon me",
    "buoi",
    "cuc cut",
    "dm",
    "đm",
    "dmm",
    "đmm",
    "dcm",
    "đcm",
    "dkm",
    "đkm",
    "cmm",
    "cđm",
    "vcl",
    "vkl",
    "vl",
    "vcc",
    "clgt",
    "cl",
    "clm",
    "cc",
    "fuck",
    "fucking",
    "shit",
    "bitch",
    "dick",
    "pussy",
)
_CONTROL = re.compile("[\x00-\x1f\x7f\u200b-\u200f\u2028-\u202e\u2060-\u206f\ufeff]")
_SPACES = re.compile(r"\s+")


def _pattern() -> re.Pattern[str]:
    words = sorted({unicodedata.normalize("NFC", w) for w in BAD_WORDS}, key=len, reverse=True)
    body = "|".join(re.escape(w).replace(r"\ ", r"\s+") for w in words)
    return re.compile(rf"(?<![\w])(?:{body})(?![\w])", re.IGNORECASE)


_BAD = _pattern()


def clean(text: object) -> str:
    """Bỏ ký tự điều khiển, gộp khoảng trắng, chuẩn hoá dấu (NFC), cắt còn tối đa MAX_LEN ký tự."""
    if not isinstance(text, str):
        return ""
    # xuống dòng, tab thành dấu cách trước rồi mới bỏ ký tự điều khiển
    text = _SPACES.sub(" ", unicodedata.normalize("NFC", text))
    text = _CONTROL.sub("", text)
    return _SPACES.sub(" ", text).strip()[:MAX_LEN]


def censor(text: str) -> str:
    """Thay mỗi từ tục bằng dấu sao, giữ độ dài để vẫn đọc được phần còn lại của câu."""
    return _BAD.sub(lambda m: "*" * len(m.group(0)), text)
