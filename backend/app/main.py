from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import settings


# 프론트 빌드 산출물 위치: backend/static (CloudType 빌드 스텝에서 dist를 여기에 복사)
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
INDEX_FILE = STATIC_DIR / "index.html"


app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1024)

app.include_router(api_router, prefix=settings.api_prefix)


if INDEX_FILE.exists():
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        # /api/* 는 위 라우터에서 이미 처리됨. 나머지는 정적 파일 또는 index.html 반환.
        if full_path:
            candidate = STATIC_DIR / full_path
            if candidate.is_file():
                return FileResponse(candidate)
        return FileResponse(INDEX_FILE)
else:

    @app.get("/")
    def root() -> dict[str, str]:
        """프론트 빌드가 아직 없을 때(로컬 개발 환경) 안내용 응답."""
        return {
            "service": settings.app_name,
            "hint": "웹 화면은 프론트 개발 서버에서 여세요 (예: npm run dev → http://127.0.0.1:5173/).",
            "openapi_docs": "/docs",
            "api_health": f"{settings.api_prefix}/health",
        }
