#!/bin/sh
# Lệnh chạy trong image: cập nhật cấu trúc cơ sở dữ liệu, tạo tài khoản quản trị rồi mở máy chủ.
set -e
python -m alembic upgrade head
python -m seed.create_admin
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips="*"
