"""리포트 vs 컨텍스트 정합성 지표."""
from __future__ import annotations

import re
from typing import Any


def calculate_algorithmic_metrics(
    data_context: str,
    news_context: str,
    report: str,
    feature_weights: list[tuple[str, float]],
    valid_extra_vocab: set[str] | None = None,
) -> dict[str, Any]:
    alias_dict: dict[str, list[str]] = {
        "temp": ["기온", "온도", "날씨"],
        "rhum": ["습도"],
        "precip": ["강수량", "비"],
        "load": ["전력부하", "수요", "real_value"],
        "경제": ["경제 상황", "경기"],
        "정치": ["정치 상황"],
        "사회": ["사회적 요인"],
    }

    def is_feature_mentioned(feat_name: str, text: str) -> bool:
        if feat_name in text:
            return True
        clean_name = feat_name.split(":")[-1]
        if clean_name in text or clean_name.replace("_", " ") in text:
            return True
        for alias in alias_dict.get(clean_name, []):
            if alias in text:
                return True
        return False

    num_pattern = r"\d+(?:,\d{3})*(?:\.\d+)?"

    def extract_and_normalize(text: str) -> list[str]:
        return [n.replace(",", "") for n in re.findall(num_pattern, text)]

    report_numbers = extract_and_normalize(report)
    context_numbers = set(extract_and_normalize(data_context))
    context_numbers.update(extract_and_normalize(news_context))

    mismatched_numbers: list[str] = []
    if not report_numbers:
        numeric_accuracy = 100.0
    else:
        ignore_numbers = set(str(i) for i in range(25)) | {"0.1", "0.5", "0.9", "0.0"}
        for n in report_numbers:
            if n not in context_numbers and n not in ignore_numbers:
                mismatched_numbers.append(n)
        correct_count = len(report_numbers) - len(mismatched_numbers)
        numeric_accuracy = (max(0, correct_count) / len(report_numbers)) * 100

    rrac = 0.0
    rrac_features: list[str] = []
    rrac_reach = 0
    ac = 0.0
    combined_metric = 0.0

    K = min(5, len(feature_weights))
    top_k = feature_weights[:K]
    mentioned_indices = [
        i for i, (label, _) in enumerate(top_k) if is_feature_mentioned(label, report)
    ]

    if mentioned_indices:
        r = max(mentioned_indices) + 1
        rrac_reach = r
        rrac_features = [top_k[i][0] for i in mentioned_indices]
        reach_mass = sum(w for _, w in top_k[:r])
        if reach_mass > 0:
            mentioned_mass = sum(top_k[i][1] for i in mentioned_indices)
            rrac = (mentioned_mass / reach_mass) * 100
            ac = mentioned_mass
            combined_metric = rrac * ac

    return {
        "numeric_accuracy": numeric_accuracy,
        "keyword_hallucination": 0.0,
        "rrac": rrac,
        "ac": ac,
        "combined_metric": combined_metric,
        "rrac_features": rrac_features,
        "rrac_reach": rrac_reach,
        "hallucinated_keywords": [],
        "mismatched_numbers": sorted(set(mismatched_numbers)),
    }
