import os
from openai import OpenAI

class TSFMEvaluator:
    def __init__(self, client=None):
        self.client = client or OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def evaluate(self, data_context, news_context, report, algo_metrics):
        """
        생성된 리포트를 평가합니다. (알고리즘 지표를 참고하여 정성적 평가 수행)
        """
        eval_prompt = f"""
당신은 전력 수요 예측 리포트의 신뢰성을 검토하는 엄격한 데이터 감사관입니다.
제공된 [원본 데이터]와 [시스템 감사 결과]를 바탕으로 [작성된 리포트]를 정밀 평가하세요.

[원본 데이터 섹션]
- 전력/기상/뉴스 통계 데이터가 포함되어 있습니다.

[시스템 감사 결과 (Deterministic)]
- 수치 데이터 정합성: {algo_metrics['numeric_accuracy']:.1f}% (100%일수록 리포트 내 숫자가 데이터와 일치함)
- 뉴스 키워드 환각률: {algo_metrics['keyword_hallucination']:.1f}% (0%일수록 지어낸 키워드가 없음)
- RRAC (Attention Coverage): {algo_metrics['rrac']:.1f}% (도달 범위 내에서의 충실도)
- AC (Attention Sum): {algo_metrics['ac']:.4f} (리포트가 설명한 피처들의 절대적 중요도 합계)
- Combined Score: {algo_metrics['combined_metric']:.2f} (RRAC와 AC를 종합한 분석 품질 점수)

[작성된 리포트 섹션]
{report}

[평가 지표 가이드라인]
1. Faithfulness Score (0-100): 리포트의 주장이 데이터에 충실한가?
   - **RRAC 점수를 적극 참고하세요. AC는 언급한 Attention 가중치치의 비중이 전체중 어느정도인지를 나타냅니다.** 
   - RRAC가 높으면 도달 범위 내에서 충실한 것이고, AC가 높으면 모델이 중요하게 본 핵심 요소들을 절대적으로 많이 다루고 있다는 뜻입니다.
   - RRAC가 높아도, AC가 0.05 이하면 감점하세요.

2. Hallucination Rate (0-100): 데이터에 없는 정보를 지어낸 비중은? (높을수록 환각이 없음을 의미함)
   - 시스템 감사 결과의 '뉴스 키워드 환각률', '수치 데이터 정합성'이 **0%에 가까울수록(낮을수록)** 리포트의 신뢰도가 높은 것이므로 **0점에 가까운 낮은 점수**를 부여하세요.
   - '뉴스 키워드 환각률', '수치 데이터 정합성'이 모두 100%이면 0점입니다.
   - 수치 데이터 정합성 또한 100% 미만이라면 환각이나 오류로 간주하여 0점보다 높게 주세요.
   
3. Overall Score (0-100): 종합적인 분석 품질 및 전문성.
   - **Combined Score가 80점 이상이면 매우 우수한 분석으로 평가하세요.** 
   - RRAC가 높아도, AC가 0.05 이하면 좋은 점수를 주기 어렵습니다.
   - 그 외에도 논리적 모순이 발견되거나, 수치 정합성이 낮다면 추가 감점하세요.

[출력 형식]
- Faithfulness Score: [점수] / 100 (이유: ...)
- Hallucination Rate: [점수] / 100 (이유: ...)
- Overall Score: [점수] (이유: ...)
"""

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 데이터 정합성 및 시계열 분석 검증 전문가입니다."},
                {"role": "user", "content": eval_prompt}
            ],
            temperature=0
        )

        return response.choices[0].message.content
