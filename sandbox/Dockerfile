# Test-runner image: Python 3.11 + uv, non-root. Venv lives in a per-run volume at /venv.
FROM python:3.11-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.3 /uv /usr/local/bin/uv
RUN useradd -m -u 1000 runner && mkdir -p /venv /uvcache && chown runner /venv /uvcache
USER runner
WORKDIR /work
ENV VIRTUAL_ENV=/venv PATH=/venv/bin:$PATH UV_CACHE_DIR=/uvcache UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 PIP_DISABLE_PIP_VERSION_CHECK=1
