# syntax=docker/dockerfile:1.7
#
# CloudType 통합 배포: Vue → backend/static, FastAPI가 /api + SPA 동시 서빙
#
# CloudType 배포 설정:
#   Branch = master (최신 커밋 push 후 재배포)
#   Port = 8000
#   Health Check = /api/live
#   Start command = (비움)
#
# Git 커밋(.git/HEAD, refs)을 빌드에 포함 → push할 때마다 Vue static 자동 재빌드

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

# 커밋이 바뀌면 이 COPY 레이어가 무효화 → npm build 반드시 재실행
COPY .git/HEAD .git/HEAD
COPY .git/refs ./.git/refs

ENV VITE_API_BASE_URL=

RUN set -e; \
    REF="$(cat .git/HEAD)"; \
    case "$REF" in \
      ref:*) \
        REF_PATH=".git/${REF#ref: }"; \
        if [ -f "$REF_PATH" ]; then COMMIT="$(cat "$REF_PATH")"; \
        elif [ -f .git/packed-refs ]; then COMMIT="$(grep " ${REF#ref: }$" .git/packed-refs | awk '{print $1}')"; \
        else COMMIT="unknown"; fi ;; \
      *) COMMIT="$REF" ;; \
    esac; \
    echo "Building commit: $COMMIT"; \
    echo "$COMMIT" > /tmp/BUILD_COMMIT; \
    rm -rf backend/static; \
    mkdir -p backend/static; \
    npm run build:unified; \
    test -f backend/static/index.html

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
COPY --from=frontend /tmp/BUILD_COMMIT ./BUILD_COMMIT

COPY backend/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
