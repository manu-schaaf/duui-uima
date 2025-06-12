FROM ghcr.io/astral-sh/uv:python3.13-alpine AS base

COPY pyproject.toml pyproject.toml
COPY uv.lock uv.lock
RUN uv sync --locked

COPY --from=docker.io/gnames/gnfinder:latest /bin/gnfinder /bin/gnfinder

WORKDIR /app
COPY src/main/ /app/

ENTRYPOINT ["sh", "entrypoint.sh"]
CMD ["--workers", "1"]