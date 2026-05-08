from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from decimal import Decimal

from app.api.routes.common import row_to_dict
from app.core.db import SessionLocal

router = APIRouter()

DATE_COLUMN_CANDIDATES = ("date", "target_date", "news_date", "target_ts", "ts")
EXCLUDED_COLUMNS = {
    "region_id",
    "model_id",
    "run_id",
    "created_at",
    "updated_at",
    "id",
}


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


def _is_number(value) -> bool:
    return isinstance(value, (int, float, Decimal)) and not isinstance(value, bool)


def _expand_news_rows(rows: list[dict], date_col: str | None) -> list[dict]:
    expanded = []
    for row in rows:
        row_dict = row_to_dict(row)
        row_date = (
            row_dict.get(date_col) if date_col else
            row_dict.get("date") or
            row_dict.get("target_date") or
            row_dict.get("news_date") or
            row_dict.get("target_ts") or
            row_dict.get("ts")
        )
        row_date = str(row_date)[:10] if row_date else None

        topic_counts = row_dict.get("topic_counts")
        if isinstance(topic_counts, dict):
            for keyword, raw_count in topic_counts.items():
                if not _is_number(raw_count):
                    continue
                count = float(raw_count)
                if count <= 0:
                    continue
                expanded.append(
                    {
                        "region_id": row_dict.get("region_id"),
                        "date": row_date,
                        "keyword": str(keyword),
                        "event_type": str(keyword),
                        "keyword_count": count,
                    }
                )

        for col, val in row_dict.items():
            col_lower = col.lower()
            if col_lower in EXCLUDED_COLUMNS:
                continue
            if col_lower in {"topic_counts", "topic_count_sum"}:
                continue
            if col_lower == (date_col or "").lower():
                continue
            if not _is_number(val):
                continue
            count = float(val)
            if count <= 0:
                continue
            keyword = col[:-6] if col_lower.endswith("_count") else col
            expanded.append(
                {
                    "region_id": row_dict.get("region_id"),
                    "date": row_date,
                    "keyword": keyword,
                    "event_type": keyword,
                    "keyword_count": count,
                }
            )
    return expanded


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
        return _expand_news_rows(rows, date_col)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch news-count data: {exc}") from exc

