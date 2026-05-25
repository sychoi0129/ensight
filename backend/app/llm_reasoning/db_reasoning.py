"""
Ensight DB(rt_schedule, weather_hourly, news_count_daily) + LLM reasoning.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from openai import OpenAI

from app.llm_reasoning.context_from_db import build_contexts_from_db
from app.llm_reasoning.llm_client import (
    format_llm_error,
    generate_report,
    llm_configured,
    llm_unconfigured_message,
    resolve_llm_provider,
)
from app.llm_reasoning.metrics import calculate_algorithmic_metrics

_SCHEMA_PATH = Path(__file__).resolve().parent / "reasoner_schema.json"
_schema_cache: dict[str, Any] | None = None


def _load_schema() -> dict[str, Any]:
    global _schema_cache
    if _schema_cache is None:
        with open(_SCHEMA_PATH, encoding="utf-8") as f:
            _schema_cache = json.load(f)
    return _schema_cache


def _maybe_evaluate(
    data_context: str,
    news_context: str,
    report: str,
    algo_metrics: dict[str, Any],
    client: OpenAI,
) -> str | None:
    if os.getenv("ENSIGHT_REASONING_EVAL", "").lower() not in ("1", "true", "yes"):
        return None
    if resolve_llm_provider() != "openai":
        return None
    try:
        from app.llm_reasoning.tsfm_evaluator import TSFMEvaluator
    except ImportError:
        import sys

        xai_dir = Path(__file__).resolve().parents[2] / "xai"
        if str(xai_dir) not in sys.path:
            sys.path.insert(0, str(xai_dir))
        from tsfm_evaluator import TSFMEvaluator  # noqa: E402

    return TSFMEvaluator(client=client).evaluate(
        data_context, news_context, report, algo_metrics
    )


def build_reasoning_from_db(
    region_id: int,
    issue_ts: str,
    include_eval: bool = False,
) -> dict[str, Any]:
    date_str = (issue_ts or "")[:10]
    base: dict[str, Any] = {
        "date": date_str,
        "region_id": region_id,
        "issue_ts": issue_ts,
        "top_features": [],
        "metrics": None,
        "evaluation": None,
        "llm_provider": resolve_llm_provider(),
    }

    if not llm_configured():
        return {
            **base,
            "source": "unconfigured",
            "report": "",
            "error": llm_unconfigured_message(),
        }

    ctx = build_contexts_from_db(region_id, issue_ts)
    if ctx.get("error"):
        return {**base, "source": "no_data", "report": "", "error": ctx["error"]}

    data_context = ctx["data_context"]
    news_context = ctx["news_context"]
    feature_weights = ctx["feature_weights"]
    news_totals = ctx.get("news_totals") or {}

    try:
        schema = _load_schema()
        report, provider_used = generate_report(
            schema, date_str, data_context, news_context
        )
        algo_metrics = calculate_algorithmic_metrics(
            data_context,
            news_context,
            report,
            feature_weights,
            valid_extra_vocab=set(news_totals.keys()),
        )
        evaluation = None
        if include_eval and provider_used == "openai":
            from app.core.config import settings

            client = OpenAI(api_key=(settings.openai_api_key or "").strip())
            evaluation = _maybe_evaluate(
                data_context, news_context, report, algo_metrics, client
            )

        return {
            **base,
            "source": "llm_db",
            "llm_provider": provider_used,
            "report": report,
            "error": None,
            "metrics": algo_metrics,
            "top_features": algo_metrics.get("rrac_features") or [],
            "evaluation": evaluation,
        }
    except Exception as exc:
        return {
            **base,
            "source": "error",
            "report": "",
            "error": format_llm_error(exc),
        }
