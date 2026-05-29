from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.cache import cache_response
from app.core.db import SessionLocal

router = APIRouter()


def _region_name(db, region_id: int) -> str | None:
    sql = text(
        """
        SELECT region_name
        FROM capstone.regions
        WHERE region_id = :region_id
        LIMIT 1
        """
    )
    row = db.execute(sql, {"region_id": region_id}).mappings().first()
    return row["region_name"] if row else None


@router.get("/xai-sample/regions")
@cache_response(ttl_seconds=3600)
def get_xai_sample_regions() -> dict:
    """로컬 샘플 attention 파일이 있는 region_id 목록."""
    from app.xai_sample.store import list_sample_regions

    return {
        "regions": list_sample_regions(),
        "rank_mode": "attention_x_log1p_count",
    }


@router.get("/news-events")
@cache_response(ttl_seconds=300)
def get_news_events(
    region_id: int = Query(...),
    date: str = Query(..., description="YYYY-MM-DD"),
) -> dict:
    """
    뉴스 이벤트 상위 3건.
    hybrid_score = attention_weight * log1p(keyword_count)
    region_id ↔ load_{region_id} (region_series_map.json 오버라이드 가능).
    """
    day = date[:10]

    from app.xai_sample.store import build_news_events, is_sample_region

    if not is_sample_region(region_id):
        return build_news_events(region_id, "", day)

    try:
        with SessionLocal() as db:
            region_name = _region_name(db, region_id)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to resolve region name: {exc}"
        ) from exc

    if not region_name:
        raise HTTPException(status_code=404, detail=f"region_id={region_id} not found")

    try:
        return build_news_events(region_id, region_name, day)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
