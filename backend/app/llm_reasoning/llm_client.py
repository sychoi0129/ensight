"""LLM 리포트 생성 (OpenAI / Gemini)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from openai import OpenAI

from app.core.config import settings


def _load_generation_params(schema: dict[str, Any]) -> dict[str, Any]:
    return schema.get("generation_params") or {}


def _build_prompt(schema: dict[str, Any], date_str: str, data_context: str, news_context: str) -> tuple[str, str]:
    guidelines_str = "\n".join(schema.get("guidelines", []))
    prompt = schema["prompt_template"].format(
        date_str=date_str,
        news_context=news_context,
        data_context=data_context,
        guidelines=guidelines_str,
        cautions=schema.get("cautions", ""),
        output_format=schema.get("output_format", ""),
    )
    system = schema.get(
        "system_role",
        "당신은 에너지 시계열 예측 모델의 거동을 설명하는 전문가입니다.",
    )
    return system, prompt


def resolve_llm_provider() -> str:
    raw = (settings.llm_provider or "openai").strip().lower()
    if raw in ("gemini", "google"):
        return "gemini"
    return "openai"


def llm_configured() -> bool:
    provider = resolve_llm_provider()
    if provider == "gemini":
        return bool((settings.gemini_api_key or "").strip())
    return bool((settings.openai_api_key or "").strip())


def llm_unconfigured_message() -> str:
    provider = resolve_llm_provider()
    if provider == "gemini":
        return (
            "GEMINI_API_KEY가 없습니다. backend/.env에 GEMINI_API_KEY=AIza... 를 넣고 "
            "LLM_PROVIDER=gemini 로 설정한 뒤 백엔드를 재시작하세요."
        )
    return (
        "OPENAI_API_KEY가 없습니다. backend/.env에 OpenAI Secret key(sk-proj-...)를 넣거나, "
        "Gemini를 쓰려면 LLM_PROVIDER=gemini 와 GEMINI_API_KEY를 설정하세요."
    )


def generate_report(
    schema: dict[str, Any],
    date_str: str,
    data_context: str,
    news_context: str,
) -> tuple[str, str]:
    """Returns (report_text, provider_used)."""
    system, prompt = _build_prompt(schema, date_str, data_context, news_context)
    gen = _load_generation_params(schema)
    provider = resolve_llm_provider()

    if provider == "gemini":
        return _generate_gemini(system, prompt, gen), "gemini"

    client = OpenAI(api_key=(settings.openai_api_key or "").strip())
    response = client.chat.completions.create(
        model=gen.get("model", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=gen.get("temperature", 0.7),
    )
    return response.choices[0].message.content or "", "openai"


def _generate_gemini(system: str, prompt: str, gen: dict[str, Any]) -> str:
    api_key = (settings.gemini_api_key or "").strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set")

    model = (settings.gemini_model or "gemini-2.0-flash").strip()
    temperature = float(gen.get("temperature", 0.7))
    body = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": f"{system}\n\n{prompt}"}],
            }
        ],
        "generationConfig": {"temperature": temperature},
    }
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
        f":generateContent?key={api_key}"
    )
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"Gemini API HTTP {exc.code}: {detail}") from exc

    candidates = payload.get("candidates") or []
    if not candidates:
        raise RuntimeError(f"Gemini empty response: {payload}")

    parts = (candidates[0].get("content") or {}).get("parts") or []
    text = "".join(str(p.get("text", "")) for p in parts).strip()
    if not text:
        raise RuntimeError(f"Gemini returned no text: {payload}")
    return text


def format_llm_error(exc: Exception) -> str:
    msg = str(exc)
    hint = ""
    if "invalid_api_key" in msg or "Incorrect API key" in msg:
        hint = (
            " 현재 OPENAI_API_KEY(sk-svcacct 등)는 Chat Completions API에서 거부됩니다. "
            "platform.openai.com/api-keys 의 sk-proj-... Secret key를 쓰거나, "
            "backend/.env 에 LLM_PROVIDER=gemini + GEMINI_API_KEY(AIza...) 로 전환하세요."
        )
    return f"reasoning 실행 실패: {exc}{hint}"
