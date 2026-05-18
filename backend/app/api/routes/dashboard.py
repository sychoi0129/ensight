from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes.common import row_to_dict
from app.core.cache import cache_response
from app.core.db import SessionLocal

router = APIRouter()


@router.get("/dashboard")
@cache_response(ttl_seconds=300)
def get_dashboard(
    region_id: int = Query(...),
    start: str = Query(...),
    end: str = Query(...),
) -> list[dict]:
    sql = text(
        """
        SELECT
            s.region_id,
            r.region_name,
            s.ts,
            p.usage_value,
            s.real_value,
            s.pred_1_step,
            s.pred_24_step,
            s.price,
            s.max_rate_kw,
            s.x_rt,
            s.ess_adjustment_kw,
            s.charge_kw,
            s.discharge_kw,
            s.charge_kwh,
            s.discharge_kwh,
            s.soc,
            s.rt_result
        FROM capstone.rt_schedule_region_hourly s
        JOIN capstone.regions r
            ON s.region_id = r.region_id
        LEFT JOIN capstone.power_usage_hourly p
            ON s.region_id = p.region_id
           AND s.ts = p.ts
        WHERE s.region_id = :region_id
          AND s.ts >= :start
          AND s.ts < :end
        ORDER BY s.ts
        """
    )
    params = {"region_id": region_id, "start": start, "end": end}

    try:
        with SessionLocal() as db:
            rows = db.execute(sql, params).mappings().all()
        return [row_to_dict(row) for row in rows]
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch dashboard data: {exc}") from exc

