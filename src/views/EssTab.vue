<template>
  <div style="display:flex; flex-direction:column; gap:14px;">
    <div class="panel" style="display:flex; flex-direction:column;">
      <div class="section-label">실측/예측/ESS 비교</div>
      <div ref="compareChartEl" style="width:100%; min-height:340px;"></div>
    </div>

    <div class="ess-split-row">
      <div class="panel ess-chart-panel" style="display:flex; flex-direction:column;">
        <div class="section-label">ESS 운전 상태 (충전/방전/SOC/가격)</div>
        <div ref="essChartEl" style="width:100%; flex:1; min-height:340px;"></div>
      </div>

      <div class="ess-kpi-column">
        <div class="panel">
          <div class="section-label">선택 시간 ESS 상태</div>
          <div class="ess-stat-list">
            <div class="ess-stat-row">
              <span class="ess-stat-label">충전 전력</span>
              <span class="ess-stat-value">{{ formatPowerKw(selectedPoint?.charge_kw) }}</span>
            </div>
            <div class="ess-stat-row">
              <span class="ess-stat-label">방전 전력</span>
              <span class="ess-stat-value">{{ formatPowerKw(selectedPoint?.discharge_kw) }}</span>
            </div>
            <div class="ess-stat-row">
              <span class="ess-stat-label">ESS 조정량</span>
              <span class="ess-stat-value">{{ formatSignedPowerKw(selectedPoint?.ess_adjustment_kw) }}</span>
            </div>
            <div class="ess-stat-row">
              <span class="ess-stat-label">SOC</span>
              <span class="ess-stat-value">{{ formatSocPct(selectedPoint?.soc) }}</span>
            </div>
            <div class="ess-stat-row">
              <span class="ess-stat-label">전력가격</span>
              <span class="ess-stat-value">{{ formatPriceKwh(selectedPoint?.price) }}</span>
            </div>
            <div class="ess-stat-row">
              <span class="ess-stat-label">ESS 적용 후 부하</span>
              <span class="ess-stat-value">{{ formatPowerKw(selectedPoint?.rt_result) }}</span>
            </div>
          </div>
        </div>

        <div class="panel">
          <div class="section-label">ESS 요약 지표</div>
          <div class="ess-stat-list">
            <div class="ess-stat-row">
              <span class="ess-stat-label">총 충전량</span>
              <span class="ess-stat-value">{{ formatEnergyKwh(metrics.total_charge_kwh) }}</span>
            </div>
            <div class="ess-stat-row">
              <span class="ess-stat-label">총 방전량</span>
              <span class="ess-stat-value">{{ formatEnergyKwh(metrics.total_discharge_kwh) }}</span>
            </div>
            <div class="ess-stat-row">
              <span class="ess-stat-label">평균 SOC</span>
              <span class="ess-stat-value">{{ formatSocPct(metrics.avg_soc) }}</span>
            </div>
            <div class="ess-stat-row">
              <span class="ess-stat-label">{{ peakDisplay.title }}</span>
              <span class="ess-stat-value">{{ peakDisplay.body }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import echarts from '@/plugins/echarts'

const POWER_KEYS = ['charge_kw', 'discharge_kw', 'ess_adjustment_kw', 'rt_result', 'actual', 'pred_1_step', 'pred_24_step']
const POWER_MW_THRESHOLD_KW = 1000

const props = defineProps({
  series: { type: Array, default: () => [] },
  metrics: { type: Object, default: () => ({}) },
  selectedDate: { type: String, default: '' },
  selectedTime: { type: String, default: '00:00' },
})

const compareChartEl = ref(null)
const essChartEl = ref(null)
let compareChart = null
let essChart = null

const daySeries = computed(() =>
  props.series.filter((row) => row.ts.slice(0, 10) === props.selectedDate)
)

const selectedPoint = computed(() => {
  if (!daySeries.value.length) return null
  return daySeries.value.find((row) => row.ts.slice(11, 16) === props.selectedTime) ?? daySeries.value[0]
})

function collectPowerMagnitudes(rows, metrics) {
  const vals = []
  for (const row of rows) {
    for (const k of POWER_KEYS) {
      const v = Number(row[k])
      if (Number.isFinite(v)) vals.push(Math.abs(v))
    }
  }
  const pr = Number(metrics?.peak_reduction)
  if (Number.isFinite(pr)) vals.push(Math.abs(pr))
  return vals
}

const displayScale = computed(() => {
  const vals = collectPowerMagnitudes(daySeries.value, props.metrics)
  const maxVal = vals.length ? Math.max(...vals) : 0
  const useMW = maxVal >= POWER_MW_THRESHOLD_KW
  return {
    useMW,
    pFactor: useMW ? 0.001 : 1,
    pUnit: useMW ? 'MW' : 'kW',
    eFactor: useMW ? 0.001 : 1,
    eUnit: useMW ? 'MWh' : 'kWh',
  }
})

function fmtFixed2(n) {
  return n.toLocaleString('ko-KR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

/** SOC: DB가 0~1 비율이면 %로, 이미 0~100이면 그대로 정수 % */
function toSocPercentNumber(v) {
  if (!Number.isFinite(v)) return NaN
  if (v >= 0 && v <= 1) return v * 100
  if (v > 1 && v <= 100) return v
  return v * 100
}

function formatSocPct(value) {
  const pct = toSocPercentNumber(Number(value))
  if (!Number.isFinite(pct)) return '—'
  return `${Math.round(pct)}%`
}

function formatPowerKw(rawKw) {
  if (!Number.isFinite(Number(rawKw))) return '—'
  const v = Number(rawKw) * displayScale.value.pFactor
  return `${fmtFixed2(v)} ${displayScale.value.pUnit}`
}

function formatSignedPowerKw(rawKw) {
  if (!Number.isFinite(Number(rawKw))) return '—'
  const raw = Number(rawKw)
  const v = Math.abs(raw) * displayScale.value.pFactor
  const s = fmtFixed2(v)
  if (raw === 0) return `0.00 ${displayScale.value.pUnit}`
  return `${raw > 0 ? '+' : '-'}${s} ${displayScale.value.pUnit}`
}

function formatPriceKwh(raw) {
  if (!Number.isFinite(Number(raw))) return '—'
  return `${fmtFixed2(Number(raw))} 원/kWh`
}

function formatEnergyKwh(rawKwh) {
  if (!Number.isFinite(Number(rawKwh))) return '—'
  const v = Number(rawKwh) * displayScale.value.eFactor
  return `${fmtFixed2(v)} ${displayScale.value.eUnit}`
}

const peakDisplay = computed(() => {
  const raw = Number(props.metrics?.peak_reduction)
  const { pFactor, pUnit } = displayScale.value
  const titleDefault = '피크 감소량'
  if (!Number.isFinite(raw)) return { title: titleDefault, body: '—' }
  const mag = Math.abs(raw) * pFactor
  const str = fmtFixed2(mag)
  if (raw < 0) return { title: titleDefault, body: `${str} ${pUnit} 감소` }
  if (raw > 0) return { title: '피크 변화량', body: `${str} ${pUnit} 증가` }
  return { title: titleDefault, body: `0.00 ${pUnit}` }
})

function fmtCompareTime(d) {
  const p = (n) => String(n).padStart(2, '0')
  return `${p(d.getMonth() + 1)}/${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

function buildCompareOption(scale) {
  const values = daySeries.value
    .flatMap((row) => [row.actual, row.pred_1_step, row.pred_24_step, row.rt_result])
    .filter(Number.isFinite)
  const rawMin = values.length ? Math.min(...values) * 0.97 : undefined
  const rawMax = values.length ? Math.max(...values) * 1.03 : undefined
  const yMin = Number.isFinite(rawMin) ? Math.floor(rawMin) : undefined
  const yMax = Number.isFinite(rawMax) ? Math.ceil(rawMax) : undefined

  return {
    backgroundColor: 'transparent',
    grid: { left: 60, right: 20, top: 44, bottom: 36 },
    legend: {
      top: 8,
      left: 0,
      textStyle: { color: '#8898aa', fontSize: 11, fontFamily: 'Pretendard' },
    },
    xAxis: {
      type: 'time',
      axisLine: { lineStyle: { color: '#e9ecef' } },
      axisTick: { show: false },
      axisLabel: { color: '#8898aa', fontSize: 10 },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      min: yMin,
      max: yMax,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        fontSize: 10,
        formatter: (v) => {
          if (!Number.isFinite(v)) return ''
          const numStr = scale.useMW ? fmtFixed2(v * scale.pFactor) : `${Math.round(v)}`
          if (Number.isFinite(yMin) && Math.abs(v - yMin) < 1e-4) {
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
      formatter: (params) => {
        if (!params?.length) return ''
        const d = new Date(params[0].value[0])
        let html = `<div style="font-weight:700;margin-bottom:6px;color:#c8c8e0;">${fmtCompareTime(d)}</div>`
        for (const p of params) {
          const y = Number(p.value[1])
          if (!Number.isFinite(y)) continue
          const valStr = fmtFixed2(y * scale.pFactor)
          html += `<div style="display:flex;align-items:center;gap:6px;">
            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};"></span>
            <span style="color:#a0a0c0;">${p.seriesName}</span>
            <b style="margin-left:auto;font-size:13px;">${valStr} ${scale.pUnit}</b>
          </div>`
        }
        return html
      },
    },
    series: [
      {
        name: '실측 부하',
        type: 'line',
        data: daySeries.value.map((row) => [row.ts, row.actual]),
        symbol: 'none',
        lineStyle: { color: '#5e72e4', width: 2 },
        itemStyle: { color: '#5e72e4' },
        smooth: 0.25,
      },
      {
        name: '1시간 예측',
        type: 'line',
        data: daySeries.value.map((row) => [row.ts, row.pred_1_step]),
        symbol: 'none',
        lineStyle: { color: '#11cdef', width: 2, type: 'dashed' },
        itemStyle: { color: '#11cdef' },
        smooth: 0.25,
      },
      {
        name: '24시간 예측',
        type: 'line',
        data: daySeries.value.map((row) => [row.ts, row.pred_24_step]),
        symbol: 'none',
        lineStyle: { color: '#fb6340', width: 2, type: 'dotted' },
        itemStyle: { color: '#fb6340' },
        smooth: 0.25,
      },
      {
        name: 'ESS 적용 부하',
        type: 'line',
        data: daySeries.value.map((row) => [row.ts, row.rt_result]),
        symbol: 'none',
        lineStyle: { color: '#2dce89', width: 2 },
        itemStyle: { color: '#2dce89' },
        smooth: 0.25,
      },
    ],
  }
}

function buildOption(scale) {
  const pAxisFormatter = (v) => {
    if (!Number.isFinite(v)) return ''
    if (scale.useMW) return fmtFixed2(v * scale.pFactor)
    return `${Math.round(v)}`
  }

  return {
    backgroundColor: 'transparent',
    grid: { left: 52, right: 52, top: 40, bottom: 34 },
    legend: {
      top: 0,
      textStyle: { color: '#8898aa', fontSize: 11, fontFamily: 'Pretendard' },
      selected: { '전력 가격': false },
    },
    xAxis: {
      type: 'time',
      axisLine: { lineStyle: { color: '#e9ecef' } },
      axisTick: { show: false },
      axisLabel: { color: '#8898aa', fontSize: 10 },
      splitLine: { show: false },
    },
    yAxis: [
      {
        type: 'value',
        name: scale.pUnit,
        nameTextStyle: { color: '#8898aa', fontSize: 10 },
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: {
          color: '#8898aa',
          fontSize: 10,
          formatter: pAxisFormatter,
        },
        splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } },
      },
      {
        type: 'value',
        name: 'SOC/가격',
        nameTextStyle: { color: '#8898aa', fontSize: 10 },
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: '#8898aa', fontSize: 10 },
        splitLine: { show: false },
      },
    ],
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#1a1a2e',
      borderColor: 'transparent',
      borderRadius: 10,
      padding: [10, 14],
      textStyle: { color: '#fff', fontSize: 12, fontFamily: 'Pretendard' },
      axisPointer: { lineStyle: { color: '#dee2e6', type: 'dashed' } },
      formatter: (params) => {
        if (!params?.length) return ''
        const d = new Date(params[0].value[0])
        let html = `<div style="font-weight:700;margin-bottom:6px;color:#c8c8e0;">${fmtCompareTime(d)}</div>`
        for (const p of params) {
          const y = Number(p.value[1])
          let rowHtml = ''
          if (p.seriesName === '배터리 SOC') {
            const pct = toSocPercentNumber(y)
            const label = Number.isFinite(pct) ? `${Math.round(pct)}%` : '—'
            rowHtml = `<b style="margin-left:auto;font-size:13px;">${label}</b>`
          } else if (p.seriesName === '전력 가격') {
            const label = Number.isFinite(y) ? `${fmtFixed2(y)} 원/kWh` : '—'
            rowHtml = `<b style="margin-left:auto;font-size:13px;">${label}</b>`
          } else if (Number.isFinite(y)) {
            rowHtml = `<b style="margin-left:auto;font-size:13px;">${fmtFixed2(y * scale.pFactor)} ${scale.pUnit}</b>`
          } else {
            rowHtml = '<b style="margin-left:auto;">—</b>'
          }
          html += `<div style="display:flex;align-items:center;gap:6px;">
            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};"></span>
            <span style="color:#a0a0c0;">${p.seriesName}</span>
            ${rowHtml}
          </div>`
        }
        return html
      },
    },
    series: [
      {
        name: '충전 전력',
        type: 'bar',
        yAxisIndex: 0,
        data: daySeries.value.map((row) => [row.ts, row.charge_kw]),
        itemStyle: { color: '#11cdef' },
      },
      {
        name: '방전 전력',
        type: 'bar',
        yAxisIndex: 0,
        data: daySeries.value.map((row) => [row.ts, row.discharge_kw]),
        itemStyle: { color: '#fb6340' },
      },
      {
        name: '배터리 SOC',
        type: 'line',
        yAxisIndex: 1,
        data: daySeries.value.map((row) => [row.ts, row.soc]),
        symbol: 'none',
        lineStyle: { color: '#2dce89', width: 2 },
        itemStyle: { color: '#2dce89' },
      },
      {
        name: '전력 가격',
        type: 'line',
        yAxisIndex: 1,
        data: daySeries.value.map((row) => [row.ts, row.price]),
        symbol: 'none',
        lineStyle: { color: '#5e72e4', width: 2, type: 'dashed' },
        itemStyle: { color: '#5e72e4' },
      },
    ],
  }
}

async function draw() {
  await nextTick()
  const scale = displayScale.value
  if (compareChartEl.value) {
    if (!compareChart) compareChart = echarts.init(compareChartEl.value)
    compareChart.setOption(buildCompareOption(scale), true)
  }
  if (!essChartEl.value) return
  if (!essChart) essChart = echarts.init(essChartEl.value)
  essChart.setOption(buildOption(scale), true)
}

onMounted(() => setTimeout(draw, 100))
onUnmounted(() => {
  compareChart?.dispose()
  essChart?.dispose()
})
watch([() => props.series, () => props.selectedDate, () => props.metrics], draw, { deep: true })
</script>

<style scoped>
/* 차트 : KPI = 5 : 1 (기존 2:1 대비 우측 카드 폭 약 절반) */
.ess-split-row {
  display: grid;
  grid-template-columns: 5fr 1fr;
  gap: 14px;
  align-items: stretch;
}

.ess-chart-panel {
  min-width: 0;
}

.ess-kpi-column {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}

@media (max-width: 900px) {
  .ess-split-row {
    grid-template-columns: 1fr;
  }
}

.ess-stat-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  font-size: 12px;
  line-height: 1.4;
}

.ess-stat-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 14px;
  padding: 2px 0;
}

.ess-stat-label {
  color: var(--text2, #8898aa);
  flex: 0 1 auto;
  min-width: 0;
}

.ess-stat-label::after {
  content: ' :';
}

.ess-stat-value {
  font-weight: 600;
  color: var(--text1, #32325d);
  text-align: right;
  white-space: nowrap;
  flex-shrink: 0;
  font-variant-numeric: tabular-nums;
}
</style>