"""LLM reasoning API — Ensight DB 컨텍스트 + OpenAI."""

from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

_STATUS_TO_HTTP = {
    "no_data": 404,
    "unconfigured": 503,
    "error": 502,
}


@router.get("/reasoning")
def get_reasoning(
    region_id: int = Query(..., description="regions.region_id"),
    issue_ts: str = Query(
        ...,
        description="기준 시각 ISO 로컬, 예: 2014-01-02T14:00:00",
    ),
    eval_: bool = Query(False, alias="eval", description="true면 2차 LLM 평가 포함"),
) -> dict:
    from app.llm_reasoning.db_reasoning import build_reasoning_from_db

    try:
        result = build_reasoning_from_db(region_id, issue_ts, include_eval=eval_)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"reasoning failed: {exc}"
        ) from exc

    source = result.get("source")
    if source == "llm_db":
        return result

    status = _STATUS_TO_HTTP.get(source)
    if status is not None:
        raise HTTPException(
            status_code=status,
            detail=result.get("error") or f"reasoning failed ({source})",
        )

    return result
