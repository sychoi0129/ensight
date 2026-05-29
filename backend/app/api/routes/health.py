from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

from app.core.db import SessionLocal

router = APIRouter()


@router.get("/live")
def liveness() -> dict[str, str]:
    """DB 없이 프로세스만 확인 (CloudType startup/readiness probe용)."""
    return {"status": "ok"}


@router.get("/health")
def health_check() -> dict[str, int | str]:
    try:
        with SessionLocal() as db:
            db_value = db.execute(text("SELECT 1")).scalar_one()
        return {"status": "ok", "db": int(db_value)}
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"DB connection failed: {exc}") from exc
