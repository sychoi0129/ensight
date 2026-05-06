from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes.common import row_to_dict
from app.core.db import SessionLocal

router = APIRouter()

DATE_COLUMN_CANDIDATES = ("date", "target_date", "news_date")


def _detect_news_date_column(db) -> str | None:
    sql = text(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'capstone'
          AND table_name = 'news_count_daily'
        """
    )
    columns = {row["column_name"] for row in db.execute(sql).mappings().all()}
    for candidate in DATE_COLUMN_CANDIDATES:
        if candidate in columns:
            return candidate
    return None


@router.get("/news-count")
def get_news_count(
    region_id: int = Query(...),
    start: str = Query(...),
    end: str = Query(...),
) -> list[dict]:
    try:
        with SessionLocal() as db:
            date_col = _detect_news_date_column(db)

            if date_col:
                # 날짜 컬럼명이 환경마다 다를 수 있어 동적으로 조건을 붙입니다.
                sql = text(
                    f"""
                    SELECT *
                    FROM capstone.news_count_daily
                    WHERE region_id = :region_id
                      AND {date_col} >= :start
                      AND {date_col} < :end
                    ORDER BY {date_col}
                    """
                )
                params = {"region_id": region_id, "start": start, "end": end}
            else:
                # 날짜 컬럼을 못 찾은 경우 region_id 기반으로 우선 조회합니다.
                sql = text(
                    """
                    SELECT *
                    FROM capstone.news_count_daily
                    WHERE region_id = :region_id
                    ORDER BY region_id
                    """
                )
                params = {"region_id": region_id}

            rows = db.execute(sql, params).mappings().all()
        return [row_to_dict(row) for row in rows]
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch news-count data: {exc}") from exc

