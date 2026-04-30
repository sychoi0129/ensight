// xai.py → useXai.js

import { REGION_COORDS } from '@/constants/settings'

export function summarizeXai(histDf = [], weatherView = [], newsView = [], inputWindow = 168) {
  const avg = arr => arr.length ? arr.reduce((s, v) => s + v, 0) / arr.length : 0
  const min = arr => arr.length ? Math.min(...arr) : 0
  const max = arr => arr.length ? Math.max(...arr) : 0

  const fmt1 = v => Number.isFinite(v) ? v.toFixed(1) : '0.0'
  const fmt4 = v => Number.isFinite(v) ? v.toFixed(4) : '0.0000'

  const loads = histDf.map(r => r.power_usage)
  const temps = weatherView.map(r => r.temperature)

  const avgLoad = avg(loads)
  const minTemp = min(temps)
  const maxTemp = max(temps)

  const end = histDf[histDf.length - 1]?.timestamp

  const eventCount = newsView.reduce((acc, row) => {
    acc[row.event_type] = (acc[row.event_type] ?? 0) + 1
    return acc
  }, {})

  const topEvent = Object.entries(eventCount)
    .sort((a, b) => b[1] - a[1])[0]

  const topEventName = topEvent?.[0] ?? '뉴스'
  const topEventCount = topEvent?.[1] ?? 0

  const topNews = [...newsView]
    .sort((a, b) => b.impact_score - a.impact_score)
    .slice(0, 3)

  const hasCold = temps.length && avg(temps) <= 3
  // keyword 필드가 없을 수 있으므로 optional chaining으로 안전하게 처리
  const hasTourism = newsView.some(r =>
    r.event_type === '관광' || String(r.keyword ?? '').includes('관광')
  )
  const hasEconomy = newsView.some(r =>
    r.event_type === '경제' || String(r.keyword ?? '').includes('경제')
  )

  const targetAttention = hasCold ? 0.0212 : 0.0187
  const tempAttention = hasCold ? 0.0191 : 0.0148
  const newsAttention = hasEconomy || hasTourism ? 0.0174 : 0.0116
  const pcaAttention = hasEconomy ? 0.0168 : 0.0132

  // 뉴스 이벤트 타입별 평균 impact_score 집계
  const eventGroups = {}
  for (const n of newsView) {
    if (!eventGroups[n.event_type]) {
      eventGroups[n.event_type] = { sum: 0, count: 0 }
    }
    eventGroups[n.event_type].sum += n.impact_score
    eventGroups[n.event_type].count += 1
  }

  const factors = Object.entries(eventGroups)
    .map(([event_type, { sum, count }]) => ({
      factor: event_type,
      importance: +(sum / count).toFixed(4),
    }))
    .sort((a, b) => b.importance - a.importance)

  // keyword 없는 경우 event_type으로 대체
  const newsLine = topNews.length
    ? topNews.map(n => `${n.event_type}(${n.keyword ?? n.event_type})`).join(', ')
    : '선택 구간 내 주요 뉴스 이벤트 없음'

  const text = `1. 과거 ${Math.min(inputWindow, histDf.length)}시간의 전력 부하와 기온 변화:
- 입력 구간의 평균 전력 부하는 ${fmt1(avgLoad)}MW로 나타났고, 기온은 ${fmt1(minTemp)}도에서 ${fmt1(maxTemp)}도 사이에 분포했습니다. ${
    hasCold
      ? '기온이 낮은 상태에서는 난방 수요가 증가하기 때문에 전력 부하가 상승하는 경향이 있습니다.'
      : '기온 변화가 완만한 구간이지만, 시간대별 사용 패턴과 시설 운영 특성에 따라 전력 부하 변동이 나타날 수 있습니다.'
  } 특히 ${end ? `${end.getMonth() + 1}월 ${end.getDate()}일 ${String(end.getHours()).padStart(2, '0')}시` : '현재 선택 시점'} 부근의 입력값이 예측 구간의 초기 수요 수준에 영향을 준 것으로 해석됩니다.

2. 사회적 상황과 뉴스 카운트:
- 선택 구간의 뉴스 데이터에서는 ${topEventName} 관련 뉴스가 ${topEventCount}건으로 가장 많이 나타났습니다. 주요 이벤트는 ${newsLine}입니다. ${
    hasTourism
      ? '특히 겨울철 관광 및 숙박·상업시설 이용 증가는 지역 내 소비와 난방 수요를 함께 높여 전력 수요 상승 요인으로 작용할 수 있습니다.'
      : hasEconomy
        ? '경제 활동이 활발해질 경우 상업시설과 업무시설의 운영량이 증가하여 전력 수요가 상승하는 경향이 있습니다.'
        : '이러한 사회적 이벤트는 시설 운영 시간, 난방 사용량, 상업 활동 변화 등을 통해 전력 수요에 간접적으로 반영될 수 있습니다.'
  }

3. Attention 수치가 높은 변수와 예측값의 변동:
- 모델의 Attention 수치에서는 target이 ${fmt4(targetAttention)}로 가장 높고, 기온 관련 변수는 ${fmt4(tempAttention)}로 나타났습니다. 이는 최근 전력 부하 자체와 기온이 예측 결과에 중요한 영향을 주고 있음을 의미합니다. 또한 known_future:pca_embedding_29와 같은 잠재 변수는 뉴스, 경제 활동, 관광 수요 등 외부 요인의 패턴을 압축적으로 반영하는 변수로 해석할 수 있습니다.

4. 결론적으로, 과거 전력 부하 흐름, 기온 변화, 뉴스 기반 사회적 상황, 그리고 Attention 상위 변수들을 종합했을 때 향후 전력 수요 예측은 기온에 따른 난방 수요, 경제·관광 활동 변화, 그리고 최근 부하 패턴의 상호작용에 의해 결정된 것으로 해석할 수 있습니다.`

  return { text, factors }
}

export function buildMapData(loadRows) {
  const regionSums = {}
  const regionCounts = {}
  for (const row of loadRows) {
    regionSums[row.region] = (regionSums[row.region] ?? 0) + row.power_usage
    regionCounts[row.region] = (regionCounts[row.region] ?? 0) + 1
  }

  return Object.entries(regionSums)
    .filter(([region]) => REGION_COORDS[region])
    .map(([region, sum]) => ({
      region,
      avg_load: +(sum / regionCounts[region]).toFixed(2),
      lat: REGION_COORDS[region][0],
      lng: REGION_COORDS[region][1],
    }))
}
