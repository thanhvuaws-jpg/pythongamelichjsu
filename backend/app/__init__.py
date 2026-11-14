"""Backend_API. Gói `shared/` nằm ở thư mục gốc repo, thêm vào sys.path khi chạy từ backend/."""

import sys
from importlib.util import find_spec
from pathlib import Path

if find_spec("shared") is None:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
