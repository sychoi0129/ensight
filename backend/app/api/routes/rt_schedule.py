from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes.common import row_to_dict
from app.core.db import SessionLocal

router = APIRouter()


@router.get("/rt-schedule")
def get_rt_schedule(
    region_id: int = Query(...),
    start: str = Query(...),
    end: str = Query(...),
) -> list[dict]:
    sql = text(
        """
        SELECT
            region_id,
            ts,
            real_value,
            pred_1_step,
            pred_24_step,
            price,
            max_rate_kw,
            x_rt,
            ess_adjustment_kw,
            charge_kw,
            discharge_kw,
            charge_kwh,
            discharge_kwh,
            soc,
            rt_result
        FROM capstone.rt_schedule_region_hourly
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
        raise HTTPException(status_code=500, detail=f"Failed to fetch rt schedule: {exc}") from exc


@router.get("/latest-date")
def get_latest_date(region_id: int = Query(...)) -> dict:
    sql = text(
        """
        SELECT MAX(ts) AS latest_ts
        FROM capstone.rt_schedule_region_hourly
        WHERE region_id = :region_id
          AND pred_1_step IS NOT NULL
        """
    )

    try:
        with SessionLocal() as db:
            row = db.execute(sql, {"region_id": region_id}).mappings().first()
        latest_ts = row["latest_ts"] if row else None
        if latest_ts is None:
            return {"latest_date": None}
        return {"latest_date": latest_ts.date().isoformat()}
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch latest date: {exc}") from exc

