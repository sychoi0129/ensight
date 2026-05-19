"""LLM reasoning API — DB 컨텍스트 + OpenAI (키 없으면 빈 리포트)."""

from fastapi import APIRouter, HTTPException, Query

from app.llm_reasoning.db_reasoning import build_reasoning_from_db

router = APIRouter()


@router.get("/reasoning")
def get_reasoning(
    region_id: int = Query(..., description="regions.region_id"),
    issue_ts: str = Query(
        ...,
        description="기준 시각 ISO 로컬, 예: 2014-01-02T14:00:00",
    ),
    eval_: bool = Query(False, alias="eval", description="true면 2차 LLM 평가 포함"),
) -> dict:
    try:
        return build_reasoning_from_db(region_id, issue_ts, include_eval=eval_)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"reasoning failed: {exc}"
        ) from exc
