from fastapi import APIRouter
from sqlalchemy.exc import SQLAlchemyError

from app.core.db import check_db_connection

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/db")
def health_db_check() -> dict[str, str]:
    try:
        check_db_connection()
        return {"status": "ok", "database": "connected"}
    except SQLAlchemyError:
        return {"status": "error", "database": "disconnected"}
