FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/data \
    EMBED_CACHE_DIR=/data/models

WORKDIR /app
COPY pyproject.toml ./
COPY learnmate ./learnmate
RUN pip install --no-cache-dir .
COPY alembic.ini ./
COPY migrations ./migrations

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=4)"]
CMD ["sh", "-c", "alembic -c alembic.ini upgrade head && exec uvicorn learnmate.main:create_app --factory --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
