from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes.common import row_to_dict
from app.core.db import SessionLocal

router = APIRouter()


@router.get("/compare")
def get_compare(
    region_id: int = Query(...),
    start: str = Query(...),
    end: str = Query(...),
) -> dict:
    dashboard_sql = text(
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
            s.ess_adjustment_kw,
            s.charge_kw,
            s.discharge_kw,
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

    metrics_sql = text(
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
            dashboard_rows = db.execute(dashboard_sql, params).mappings().all()
            metrics_row = db.execute(metrics_sql, params).mappings().first()

        dashboard_records = [row_to_dict(row) for row in dashboard_rows]
        series = [
            {
                "ts": row.get("ts"),
                "actual": row.get("real_value"),
                "power_usage": row.get("usage_value"),
                "pred_1_step": row.get("pred_1_step"),
                "pred_24_step": row.get("pred_24_step"),
                "rt_result": row.get("rt_result"),
                "ess_adjustment_kw": row.get("ess_adjustment_kw"),
                "charge_kw": row.get("charge_kw"),
                "discharge_kw": row.get("discharge_kw"),
                "soc": row.get("soc"),
                "price": row.get("price"),
            }
            for row in dashboard_records
        ]

        region = None
        if dashboard_records:
            first = dashboard_records[0]
            region = {
                "region_id": first.get("region_id"),
                "region_name": first.get("region_name"),
            }

        metrics = row_to_dict(metrics_row) if metrics_row else {}
        metrics.pop("region_id", None)

        return {"region": region, "series": series, "metrics": metrics}
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch compare data: {exc}") from exc

