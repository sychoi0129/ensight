// xai.py → useXai.js

import { REGION_COORDS } from '@/constants/settings'

export function summarizeXai(historyRows, weatherRows, newsRows, inputWindow = 168) {
  if (!historyRows || historyRows.length === 0) {
    return { text: '입력 구간 데이터가 없어 설명을 생성할 수 없습니다.', factors: [] }
  }

  const sorted = [...historyRows].sort((a, b) => a.timestamp - b.timestamp)
  const latest = sorted[sorted.length - 1]

  const recentW = [...weatherRows]
    .sort((a, b) => a.timestamp - b.timestamp)
    .slice(-inputWindow)

  const avgTemp = recentW.length > 0
    ? recentW.reduce((s, r) => s + r.temperature, 0) / recentW.length
    : 0
  const rainSum = recentW.reduce((s, r) => s + r.rainfall, 0)

  const factors = []

  if (avgTemp < 5) {
    factors.push({ factor: '낮은 기온', direction: '증가', importance: 0.42 })
  } else {
    factors.push({ factor: '완만한 기온', direction: '보합', importance: 0.24 })
  }

  if (rainSum > 20) {
    factors.push({ factor: '강수 이벤트', direction: '증가', importance: 0.27 })
  } else {
    factors.push({ factor: '강수 영향 제한적', direction: '보합', importance: 0.14 })
  }

  if (newsRows.length > 0) {
    const top = [...newsRows].sort((a, b) => b.impact_score - a.impact_score)[0]
    factors.push({
      factor: `뉴스: ${top.event_type}`,
      direction: top.impact_score >= 0.6 ? '증가' : '변동성 확대',
      importance: top.impact_score,
    })
  }

  const text =
    `입력 구간 ${inputWindow} step 기준 최근 전력 사용량은 ${latest.power_usage.toFixed(1)} 수준이며, ` +
    `입력 구간 평균 기온은 ${avgTemp.toFixed(1)}°C입니다. ` +
    `기온, 강수, 뉴스 이벤트를 종합하면 향후 12 step 동안 ` +
    `전력 수요의 상승 또는 변동성 확대 가능성이 있습니다.`

  return { text, factors }
}

export function buildMapData(loadRows) {
  // 지역별 평균 집계
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
