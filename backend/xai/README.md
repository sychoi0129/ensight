# xai (레거시)

AI reasoning은 **`app/llm_reasoning/`** 에서 **Ensight DB**만 사용합니다.

- `reasoner_schema.json` → `app/llm_reasoning/reasoner_schema.json` 로 이전됨
- `data/` 샘플 CSV·JSON → **삭제됨** (더 이상 필요 없음)

`tsfm_reasoner.py` 등은 오프라인 실험용으로만 남아 있으며, API 서버는 참조하지 않습니다.
