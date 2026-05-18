from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes.common import row_to_dict
from app.core.cache import cache_response
from app.core.db import SessionLocal

router = APIRouter()


@router.get("/regions")
@cache_response(ttl_seconds=3600)
def get_regions() -> list[dict]:
    sql = text(
        """
        SELECT region_id, region_name
        FROM capstone.regions
        ORDER BY region_id
        """
    )

    try:
        with SessionLocal() as db:
            rows = db.execute(sql).mappings().all()
        return [row_to_dict(row) for row in rows]
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch regions: {exc}") from exc

