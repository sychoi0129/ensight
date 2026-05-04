<template>
  <div>
    <div style="display:flex; gap:16px; margin-bottom:14px;">
      <label class="toggle-wrap">
        <input type="checkbox" v-model="showCi" />
        <span class="toggle-track"><span class="toggle-thumb"></span></span>
        신뢰구간
      </label>
      <label class="toggle-wrap">
        <input type="checkbox" v-model="showNews" />
        <span class="toggle-track"><span class="toggle-thumb"></span></span>
        뉴스 오버레이
      </label>
    </div>

    <div class="row" style="gap:14px; align-items:stretch;">
      <div class="col-2 panel" style="display:flex; flex-direction:column;">
        <div class="section-label">과거 7일의 전력 소모량</div>
        <div style="display:flex; align-items:center; gap:10px; margin:10px 0 8px 0;">
          <span style="font-size:12px; color:var(--text3); font-weight:500;">기상 변수</span>
          <select class="content-select" v-model="selectedWeatherLabel">
            <option v-for="l in weatherMetricLabels" :key="l">{{ l }}</option>
          </select>
        </div>
        <div ref="chartEl" style="width:100%; flex:1; min-height:340px;"></div>
      </div>

      <div class="col-1" style="display:flex; flex-direction:column; gap:12px;">
        <div class="panel" style="flex:1;">
          <div class="section-label">향후 {{ horizon }}시간의 전력 수요량 예측</div>

          <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; margin-bottom:14px;">
            <div class="mini-stat">
              <div class="mini-stat-label">평균 ({{ powerUnit }})</div>
              <div class="mini-stat-value" style="color:#5e72e4;">{{ predMean.toFixed(2) }}</div>
            </div>
            <div class="mini-stat">
              <div class="mini-stat-label">피크 ({{ powerUnit }})</div>
              <div class="mini-stat-value" style="color:#f5365c;">{{ predMax.toFixed(2) }}</div>
            </div>
            <div class="mini-stat">
              <div class="mini-stat-label">최저 ({{ powerUnit }})</div>
              <div class="mini-stat-value" style="color:#2dce89;">{{ predMin.toFixed(2) }}</div>
            </div>
          </div>

          <div style="overflow-y:auto; max-height:280px;">
            <table style="width:100%; border-collapse:collapse; font-size:12px;">
              <thead>
                <tr style="border-bottom:2px solid var(--border);">
                  <th style="padding:6px 8px; text-align:left; color:var(--text3); font-weight:600; font-size:10px; text-transform:uppercase; letter-spacing:.06em;">시각</th>
                  <th style="padding:6px 8px; text-align:right; color:var(--text3); font-weight:600; font-size:10px; text-transform:uppercase; letter-spacing:.06em;">예측 ({{ powerUnit }})</th>
                  <th style="padding:6px 8px; text-align:right; color:var(--text3); font-weight:600; font-size:10px; text-transform:uppercase; letter-spacing:.06em;">범위</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(row, i) in forecastDf" :key="i"
                  style="border-bottom:1px solid var(--border);"
                >
                  <td style="padding:7px 8px; color:var(--text3); font-family:var(--mono); font-size:11px;">
                    +{{ i+1 }}h
                  </td>
                  <td style="padding:7px 8px; text-align:right; font-family:var(--mono); font-weight:600;"
                    :style="{
                      color: row.prediction === predMax ? '#f5365c'
                        : row.prediction === predMin ? '#2dce89'
                        : 'var(--text1)'
                    }"
                  >
                    {{ row.prediction.toFixed(2) }}
                  </td>
                  <td style="padding:7px 8px; text-align:right; color:var(--text3); font-family:var(--mono); font-size:11px;">
                    {{ row.lower.toFixed(2) }} – {{ row.upper.toFixed(2) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <div style="margin-top:16px;">
      <XaiTab :xai-result="xaiResult" :news-view="newsView" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import XaiTab from '@/views/XaiTab.vue'
import { WEATHER_METRIC_MAP } from '@/constants/settings'
import * as echarts from 'echarts'

const props = defineProps({
  histDf:       { type: Array,  default: () => [] },
  forecastDf:   { type: Array,  default: () => [] },
  weatherView:  { type: Array,  default: () => [] },
  newsView:     { type: Array,  default: () => [] },
  horizon:      { type: Number, default: 12 },
  xaiResult:    { type: Object, default: () => ({ text: '', factors: [] }) },
  powerUnit:    { type: String, default: 'MW' },
})

const weatherMetricLabels = Object.keys(WEATHER_METRIC_MAP)
const selectedWeatherLabel = ref(weatherMetricLabels[0] ?? '기온 (°C)')

const WEATHER_LINE_COLOR = {
  temperature: '#2dce89',
  rainfall: '#11cdef',
  wind_speed: '#fb6340',
  humidity: '#b4bcc8',
}

function weatherAt(tsMs) {
  return props.weatherView.find(
    r => r?.timestamp && Number(r.timestamp.getTime()) === tsMs,
  )
}

function alignWeatherSeries(key) {
  return props.histDf.map(h => {
    const ts = h.timestamp
    const w = weatherAt(new Date(ts).getTime())
    if (!w) return [ts, null]
    const v = w[key]
    const n = Number(v)
    return [ts, Number.isFinite(n) ? n : null]
  })
}

function numericRangeFromPairs(pairs, pad = 0.06) {
  const nums = pairs.map(p => p[1]).filter(v => v != null && Number.isFinite(v))
  if (!nums.length) return [0, 1]
  const lo = Math.min(...nums)
  const hi = Math.max(...nums)
  if (lo === hi) return [lo === 0 ? -0.5 : lo * 0.92, hi === 0 ? 0.5 : hi * 1.08]
  const span = hi - lo
  return [lo - span * pad, hi + span * pad]
}

function fmtWeatherAxisTick(metricKey, v) {
  const n = Number(v)
  if (!Number.isFinite(n)) return ''
  if (metricKey === 'rainfall') return n.toFixed(3)
  return String(Math.round(n))
}

function fmtWeatherSeriesVal(metricKey, val) {
  if (!Number.isFinite(val)) return ''
  if (metricKey === 'rainfall') return val.toFixed(3)
  return String(Math.round(val))
}

const showCi   = ref(true)
const showNews = ref(false)
const chartEl  = ref(null)
let chart = null

const predMean = computed(() =>
  props.forecastDf.length ? props.forecastDf.reduce((s, r) => s + r.prediction, 0) / props.forecastDf.length : 0,
)
const predMax = computed(() => props.forecastDf.length ? Math.max(...props.forecastDf.map(r => r.prediction)) : 0)
const predMin = computed(() => props.forecastDf.length ? Math.min(...props.forecastDf.map(r => r.prediction)) : 0)

const fmtTime = d => {
  const p = n => String(n).padStart(2, '0')
  return `${p(d.getMonth()+1)}/${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

function buildOption() {
  const histX = props.histDf.map(r => r.timestamp)
  const histY = props.histDf.map(r => r.power_usage)
  const fcX   = props.forecastDf.map(r => r.timestamp)
  const fcY   = props.forecastDf.map(r => r.prediction)
  const allY  = [...histY, ...fcY]
  const upperBand = showCi.value && props.forecastDf.length
    ? props.forecastDf.map(r => r.upper)
    : []
  const yMin = allY.length
    ? Math.min(...allY, ...upperBand) * 0.97
    : 0
  const yMax = allY.length
    ? Math.max(...allY, ...upperBand) * 1.04
    : 1

  const useWeather = props.weatherView.length > 0 && props.histDf.length > 0
  const metricKey = WEATHER_METRIC_MAP[selectedWeatherLabel.value]
  const weatherColor = metricKey ? WEATHER_LINE_COLOR[metricKey] : '#2dce89'

  const weatherSeriesFirst = []
  if (useWeather && metricKey) {
    weatherSeriesFirst.push({
      name: selectedWeatherLabel.value,
      type: 'line',
      yAxisIndex: 1,
      data: alignWeatherSeries(metricKey),
      symbol: 'none',
      lineStyle: { color: weatherColor, width: 2, type: 'dashed' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: `${weatherColor}26` },
          { offset: 1, color: `${weatherColor}05` },
        ]),
      },
      smooth: 0.25,
      z: 1,
    })
  }

  const series = [
    ...weatherSeriesFirst,
    {
      name: '과거 사용량',
      type: 'line',
      yAxisIndex: 0,
      data: histX.map((x, i) => [x, histY[i]]),
      symbol: 'none',
      lineStyle: { color: '#5e72e4', width: 2 },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(94,114,228,0.2)' },
          { offset: 1, color: 'rgba(94,114,228,0.01)' },
        ]),
      },
      smooth: 0.25,
      z: 2,
    },
    {
      name: '예측값',
      type: 'line',
      yAxisIndex: 0,
      data: fcX.map((x, i) => [x, fcY[i]]),
      symbol: 'none',
      lineStyle: { color: '#11cdef', width: 2.5 },
      areaStyle: showCi.value ? {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(17,205,239,0.12)' },
          { offset: 1, color: 'rgba(17,205,239,0.01)' },
        ]),
      } : undefined,
      smooth: 0.25,
      z: 2,
    },
  ]

  if (showCi.value && props.forecastDf.length) {
    series.push({
      name: '신뢰구간',
      type: 'line',
      yAxisIndex: 0,
      data: fcX.map((x, i) => [x, props.forecastDf[i].upper]),
      lineStyle: { opacity: 0 },
      areaStyle: { color: 'rgba(17,205,239,0.05)', origin: 'auto' },
      symbol: 'none',
      silent: true,
      showInLegend: false,
    })
  }

  if (showNews.value && props.newsView.length && allY.length) {
    series.push({
      name: '뉴스',
      type: 'scatter',
      yAxisIndex: 0,
      data: props.newsView.map(r => ({
        value: [r.timestamp, yMin + (yMax - yMin) * 0.015],
        headline: r.headline,
        event_type: r.event_type,
      })),
      symbol: 'diamond',
      symbolSize: 12,
      itemStyle: { color: '#f5365c', borderColor: 'rgba(245,54,92,0.25)', borderWidth: 8 },
    })
  }

  const powerYAxis = {
    type: 'value',
    min: yMin,
    max: yMax,
    name: props.powerUnit,
    position: 'left',
    nameGap: 6,
    nameTextStyle: { color: '#8898aa', fontSize: 10, fontFamily: 'Pretendard', padding: [-4, 0, 0, 8] },
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: {
      color: '#8898aa',
      fontSize: 10,
      fontFamily: 'Pretendard',
      formatter: v => Number(v).toFixed(2),
    },
    splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } },
  }

  let weatherYAxes = []
  if (useWeather && metricKey) {
    const data = alignWeatherSeries(metricKey)
    let [wMin, wMax] = numericRangeFromPairs(data)
    if (metricKey === 'humidity') {
      wMin = Math.max(0, wMin)
      wMax = Math.min(100, wMax)
      if (wMax - wMin < 1e-6) wMax = wMin + 5
    }
    if (metricKey === 'rainfall') wMin = Math.max(0, wMin)
    weatherYAxes = [
      {
        type: 'value',
        min: wMin,
        max: wMax,
        name: selectedWeatherLabel.value,
        position: 'right',
        offset: 0,
        nameTextStyle: { color: weatherColor, fontSize: 10, fontFamily: 'Pretendard' },
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: {
          color: weatherColor,
          fontSize: 10,
          fontFamily: 'Pretendard',
          formatter: v => fmtWeatherAxisTick(metricKey, v),
        },
        splitLine: { show: false },
      },
    ]
  }

  const tooltipOrder = [selectedWeatherLabel.value, '과거 사용량', '예측값']
  const chartRightPad =
    useWeather && metricKey ? (metricKey === 'rainfall' ? 58 : 46) : 20
  const legendRightPad =
    useWeather && metricKey ? (metricKey === 'rainfall' ? 64 : 50) : 8

  return {
    backgroundColor: 'transparent',
    grid: {
      left: 52,
      right: chartRightPad,
      top: useWeather && metricKey ? 48 : 40,
      bottom: 36,
    },
    legend: {
      type: 'scroll',
      top: 2,
      left: 0,
      right: legendRightPad,
      itemWidth: 24,
      itemHeight: 3,
      textStyle: { color: '#8898aa', fontSize: 11, fontFamily: 'Pretendard' },
    },
    xAxis: {
      type: 'time',
      axisLine: { lineStyle: { color: '#e9ecef' } },
      axisTick: { show: false },
      axisLabel: {
        color: '#8898aa',
        fontSize: 10,
        fontFamily: 'Pretendard',
        formatter: v => {
          const d = new Date(v)
          const p = n => String(n).padStart(2, '0')
          return `${p(d.getMonth()+1)}/${p(d.getDate())}`
        },
      },
      splitLine: { show: false },
    },
    yAxis: useWeather && metricKey && weatherYAxes.length ? [powerYAxis, ...weatherYAxes] : powerYAxis,
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#1a1a2e',
      borderColor: 'transparent',
      borderRadius: 10,
      padding: [10, 14],
      textStyle: { color: '#fff', fontSize: 12, fontFamily: 'Pretendard' },
      axisPointer: { lineStyle: { color: '#dee2e6', type: 'dashed' } },
      formatter: params => {
        const news = params.find(p => p.seriesName === '뉴스')
        if (news?.data) {
          return `<div style="font-weight:700;margin-bottom:4px;">${news.data.event_type}</div>
                  <div style="font-size:11px;color:#c0c0d8;">${news.data.headline}</div>`
        }
        const t0 = params.find(p => p.value && p.value[0] != null)
        if (!t0) return ''
        const d = new Date(t0.value[0])
        let body = ''
        for (const seriesName of tooltipOrder) {
          const p = params.find(x => x.seriesName === seriesName)
          if (!p || p.value == null || p.value[1] == null) continue
          const val = p.value[1]
          if (!Number.isFinite(val)) continue
          const unit =
            seriesName === selectedWeatherLabel.value
              ? ''
              : ['과거 사용량', '예측값'].includes(seriesName)
                ? props.powerUnit
                : ''
          const valStr =
            seriesName === selectedWeatherLabel.value
              ? fmtWeatherSeriesVal(metricKey, val)
              : val.toFixed(2)
          body += `<div style="display:flex;align-items:center;gap:6px;margin:3px 0;">
            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};"></span>
            <span style="color:#a0a0c0;">${seriesName}</span>
            <b style="margin-left:auto;">${valStr}</b>
            ${unit ? `<span style="color:#6a6a8a;font-size:11px;margin-left:4px;">${unit}</span>` : ''}
          </div>`
        }
        if (!body) return ''
        return `<div style="font-weight:700;margin-bottom:6px;color:#c8c8e0;">${fmtTime(d)}</div>${body}`
      },
    },
    series,
  }
}

async function draw() {
  await nextTick()
  if (!chartEl.value) return
  if (!chart) chart = echarts.init(chartEl.value)
  chart.setOption(buildOption(), true)
}

onMounted(() => setTimeout(draw, 100))
onUnmounted(() => chart?.dispose())
watch(
  [
    () => props.histDf,
    () => props.forecastDf,
    () => props.weatherView,
    () => props.newsView,
    () => props.powerUnit,
    showCi,
    showNews,
    selectedWeatherLabel,
  ],
  draw,
)
</script>
