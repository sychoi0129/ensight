import pandas as pd
import json
import os
import re
import numpy as np
from openai import OpenAI
import api_key
from tsfm_evaluator import TSFMEvaluator

class TSFMReasoner:
    def __init__(self, data_dir, api_key_value=None, schema_path="reasoner_schema.json"):
        self.data_dir = data_dir
        if api_key_value is None:
            api_key_value = api_key.open_api_key
        self.client = OpenAI(api_key=api_key_value)
        self.evaluator = TSFMEvaluator(client=self.client)
        
        # Load schema
        with open(schema_path, 'r', encoding='utf-8') as f:
            self.schema = json.load(f)
        
        # Load datasets
        self.pred_df = pd.read_csv(os.path.join(data_dir, "load_26_pred_result.csv"))
        self.attn_summary_df = pd.read_csv(os.path.join(data_dir, "load_26_attn_summary.csv"))
        self.input_df = pd.read_csv(os.path.join(data_dir, "load_26_input.csv"))
        
        with open(os.path.join(data_dir, "load_26_xai_payloads.json"), 'r', encoding='utf-8') as f:
            self.xai_payloads = json.load(f)
            
        self.payload_lookup = {item['window_idx']: item for item in self.xai_payloads}

    def get_past_context(self, start_time_str):
        """
        예측 시작 시점 기준 과거 168시간(7일)의 실측 데이터를 요약합니다.
        """
        # input_df에서 해당 시점의 인덱스 찾기
        idx_list = self.input_df.index[self.input_df['time'] == start_time_str].tolist()
        if not idx_list:
            return "과거 실측 데이터를 찾을 수 없습니다."
        
        target_idx = idx_list[0]
        # 과거 168시간 데이터 추출
        start_idx = max(0, target_idx - 168)
        past_data = self.input_df.iloc[start_idx:target_idx]
        
        if past_data.empty:
            return "과거 데이터가 부족합니다."

        # 1. 전력 및 기상 요약
        summary = "### [Input: 과거 168시간(7일) 실측 요약]\n"
        summary += f"- 전력부하(load): 평균 {past_data['load'].mean():.1f}, 최대 {past_data['load'].max():.1f}, 최소 {past_data['load'].min():.1f}\n"
        summary += f"- 기온(temp): 평균 {past_data['temp'].mean():.1f}, 최대 {past_data['temp'].max():.1f}, 최소 {past_data['temp'].min():.1f}\n"
        
        # 2. 뉴스 카운트 데이터 요약
        news_cols = ['정치', '경제', '사회', '문화', '국제', '지역', '스포츠', 'IT_과학', '범죄', '사고', '재해', '사회_사건사고']
        news_counts = past_data[news_cols].sum().to_dict()
        top_news = sorted(news_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        summary += f"- 주요 뉴스 카테고리(발생 건수): " + ", ".join([f"{k}({int(v)})" for k, v in top_news]) + "\n"
        
        return summary

    def get_window_context(self, window_idx):
        if window_idx not in self.payload_lookup:
            return None
        
        payload = self.payload_lookup[window_idx]
        preds = self.pred_df[self.pred_df['window_idx'] == window_idx].sort_values('horizon_step')
        
        # input context 가져오기 (첫 번째 타임스탬프 기준)
        start_time = preds.iloc[0]['timestamp']
        past_context = self.get_past_context(start_time)
        
        # 예측 결과 요약
        pred_summary = "### [Output: 향후 24시간 모델 예측값]\n"
        for _, row in preds.iterrows():
            # 사용자가 '실제값과 비교하지 말라'는 의도를 비춰 예측값 위주로 설명
            pred_summary += f"- {row['timestamp']}: 예측값={row['predictions']:.1f}\n"
            
        attn_summary = "\n### [Model Attention: 주요 영향 요인]\n"
        group_attn = payload.get('group_attention_mean', [])
        
        if group_attn:
            import numpy as np
            avg_attn = np.mean(group_attn, axis=0)
            row_labels = payload.get('row_labels', [])
            sorted_indices = np.argsort(avg_attn)[::-1]
            
            feature_weights = []
            for idx in sorted_indices:
                if idx < len(row_labels):
                    label = row_labels[idx]
                    weight = float(avg_attn[idx])
                    feature_weights.append((label, weight))
            
            for label, weight in feature_weights[:5]:
                attn_summary += f"- {label}: {weight:.4f}\n"

        return f"{past_context}\n{pred_summary}{attn_summary}", feature_weights

    def get_windows_for_date(self, date_str):
        matching_windows = self.attn_summary_df[self.attn_summary_df['timestamp_start'].str.startswith(date_str)]
        return matching_windows['window_idx'].tolist()

    def get_news_context(self, target_date):
        """
        인풋 데이터에 포함된 뉴스 컬럼들을 사용하여 통계를 생성합니다.
        """
        news_cols = ['정치', '경제', '사회', '문화', '국제', '지역', '스포츠', 'IT_과학', '범죄', '사고', '재해', '사회_사건사고']
        
        target_dt = pd.to_datetime(target_date)
        start_dt = target_dt - pd.Timedelta(days=7)
        
        # input_df에서 해당 기간 데이터 필터링
        mask = (pd.to_datetime(self.input_df['time']) >= start_dt) & \
               (pd.to_datetime(self.input_df['time']) <= target_dt)
        
        past_data = self.input_df[mask]
        
        if past_data.empty:
            return "해당 기간의 뉴스 통계가 없습니다."

        # 전체 기간 동안의 각 카테고리 합계 계산
        total_counts = past_data[news_cols].sum().sort_values(ascending=False)
        top_categories = total_counts.head(15)
        
        context = f"[과거 7일간 주요 뉴스 카테고리 통계]\n"
        for cat, count in top_categories.items():
            context += f"- {cat}: {int(count)}건\n"
            
        return context

    def get_context_for_windows(self, window_indices):
        """
        여러 window_idx에 대한 통합 컨텍스트를 생성합니다.
        """
        combined_context = ""
        aggregated_weights = {}
        
        for idx in window_indices:
            window_text, feature_weights = self.get_window_context(idx)
            if window_text:
                combined_context += f"\n--- Window {idx} 상세 데이터 ---\n{window_text}\n"
                for label, weight in feature_weights:
                    if label not in aggregated_weights:
                        aggregated_weights[label] = []
                    aggregated_weights[label].append(weight)
        
        # 여러 윈도우의 가중치를 평균내어 단일 랭킹 생성
        final_feature_weights = [
            (label, sum(weights)/len(weights)) 
            for label, weights in aggregated_weights.items()
        ]
        final_feature_weights.sort(key=lambda x: x[1], reverse=True)
        
        return combined_context, final_feature_weights

    def calculate_algorithmic_metrics(self, data_context, news_context, report, window_indices, feature_weights):
        """
        알고리즘 기반의 수치 지표를 계산합니다. (수합 정합성, PACS@K, 환각률 중심)
        """
        import re

        # --- 유연한 피처 매칭을 위한 헬퍼 함수 ---
        alias_dict = {
            'temp': ['기온', '온도', '날씨'],
            'rhum': ['습도'],
            'precip': ['강수량', '비'],
            'load': ['전력부하', '수요'],
            '경제': ['경제 상황', '경기'],
            '정치': ['정치 상황'],
            '사회': ['사회적 요인'],
            'wrn_C_한파': ['한파', '추위'],
            'wrn_H_폭염': ['폭염', '더위']
        }

        def is_feature_mentioned(feat_name, text):
            # 1. 직접 매칭
            if feat_name in text: return True
            
            # 2. prefix 제거 및 underscore 변환 매칭
            clean_name = feat_name.split(':')[-1]
            if clean_name in text: return True
            if clean_name.replace('_', ' ') in text: return True
            
            # 3. Alias 매칭
            for alias in alias_dict.get(clean_name, []):
                if alias in text: return True
            return False

        # 1. 수치 데이터 정합성 (Numeric Accuracy)
        # 쉼표(,)가 포함된 숫자도 하나로 잡도록 정규표현식 개선
        num_pattern = r'\d+(?:,\d{3})*(?:\.\d+)?'
        
        def extract_and_normalize(text):
            found = re.findall(num_pattern, text)
            # '536,548' -> '536548' 형태로 쉼표 제거 후 반환
            return [n.replace(',', '') for n in found]

        report_numbers = extract_and_normalize(report)
        context_numbers = set(extract_and_normalize(data_context))
        context_numbers.update(extract_and_normalize(news_context))
        
        mismatched_numbers = []
        if not report_numbers:
            numeric_accuracy = 100
        else:
            # 시간(0-24), 분위수(0.1, 0.5, 0.9) 등 흔한 기술적 숫자는 제외
            ignore_numbers = set([str(i) for i in range(25)] + ['0.1', '0.5', '0.9', '0.0'])
            
            for n in report_numbers:
                if n not in context_numbers and n not in ignore_numbers:
                    mismatched_numbers.append(n)
            
            correct_count = len(report_numbers) - len(mismatched_numbers)
            numeric_accuracy = (max(0, correct_count) / len(report_numbers)) * 100

        # 2. RRAC@K 계산 (K=5 기준)
        K = min(5, len(feature_weights))
        top_k_features = feature_weights[:K]
        
        # Top-K 안에서 언급된 피처 인덱스 수집
        mentioned_indices = []
        for i, (label, weight) in enumerate(top_k_features):
            if is_feature_mentioned(label, report):
                mentioned_indices.append(i)
        
        if not mentioned_indices:
            rrac = 0
            rrac_features = []
            rrac_reach = 0
        else:
            # 언급된 피처 중 가장 낮은 순위 r (1-indexed 기준 i+1)
            r = max(mentioned_indices) + 1
            rrac_reach = r
            rrac_features = [top_k_features[i][0] for i in mentioned_indices]
            
            # r 범위 내의 총 attention mass (분모)
            reach_total_mass = sum(w for _, w in top_k_features[:r])
            
            if reach_total_mass <= 0:
                rrac = 0
            else:
                # r 범위 내에서 실제로 언급된 피처들의 attention mass 합 (분자)
                mentioned_mass = sum(top_k_features[i][1] for i in mentioned_indices)
                rrac = (mentioned_mass / reach_total_mass) * 100
                
                # AC: 언급된 피처들의 어텐션 가중치 순수 합
                ac = mentioned_mass
                
                # AC: 언급된 피처들의 어텐션 가중치 순수 합
                ac = mentioned_mass
                
                # Combined Score: RRAC(충실도) * AC(가중치 합)
                # 예: RRAC 100% * AC 0.10 = 10.0
                combined_metric = (rrac * ac)

        # 3. 뉴스 키워드 환각률 (Keyword Hallucination Rate)
        quoted_words = re.findall(r"'(.*?)'", report)
        news_cols = ['정치', '경제', '사회', '문화', '국제', '지역', '스포츠', 'IT_과학', '범죄', '사고', '재해', '사회_사건사고']
        valid_vocabulary = set(news_cols + [c for c in self.input_df.columns if c.startswith('wrn_')] + ['target', 'temp', 'load', 'rhum', 'precip', 'rain', 'snow', 'press', 'wind_sp', 'wind_dir'])
        
        hallucinated_keywords = []
        news_related_quotes = []
        if quoted_words:
            for q_word in quoted_words:
                if q_word in valid_vocabulary or 'known_future' in q_word or 'pca' in q_word: continue
                news_related_quotes.append(q_word)
                if not any(any(p in cat or cat in p for cat in news_cols) for p in re.split(r'[ ,&및]+', q_word) if len(p) >= 1):
                    hallucinated_keywords.append(q_word)
        
        keyword_hallucination = (len(hallucinated_keywords) / len(news_related_quotes)) * 100 if news_related_quotes else 0

        return {
            "numeric_accuracy": numeric_accuracy,
            "keyword_hallucination": keyword_hallucination,
            "rrac": rrac,
            "ac": ac if 'mentioned_indices' in locals() and mentioned_indices else 0,
            "combined_metric": combined_metric if 'mentioned_indices' in locals() and mentioned_indices else 0,
            "rrac_features": rrac_features,
            "rrac_reach": rrac_reach,
            "hallucinated_keywords": sorted(list(set(hallucinated_keywords))),
            "mismatched_numbers": sorted(list(set(mismatched_numbers)))
        }

    @staticmethod
    def evaluate_rrac_batch(samples, k=5, feature_aliases=None):
        """
        여러 샘플에 대해 RRAC의 평균을 계산합니다.
        samples: [{'report': str, 'feature_names': list, 'attention_weights': list}, ...]
        """
        if not samples:
            return 0
            
        total_rrac = 0
        for sample in samples:
            report = sample['report']
            f_names = sample['feature_names']
            a_weights = sample['attention_weights']
            
            if len(f_names) != len(a_weights):
                raise ValueError("feature_names와 attention_weights의 길이가 다릅니다.")
            
            if not report:
                total_rrac += 0
                continue
                
            # 정렬 및 Top-K 추출
            features = sorted(zip(f_names, a_weights), key=lambda x: x[1], reverse=True)
            k_eff = min(k, len(features))
            top_k = features[:k_eff]
            
            # 언급 여부 확인용 간단 매칭 (Alias 반영)
            def check_mention(feat, text):
                if feat in text: return True
                clean = feat.split(':')[-1]
                if clean in text or clean.replace('_', ' ') in text: return True
                if feature_aliases and clean in feature_aliases:
                    for alias in feature_aliases[clean]:
                        if alias in text: return True
                return False
                
            mentioned_indices = [i for i, (name, _) in enumerate(top_k) if check_mention(name, report)]
            
            if not mentioned_indices:
                rrac = 0
            else:
                r = max(mentioned_indices) + 1
                reach_mass = sum(w for _, w in top_k[:r])
                mentioned_mass = sum(top_k[i][1] for i in mentioned_indices)
                rrac = (mentioned_mass / reach_mass) * 100 if reach_mass > 0 else 0
            
            total_rrac += rrac
            
        return total_rrac / len(samples)

    def get_context_for_date(self, date_str):
        """특정 날짜에 대한 모든 컨텍스트와 피처 가중치를 수집합니다."""
        window_indices = self.get_windows_for_date(date_str)
        if not window_indices:
            return None, None, None, None
            
        data_context, feature_weights = self.get_context_for_windows(window_indices)
        news_context = self.get_news_context(date_str)
        return data_context, news_context, feature_weights, window_indices

    def generate_report(self, date_str, data_context, news_context):
        """컨텍스트를 바탕으로 분석 리포트(추론) 본문만 생성합니다. (스키마 기반)"""
        guidelines_str = "\n".join(self.schema.get("guidelines", []))
        prompt = self.schema["prompt_template"].format(
            date_str=date_str,
            news_context=news_context,
            data_context=data_context,
            guidelines=guidelines_str,
            cautions=self.schema.get("cautions", ""),
            output_format=self.schema.get("output_format", "")
        )

        gen_params = self.schema.get("generation_params", {})
        model_name = gen_params.get("model", "gpt-4o-mini")
        temperature = gen_params.get("temperature", 0.7)

        response = self.client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": self.schema.get("system_role", "당신은 에너지 시계열 예측 모델의 거동을 설명하는 전문가입니다.")},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature
        )
        return response.choices[0].message.content

    def reason_by_date(self, date_str, num_samples=3):
        data_context, news_context, feature_weights, window_indices = self.get_context_for_date(date_str)
        if not data_context:
            return {"error": f"{date_str}에 해당하는 데이터를 찾을 수 없습니다."}

        sections = []
        for i in range(num_samples):
            # 1. 추론 리포트 생성 (Reasoning)
            report = self.generate_report(date_str, data_context, news_context)
            
            # 2. 알고리즘 기반 지표 계산 (Deterministic Verification)
            algo_metrics = self.calculate_algorithmic_metrics(data_context, news_context, report, window_indices, feature_weights)
            
            # 3. LLM 평가 수행 (Judgement)
            evaluation = self.evaluator.evaluate(data_context, news_context, report, algo_metrics)
            
            # 4. 결과 저장
            sections.append({
                f"reasoning{i+1}": {
                    "report": report,
                    "metrics": algo_metrics,
                    "evaluation": evaluation
                }
            })
            
        return sections

if __name__ == "__main__":
    # 날짜 기반 테스트 실행
    data_dir = r"d:\00std\깹스똔\text_reasoning_sample_data"
    reasoner = TSFMReasoner(data_dir)
    test_date = "2014-01-02"
    print(f"--- Reasoning for Date: {test_date} ---")
    print(reasoner.reason_by_date(test_date))
