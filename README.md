# ensight-vue

This template should help get you started developing with Vue 3 in Vite.

## Recommended IDE Setup

[VS Code](https://code.visualstudio.com/) + [Vue (Official)](https://marketplace.visualstudio.com/items?itemName=Vue.volar) (and disable Vetur).

## Recommended Browser Setup

- Chromium-based browsers (Chrome, Edge, Brave, etc.):
  - [Vue.js devtools](https://chromewebstore.google.com/detail/vuejs-devtools/nhdogjmejiglipccpnnnanhbledajbpd)
  - [Turn on Custom Object Formatter in Chrome DevTools](http://bit.ly/object-formatters)
- Firefox:
  - [Vue.js devtools](https://addons.mozilla.org/en-US/firefox/addon/vue-js-devtools/)
  - [Turn on Custom Object Formatter in Firefox DevTools](https://fxdx.dev/firefox-devtools-custom-object-formatters/)

## Customize configuration

See [Vite Configuration Reference](https://vite.dev/config/).

## Project Setup

```sh
npm install
```

### Compile and Hot-Reload for Development

```sh
npm run dev
```

### Compile and Minify for Production

```sh
npm run build
```

## 통합 배포 (CloudType — 컨테이너 1개로 프론트 + 백엔드)

FastAPI가 `/api/*`는 API로, 그 외 경로는 빌드된 Vue SPA(`backend/static/`)를 서빙합니다.
같은 도메인에서 동작하므로 `VITE_API_BASE_URL`/`CORS_ORIGINS` 설정 없이 동작합니다.

### Build command

```sh
npm ci && npm run build:unified && pip install -r backend/requirements.txt
```

- `npm run build:unified`은 Vite의 `outDir`을 `backend/static`으로 지정해 빌드합니다.
- 이후 FastAPI가 부팅 시 `backend/static/index.html`이 있으면 정적 서빙 모드로 동작합니다.

### Start command

```sh
cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
```

루트의 `Procfile`도 동일한 명령을 담고 있어, CloudType이 자동으로 인식합니다.

### 필요한 환경변수 (CloudType > 서비스 > 환경변수)

| 키 | 값 예시 | 설명 |
| --- | --- | --- |
| `DB_HOST` | `ep-xxxx.neon.tech` | Neon 호스트 |
| `DB_PORT` | `5432` | |
| `DB_NAME` | `neondb` | |
| `DB_USER` | `neondb_owner` | |
| `DB_PASSWORD` | `npg_...` | |
| `DB_SCHEMA` | `capstone` | |
| `DB_SSLMODE` | `require` | Neon은 필수 |

`PORT`는 CloudType이 자동 주입하므로 직접 추가하지 마세요.
프론트/백엔드가 같은 origin이라 `CORS_ORIGINS`, `VITE_API_BASE_URL`은 비워둬도 됩니다.

### Node + Python 동시 빌드

CloudType에서 Node와 Python을 모두 사용하려면 보통 **Python 베이스 이미지** 위에서 Node를 같이 설치할 수 있는 빌드팩을 선택하거나, Buildpack/Dockerfile을 사용해야 합니다. Node 단독 빌드팩은 `pip` 단계에서 실패할 수 있으니, 빌드팩이 두 런타임을 모두 지원하지 않으면 아래 분리 배포로 가는 게 안전합니다.

## 분리 배포 (기존 방식)

- 백엔드: `backend/` 디렉터리, 시작 `uvicorn main:app --host 0.0.0.0 --port $PORT`
- 프론트: 정적 호스팅, 빌드 시 `VITE_API_BASE_URL=https://<백엔드 URL>` 주입
- 백엔드 env에 `CORS_ORIGINS=https://<프론트 URL>` 추가
