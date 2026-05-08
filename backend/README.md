# Ensight FastAPI Backend

## 실행 방법

1. 가상환경 생성 및 활성화
2. 의존성 설치

```bash
pip install -r requirements.txt
```

3. `.env` 파일에 DB 접속 정보 설정

```env
DB_HOST=127.0.0.1
DB_PORT=5433
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=000704
DB_SCHEMA=capstone
```

4. 서버 실행

```bash
uvicorn main:app --reload --port 8000
```

## 주요 엔드포인트

- `GET /api/health`
- `GET /api/regions`
- `GET /api/dashboard`
- `GET /api/rt-schedule`
- `GET /api/metrics`
- `GET /api/power`
- `GET /api/weather`
- `GET /api/news-count`
- `GET /api/compare`

