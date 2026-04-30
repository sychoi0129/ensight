<template>
  <div>
    <div style="display:flex; align-items:center; gap:10px; margin-bottom:16px;">
      <span style="font-size:12px; color:var(--text3); font-weight:500;">기상 변수</span>
      <select class="content-select" v-model="selectedLabel">
        <option v-for="l in metricLabels" :key="l">{{ l }}</option>
      </select>
    </div>

    <div class="panel" style="margin-bottom:1px;">
      <div class="section-label">{{ selectedLabel }} + 전력 사용량</div>
      <div ref="dualEl" style="width:100%; height:300px;"></div>
    </div>

    <div class="panel">
      <div class="section-label">{{ selectedLabel }} ↔ 전력 상관관계</div>
      <div ref="scatterEl" style="width:100%; height:260px;"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { WEATHER_METRIC_MAP } from '@/constants/settings'
import * as echarts from 'echarts'

const props = defineProps({
  weatherView: { type: Array, default: () => [] },
  histDf:      { type: Array, default: () => [] },
})

const metricLabels  = Object.keys(WEATHER_METRIC_MAP)
const selectedLabel = ref(metricLabels[0])
const metric        = computed(() => WEATHER_METRIC_MAP[selectedLabel.value])
const dualEl        = ref(null)
const scatterEl     = ref(null)
let dualChart    = null
let scatterChart = null

const TOOLTIP_STYLE = {
  backgroundColor: '#1a1a2e',
  borderColor: 'transparent',
  borderRadius: 10,
  padding: [10, 14],
  textStyle: { color: '#fff', fontSize: 12, fontFamily: 'Pretendard' },
}

async function draw() {
  await nextTick()
  if (!dualEl.value || !scatterEl.value) return

  // ── 이중 Y축 ─────────────────────────────────────────
  if (!dualChart) dualChart = echarts.init(dualEl.value)

  dualChart.setOption({
    backgroundColor: 'transparent',
    grid: { left: 52, right: 52, top: 64, bottom: 36 },
    legend: {
      top: 6, left: 0, itemWidth: 24, itemHeight: 3,
      textStyle: { color: '#8898aa', fontSize: 11, fontFamily: 'Pretendard' },
      data: [selectedLabel.value, '전력 사용량'],
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
    yAxis: [
      {
        type: 'value', name: selectedLabel.value,
        nameTextStyle: { color: '#8898aa', fontSize: 10, fontFamily: 'Pretendard' },
        axisLine: { show: false }, axisTick: { show: false },
        axisLabel: { color: '#8898aa', fontSize: 10, fontFamily: 'Pretendard' },
        splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } },
      },
      {
        type: 'value', name: 'W',
        nameTextStyle: { color: '#8898aa', fontSize: 10, fontFamily: 'Pretendard' },
        axisLine: { show: false }, axisTick: { show: false },
        axisLabel: { color: '#8898aa', fontSize: 10, fontFamily: 'Pretendard' },
        splitLine: { show: false },
      },
    ],
    tooltip: {
      trigger: 'axis',
      ...TOOLTIP_STYLE,
      axisPointer: { lineStyle: { color: '#dee2e6', type: 'dashed' } },
      formatter: params => {
        if (!params.length) return ''
        const d = new Date(params[0].value[0])
        const p = n => String(n).padStart(2,'0')
        const timeStr = `${p(d.getMonth()+1)}/${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
        return `<div style="font-weight:700;margin-bottom:6px;color:#c8c8e0;">${timeStr}</div>` +
          params.map(p => `<div style="display:flex;align-items:center;gap:6px;margin:2px 0;">
            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};"></span>
            <span style="color:#a0a0c0;">${p.seriesName}</span>
            <b style="margin-left:auto;">${p.value[1].toFixed(1)}</b>
          </div>`).join('')
      },
    },
    series: [
      {
        name: selectedLabel.value,
        type: 'line', yAxisIndex: 0,
        data: props.weatherView.map(r => [r.timestamp, r[metric.value]]),
        symbol: 'none',
        lineStyle: { color: '#2dce89', width: 2 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(45,206,137,0.15)' },
            { offset: 1, color: 'rgba(45,206,137,0.01)' },
          ]),
        },
        smooth: 0.3,
      },
      {
        name: '전력 사용량',
        type: 'line', yAxisIndex: 1,
        data: props.histDf.map(r => [r.timestamp, r.power_usage]),
        symbol: 'none',
        lineStyle: { color: '#5e72e4', width: 1.5, type: 'dashed' },
        smooth: 0.3,
        opacity: 0.7,
      },
    ],
  }, true)

  // ── 산점도 + 추세선 ──────────────────────────────────
  const merged = props.histDf.map(h => {
    const w = props.weatherView.find(r => r.timestamp.getTime() === h.timestamp.getTime())
    return w ? [w[metric.value], h.power_usage] : null
  }).filter(Boolean)

  if (merged.length < 2) return
  if (!scatterChart) scatterChart = echarts.init(scatterEl.value)

  const xv = merged.map(r => r[0]), yv = merged.map(r => r[1])
  const n = xv.length
  const sx = xv.reduce((a,b) => a+b, 0), sy = yv.reduce((a,b) => a+b, 0)
  const sxy = xv.reduce((s,x,i) => s+x*yv[i], 0), sx2 = xv.reduce((s,x) => s+x*x, 0)
  const m = (n*sxy - sx*sy) / (n*sx2 - sx*sx)
  const b = (sy - m*sx) / n
  const xMin = Math.min(...xv), xMax = Math.max(...xv)

  scatterChart.setOption({
    backgroundColor: 'transparent',
    grid: { left: 52, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: 'value', name: selectedLabel.value,
      nameLocation: 'middle', nameGap: 28,
      nameTextStyle: { color: '#8898aa', fontSize: 10, fontFamily: 'Pretendard' },
      axisLine: { lineStyle: { color: '#e9ecef' } },
      axisTick: { show: false },
      axisLabel: { color: '#8898aa', fontSize: 10, fontFamily: 'Pretendard' },
      splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } },
    },
    yAxis: {
      type: 'value', name: 'W',
      nameTextStyle: { color: '#8898aa', fontSize: 10, fontFamily: 'Pretendard' },
      axisLine: { show: false }, axisTick: { show: false },
      axisLabel: { color: '#8898aa', fontSize: 10, fontFamily: 'Pretendard' },
      splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } },
    },
    tooltip: {
      trigger: 'item',
      ...TOOLTIP_STYLE,
      formatter: p => `<b style="font-size:13px;">${p.value[1].toFixed(1)}</b> W<br>
                       <span style="color:#a0a0c0;">${selectedLabel.value}: ${p.value[0].toFixed(1)}</span>`,
    },
    series: [
      {
        name: '데이터',
        type: 'scatter',
        data: merged,
        symbolSize: 5,
        itemStyle: { color: '#5e72e4', opacity: 0.3 },
      },
      {
        name: '추세선',
        type: 'line',
        data: [[xMin, m*xMin+b], [xMax, m*xMax+b]],
        symbol: 'none',
        lineStyle: { color: '#5e72e4', width: 2, type: 'dashed' },
        smooth: false,
        silent: true,
      },
    ],
  }, true)
}

onMounted(() => setTimeout(draw, 100))
onUnmounted(() => { dualChart?.dispose(); scatterChart?.dispose() })
watch([() => props.weatherView, () => props.histDf, selectedLabel], draw)
</script>
