FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

ENV DJANGO_DEBUG=false \
    DJANGO_DB_PATH=/data/db.sqlite3 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN addgroup --system bookkin \
    && adduser --system --ingroup bookkin --home /home/bookkin bookkin \
    && mkdir -p /home/bookkin /data \
    && chown bookkin:bookkin /app /home/bookkin /data

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY --chown=bookkin:bookkin manage.py ./
COPY --chown=bookkin:bookkin config/ config/
COPY --chown=bookkin:bookkin bookkin/ bookkin/

USER bookkin

# Static assets are baked into the image and served over HTTP by WhiteNoise.
RUN DJANGO_SECRET_KEY=build-only \
    DJANGO_ALLOWED_HOSTS=localhost \
    python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "--bind=0.0.0.0:8000", "--access-logfile=-", "--error-logfile=-", "config.wsgi:application"]
