"""Ensight DB에서 LLM 프롬프트용 컨텍스트 구성."""
from __future__ import annotations

import math
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from app.api.routes.common import row_to_dict
from app.core.db import SessionLocal

DATE_COLUMN_CANDIDATES = ("date", "target_date", "news_date", "target_ts", "ts")
NEWS_EXCLUDED = {
    "region_id",
    "model_id",
    "run_id",
    "created_at",
    "updated_at",
    "id",
}


def _parse_issue_ts(issue_ts: str) -> datetime:
    s = (issue_ts or "").strip().replace(" ", "T")
    if len(s) == 10:
        s += "T00:00:00"
    if s.count(":") == 1:
        s += ":00"
    return datetime.fromisoformat(s)


def _ts_key(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat(sep="T", timespec="seconds")[:19]
    return str(value).replace(" ", "T")[:19]


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float, Decimal)) and not isinstance(value, bool)


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


def _news_totals_from_rows(rows: list, date_col: str | None) -> dict[str, float]:
    totals: dict[str, float] = {}
    for row in rows:
        row_dict = row_to_dict(row)
        topic_counts = row_dict.get("topic_counts")
        if isinstance(topic_counts, dict):
            for keyword, raw in topic_counts.items():
                if _is_number(raw) and float(raw) > 0:
                    k = str(keyword)
                    totals[k] = totals.get(k, 0) + float(raw)
            continue
        for col, val in row_dict.items():
            col_lower = col.lower()
            if col_lower in NEWS_EXCLUDED or col_lower in {"topic_counts", "topic_count_sum"}:
                continue
            if date_col and col_lower == date_col.lower():
                continue
            if not _is_number(val) or float(val) <= 0:
                continue
            keyword = col[:-6] if col_lower.endswith("_count") else col
            k = str(keyword)
            totals[k] = totals.get(k, 0) + float(val)
    return totals


def _fetch_compare_series(db, region_id: int, start: str, end: str) -> list[dict[str, Any]]:
    sql = text(
        """
        SELECT s.ts, s.real_value, s.pred_1_step
        FROM capstone.rt_schedule_region_hourly s
        WHERE s.region_id = :region_id
          AND s.ts >= :start
          AND s.ts < :end
        ORDER BY s.ts
        """
    )
    rows = db.execute(sql, {"region_id": region_id, "start": start, "end": end}).mappings().all()
    return [
        {
            "ts": row_to_dict(r)["ts"],
            "actual": row_to_dict(r).get("real_value"),
            "pred_1_step": row_to_dict(r).get("pred_1_step"),
        }
        for r in rows
    ]


def _fetch_weather(db, region_id: int, start: str, end: str) -> list[dict[str, Any]]:
    sql = text(
        """
        SELECT ts, temp, rhum
        FROM capstone.weather_hourly
        WHERE region_id = :region_id
          AND ts >= :start
          AND ts < :end
        ORDER BY ts
        """
    )
    return [row_to_dict(r) for r in db.execute(sql, {"region_id": region_id, "start": start, "end": end}).mappings().all()]


def _fetch_news_totals(db, region_id: int, start: str, end: str) -> dict[str, float]:
    date_col = _detect_news_date_column(db)
    if date_col:
        sql = text(
            f"""
            SELECT *
            FROM capstone.news_count_daily
            WHERE region_id = :region_id
              AND {date_col} >= :start
              AND {date_col} < :end
            """
        )
        params = {"region_id": region_id, "start": start, "end": end}
    else:
        sql = text(
            """
            SELECT *
            FROM capstone.news_count_daily
            WHERE region_id = :region_id
            """
        )
        params = {"region_id": region_id}
    rows = db.execute(sql, params).mappings().all()
    return _news_totals_from_rows(rows, date_col)


def _coeff_var(vals: list[float]) -> float:
    vals = [v for v in vals if math.isfinite(v)]
    if len(vals) < 2:
        return 0.0
    m = sum(vals) / len(vals)
    var = sum((x - m) ** 2 for x in vals) / len(vals)
    std = math.sqrt(var)
    return std / abs(m) if abs(m) > 1e-9 else std


def _heuristic_attention(
    loads: list[float], temps: list[float], rhums: list[float]
) -> list[tuple[str, float]]:
    raw = [
        ("known_future:load", _coeff_var(loads)),
        ("known_future:temp", _coeff_var(temps)),
        ("known_future:rhum", _coeff_var(rhums)),
        ("past_covariate:hour_of_day", 0.12),
        ("past_covariate:seasonal_pattern", 0.10),
    ]
    raw.sort(key=lambda x: x[1], reverse=True)
    top = raw[:5]
    s = sum(w for _, w in top) or 1.0
    return [(name, w / s) for name, w in top]


def build_contexts_from_db(
    region_id: int,
    issue_ts: str,
) -> dict[str, Any]:
    """
    data_context, news_context, feature_weights, news_totals, error(optional).
    """
    anchor = _parse_issue_ts(issue_ts)
    anchor_key = anchor.isoformat(timespec="seconds")[:19]
    win_start = anchor - timedelta(hours=168)

    q_start = (anchor - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
    q_end = (anchor + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
    news_start = win_start.date().isoformat()
    news_end = (anchor.date() + timedelta(days=1)).isoformat()
    win_start_key = win_start.isoformat(timespec="seconds")[:19]

    with SessionLocal() as db:
        series = _fetch_compare_series(db, region_id, q_start, q_end)
        weather_rows = _fetch_weather(db, region_id, q_start, q_end)
        news_totals = _fetch_news_totals(db, region_id, news_start, news_end)

    if not series:
        return {
            "data_context": "",
            "news_context": "",
            "feature_weights": [],
            "news_totals": {},
            "error": f"region_id={region_id}, 시각={anchor_key} 구간에 스케줄 데이터가 없습니다.",
        }

    idx = -1
    for i, row in enumerate(series):
        if _ts_key(row["ts"])[:19] <= anchor_key:
            idx = i
        else:
            break
    if idx < 0:
        idx = 0

    hist = series[max(0, idx - 167) : idx + 1]
    forecast = series[idx + 1 : idx + 25]

    loads: list[float] = []
    for row in hist:
        try:
            v = float(row["actual"])
            if math.isfinite(v):
                loads.append(v)
        except (TypeError, ValueError):
            pass

    temps: list[float] = []
    rhums: list[float] = []
    for w in weather_rows:
        wk = _ts_key(w.get("ts"))[:19]
        if wk < win_start_key or wk > anchor_key:
            continue
        for key, bucket in (("temp", temps), ("rhum", rhums)):
            try:
                v = float(w.get(key))
                if math.isfinite(v):
                    bucket.append(v)
            except (TypeError, ValueError):
                pass

    if not loads:
        return {
            "data_context": "",
            "news_context": "",
            "feature_weights": [],
            "news_totals": news_totals,
            "error": "과거 168시간 전력 실측(real_value)이 없습니다.",
        }

    past_block = "### [Input: 과거 168시간(7일) 실측 요약 — DB]\n"
    past_block += (
        f"- 전력부하(real_value): 평균 {sum(loads)/len(loads):.1f}, "
        f"최대 {max(loads):.1f}, 최소 {min(loads):.1f}\n"
    )
    if temps:
        past_block += (
            f"- 기온(temp): 평균 {sum(temps)/len(temps):.1f}, "
            f"최대 {max(temps):.1f}, 최소 {min(temps):.1f}\n"
        )
    else:
        past_block += "- 기온(temp): 해당 구간 데이터 없음\n"
    if rhums:
        past_block += (
            f"- 습도(rhum): 평균 {sum(rhums)/len(rhums):.1f}, "
            f"최대 {max(rhums):.1f}, 최소 {min(rhums):.1f} (%)\n"
        )
    else:
        past_block += "- 습도(rhum): 해당 구간 데이터 없음\n"

    pred_block = "### [Output: 향후 24시간 모델 예측값 — DB]\n"
    if forecast:
        for row in forecast:
            ts = _ts_key(row["ts"])
            try:
                pv = float(row["pred_1_step"])
            except (TypeError, ValueError):
                pv = float("nan")
            if math.isfinite(pv):
                pred_block += f"- {ts}: 예측값={pv:.1f}\n"
    else:
        pred_block += "- 예측 시계열 없음\n"

    feature_weights = _heuristic_attention(loads, temps, rhums)
    attn_source = "DB 기반 휴리스틱"
    try:
        from app.xai_sample.store import feature_weights_for_region, series_id_for_region

        series_id = series_id_for_region(region_id)
        if series_id:
            sample_weights = feature_weights_for_region(region_id, anchor_key)
            if sample_weights:
                feature_weights = sample_weights
                attn_source = f"Chronos 샘플 attention ({series_id}_xai_payloads.json)"
    except Exception:
        pass

    attn_block = f"\n### [Model Attention: 주요 영향 요인 ({attn_source})]\n"
    for label, weight in feature_weights:
        attn_block += f"- {label}: {weight:.4f}\n"

    data_context = f"{past_block}\n{pred_block}{attn_block}"

    news_context = "[과거 7일간 주요 뉴스 키워드 통계 — DB]\n"
    if news_totals:
        for cat, count in sorted(news_totals.items(), key=lambda x: x[1], reverse=True)[:15]:
            news_context += f"- '{cat}': {int(count)}건\n"
    else:
        news_context += "- 해당 구간 뉴스 집계 없음\n"

    return {
        "data_context": data_context,
        "news_context": news_context,
        "feature_weights": feature_weights,
        "news_totals": news_totals,
        "error": None,
    }
