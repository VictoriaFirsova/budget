FROM node:20-alpine AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev python3-dev && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml poetry.lock README.md ./
RUN pip install --no-cache-dir "poetry==1.8.5" \
    && poetry config virtualenvs.create false \
    && poetry install --only main --no-root --no-interaction --no-ansi

COPY backend/ ./
COPY --from=frontend /fe/build /app/frontend_build
COPY start.sh /app/start.sh
RUN sed -i 's/\r$//' /app/start.sh && chmod +x /app/start.sh \
    && mkdir -p /app/staticfiles /app/media

ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=server.settings
ENV DEBUG=False
ENV FRONTEND_BUILD_DIR=/app/frontend_build
ENV PORT=8080
EXPOSE 8080

CMD ["/app/start.sh"]
