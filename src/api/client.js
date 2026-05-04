import { apiUrl } from '@/constants/api'

export function toLocalIso(d) {
  if (!d) return ''
  const p = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

export async function fetchRegions() {
  const res = await fetch(apiUrl('/api/regions'))
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function fetchTimeRange(regionId) {
  const u = new URL(apiUrl('/api/time-range'))
  u.searchParams.set('region_id', String(regionId))
  const res = await fetch(u)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function fetchDashboard(
  regionId,
  issueTsIso,
  pastHours = 168,
  modelId = 5,
  forecastHours = 24,
) {
  const u = new URL(apiUrl('/api/dashboard'))
  u.searchParams.set('region_id', String(regionId))
  u.searchParams.set('issue_ts', issueTsIso)
  u.searchParams.set('model_id', String(modelId))
  u.searchParams.set('past_hours', String(pastHours))
  u.searchParams.set('forecast_hours', String(forecastHours))
  const res = await fetch(u)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function fetchMapSummary(issueTsIso, pastHours = 168) {
  const u = new URL(apiUrl('/api/map-summary'))
  u.searchParams.set('issue_ts', issueTsIso)
  u.searchParams.set('past_hours', String(pastHours))
  const res = await fetch(u)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

/** histDf 한 줄마다 동일 스냅샷 기상(백엔드 단일 시각 행)을 붙여 WeatherTab 형식으로 맞춤 */
export function weatherRowsFromSnapshot(histDf, weatherDict, regionName) {
  if (!weatherDict || !histDf.length) return []
  const temperature = Number(weatherDict.temp ?? weatherDict.temperature ?? NaN)
  const rainfall = Number(
    weatherDict.rainfall ?? weatherDict.precip ?? weatherDict.prcp ?? weatherDict.rain ?? 0,
  )
  const wind_speed = Number(
    weatherDict.wind_speed ??
      weatherDict.wspd ??
      weatherDict.windspeed ??
      weatherDict.wind_sp ??
      0,
  )
  const humidity = Number(
    weatherDict.humidity ?? weatherDict.rh ?? weatherDict.rhum ?? 0,
  )
  return histDf.map(h => ({
    timestamp: h.timestamp,
    region: regionName,
    temperature: Number.isFinite(temperature) ? temperature : 0,
    rainfall: Number.isFinite(rainfall) ? rainfall : 0,
    wind_speed: Number.isFinite(wind_speed) ? wind_speed : 0,
    humidity: Number.isFinite(humidity) ? humidity : 0,
  }))
}

export function weatherRowsFromSeries(weatherSeries, regionName) {
  if (!Array.isArray(weatherSeries) || !weatherSeries.length) return []
  return weatherSeries
    .map(r => {
      const ts = new Date(r.ts)
      if (!Number.isFinite(ts.getTime())) return null
      const temperature = Number(r.temp ?? r.temperature ?? NaN)
      const rainfall = Number(r.rainfall ?? r.precip ?? r.prcp ?? r.rain ?? 0)
      const wind_speed = Number(
        r.wind_speed ?? r.wspd ?? r.windspeed ?? r.wind_sp ?? 0,
      )
      const humidity = Number(r.humidity ?? r.rh ?? r.rhum ?? 0)
      return {
        timestamp: ts,
        region: regionName,
        temperature: Number.isFinite(temperature) ? temperature : 0,
        rainfall: Number.isFinite(rainfall) ? rainfall : 0,
        wind_speed: Number.isFinite(wind_speed) ? wind_speed : 0,
        humidity: Number.isFinite(humidity) ? humidity : 0,
      }
    })
    .filter(Boolean)
}

function parseTopicCounts(raw) {
  if (!raw) return {}
  if (typeof raw === 'object') return raw
  if (typeof raw === 'string') {
    try {
      const parsed = JSON.parse(raw)
      return parsed && typeof parsed === 'object' ? parsed : {}
    } catch {
      return {}
    }
  }
  return {}
}

/** 일별 뉴스 언급 합 — topic_count_sum 우선, 없으면 topic_counts 합산 */
export function newsDayMentionTotal(dayRow) {
  if (!dayRow) return 0
  const sumField = Number(dayRow.topic_count_sum)
  if (Number.isFinite(sumField) && sumField > 0) return sumField
  const tc = parseTopicCounts(dayRow.topic_counts)
  return Object.values(tc).reduce((s, v) => s + (Number(v) || 0), 0)
}

/** 기준 일 행에서 topic_counts에 언급이 있는 키워드(토픽) 종류 수. 상세 없이 합계만 있으면 1 */
export function newsDayKeywordCount(dayRow) {
  if (!dayRow) return 0
  const tc = parseTopicCounts(dayRow.topic_counts)
  const kinds = Object.values(tc).filter(v => Number(v) > 0).length
  if (kinds > 0) return kinds
  const sumField = Number(dayRow.topic_count_sum)
  return Number.isFinite(sumField) && sumField > 0 ? 1 : 0
}

export function newsSeriesMentionTotal(newsSeries) {
  if (!Array.isArray(newsSeries) || !newsSeries.length) return 0
  return newsSeries.reduce((s, row) => s + newsDayMentionTotal(row), 0)
}

export function newsRowsFromDashboardNewsSeries(newsSeries, regionName) {
  if (!Array.isArray(newsSeries) || !newsSeries.length) return []

  const rows = []
  for (const dayRow of newsSeries) {
    const topicCounts = parseTopicCounts(dayRow?.topic_counts)
    let entries = Object.entries(topicCounts)
      .map(([event_type, cnt]) => ({
        event_type,
        count: Number(cnt),
      }))
      .filter(r => Number.isFinite(r.count) && r.count > 0)
      .sort((a, b) => b.count - a.count)

    const newsDate = dayRow?.news_date ? new Date(dayRow.news_date) : null
    if (!Number.isFinite(newsDate?.getTime())) continue
    newsDate.setHours(12, 0, 0, 0)

    if (!entries.length) {
      const totalOnly = newsDayMentionTotal(dayRow)
      if (totalOnly <= 0) continue
      entries = [{ event_type: '일간 집계', count: totalOnly }]
    }

    const total = entries.reduce((s, r) => s + r.count, 0)

    for (const [idx, row] of entries.entries()) {
      const ratio = total > 0 ? row.count / total : 0
      const impact = Math.min(0.95, Math.max(0.35, 0.35 + ratio * 0.6))
      const ts = new Date(newsDate)
      ts.setMinutes(ts.getMinutes() + idx)
      rows.push({
        timestamp: ts,
        region: regionName,
        event_type: row.event_type,
        keyword: row.event_type,
        direction: 'neutral',
        headline: `${regionName} ${row.event_type} 언급 ${row.count}건`,
        summary: `${dayRow.news_date} 뉴스에서 ${row.event_type} 카테고리가 ${row.count}건 집계되었습니다.`,
        impact_score: +impact.toFixed(2),
        count: row.count,
      })
    }
  }

  return rows
}

export function histFromDashboard(series) {
  if (!series?.length) return []
  return series.map(r => ({
    timestamp: new Date(r.ts),
    power_usage: Number(r.usage_value),
  }))
}

export function forecastFromDashboard(series) {
  if (!series?.length) return []
  return series.map(r => ({
    timestamp: new Date(r.target_ts),
    prediction: Number(r.yhat_value),
    lower: Number(r.yhat_lower),
    upper: Number(r.yhat_upper),
  }))
}

export async function fetchMapAverages(regionList, issueTsIso, pastHours) {
  const settled = await Promise.allSettled(
    regionList.map(({ region_id }) =>
      fetchDashboard(region_id, issueTsIso, pastHours).then(d => ({
        region_id,
        actual_series: d.actual_series,
      })),
    ),
  )
  return settled
    .map(r => (r.status === 'fulfilled' ? r.value : null))
    .filter(Boolean)
}
