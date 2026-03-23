# ─── Stage 1: builder ─────────────────────────────────────────────────────────
# uv export lit le lockfile et génère un requirements.txt pur PyPI,
# sans jamais résoudre de chemins locaux (workspace, sources, editable).
FROM python:3.13-slim-bookworm AS builder

WORKDIR /app

RUN pip install uv --no-cache-dir

COPY pyproject.toml uv.lock ./

RUN uv export --frozen --no-dev --no-emit-project --output-file /tmp/requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m venv .venv \
 && .venv/bin/pip install --cache-dir /root/.cache/pip --compile -r /tmp/requirements.txt


# ─── Stage 2: runtime ─────────────────────────────────────────────────────────
# Image finale minimale : pas d'uv, pas d'outils de build, user non-root.
FROM python:3.13-slim-bookworm AS runtime

RUN groupadd --gid 1001 app \
 && useradd --uid 1001 --gid app --shell /sbin/nologin --no-create-home app

WORKDIR /app

COPY --from=builder --chown=app:app /app/.venv /app/.venv

COPY --chown=app:app domain/        domain/
COPY --chown=app:app application/   application/
COPY --chown=app:app adapters/      adapters/
COPY --chown=app:app infrastructure/ infrastructure/
COPY --chown=app:app main_api.py \
                     main_cli.py \
                     main_mcp_sse.py \
                     main_mcp_stdio.py \
                     main_mcp_http.py \
                     __init__.py \
                     ./

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER app
