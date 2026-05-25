"""
로컬 LLM_reasoning 샘플 파일 기반 XAI (B: 배치, DB 미적재).

region_id ↔ load_{region_id} (region_series_map.json 오버라이드 가능).
디렉터리에 load_N_xai_payloads.json 이 있으면 해당 지역 지원.
"""

from __future__ import annotations

import json
import math
import re
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

DATE_START = "2013-01-02"
DATE_END = "2014-12-31"
DEFAULT_SERIES_PATTERN = "load_{region_id}"
MAP_FILENAME = "region_series_map.json"

NEWS_CATEGORY_KEYS = frozenset(
    {
        "정치",
        "경제",
        "사회",
        "문화",
        "국제",
        "지역",
        "스포츠",
        "IT_과학",
        "범죄",
        "사고",
        "재해",
        "사회_사건사고",
    }
)

TOPIC_TO_ATTENTION_LABEL: dict[str, str] = {
    "과학": "known_future:IT_과학",
    "IT_과학일반": "known_future:IT_과학",
    "IT_과학": "known_future:IT_과학",
}

REGION_TOPIC_NAMES = frozenset(
    {
        "충남",
        "대전",
        "경남",
        "제주",
        "대구",
        "경기",
        "지역일반",
        "울산",
        "광주",
        "강원",
        "전북",
        "충북",
        "부산",
        "경북",
        "전남",
        "경기북부",
        "서울",
        "남서울",
        "인천",
        "광주전남",
    }
)

EXCLUDED_WIDE_COLUMNS = frozenset(
    {"news_date", "region_name", "topic_count_sum", "행정_자치", "북한"}
)


def _capstone_root() -> Path:
    return Path(__file__).resolve().parents[3].parent


def resolve_sample_data_dir() -> Path | None:
    from app.core.config import settings

    if settings.xai_sample_data_dir:
        path = Path(settings.xai_sample_data_dir)
        if _discover_series_in_dir(path):
            return path

    root = _capstone_root()
    for rel in (
        "LLM_reasoning/text_reasoning_sample_data",
        "LLM_reasoning/LLM_reasoning/text_reasoning_sample_data",
    ):
        path = root / rel
        if _discover_series_in_dir(path):
            return path
    return None


def _discover_series_in_dir(data_dir: Path) -> list[str]:
    if not data_dir.is_dir():
        return []
    found = sorted(
        {
            m.group(1)
            for p in data_dir.glob("load_*_xai_payloads.json")
            if (m := re.match(r"^(load_\d+)_xai_payloads\.json$", p.name))
        }
    )
    return found


@lru_cache(maxsize=1)
def _series_map_config() -> dict:
    data_dir = resolve_sample_data_dir()
    if not data_dir:
        return {"default_pattern": DEFAULT_SERIES_PATTERN, "overrides": {}, "date_range": {}}

    map_path = data_dir / MAP_FILENAME
    if map_path.is_file():
        with open(map_path, encoding="utf-8") as f:
            raw = json.load(f)
    else:
        raw = {}

    overrides = raw.get("overrides") or {}
    overrides = {str(k): str(v) for k, v in overrides.items()}
    date_range = raw.get("date_range") or {}
    default_pattern = raw.get("default_pattern", DEFAULT_SERIES_PATTERN)
    if default_pattern is None:
        default_pattern = None
    elif not default_pattern:
        default_pattern = DEFAULT_SERIES_PATTERN
    return {
        "default_pattern": default_pattern,
        "overrides": overrides,
        "date_range": date_range,
        "discovered": _discover_series_in_dir(data_dir),
        "data_dir": str(data_dir),
    }


def _date_bounds() -> tuple[str, str]:
    cfg = _series_map_config()
    dr = cfg.get("date_range") or {}
    return (
        str(dr.get("start") or DATE_START)[:10],
        str(dr.get("end") or DATE_END)[:10],
    )


def series_id_for_region(region_id: int) -> str | None:
    """region_id에 대응하는 load_XX 시리즈. payload 파일이 있을 때만 반환."""
    data_dir = resolve_sample_data_dir()
    if not data_dir:
        return None

    cfg = _series_map_config()
    key = str(region_id)
    series_id = cfg["overrides"].get(key)
    if not series_id:
        pattern = cfg.get("default_pattern")
        if pattern:
            series_id = pattern.format(region_id=region_id)
        else:
            return None

    payload_path = data_dir / f"{series_id}_xai_payloads.json"
    summary_path = data_dir / f"{series_id}_attn_summary.csv"
    if payload_path.is_file() and summary_path.is_file():
        return series_id
    return None


def is_sample_region(region_id: int) -> bool:
    return series_id_for_region(region_id) is not None


def list_sample_regions() -> list[dict]:
    """region_series_map + 파일 존재 기준으로 XAI attention 사용 가능 지역."""
    cfg = _series_map_config()
    out: list[dict] = []
    seen: set[int] = set()

    for rid_str, series_id in sorted(cfg.get("overrides", {}).items(), key=lambda x: int(x[0])):
        rid = int(rid_str)
        if rid in seen:
            continue
        if series_id_for_region(rid) == series_id:
            out.append({"region_id": rid, "series_id": series_id})
            seen.add(rid)

    pattern = cfg.get("default_pattern")
    if pattern:
        for series_id in sorted(cfg.get("discovered") or []):
            m = re.match(r"^load_(\d+)$", series_id)
            if not m:
                continue
            rid = int(m.group(1))
            if rid in seen:
                continue
            if series_id_for_region(rid) == series_id:
                out.append({"region_id": rid, "series_id": series_id})
                seen.add(rid)
    return out


@lru_cache(maxsize=32)
def _attn_summary_df(series_id: str) -> pd.DataFrame:
    data_dir = resolve_sample_data_dir()
    if not data_dir:
        raise FileNotFoundError("XAI sample data directory not found")
    return pd.read_csv(data_dir / f"{series_id}_attn_summary.csv")


@lru_cache(maxsize=8)
def _payload_lookup(series_id: str) -> dict[int, dict]:
    data_dir = resolve_sample_data_dir()
    if not data_dir:
        raise FileNotFoundError("XAI sample data directory not found")
    path = data_dir / f"{series_id}_xai_payloads.json"
    with open(path, encoding="utf-8") as f:
        payloads = json.load(f)
    return {int(item["window_idx"]): item for item in payloads}


@lru_cache(maxsize=1)
def _news_wide_df() -> pd.DataFrame:
    data_dir = resolve_sample_data_dir()
    if not data_dir:
        raise FileNotFoundError("XAI sample data directory not found")
    return pd.read_csv(data_dir / "news_count_daily_wide.csv")


def _date_in_sample_range(date_str: str) -> bool:
    start, end = _date_bounds()
    day = date_str[:10]
    return start <= day <= end


def _window_idx_for_date(series_id: str, date_str: str) -> int | None:
    df = _attn_summary_df(series_id)
    day = date_str[:10]
    matches = df[df["timestamp_start"].astype(str).str.startswith(day)]
    if matches.empty:
        return None
    return int(matches.iloc[0]["window_idx"])


def _attention_weights(payload: dict) -> dict[str, float]:
    group_attn = payload.get("group_attention_mean") or []
    row_labels = payload.get("row_labels") or []
    if not group_attn or not row_labels:
        return {}

    avg_attn = np.mean(np.asarray(group_attn, dtype=np.float64), axis=0)
    weights: dict[str, float] = {}
    for idx, label in enumerate(row_labels):
        if idx < avg_attn.shape[0]:
            weights[str(label)] = float(avg_attn[idx])
    return weights


def _topic_to_attention_label(topic: str) -> str:
    if topic in TOPIC_TO_ATTENTION_LABEL:
        return TOPIC_TO_ATTENTION_LABEL[topic]
    if topic in NEWS_CATEGORY_KEYS:
        return f"known_future:{topic}"
    if topic in REGION_TOPIC_NAMES:
        return "known_future:지역"
    return "known_future:사회"


def _hybrid_score(attention_weight: float, count: int) -> float:
    return attention_weight * math.log1p(max(0, count))


def _normalize_impact(raw: float, raw_max: float) -> float:
    if raw_max <= 0:
        return 0.3
    ratio = min(1.0, max(0.0, raw / raw_max))
    return round(0.3 + 0.65 * ratio, 2)


def _resolve_wide_region_name(region_name: str) -> str | None:
    df = _news_wide_df()
    names = df["region_name"].astype(str).unique().tolist()
    if region_name in names:
        return region_name
    compact = region_name.replace(" ", "")
    for name in names:
        if name.replace(" ", "") == compact:
            return name
    for name in names:
        if compact in name.replace(" ", "") or name.replace(" ", "") in compact:
            return name
    return None


def _wide_counts_for_day(region_name: str, date_str: str) -> list[tuple[str, int]]:
    df = _news_wide_df()
    day = date_str[:10]
    wide_region = _resolve_wide_region_name(region_name)
    if not wide_region:
        return []
    subset = df[
        (df["news_date"].astype(str).str[:10] == day)
        & (df["region_name"].astype(str) == wide_region)
    ]
    if subset.empty:
        return []

    row = subset.iloc[0]
    counts: list[tuple[str, int]] = []
    for col in df.columns:
        if col in EXCLUDED_WIDE_COLUMNS:
            continue
        val = row.get(col)
        try:
            count = int(float(val))
        except (TypeError, ValueError):
            continue
        if count > 0:
            counts.append((str(col), count))
    return counts


def build_news_events(
    region_id: int,
    region_name: str,
    date_str: str,
    *,
    top_n: int = 3,
) -> dict:
    """
    Returns { source, events[], rank_mode, series_id, ... }.
    정렬: hybrid_score = attention_weight * log1p(keyword_count)
    """
    day = date_str[:10]
    start, end = _date_bounds()

    series_id = series_id_for_region(region_id)
    if not series_id:
        available = list_sample_regions()
        ids = [r["region_id"] for r in available]
        return {
            "source": "unsupported",
            "events": [],
            "rank_mode": "hybrid",
            "error": (
                f"region_id={region_id}용 XAI 파일(load_{region_id}_xai_payloads.json)이 없습니다. "
                f"현재 샘플 attention 지역: {ids or '없음'}"
            ),
            "available_regions": available,
        }

    if not _date_in_sample_range(day):
        return {
            "source": "xai_sample",
            "series_id": series_id,
            "events": [],
            "rank_mode": "hybrid",
            "error": f"샘플 XAI 데이터는 {start} ~ {end} 구간만 지원합니다.",
        }

    if resolve_sample_data_dir() is None:
        return {
            "source": "xai_sample",
            "events": [],
            "rank_mode": "hybrid",
            "error": "XAI 샘플 데이터 경로를 찾을 수 없습니다.",
        }

    window_idx = _window_idx_for_date(series_id, day)
    if window_idx is None:
        return {
            "source": "xai_sample",
            "series_id": series_id,
            "events": [],
            "rank_mode": "hybrid",
            "error": f"{day}에 해당하는 attention 윈도우가 없습니다.",
        }

    payload = _payload_lookup(series_id).get(window_idx)
    if not payload:
        return {
            "source": "xai_sample",
            "series_id": series_id,
            "events": [],
            "rank_mode": "hybrid",
            "error": f"window_idx={window_idx} payload를 찾을 수 없습니다.",
        }

    attn = _attention_weights(payload)
    if not attn:
        return {
            "source": "xai_sample",
            "series_id": series_id,
            "events": [],
            "rank_mode": "hybrid",
            "error": "group_attention_mean을 해석할 수 없습니다.",
        }

    counts = _wide_counts_for_day(region_name, day)
    if not counts:
        return {
            "source": "xai_sample",
            "series_id": series_id,
            "events": [],
            "rank_mode": "hybrid",
            "error": f"{region_name} / {day} 뉴스 집계(wide CSV)가 없습니다.",
        }

    candidates = []
    for topic, count in counts:
        label = _topic_to_attention_label(topic)
        weight = attn.get(label, 0.0)
        hybrid = _hybrid_score(weight, count)
        candidates.append(
            {
                "topic": topic,
                "count": count,
                "attention_label": label,
                "attention_weight": weight,
                "hybrid_score": hybrid,
            }
        )

    candidates.sort(key=lambda x: (x["hybrid_score"], x["count"]), reverse=True)
    top = candidates[:top_n]
    raw_max = max((c["hybrid_score"] for c in top), default=0.0)

    ts = f"{day}T12:00:00"
    events = []
    for item in top:
        topic = item["topic"]
        count = item["count"]
        events.append(
            {
                "timestamp": ts,
                "headline": f"{topic} 관련 키워드",
                "event_type": topic,
                "summary": f"해당 키워드 카운트 {count}건",
                "impact_score": _normalize_impact(item["hybrid_score"], raw_max),
                "keyword": topic,
                "attention_label": item["attention_label"],
                "attention_weight": round(item["attention_weight"], 6),
                "hybrid_score": round(item["hybrid_score"], 6),
                "keyword_count": count,
            }
        )

    return {
        "source": "xai_sample",
        "series_id": series_id,
        "region_id": region_id,
        "window_idx": window_idx,
        "region_name": region_name,
        "date": day,
        "rank_mode": "attention_x_log1p_count",
        "events": events,
        "available_regions": list_sample_regions(),
    }


def feature_weights_for_region(region_id: int, date_str: str) -> list[tuple[str, float]]:
    """LLM reasoning용 Chronos attention (샘플 파일이 있는 region만)."""
    day = date_str[:10]
    series_id = series_id_for_region(region_id)
    if not series_id or not _date_in_sample_range(day):
        return []

    window_idx = _window_idx_for_date(series_id, day)
    if window_idx is None:
        return []

    payload = _payload_lookup(series_id).get(window_idx)
    if not payload:
        return []

    weights = _attention_weights(payload)
    pairs = [(label, w) for label, w in weights.items() if label != "target"]
    pairs.sort(key=lambda x: x[1], reverse=True)
    top = pairs[:8]
    total = sum(w for _, w in top) or 1.0
    return [(label, w / total) for label, w in top]


# 하위 호환
def feature_weights_for_date(date_str: str) -> list[tuple[str, float]]:
    return feature_weights_for_region(26, date_str)
