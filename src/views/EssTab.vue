<template>
  <div style="display:flex; flex-direction:column; gap:14px;">
    <div class="panel" style="display:flex; flex-direction:column;">
      <div class="section-label">실측/예측/ESS 비교</div>
      <div ref="compareChartEl" style="width:100%; min-height:340px;"></div>
    </div>

    <div class="row" style="gap:14px; align-items:stretch;">
      <div class="col-2 panel" style="display:flex; flex-direction:column;">
        <div class="section-label">ESS 운전 상태 (충전/방전/SOC/가격)</div>
        <div ref="essChartEl" style="width:100%; flex:1; min-height:340px;"></div>
      </div>

      <div class="col-1" style="display:flex; flex-direction:column; gap:12px;">
        <div class="panel">
          <div class="section-label">선택 시간 ESS 상태</div>
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; font-size:12px;">
            <div>충전 전력: <b>{{ fmt(selectedPoint?.charge_kw) }}</b></div>
            <div>방전 전력: <b>{{ fmt(selectedPoint?.discharge_kw) }}</b></div>
            <div>ESS 조정량: <b>{{ fmt(selectedPoint?.ess_adjustment_kw) }}</b></div>
            <div>SOC: <b>{{ fmt(selectedPoint?.soc) }}</b></div>
            <div>전력가격: <b>{{ fmt(selectedPoint?.price) }}</b></div>
            <div>ESS 적용 후 부하: <b>{{ fmt(selectedPoint?.rt_result) }}</b></div>
          </div>
        </div>

        <div class="panel">
          <div class="section-label">ESS 요약 지표</div>
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; font-size:12px;">
            <div>총 충전량: <b>{{ fmt(metrics.total_charge_kwh) }}</b></div>
            <div>총 방전량: <b>{{ fmt(metrics.total_discharge_kwh) }}</b></div>
            <div>평균 SOC: <b>{{ fmt(metrics.avg_soc) }}</b></div>
            <div>피크 감소량: <b>{{ fmt(metrics.peak_reduction) }}</b></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

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

function fmt(value) {
  if (!Number.isFinite(value)) return '—'
  return Number(value).toFixed(2)
}

function buildCompareOption() {
  const values = daySeries.value
    .flatMap((row) => [row.actual, row.pred_1_step, row.pred_24_step, row.rt_result])
    .filter(Number.isFinite)
  const rawMin = values.length ? Math.min(...values) * 0.97 : undefined
  const rawMax = values.length ? Math.max(...values) * 1.03 : undefined
  const yMin = Number.isFinite(rawMin) ? Math.floor(rawMin) : undefined
  const yMax = Number.isFinite(rawMax) ? Math.ceil(rawMax) : undefined

  return {
    backgroundColor: 'transparent',
    grid: { left: 52, right: 20, top: 44, bottom: 36 },
    legend: {
      top: 6,
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
        color: '#8898aa',
        fontSize: 10,
        formatter: (v) => `${Math.round(v)}`,
      },
      splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } },
    },
    tooltip: { trigger: 'axis' },
    series: [
      {
        name: '실측 부하',
        type: 'line',
        data: daySeries.value.map((row) => [row.ts, row.actual]),
        symbol: 'none',
        lineStyle: { color: '#5e72e4', width: 2 },
        smooth: 0.25,
      },
      {
        name: '1시간 예측',
        type: 'line',
        data: daySeries.value.map((row) => [row.ts, row.pred_1_step]),
        symbol: 'none',
        lineStyle: { color: '#11cdef', width: 2, type: 'dashed' },
        smooth: 0.25,
      },
      {
        name: '24시간 예측',
        type: 'line',
        data: daySeries.value.map((row) => [row.ts, row.pred_24_step]),
        symbol: 'none',
        lineStyle: { color: '#fb6340', width: 2, type: 'dotted' },
        smooth: 0.25,
      },
      {
        name: 'ESS 적용 부하',
        type: 'line',
        data: daySeries.value.map((row) => [row.ts, row.rt_result]),
        symbol: 'none',
        lineStyle: { color: '#2dce89', width: 2 },
        smooth: 0.25,
      },
    ],
  }
}

function buildOption() {
  return {
    backgroundColor: 'transparent',
    grid: { left: 52, right: 52, top: 40, bottom: 34 },
    legend: {
      top: 0,
      textStyle: { color: '#8898aa', fontSize: 11, fontFamily: 'Pretendard' },
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
        name: 'kW',
        nameTextStyle: { color: '#8898aa', fontSize: 10 },
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: '#8898aa', fontSize: 10 },
        splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } },
      },
      {
        type: 'value',
        name: 'SOC/Price',
        nameTextStyle: { color: '#8898aa', fontSize: 10 },
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: '#8898aa', fontSize: 10 },
        splitLine: { show: false },
      },
    ],
    tooltip: { trigger: 'axis' },
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
      },
      {
        name: '전력 가격',
        type: 'line',
        yAxisIndex: 1,
        data: daySeries.value.map((row) => [row.ts, row.price]),
        symbol: 'none',
        lineStyle: { color: '#5e72e4', width: 2, type: 'dashed' },
      },
    ],
  }
}

async function draw() {
  await nextTick()
  if (compareChartEl.value) {
    if (!compareChart) compareChart = echarts.init(compareChartEl.value)
    compareChart.setOption(buildCompareOption(), true)
  }
  if (!essChartEl.value) return
  if (!essChart) essChart = echarts.init(essChartEl.value)
  essChart.setOption(buildOption(), true)
}

onMounted(() => setTimeout(draw, 100))
onUnmounted(() => {
  compareChart?.dispose()
  essChart?.dispose()
})
watch(() => props.series, draw, { deep: true })
watch(() => props.selectedDate, draw)
</script>

