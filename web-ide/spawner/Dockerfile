FROM oven/bun:1.2.22 AS bun
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY --from=bun /usr/local/bin/bun /usr/local/bin/bun

COPY pyproject.toml README.md main.py config.toml ./
COPY playground_app/ ./playground_app/
COPY web/ ./web/
COPY Caddyfile ./Caddyfile

RUN uv sync --no-dev
RUN uv run main.py web build

EXPOSE 8080

CMD ["uv", "run", "main.py", "server", "start"]
