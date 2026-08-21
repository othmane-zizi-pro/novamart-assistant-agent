# Stage 1: build the frontend bundle
FROM node:22-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: the Python service, serving the API and the built frontend
FROM python:3.12-slim
WORKDIR /srv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY app/ app/
COPY corpus/ corpus/
COPY --from=frontend /build/dist frontend/dist

# The embedding index is built at boot (37 chunks, a few seconds) so the image
# stays credential-free and corpus edits only need a redeploy, not a rebuild.
ENV PORT=8080
CMD ["sh", "-c", "uv run --no-sync python -m app.indexer && uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port 8080"]
