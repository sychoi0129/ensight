"""LLM 리포트 2차 평가 (선택)."""
import os

from openai import OpenAI


class TSFMEvaluator:
    def __init__(self, client=None):
        self.client = client or OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def evaluate(self, data_context, news_context, report, algo_metrics):
        eval_prompt = f"""
당신은 전력 수요 예측 리포트의 신뢰성을 검토하는 엄격한 데이터 감사관입니다.

[시스템 감사 결과]
- 수치 데이터 정합성: {algo_metrics['numeric_accuracy']:.1f}%
- RRAC: {algo_metrics['rrac']:.1f}%
- AC: {algo_metrics['ac']:.4f}

[작성된 리포트]
{report}

[출력 형식]
- Faithfulness Score: [점수] / 100 (이유: ...)
- Hallucination Rate: [점수] / 100 (이유: ...)
- Overall Score: [점수] (이유: ...)
"""
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 데이터 정합성 검증 전문가입니다."},
                {"role": "user", "content": eval_prompt},
            ],
            temperature=0,
        )
        return response.choices[0].message.content
