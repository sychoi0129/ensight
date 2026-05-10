<template>
  <div>
    <!-- 토글 -->
    <div style="display:flex; gap:16px; margin-bottom:14px;">
      <label class="toggle-wrap">
        <input type="checkbox" v-model="showCi" />
        <span class="toggle-track"><span class="toggle-thumb"></span></span>
        신뢰구간
      </label>
    </div>

    <div class="row" style="gap:14px; align-items:stretch;">
      <div class="col-2 panel" style="display:flex; flex-direction:column;">
        <div class="section-label">과거 7일의 전력 소모량</div>
        <div ref="chartEl" style="width:100%; flex:1; min-height:340px;"></div>
      </div>

      <div class="col-1" style="display:flex; flex-direction:column; gap:12px;">
        <div class="panel" style="flex:1;">
          <div class="section-label">향후 12시간의 전력 수요량 예측</div>

          <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; margin-bottom:14px;">
            <div class="mini-stat">
              <div class="mini-stat-label">평균</div>
              <div class="mini-stat-value" style="color:#5e72e4;">{{ predMean }}</div>
            </div>
            <div class="mini-stat">
              <div class="mini-stat-label">피크</div>
              <div class="mini-stat-value" style="color:#f5365c;">{{ predMax }}</div>
            </div>
            <div class="mini-stat">
              <div class="mini-stat-label">최저</div>
              <div class="mini-stat-value" style="color:#2dce89;">{{ predMin }}</div>
            </div>
          </div>

          <div style="overflow-y:auto; max-height:280px;">
            <table style="width:100%; border-collapse:collapse; font-size:12px;">
              <thead>
                <tr style="border-bottom:2px solid var(--border);">
                  <th style="padding:6px 8px; text-align:left; color:var(--text3); font-weight:600; font-size:10px; text-transform:uppercase; letter-spacing:.06em;">시각</th>
                  <th style="padding:6px 8px; text-align:right; color:var(--text3); font-weight:600; font-size:10px; text-transform:uppercase; letter-spacing:.06em;">예측 ({{ demandDisplayScale.pUnit }})</th>
                  <th style="padding:6px 8px; text-align:right; color:var(--text3); font-weight:600; font-size:10px; text-transform:uppercase; letter-spacing:.06em;">범위</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, i) in forecastRows" :key="row.ts" style="border-bottom:1px solid var(--border);">
                  <td style="padding:7px 8px; color:var(--text3); font-family:var(--mono); font-size:11px;">
                    +{{ i + 1 }}h
                  </td>
                  <td style="padding:7px 8px; text-align:right; font-family:var(--mono); font-weight:600;"
                    :style="{
                      color: forecastStats && Number(row.pred_1_step) === forecastStats.max ? '#f5365c'
                          : forecastStats && Number(row.pred_1_step) === forecastStats.min ? '#2dce89'
                          : 'var(--text1)'
                    }"
                  >
                    {{ formatDemandValue(row.pred_1_step) }}
                  </td>
                  <td style="padding:7px 8px; text-align:right; color:var(--text3); font-family:var(--mono); font-size:11px;">
                    {{ formatDemandValue((row.pred_1_step ?? 0) - 6) }} – {{ formatDemandValue((row.pred_1_step ?? 0) + 6) }}
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
import echarts from '@/plugins/echarts'
import XaiTab from '@/views/XaiTab.vue'

const props = defineProps({
  series:       { type: Array, default: () => [] },
  newsView:     { type: Array, default: () => [] },
  xaiResult:    { type: Object, default: () => ({ text: '', factors: [] }) },
  selectedDate: { type: String, default: '' },
  selectedTime: { type: String, default: '00:00' },
  isLoading:    { type: Boolean, default: false },
})

const chartEl = ref(null)
let chart = null
const showCi = ref(true)

const POWER_MW_THRESHOLD_KW = 1000

function fmtFixed2(n) {
  return n.toLocaleString('ko-KR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const sortedSeries = computed(() =>
  [...props.series].sort((a, b) => new Date(a.ts) - new Date(b.ts))
)

const anchorIndex = computed(() =>
  sortedSeries.value.findIndex(
    (row) => row.ts.slice(0, 10) === props.selectedDate && row.ts.slice(11, 16) === props.selectedTime
  )
)

const histRows = computed(() => {
  if (!sortedSeries.value.length) return []
  const idx = anchorIndex.value >= 0 ? anchorIndex.value : sortedSeries.value.length - 1
  const startIdx = Math.max(0, idx - 167)
  return sortedSeries.value.slice(startIdx, idx + 1)
})

const forecastRows = computed(() => {
  if (!sortedSeries.value.length) return []
  const idx = anchorIndex.value >= 0 ? anchorIndex.value : sortedSeries.value.length - 1
  const startIdx = Math.min(sortedSeries.value.length, idx + 1)
  return sortedSeries.value.slice(startIdx, startIdx + 12)
})

const forecastPlotRows = computed(() => {
  if (!forecastRows.value.length) return []
  const lastHist = histRows.value[histRows.value.length - 1]
  if (!lastHist) return forecastRows.value
  return [
    {
      ts: lastHist.ts,
      pred_1_step: lastHist.actual,
    },
    ...forecastRows.value,
  ]
})

const demandDisplayScale = computed(() => {
  const vals = []
  for (const row of histRows.value) {
    for (const k of ['actual', 'pred_1_step']) {
      const v = Number(row[k])
      if (Number.isFinite(v)) vals.push(Math.abs(v))
    }
  }
  for (const row of forecastRows.value) {
    const v = Number(row.pred_1_step)
    if (Number.isFinite(v)) vals.push(Math.abs(v))
    if (showCi.value) {
      const u = Number((row.pred_1_step ?? 0) + 6)
      if (Number.isFinite(u)) vals.push(Math.abs(u))
    }
  }
  const maxVal = vals.length ? Math.max(...vals) : 0
  const useMW = maxVal >= POWER_MW_THRESHOLD_KW
  return {
    useMW,
    pFactor: useMW ? 0.001 : 1,
    pUnit: useMW ? 'MW' : 'kW',
  }
})

const forecastStats = computed(() => {
  if (!forecastRows.value.length) return null
  const nums = forecastRows.value.map((row) => Number(row.pred_1_step)).filter(Number.isFinite)
  if (!nums.length) return null
  const min = Math.min(...nums)
  const max = Math.max(...nums)
  const mean = nums.reduce((a, b) => a + b, 0) / nums.length
  return { min, max, mean }
})

const predMean = computed(() => {
  const s = forecastStats.value
  if (!s) return '—'
  const { pFactor, pUnit } = demandDisplayScale.value
  return `${fmtFixed2(s.mean * pFactor)} ${pUnit}`
})
const predMax = computed(() => {
  const s = forecastStats.value
  if (!s) return '—'
  const { pFactor, pUnit } = demandDisplayScale.value
  return `${fmtFixed2(s.max * pFactor)} ${pUnit}`
})
const predMin = computed(() => {
  const s = forecastStats.value
  if (!s) return '—'
  const { pFactor, pUnit } = demandDisplayScale.value
  return `${fmtFixed2(s.min * pFactor)} ${pUnit}`
})

const fmtTime = d => {
  const p = n => String(n).padStart(2, '0')
  return `${p(d.getMonth()+1)}/${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

function formatDemandValue(value) {
  if (!Number.isFinite(Number(value))) return '—'
  const v = Number(value) * demandDisplayScale.value.pFactor
  return fmtFixed2(v)
}

function buildOption() {
  if (!sortedSeries.value.length) {
    return { xAxis: { type: 'time' }, yAxis: { type: 'value' }, series: [] }
  }

  const scale = demandDisplayScale.value

  const valueList = [...histRows.value, ...forecastRows.value]
    .flatMap((row) => [row.actual, row.pred_1_step])
    .filter(Number.isFinite)
  if (showCi.value && forecastRows.value.length) {
    for (const r of forecastRows.value) {
      const u = Number((r.pred_1_step ?? 0) + 6)
      if (Number.isFinite(u)) valueList.push(u)
    }
  }

  const rawMin = valueList.length ? Math.min(...valueList) * 0.97 : undefined
  const rawMax = valueList.length ? Math.max(...valueList) * 1.03 : undefined
  const yMinTick = Number.isFinite(rawMin) ? Math.floor(rawMin) : undefined
  const yMaxTick = Number.isFinite(rawMax) ? Math.ceil(rawMax) : undefined

  const series = [
    {
      name: '과거 사용량',
      type: 'line',
      data: histRows.value.map((row) => [row.ts, row.actual]),
      symbol: 'none',
      lineStyle: { color: '#5e72e4', width: 2 },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(94,114,228,0.2)' },
          { offset: 1, color: 'rgba(94,114,228,0.01)' },
        ]),
      },
      smooth: 0.08,
    },
    {
      name: '예측값',
      type: 'line',
      data: forecastPlotRows.value.map((row) => [row.ts, row.pred_1_step]),
      symbol: 'none',
      lineStyle: { color: '#11cdef', width: 2.5, type: 'dashed' },
      areaStyle: showCi.value ? {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(17,205,239,0.12)' },
          { offset: 1, color: 'rgba(17,205,239,0.01)' },
        ]),
      } : undefined,
      smooth: 0.08,
    },
  ]

  if (showCi.value && forecastRows.value.length) {
    series.push({
      name: '신뢰구간',
      type: 'line',
      data: forecastRows.value.map((row) => [row.ts, (row.pred_1_step ?? 0) + 6]),
      lineStyle: { opacity: 0 },
      areaStyle: { color: 'rgba(17,205,239,0.05)', origin: 'auto' },
      symbol: 'none',
      silent: true,
      showInLegend: false,
    })
  }

  return {
    backgroundColor: 'transparent',
    grid: { left: 60, right: 20, top: 44, bottom: 36 },
    legend: {
      top: 8, left: 0,
      itemWidth: 24, itemHeight: 3,
      textStyle: { color: '#8898aa', fontSize: 11, fontFamily: 'Pretendard' },
    },
    xAxis: {
      type: 'time',
      axisLine: { lineStyle: { color: '#e9ecef' } },
      axisTick: { show: false },
      axisLabel: {
        color: '#8898aa', fontSize: 10, fontFamily: 'Pretendard',
        formatter: v => {
          const d = new Date(v), p = n => String(n).padStart(2,'0')
          return `${p(d.getMonth()+1)}/${p(d.getDate())}`
        },
      },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      min: yMinTick,
      max: yMaxTick,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        fontSize: 10,
        fontFamily: 'Pretendard',
        formatter: (v) => {
          if (!Number.isFinite(v)) return ''
          const numStr = scale.useMW ? fmtFixed2(v * scale.pFactor) : `${Math.round(v)}`
          if (Number.isFinite(yMinTick) && Math.abs(v - yMinTick) < 1e-4) {
            return `{unit|${scale.pUnit}}{val|\u00A0${numStr}}`
          }
          return `{val|${numStr}}`
        },
        rich: {
          unit: {
            color: '#1a1a1a',
            fontWeight: 700,
            fontSize: 10,
            fontFamily: 'Pretendard',
          },
          val: {
            color: '#8898aa',
            fontWeight: 400,
            fontSize: 10,
            fontFamily: 'Pretendard',
          },
        },
      },
      splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } },
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#1a1a2e',
      borderColor: 'transparent',
      borderRadius: 10,
      padding: [10, 14],
      textStyle: { color: '#fff', fontSize: 12, fontFamily: 'Pretendard' },
      axisPointer: { lineStyle: { color: '#dee2e6', type: 'dashed' } },
      formatter: params => {
        if (!params.length) return ''
        const d = new Date(params[0].value[0])
        return `<div style="font-weight:700;margin-bottom:6px;color:#c8c8e0;">${fmtTime(d)}</div>` +
          params.map((p) => {
            const y = Number(p.value[1])
            if (!Number.isFinite(y)) return ''
            const valStr = fmtFixed2(y * scale.pFactor)
            return `<div style="display:flex;align-items:center;gap:6px;">
              <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};"></span>
              <span style="color:#a0a0c0;">${p.seriesName}</span>
              <b style="margin-left:auto;font-size:13px;">${valStr} ${scale.pUnit}</b>
            </div>`
          }).join('')
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
  [() => props.series, () => props.selectedDate, () => props.selectedTime, () => props.isLoading, showCi, demandDisplayScale],
  draw,
  { deep: true }
)
</script>