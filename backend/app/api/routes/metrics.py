from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes.common import row_to_dict
from app.core.db import SessionLocal

router = APIRouter()


@router.get("/metrics")
def get_metrics(
    region_id: int = Query(...),
    start: str = Query(...),
    end: str = Query(...),
) -> dict:
    sql = text(
        """
        SELECT
            region_id,
            AVG(ABS(real_value - pred_1_step)) AS mae_1_step,
            SQRT(AVG(POWER(real_value - pred_1_step, 2))) AS rmse_1_step,
            AVG(ABS(real_value - pred_24_step)) AS mae_24_step,
            SQRT(AVG(POWER(real_value - pred_24_step, 2))) AS rmse_24_step,
            SUM(charge_kwh) AS total_charge_kwh,
            SUM(discharge_kwh) AS total_discharge_kwh,
            AVG(soc) AS avg_soc,
            MAX(real_value) AS peak_before_ess,
            MAX(rt_result) AS peak_after_ess,
            MAX(real_value) - MAX(rt_result) AS peak_reduction
        FROM capstone.rt_schedule_region_hourly
        WHERE region_id = :region_id
          AND ts >= :start
          AND ts < :end
        GROUP BY region_id
        """
    )
    params = {"region_id": region_id, "start": start, "end": end}

    try:
        with SessionLocal() as db:
            row = db.execute(sql, params).mappings().first()
        return row_to_dict(row) if row else {}
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch metrics: {exc}") from exc

