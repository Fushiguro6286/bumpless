# Hosted demo: API + built frontend. Without API keys it serves recorded runs (replays) only.
#   docker build -t bumpless-web . && docker run -p 8000:8000 bumpless-web
FROM node:22-slim AS frontend
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.3 /uv /usr/local/bin/uv
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 app
WORKDIR /app
COPY --chown=app pyproject.toml uv.lock README.md LICENSE ./
COPY --chown=app bumpless/ bumpless/
RUN uv sync --frozen --no-dev && chown -R app /app
COPY --chown=app . .
COPY --from=frontend --chown=app /src/dist frontend/dist
USER app
# No Docker inside the container: live runs use the local executor, which the API limits to bundled fixtures.
ENV EXECUTOR=local PORT=8000 PATH=/app/.venv/bin:$PATH PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["sh", "-c", "bumpless serve --host 0.0.0.0 --port $PORT"]
