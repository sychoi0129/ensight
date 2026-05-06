from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes.common import row_to_dict
from app.core.db import SessionLocal

router = APIRouter()


@router.get("/weather")
def get_weather(
    region_id: int = Query(...),
    start: str = Query(...),
    end: str = Query(...),
) -> list[dict]:
    sql = text(
        """
        SELECT *
        FROM capstone.weather_hourly
        WHERE region_id = :region_id
          AND ts >= :start
          AND ts < :end
        ORDER BY ts
        """
    )
    params = {"region_id": region_id, "start": start, "end": end}

    try:
        with SessionLocal() as db:
            rows = db.execute(sql, params).mappings().all()
        return [row_to_dict(row) for row in rows]
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch weather data: {exc}") from exc

