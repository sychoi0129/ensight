"""FastAPI ↔ TSFMReasoner 연결 브릿지."""

import os
import sys
from pathlib import Path

# xai/ 폴더를 import 경로에 추가
_XAI_DIR = Path(__file__).resolve().parents[2] / "xai"
print(f"[DEBUG] XAI_DIR = {_XAI_DIR}")
print(f"[DEBUG] exists = {_XAI_DIR.exists()}")
if str(_XAI_DIR) not in sys.path:
    sys.path.insert(0, str(_XAI_DIR))

from tsfm_reasoner import TSFMReasoner  # noqa: E402

# 서버 시작 시 1회만 초기화
_reasoner: TSFMReasoner | None = None


def _get_reasoner() -> TSFMReasoner:
    global _reasoner
    if _reasoner is None:
        data_dir = _XAI_DIR / "data"
        schema_path = _XAI_DIR / "reasoner_schema.json"
        api_key_value = os.getenv("OPENAI_API_KEY")

        if not api_key_value:
            raise RuntimeError(
                "OPENAI_API_KEY 환경변수가 설정되지 않았습니다. "
                ".env 파일 또는 시스템 환경변수를 확인하세요."
            )

        _reasoner = TSFMReasoner(
            data_dir=str(data_dir),
            api_key_value=api_key_value,
            schema_path=str(schema_path),
        )
    return _reasoner


def build_reasoning_from_db(
    region_id: int,
    issue_ts: str,
    include_eval: bool = False,
) -> dict:
    """
    reasoning.py 엔드포인트에서 호출하는 메인 함수.

    Parameters
    ----------
    region_id  : regions.region_id (현재는 load_26 고정, 추후 확장 가능)
    issue_ts   : ISO 로컬 시각, 예) "2014-01-16T00:00:00"
    include_eval: True면 LLM 2차 평가 포함 (응답 느려짐)

    Returns
    -------
    {
      "date": "2014-01-16",
      "region_id": 26,
      "report": "...",
      "metrics": { ... },
      "evaluation": "..."   # include_eval=True 일 때만 포함
    }
    """
    # issue_ts에서 날짜만 추출 ("2014-01-16T14:00:00" → "2014-01-16")
    date_str = issue_ts[:10]

    reasoner = _get_reasoner()
    results = reasoner.reason_by_date(date_str, num_samples=1)

    if isinstance(results, dict) and "error" in results:
        raise ValueError(results["error"])

    # num_samples=1 이므로 첫 번째 결과만 사용
    first = results[0]["reasoning1"]

    response = {
        "date": date_str,
        "region_id": region_id,
        "report": first["report"],
        "metrics": first["metrics"],
    }

    if include_eval:
        response["evaluation"] = first["evaluation"]

    return response
