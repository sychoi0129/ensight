from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import bindparam, text
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes.common import row_to_dict
from app.core.db import SessionLocal

router = APIRouter()


_METRICS_SELECT = """
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
"""


@router.get("/metrics")
def get_metrics(
    region_id: int = Query(...),
    start: str = Query(...),
    end: str = Query(...),
) -> dict:
    sql = text(
        f"""
        SELECT {_METRICS_SELECT}
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


@router.get("/metrics-bulk")
def get_metrics_bulk(
    start: str = Query(...),
    end: str = Query(...),
    region_ids: str | None = Query(
        default=None,
        description="쉼표로 구분된 region_id 목록. 비우면 전 지역 반환.",
    ),
) -> list[dict]:
    """전체(또는 지정한) 지역의 metrics를 한 번의 쿼리로 묶어서 반환.

    프론트의 N+1 호출(/metrics × 지역 수) 제거용.
    """
    params: dict = {"start": start, "end": end}
    where_region = ""

    if region_ids:
        try:
            ids = [int(x) for x in region_ids.split(",") if x.strip()]
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="region_ids 파싱 실패") from exc
        if ids:
            where_region = "AND region_id IN :region_ids"
            params["region_ids"] = ids

    sql = text(
        f"""
        SELECT {_METRICS_SELECT}
        FROM capstone.rt_schedule_region_hourly
        WHERE ts >= :start
          AND ts < :end
          {where_region}
        GROUP BY region_id
        ORDER BY region_id
        """
    )
    if "region_ids" in params:
        sql = sql.bindparams(bindparam("region_ids", expanding=True))

    try:
        with SessionLocal() as db:
            rows = db.execute(sql, params).mappings().all()
        return [row_to_dict(r) for r in rows]
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch metrics-bulk: {exc}") from exc
