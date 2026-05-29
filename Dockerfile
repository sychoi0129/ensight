# syntax=docker/dockerfile:1.7
#
# CloudType 통합 배포: Vue → backend/static, FastAPI가 /api + SPA 동시 서빙
# 환경변수: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DB_SCHEMA, DB_SSLMODE
#           OPENAI_API_KEY (또는 LLM_PROVIDER=gemini + GEMINI_API_KEY)
#
# CloudType 배포 설정:
#   Port = 8000
#   Health Check = /api/live
#   Start command = (비움, Dockerfile ENTRYPOINT 사용)
#   Build arguments = CACHE_BUST=1 (재배포마다 숫자 올리면 프론트 강제 재빌드)

############################
# 1) Frontend build (Vue)
############################
FROM node:20-alpine AS frontend
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --no-audit --no-fund

COPY index.html jsconfig.json vite.config.js ./
COPY public ./public
COPY src ./src
COPY scripts ./scripts

ENV VITE_API_BASE_URL=

# CACHE_BUST 빌드 인자를 바꾸면 Vue static이 새로 생성됨 (외부 URL 불필요)
# CloudType → Build arguments: CACHE_BUST=2, 3… 재배포마다 숫자 올리기
ARG CACHE_BUST=1
RUN echo "cache-bust=${CACHE_BUST}" >/tmp/.cache-bust \
    && rm -rf backend/static \
    && mkdir -p backend/static \
    && npm run build:unified \
    && test -f backend/static/index.html

############################
# 2) Backend runtime (Python)
############################
FROM python:3.11-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app/backend

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY backend ./

RUN rm -rf ./static
COPY --from=frontend /app/backend/static ./static

COPY backend/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
