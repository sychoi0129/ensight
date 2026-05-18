# syntax=docker/dockerfile:1.7

############################
# 1) Frontend build (Vue)
############################
FROM node:20-alpine AS frontend
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY index.html jsconfig.json vite.config.js ./
COPY public ./public
COPY src ./src
COPY scripts ./scripts

RUN npm run build:unified


############################
# 2) Backend runtime (Python)
############################
FROM python:3.11-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app/backend

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY backend ./

COPY --from=frontend /app/backend/static ./static

EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
