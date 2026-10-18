FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /bin/uv

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH" \
    PORT=8080

WORKDIR /app

# Install dependencies first so this layer is cached between code changes.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

# Bake the embedding model into the image so cold starts don't download it (~70 MB).
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5', cache_dir='/app/data/models')"

COPY app ./app

# Run as an unprivileged user that can write data/ (Milvus Lite db + model cache).
RUN useradd --create-home --uid 10001 appuser && chown -R appuser /app/data
USER appuser

EXPOSE 8080

# Cloud Run injects $PORT; exec so uvicorn receives shutdown signals directly.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
