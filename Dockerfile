# Một image duy nhất chạy cả game, trang web và API trên cùng một địa chỉ.

# Giai đoạn 1: đóng gói game sang WebAssembly. Cần mạng vì pygbag tải mẫu trang từ CDN của nó.
FROM python:3.12-slim AS game
WORKDIR /src
RUN pip install --no-cache-dir pygbag==0.9.3 pygame-ce==2.5.7
COPY game ./game
COPY shared ./shared
COPY tools/build_web.py ./tools/build_web.py
RUN python tools/build_web.py

# Giai đoạn 2: máy chủ FastAPI
FROM python:3.12-slim
WORKDIR /srv/backend
COPY backend/pyproject.toml ./pyproject.toml
COPY backend/app ./app
RUN pip install --no-cache-dir .
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./alembic.ini
COPY backend/seed ./seed
COPY backend/start.sh ./start.sh
COPY shared /srv/shared
COPY web /srv/web
COPY game/content /srv/game/content
COPY --from=game /src/build/sukydieutra/build/web /srv/game_web
ENV PYTHONPATH=/srv:/srv/backend \
    PYTHONUNBUFFERED=1 \
    WEB_DIR=/srv/web \
    GAME_WEB_DIR=/srv/game_web \
    GAME_CONTENT_DIR=/srv/game/content \
    ENVIRONMENT=production
EXPOSE 8000
CMD ["sh", "start.sh"]
