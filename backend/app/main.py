from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.router import api_router
from app.core.config import settings


app = FastAPI(title=settings.app_name)


@app.get("/")
def root() -> dict[str, str]:
    """브라우저에서 :8000/ 만 열면 FastAPI 기본으로 페이지가 없어 404처럼 보일 수 있어 안내용으로 둠."""
    return {
        "service": settings.app_name,
        "hint": "웹 화면은 프론트 개발 서버에서 여세요 (예: npm run dev → http://127.0.0.1:5173/).",
        "openapi_docs": "/docs",
        "api_health": f"{settings.api_prefix}/health",
    }


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1024)

app.include_router(api_router, prefix=settings.api_prefix)
