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