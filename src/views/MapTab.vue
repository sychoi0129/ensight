<template>
  <div class="map-tab-root">
    <div class="row map-tab-row" style="gap:14px;">
      <div class="panel panel-map" style="flex:1.65; min-width:0;">
        <div class="section-label section-label-map">지역별 평균 전력 수요 · 기준 일 하루 평균</div>
        <div
          ref="mapEl"
          class="map-plot-wrap"
          :style="{ height: MAP_PLOT_H + 'px' }"
        ></div>
      </div>
      <div class="panel" style="flex:1.35; min-width:0;">
        <div class="section-label">지역 랭킹 · 기준 일 하루 평균</div>
        <div ref="barEl" class="bar-chart-wrap" :style="{ height: BAR_PLOT_H + 'px' }"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  mapDf: { type: Array, default: () => [] },
  powerUnit: { type: String, default: 'W' },
})
const mapEl = ref(null)
const barEl = ref(null)
let barChart = null

/** 지도만 크게: Plotly·지도 래퍼 높이 */
const MAP_PLOT_H = 500
/** 랭킹 막대 영역은 기존 느낌 유지 */
const BAR_PLOT_H = 480

// 지도는 Plotly 유지 (scattergeo는 ECharts에서 별도 설정 필요)
async function drawMap() {
  await nextTick()
  const P = window.Plotly
  if (!P || !mapEl.value || !props.mapDf.length) return

  await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))

  const loads = props.mapDf.map(r => Number(r.avg_load) || 0)
  const lo = Math.min(...loads)
  const hi = Math.max(...loads)
  const span = hi - lo || 1
  const sizeMin = 10
  const sizeMax = 48
  const markerSizes = loads.map(v => {
    if (span <= 0) return (sizeMin + sizeMax) / 2
    const t = (v - lo) / span
    return sizeMin + t * (sizeMax - sizeMin)
  })

  const lats = props.mapDf.map(r => r.lat)
  const lons = props.mapDf.map(r => r.lng)
  const minLat = Math.min(...lats)
  const maxLat = Math.max(...lats)
  const minLon = Math.min(...lons)
  const maxLon = Math.max(...lons)
  /**
   * 한반도+제주가 한 프레임에 들어오도록 남·북·서·동 경계
   * (제주 ~33.5° 남쪽 바다 여유, 동쪽은 과도한 땅끝 확장을 줄여 일본 쪽 빈 공간 완화)
   */
  const fitMinLat = Math.min(minLat, 33.05) - 0.05
  const fitMaxLat = maxLat + 0.12
  const fitMinLon = Math.min(minLon, 125.0) - 0.22
  const fitMaxLon = Math.max(maxLon, 131.35) + 0.06
  const geoCenter = {
    lat: (fitMinLat + fitMaxLat) / 2 - 0.14,
    lon: (fitMinLon + fitMaxLon) / 2 - 0.22,
  }
  const latSpanFit = Math.max(fitMaxLat - fitMinLat, 0.85)
  const lonSpanFit = Math.max(fitMaxLon - fitMinLon, 0.85)
  /** projection.scale — geo 박스 안에서 육지가 더 크게 보이도록(과하면 제주 잘림) */
  const geoScale = Math.min(
    18,
    Math.max(
      10,
      (13.8 - latSpanFit * 1.08 - lonSpanFit * 0.14) * 1.02,
    ),
  )

  const trace = [{
    type: 'scattergeo',
    lat: lats,
    lon: lons,
    text: props.mapDf.map(r => r.region),
    mode: 'markers+text',
    textposition: 'middle center',
    textfont: {
      size: 8,
      color: '#2c3e50',
      family: 'Pretendard, sans-serif',
    },
    marker: {
      size: markerSizes,
      sizemode: 'diameter',
      color: loads,
      colorscale: [[0,'#e8ebfc'],[0.4,'#5865f2'],[1,'#c0b0ff']],
      showscale: true,
      colorbar: {
        title: { text: props.powerUnit, font: { color: '#8898aa', size: 10 } },
        thickness: 10,
        len: 0.72,
        x: 1.02,
        xanchor: 'left',
        xref: 'paper',
        y: 0.5,
        yref: 'paper',
        yanchor: 'middle',
        tickfont: { color: '#8898aa', size: 9 },
      },
      line: { color: '#7a8a9a', width: 0.75 },
    },
    hoverinfo: 'skip',
  }]

  const layout = {
    autosize: true,
    paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: '#ffffff',
    font: { family: 'Pretendard', color: '#8898aa', size: 10 },
    margin: { l: 0, r: 44, t: 0, b: 0 },
    height: MAP_PLOT_H,
    geo: {
      /** figure 안에서 지도 subplot이 차지하는 비율 — 좌우를 넓게(옛 0.12~0.85는 왼쪽이 너무 비었음) */
      domain: { x: [0.02, 1], y: [0, 1] },
      scope: 'asia',
      resolution: 50,
      center: geoCenter,
      projection: { scale: geoScale },
      showland: true,
      landcolor: '#e6e9ef',
      showcoastlines: true,
      coastlinecolor: '#9aa5b4',
      showframe: false,
      bgcolor: 'rgba(0,0,0,0)',
      showocean: true,
      oceancolor: '#cfdcee',
    },
    hoverlabel: { bgcolor: '#1a1a2e', bordercolor: 'transparent', font: { color: '#fff', size: 12 } },
  }

  const el = mapEl.value
  try {
    P.purge(el)
    await P.newPlot(el, trace, layout, { responsive: true })
  } catch (e) {
    console.warn('Plotly map:', e)
  }
  try {
    P.Plots.resize(el)
  } catch { /* ignore */ }
}

// 랭킹 바 차트는 ECharts
async function drawBar() {
  await nextTick()
  if (!barEl.value || !props.mapDf.length) return
  if (!barChart) barChart = echarts.init(barEl.value)

  /** 평균 부하 높은 순 → 위쪽이 1위 */
  const sorted = [...props.mapDf].sort((a, b) => b.avg_load - a.avg_load)
  /** MW: 최대가 1000 이하면 축 0~1000 고정, 초과 시 올림(CSV상 일부 일·지역은 1000↑ 있음) */
  const maxVal = Math.max(...sorted.map(r => Number(r.avg_load) || 0), 0)
  const maxAxis = maxVal > 1000 ? Math.ceil(maxVal) : 1000

  barChart.setOption({
    backgroundColor: 'transparent',
    grid: { left: 10, right: 70, top: 8, bottom: 8, containLabel: true },
    xAxis: {
      type: 'value',
      min: 0,
      max: maxAxis,
      axisLine: { show: false }, axisTick: { show: false },
      axisLabel: {
        color: '#8898aa',
        fontSize: 10,
        fontFamily: 'Pretendard',
        formatter: v => String(Math.round(Number(v))),
      },
      splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } },
    },
    yAxis: {
      type: 'category',
      inverse: true,
      data: sorted.map(r => r.region),
      axisLine: { show: false }, axisTick: { show: false },
      axisLabel: { color: '#4a5568', fontSize: 11, fontFamily: 'Pretendard' },
    },
    tooltip: {
      trigger: 'item',
      backgroundColor: '#1a1a2e',
      borderColor: 'transparent',
      borderRadius: 8,
      padding: [8, 12],
      textStyle: { color: '#fff', fontSize: 12, fontFamily: 'Pretendard' },
      formatter: p =>
        `<b>${p.name}</b><br><span style="color:#c0b0ff;">${Math.round(Number(p.value))} ${props.powerUnit}</span>`,
    },
    series: [{
      type: 'bar',
      data: sorted.map(r => ({
        value: r.avg_load,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#8b9ef0' },
            { offset: 1, color: '#5e72e4' },
          ]),
          borderRadius: [0, 4, 4, 0],
        },
      })),
      barMaxWidth: 22,
      label: {
        show: true,
        position: 'right',
        color: '#8898aa',
        fontSize: 10,
        fontFamily: 'JetBrains Mono',
        formatter: p => String(Math.round(Number(p.value))),
      },
    }],
  }, true)
  barChart.resize()
}

async function draw() {
  await drawMap()
  await drawBar()
}

onMounted(() => setTimeout(draw, 150))
onUnmounted(() => barChart?.dispose())
watch(() => [props.mapDf, props.powerUnit], draw)
</script>

<style scoped>
.map-tab-root {
  width: 100%;
}
.map-tab-row {
  align-items: flex-start;
}
.panel-map {
  padding: 12px 14px 14px;
  min-height: 0;
}
.section-label-map {
  /* 오른쪽 '지역 랭킹'과 동일 — main.css .section-label 과 맞춤 */
  margin-bottom: 12px;
  font-size: 13px;
  font-weight: 700;
  line-height: inherit;
  letter-spacing: -0.01em;
  color: var(--text2);
}
.section-label-map::after {
  display: none;
}
.map-plot-wrap,
.bar-chart-wrap {
  width: 100%;
  min-height: 0;
}
</style>
