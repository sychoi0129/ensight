// forecast.py → useForecast.js

export function makeForecast(historyRows, horizon = 12) {
  if (!historyRows || historyRows.length === 0) return []

  const sorted = [...historyRows].sort((a, b) => a.timestamp - b.timestamp)
  const values = sorted.map(r => r.power_usage)

  const lastTs = sorted[sorted.length - 1].timestamp
  const futureTimes = Array.from({ length: horizon }, (_, i) => {
    const d = new Date(lastTs)
    d.setHours(d.getHours() + i + 1)
    return d
  })

  // 최근 24시간 패턴 반복
  const last24 = values.slice(-24)
  const repeated = Array.from({ length: horizon }, (_, i) => last24[i % last24.length])

  // 레벨 조정
  const longMean = values.reduce((a, b) => a + b, 0) / values.length
  const shortMean = values.slice(-24).reduce((a, b) => a + b, 0) / 24
  const levelShift = shortMean - longMean

  // 완만한 추세
  const trend = Array.from({ length: horizon }, (_, i) => (1.5 * i) / (horizon - 1))

  return futureTimes.map((ts, i) => {
    const pred = +(repeated[i] + 0.3 * levelShift + trend[i]).toFixed(2)
    return {
      timestamp: ts,
      prediction: pred,
      lower: +(pred - 6).toFixed(2),
      upper: +(pred + 6).toFixed(2),
    }
  })
}
