<template>
  <div>
    <!-- 토글 -->
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
      <!-- 차트 패널 -->
      <div class="col-2 panel" style="display:flex; flex-direction:column;">
        <div class="section-label">과거 사용량 + 예측</div>
        <div ref="chartEl" style="width:100%; flex:1; min-height:340px;"></div>
      </div>

      <!-- 오른쪽 패널 -->
      <div class="col-1" style="display:flex; flex-direction:column; gap:12px;">
        <div class="panel" style="flex:1; display:flex; flex-direction:column;">
          <div class="section-label">향후 {{ horizon }}H 평균 예측</div>
          <div ref="gaugeEl" style="width:100%; flex:1; min-height:180px;"></div>
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:10px;">
            <div class="mini-stat">
              <div class="mini-stat-label">피크</div>
              <div class="mini-stat-value" style="color:#f87171;">{{ predMax.toFixed(1) }}</div>
            </div>
            <div class="mini-stat">
              <div class="mini-stat-label">최저</div>
              <div class="mini-stat-value" style="color:#4ade80;">{{ predMin.toFixed(1) }}</div>
            </div>
          </div>
        </div>
        <div class="panel" style="flex:0 0 auto;">
          <div class="section-label">예측 12step 분포</div>
          <div ref="barEl" style="width:100%; height:120px;"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'

const props = defineProps({
  histDf:     { type: Array, default: () => [] },
  forecastDf: { type: Array, default: () => [] },
  newsView:   { type: Array, default: () => [] },
  horizon:    { type: Number, default: 12 },
})

const showCi  = ref(true)
const showNews = ref(true)
const chartEl = ref(null)
const gaugeEl = ref(null)
const barEl   = ref(null)

const predMean = computed(() =>
  props.forecastDf.length
    ? props.forecastDf.reduce((s, r) => s + r.prediction, 0) / props.forecastDf.length
    : 0
)
const predMax = computed(() => props.forecastDf.length ? Math.max(...props.forecastDf.map(r => r.prediction)) : 0)
const predMin = computed(() => props.forecastDf.length ? Math.min(...props.forecastDf.map(r => r.prediction)) : 0)

const BASE = {
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor: '#0a0a0f',
  font: { family: 'Pretendard', color: '#9090b8', size: 10 },
  margin: { l: 48, r: 16, t: 12, b: 36 },
}
const AXIS = { gridcolor: '#1e1e2e', linecolor: '#1e1e2e', zerolinecolor: '#1e1e2e', tickfont: { color: '#9090b8', size: 10 } }
const HOVER = { bgcolor: '#141420', bordercolor: '#2a2a3e', font: { color: '#f0f0f5', size: 11 } }

async function draw() {
  await nextTick()
  const P = window.Plotly
  if (!P || !chartEl.value) return

  const toISO = d => d instanceof Date ? d.toISOString() : String(d)

  const traces = [
    {
      x: props.histDf.map(r => toISO(r.timestamp)),
      y: props.histDf.map(r => r.power_usage),
      mode: 'lines', name: '과거 사용량',
      line: { color: '#5865f2', width: 1.5 },
      hovertemplate: '%{x|%m/%d %H:%M}  %{y:.1f}<extra></extra>',
    },
    {
      x: props.forecastDf.map(r => toISO(r.timestamp)),
      y: props.forecastDf.map(r => r.prediction),
      mode: 'lines', name: '예측값',
      line: { color: '#c0b0ff', width: 2, dash: 'dot' },
      hovertemplate: '%{x|%m/%d %H:%M}  %{y:.1f}<extra></extra>',
    },
  ]

  if (showCi.value && props.forecastDf.length) {
    const fwd = props.forecastDf, rev = [...fwd].reverse()
    traces.push({
      x: [...fwd.map(r => toISO(r.timestamp)), ...rev.map(r => toISO(r.timestamp))],
      y: [...fwd.map(r => r.upper), ...rev.map(r => r.lower)],
      fill: 'toself', fillcolor: 'rgba(192,176,255,0.06)',
      line: { width: 0 }, name: '신뢰구간', hoverinfo: 'skip',
    })
  }

  if (showNews.value && props.newsView.length) {
    const maxY = Math.max(...props.histDf.map(r => r.power_usage)) * 1.04
    traces.push({
      x: props.newsView.map(r => toISO(r.timestamp)),
      y: props.newsView.map(() => maxY),
      mode: 'markers', name: '뉴스',
      marker: { symbol: 'diamond', size: 8, color: '#f87171', line: { color: '#f8717155', width: 6 } },
      hovertemplate: '%{text}<extra></extra>',
      text: props.newsView.map(r => r.headline),
    })
  }

  P.react(chartEl.value, traces, {
    ...BASE, height: 340,
    xaxis: AXIS,
    yaxis: { ...AXIS, title: { text: 'MW', font: { color: '#9090b8', size: 10 } } },
    legend: { bgcolor: 'rgba(0,0,0,0)', font: { size: 10, color: '#9090b8' }, x: 0, y: 1.05, orientation: 'h' },
    hoverlabel: HOVER,
  })

  // 게이지
  if (gaugeEl.value) {
    P.react(gaugeEl.value, [{
      type: 'indicator', mode: 'gauge+number',
      value: predMean.value,
      number: { font: { color: '#c0b0ff', size: 32, family: 'JetBrains Mono' }, suffix: '' },
      gauge: {
        axis: { range: [predMin.value * 0.9, predMax.value * 1.1], tickcolor: '#2a2a3e', tickfont: { color: '#9090b8', size: 9 } },
        bar: { color: '#5865f2', thickness: 0.5 },
        bgcolor: '#0a0a0f', bordercolor: '#1e1e2e', borderwidth: 1,
        steps: [
          { range: [predMin.value * 0.9, predMean.value], color: '#14141e' },
          { range: [predMean.value, predMax.value * 1.1], color: '#0f0f18' },
        ],
        threshold: { line: { color: '#f87171', width: 2 }, thickness: 0.8, value: predMax.value },
      },
    }], { ...BASE, height: 200, margin: { l: 20, r: 20, t: 10, b: 10 } })
  }

  // 예측 바
  if (barEl.value && props.forecastDf.length) {
    P.react(barEl.value, [{
      x: props.forecastDf.map((_, i) => `+${i+1}h`),
      y: props.forecastDf.map(r => Number(r.prediction)),
      type: 'bar',
      marker: {
        color: props.forecastDf.map(r => r.prediction),
        colorscale: [[0, '#14142a'], [1, '#5865f2']],
        opacity: 0.85,
      },
      hovertemplate: '%{x}: %{y:.1f}<extra></extra>',
    }], {
      ...BASE, height: 120,
      margin: { l: 36, r: 8, t: 8, b: 28 },
      xaxis: { ...AXIS, tickfont: { color: '#9090b8', size: 9 } },
      yaxis: { ...AXIS, tickfont: { color: '#9090b8', size: 9 } },
      hoverlabel: HOVER,
    })
  }
}

onMounted(() => {
  const t = setInterval(() => { if (window.Plotly) { clearInterval(t); draw() } }, 100)
})
watch([() => props.histDf, () => props.forecastDf, () => props.newsView, showCi, showNews], draw)
</script>
