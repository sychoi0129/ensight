# syntax=docker/dockerfile:1.7
#
# CloudType 통합 배포: Vue 빌드 → backend/static, FastAPI가 /api + SPA 동시 서빙
# CloudType 환경변수: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DB_SCHEMA, DB_SSLMODE
#                     OPENAI_API_KEY (또는 LLM_PROVIDER=gemini + GEMINI_API_KEY)
# PORT 는 CloudType이 자동 주입 (직접 설정하지 않음)

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

# 같은 origin에서 /api 호출 (분리 배포가 아니면 VITE_API_BASE_URL 비움)
ENV VITE_API_BASE_URL=
RUN mkdir -p backend/static \
    && npm run build:unified


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
