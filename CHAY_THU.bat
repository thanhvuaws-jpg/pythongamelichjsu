@echo off
chcp 65001 >nul
title Su Ky Dieu Tra - dong cua so nay de tat game
cd /d "%~dp0"
set "URL=http://127.0.0.1:8200"
set "PY=%~dp0.venv\Scripts\python.exe"

curl -s -o nul -m 2 "%URL%/health"
if not errorlevel 1 goto already_running

if not exist "%PY%" goto no_python
if not exist "backend\.env" copy ".env.example" "backend\.env" >nul

echo Đang bật cơ sở dữ liệu...
docker compose up -d db >nul 2>&1
if errorlevel 1 goto no_docker

set /a tries=0
:wait_db
docker compose exec -T db pg_isready -U sukydieutra >nul 2>&1
if not errorlevel 1 goto db_ready
set /a tries+=1
if %tries% geq 40 goto no_docker
timeout /t 1 /nobreak >nul
goto wait_db

:db_ready
if not exist "build\sukydieutra\build\web\index.html" "%PY%" tools\build_web.py

cd backend
set PYTHONPATH=..
set PYTHONUTF8=1
"%PY%" -m alembic upgrade head >nul 2>&1
if errorlevel 1 goto migrate_failed
"%PY%" -m seed.create_admin

rem Chờ máy chủ khởi động vài giây rồi mới mở trình duyệt
start "" /min cmd /c "ping -n 4 127.0.0.1 >nul & start http://127.0.0.1:8200"

echo.
echo ===================================================
echo   Trang game:     %URL%
echo   Trang quản trị: %URL%/admin/
echo.
echo   Giữ cửa sổ này mở trong lúc chơi.
echo   Đóng cửa sổ này là tắt game.
echo ===================================================
echo.
"%PY%" -m uvicorn app.main:app --host 127.0.0.1 --port 8200 --log-level warning
echo.
echo Máy chủ đã dừng.
pause
exit /b 0

:already_running
echo Game đang chạy sẵn rồi, mở trình duyệt...
start "" "%URL%"
exit /b 0

:no_python
echo Không thấy thư mục .venv nên chưa chạy được. Xem hướng dẫn trong DEPLOY.md.
pause
exit /b 1

:no_docker
echo Không bật được cơ sở dữ liệu. Hãy mở Docker Desktop, đợi nó chạy xong rồi bấm đúp lại file này.
pause
exit /b 1

:migrate_failed
echo Không cập nhật được cơ sở dữ liệu. Chạy lệnh sau trong thư mục backend để xem lỗi:
echo python -m alembic upgrade head
pause
exit /b 1
