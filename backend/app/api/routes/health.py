from pathlib import Path

from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

from app.core.db import SessionLocal

router = APIRouter()

_BUILD_COMMIT_FILE = Path(__file__).resolve().parents[3] / "BUILD_COMMIT"


def _read_build_commit() -> str:
    try:
        return _BUILD_COMMIT_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"


@router.get("/live")
def liveness() -> dict[str, str]:
    """DB 없이 프로세스만 확인 (CloudType startup/readiness probe용)."""
    return {"status": "ok", "commit": _read_build_commit()}


@router.get("/version")
def version() -> dict[str, str]:
    """배포된 Git 커밋 확인용."""
    return {"status": "ok", "commit": _read_build_commit()}


@router.get("/health")
def health_check() -> dict[str, int | str]:
    try:
        with SessionLocal() as db:
            db_value = db.execute(text("SELECT 1")).scalar_one()
        return {"status": "ok", "db": int(db_value)}
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"DB connection failed: {exc}") from exc
