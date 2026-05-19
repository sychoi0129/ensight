<<<<<<< HEAD
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
import os

router = APIRouter(prefix="/reasoning", tags=["reasoning"])

# TSFMReasoner 초기화 (서버 시작 시 1회)
_reasoner = None

def get_reasoner():
    global _reasoner
    if _reasoner is None:
        import sys
        xai_dir = Path(__file__).resolve().parents[4] / "xai"
        sys.path.insert(0, str(xai_dir))
        
        from tsfm_reasoner import TSFMReasoner
        data_dir = xai_dir / "data"
        api_key_value = os.getenv("OPENAI_API_KEY")
        schema_path = xai_dir / "reasoner_schema.json"
        
        _reasoner = TSFMReasoner(
            data_dir=str(data_dir),
            api_key_value=api_key_value,
            schema_path=str(schema_path)
        )
    return _reasoner


class ReasoningRequest(BaseModel):
    date_str: str
    num_samples: int = 1


@router.post("")
async def get_reasoning(req: ReasoningRequest):
    try:
        reasoner = get_reasoner()
        result = reasoner.reason_by_date(req.date_str, num_samples=req.num_samples)
        if isinstance(result, dict) and "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return {"date": req.date_str, "results": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
=======
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
>>>>>>> 8ab19da75f120c44e23cabc2cc462b22a90b3044
