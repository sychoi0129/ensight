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
                  <th style="padding:6px 8px; text-align:right; color:var(--text3); font-weight:600; font-size:10px; text-transform:uppercase; letter-spacing:.06em;">예측 (W)</th>
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
                      color: Number(row.pred_1_step) === Number(predMax) ? '#f5365c'
                          : Number(row.pred_1_step) === Number(predMin) ? '#2dce89'
                          : 'var(--text1)'
                    }"
                  >
                    {{ formatValue(row.pred_1_step) }}
                  </td>
                  <td style="padding:7px 8px; text-align:right; color:var(--text3); font-family:var(--mono); font-size:11px;">
                    {{ formatValue((row.pred_1_step ?? 0) - 6) }} – {{ formatValue((row.pred_1_step ?? 0) + 6) }}
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
import * as echarts from 'echarts'
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

const predMean = computed(() => {
  if (!forecastRows.value.length) return '—'
  const mean = forecastRows.value.reduce((acc, row) => acc + (row.pred_1_step ?? 0), 0) / forecastRows.value.length
  return mean.toFixed(1)
})
const predMax = computed(() => {
  if (!forecastRows.value.length) return '—'
  return Math.max(...forecastRows.value.map((row) => row.pred_1_step ?? 0)).toFixed(1)
})
const predMin = computed(() => {
  if (!forecastRows.value.length) return '—'
  return Math.min(...forecastRows.value.map((row) => row.pred_1_step ?? 0)).toFixed(1)
})

const fmtTime = d => {
  const p = n => String(n).padStart(2, '0')
  return `${p(d.getMonth()+1)}/${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

function formatValue(value) {
  if (!Number.isFinite(value)) return '—'
  return Number(value).toFixed(2)
}

function buildOption() {
  if (!sortedSeries.value.length) {
    return { xAxis: { type: 'time' }, yAxis: { type: 'value' }, series: [] }
  }

  const values = [...histRows.value, ...forecastRows.value]
    .flatMap((row) => [row.actual, row.pred_1_step])
    .filter(Number.isFinite)

  const yMin = Math.min(...values) * 0.97
  const yMax = Math.max(...values, ...(showCi.value ? forecastRows.value.map((r) => (r.pred_1_step ?? 0) + 6) : [])) * 1.03

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
    grid: { left: 52, right: 20, top: 44, bottom: 36 },
    legend: {
      top: 6, left: 0,
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
      type: 'value', min: yMin, max: yMax,
      axisLine: { show: false }, axisTick: { show: false },
      axisLabel: { color: '#8898aa', fontSize: 10, fontFamily: 'Pretendard', formatter: v => Math.round(v) },
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
          params.map((p) => (
            `<div style="display:flex;align-items:center;gap:6px;">
              <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};"></span>
              <span style="color:#a0a0c0;">${p.seriesName}</span>
              <b style="margin-left:auto;font-size:13px;">${Number(p.value[1]).toFixed(1)}</b>
            </div>`
          )).join('')
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
watch([() => props.series, () => props.selectedDate, () => props.selectedTime, () => props.isLoading, showCi], draw, { deep: true })
</script>