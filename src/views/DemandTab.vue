<template>
  <div>
    <div style="display:flex; gap:16px; margin-bottom:14px;">
      <label class="toggle-wrap">
        <input type="checkbox" checked disabled />
        <span class="toggle-track"><span class="toggle-thumb"></span></span>
        신뢰구간
      </label>
      <label class="toggle-wrap">
        <input type="checkbox" checked disabled />
        <span class="toggle-track"><span class="toggle-thumb"></span></span>
        뉴스 오버레이
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
                    +{{ i + 1 }}h ({{ row.ts.slice(11, 16) }})
                  </td>
                  <td style="padding:7px 8px; text-align:right; font-family:var(--mono); font-weight:600;">
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

        <div class="panel">
          <div class="section-label">Metrics</div>
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; font-size:12px;">
            <div>MAE 1-step: <b>{{ formatValue(metrics.mae_1_step) }}</b></div>
            <div>RMSE 1-step: <b>{{ formatValue(metrics.rmse_1_step) }}</b></div>
            <div>MAE 24-step: <b>{{ formatValue(metrics.mae_24_step) }}</b></div>
            <div>RMSE 24-step: <b>{{ formatValue(metrics.rmse_24_step) }}</b></div>
            <div>총 충전량: <b>{{ formatValue(metrics.total_charge_kwh) }}</b></div>
            <div>총 방전량: <b>{{ formatValue(metrics.total_discharge_kwh) }}</b></div>
            <div>평균 SOC: <b>{{ formatValue(metrics.avg_soc) }}</b></div>
            <div>피크 감소량: <b>{{ formatValue(metrics.peak_reduction) }}</b></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  series:       { type: Array, default: () => [] },
  metrics:      { type: Object, default: () => ({}) },
  selectedTime: { type: String, default: '00:00' },
  isLoading:    { type: Boolean, default: false },
})

const chartEl = ref(null)
let chart = null

const forecastRows = computed(() => {
  if (!props.series.length) return []
  const idx = props.series.findIndex((row) => row.ts.slice(11, 16) === props.selectedTime)
  const startIdx = idx >= 0 ? idx : 0
  return props.series.slice(startIdx, startIdx + 12)
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
  if (!props.series.length) {
    return { xAxis: { type: 'time' }, yAxis: { type: 'value' }, series: [] }
  }

  const values = props.series.flatMap((row) => [
    row.actual,
    row.pred_1_step,
    row.pred_24_step,
    row.rt_result,
  ]).filter(Number.isFinite)

  const yMin = Math.min(...values) * 0.97
  const yMax = Math.max(...values) * 1.03

  const series = [
    {
      name: 'actual',
      type: 'line',
      data: props.series.map((row) => [row.ts, row.actual]),
      symbol: 'none',
      lineStyle: { color: '#5e72e4', width: 2 },
      smooth: 0.25,
    },
    {
      name: 'pred_1_step',
      type: 'line',
      data: props.series.map((row) => [row.ts, row.pred_1_step]),
      symbol: 'none',
      lineStyle: { color: '#11cdef', width: 2, type: 'dashed' },
      smooth: 0.25,
    },
    {
      name: 'pred_24_step',
      type: 'line',
      data: props.series.map((row) => [row.ts, row.pred_24_step]),
      symbol: 'none',
      lineStyle: { color: '#fb6340', width: 2, type: 'dotted' },
      smooth: 0.25,
    },
    {
      name: 'rt_result',
      type: 'line',
      data: props.series.map((row) => [row.ts, row.rt_result]),
      symbol: 'none',
      lineStyle: { color: '#2dce89', width: 2 },
      smooth: 0.25,
    },
  ]

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
watch([() => props.series, () => props.selectedTime, () => props.isLoading], draw, { deep: true })
</script>